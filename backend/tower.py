"""The controller: reads the rooms, takes squawks, and speaks for Detente in chat."""

import asyncio
import logging
import os
import re
from typing import Any

import httpx

from backend.airspace import FACES, Airspace
from backend.detector import Collision, Report, check_code, check_plan, check_violations
from backend.plans import PlanError, parse_landed, parse_plan
from backend.switch import Event, RoomLink, Switch, SwitchError

log = logging.getLogger("detente.tower")

AGENT_NAME = os.environ.get("DETENTE_AGENT_NAME", "detente")
TOWER_ROOM = "tower"
ROLE = "tower"
OWNER_COLORS = ("lay", "a", "b", "c", "d", "e", "f", "g")  # sprite palettes, reused in order
DECISION = re.compile(r"(?:@\S+\s+)?([ab])\.?", re.IGNORECASE)
GROUND_STOP = re.compile(rf"@{AGENT_NAME}\b.*\bground stop\b", re.IGNORECASE)
RESUME = re.compile(rf"@{AGENT_NAME}\b.*\bresume\b", re.IGNORECASE)
LAND = re.compile(rf"@{AGENT_NAME}\b.*\bland\s+(\S+)", re.IGNORECASE)
FAILURES = (SwitchError, httpx.HTTPError)
RETRY_SECONDS = 5
BOARD = "Airspace"


class Tower:
    def __init__(
        self, airspace: Airspace, switch: Switch, room_id: str, link: type[RoomLink] = RoomLink
    ) -> None:
        self.airspace = airspace
        self.switch = switch
        self._link = link
        self.room = link(switch, room_id, self.on_tower_message)
        self.conflict_rooms: dict[str, RoomLink] = {}
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        self.room.start()
        for conflict in self.airspace.conflicts("open", "decided"):
            self._join_conflict(conflict["room_id"])
        while True:
            try:
                await self._prepare_room()
                return
            except FAILURES:
                log.exception("Couldn't prepare the tower room, retrying")
                await asyncio.sleep(RETRY_SECONDS)

    async def _prepare_room(self) -> None:
        roles = await self.room.call("list_roles")
        if not any(role["name"] == ROLE for role in roles):
            await self.room.call(
                "define_role", name=ROLE, instructions="The room's only controller", exclusive=True
            )
        await self.room.call("assume_role", role=ROLE)
        await self._catch_up()
        await self._update_board()

    def _join_conflict(self, room_id: str) -> RoomLink:
        link = self._link(self.switch, room_id, self.on_conflict_message)
        link.start()
        self.conflict_rooms[room_id] = link
        return link

    async def _catch_up(self) -> None:
        """Handle anything said while Detente was down. A first start acts on nothing old."""
        first_start = not self.airspace.get("started")
        context = await self.room.call("read_context", limit=50)
        for thread in context["threads"]:
            for entry in [thread["root"], *thread["replies"]]:
                if entry["kind"] != "message":
                    continue
                if first_start:
                    self.airspace.mark_seen(entry["id"])
                else:
                    await self._handle_tower(entry["sender_name"], entry["body"], entry["id"])
        self.airspace.put("started", True)

    async def _say(
        self, link: RoomLink, room: str, tag: str, text: str, to: tuple[str, ...] = ()
    ) -> None:
        body = f"{FACES[tag]} {tag} {text}"
        if to:
            await link.call("send_targeted_message", body=body, target_names=list(to))
        else:
            await link.call("post_message", body=body)
        self.airspace.record(room, "Detente", text, tag)

    async def _is_person(self, link: RoomLink, name: str) -> bool:
        participants = await link.call("list_participants")
        return any(p["name"] == name and p["type"] != "agent" for p in participants)

    # Tower room

    async def on_tower_message(self, event: Event) -> None:
        payload = event["payload"]
        await self._handle_tower(payload["sender_name"], payload["body"], payload["message_id"])

    async def _handle_tower(self, sender: str, body: str, message_id: str) -> None:
        if sender == AGENT_NAME:
            return
        try:
            plan = parse_plan(body)
        except PlanError as error:
            if self.airspace.record(TOWER_ROOM, sender, body, None, message_id):
                await self._reply(sender, str(error))
            return

        landed = parse_landed(body)
        tag = "FLIGHT PLAN" if plan else "LANDED" if landed else None
        if not self.airspace.record(TOWER_ROOM, sender, body, tag, message_id):
            return

        async with self._lock:
            if plan:
                await self._clear(sender, plan)
            elif landed:
                self.airspace.land(sender)
                await self._sync_conflicts(
                    check_code(self.airspace.reports()),
                    f"{sender} landed without a fix, so check this before merging",
                )
                await self._update_board()
            elif GROUND_STOP.search(body):
                await self._ground_stop(sender, True)
            elif RESUME.search(body):
                await self._ground_stop(sender, False)
            elif command := LAND.search(body):
                await self._land_for(sender, command.group(1))

    async def _reply(self, sender: str, text: str) -> None:
        await self.room.call("send_targeted_message", body=text, target_names=[sender])

    async def _clear(self, callsign: str, plan: Any) -> None:
        traffic = check_plan(callsign, plan, self.airspace.plans())
        self.airspace.file(callsign, plan)
        for item in traffic:
            self.airspace.add_traffic(callsign, item.other, item.reason)

        files = ", ".join(plan.edit)
        if self.airspace.get("ground_stop"):
            await self._say(
                self.room, TOWER_ROOM, "GROUND STOP", f"{callsign} filed, holding until resume."
            )
        elif traffic:
            reasons = "\n".join(f"{item.reason}. Watching." for item in traffic)
            await self._say(
                self.room,
                TOWER_ROOM,
                "TRAFFIC",
                f"{callsign} · cleared {files}\n{reasons}",
                to=(callsign,),
            )
        else:
            await self._say(self.room, TOWER_ROOM, "CLEARED", f"{callsign} · {files}", to=(callsign,))
        await self._update_board()

    async def _land_for(self, sender: str, callsign: str) -> None:
        """Clear a flight whose agent died, so its files stop blocking everyone else."""
        if not await self._is_person(self.room, sender):
            await self._reply(sender, "Only a person can land another agent's flight.")
            return
        if callsign not in self.airspace.plans():
            await self._reply(sender, f"{callsign} has no flight to land.")
            return
        self.airspace.land(callsign)
        await self._say(self.room, TOWER_ROOM, "LANDED", f"{callsign}, by {sender}.")
        await self._sync_conflicts(
            check_code(self.airspace.reports()),
            f"{callsign} was landed without a fix, so check this before merging",
        )
        await self._update_board()

    async def _ground_stop(self, sender: str, stop: bool) -> None:
        if not await self._is_person(self.room, sender):
            await self._reply(sender, "Only a person can call or lift a ground stop.")
            return
        self.airspace.put("ground_stop", stop)
        if stop:
            await self._say(self.room, TOWER_ROOM, "GROUND STOP", f"by {sender}. Every gate is closed.")
        else:
            await self._say(self.room, TOWER_ROOM, "RESUME", f"by {sender}. Clearances are back.")
        await self._update_board()

    # Squawks

    async def on_squawk(self, callsign: str, person: str, vendor: str, report: Report) -> None:
        async with self._lock:
            self.airspace.save_report(callsign, report)
            self._add_crew(callsign, person, vendor)
            try:
                await self._post_violations(callsign, report)
                await self._sync_conflicts(check_code(self.airspace.reports()))
            except FAILURES:
                # The report is saved, so the next squawk retries this.
                log.exception("Couldn't reach Switch while handling %s's squawk", callsign)

    def _add_crew(self, callsign: str, person: str, vendor: str) -> None:
        crew = self.airspace.get("crew", [])
        if any(member["callsign"] == callsign for member in crew):
            return
        people = list(dict.fromkeys(member["person"] for member in crew))
        index = people.index(person) if person in people else len(people)
        owner = OWNER_COLORS[index % len(OWNER_COLORS)]
        crew.append({"person": person, "owner": owner, "callsign": callsign, "vendor": vendor})
        self.airspace.put("crew", crew)

    def _person(self, callsign: str) -> str | None:
        for member in self.airspace.get("crew", []):
            if member["callsign"] == callsign:
                return member["person"]
        return None

    async def _post_violations(self, callsign: str, report: Report) -> None:
        files = check_violations(report, self.airspace.plans().get(callsign))
        key = f"violations:{callsign}"
        known = set(self.airspace.get(key, []))
        new = [path for path in files if path not in known]
        self.airspace.put(key, files)
        if new:
            await self._say(
                self.room,
                TOWER_ROOM,
                "VIOLATION",
                f"{callsign} changed {', '.join(new)} without clearance.",
                to=(callsign,),
            )

    async def _sync_conflicts(
        self, collisions: list[Collision], why: str = "the code fits again"
    ) -> None:
        active = {c["key"]: c for c in self.airspace.conflicts("open", "decided")}
        current = {collision["key"] for collision in collisions}
        for collision in collisions:
            if collision["key"] not in active:
                await self._open_conflict(collision)
        for key, conflict in active.items():
            if key not in current:
                await self._close_conflict(conflict, why)

    async def _open_conflict(self, collision: Collision) -> None:
        conflict_id = self.airspace.new_conflict_id(collision)
        pilots = (collision["changed_by"], collision["caller"])
        people = list(dict.fromkeys(person for person in map(self._person, pilots) if person))
        room = await self.room.call(
            "create_room",
            name=conflict_id,
            description=f"{collision['symbol']}: {collision['reason']}",
            agent_names=[AGENT_NAME, *pilots],
            user_names=people,
            instructions=(
                "Explain your change in 3 lines and propose at most two fixes. "
                "A person picks the fix by replying A or B."
            ),
        )
        room_id = room["id"]
        tower_id = self.room.room_id
        await self.room.call("link_rooms", source_room_id=tower_id, target_room_id=room_id, label="active conflict")
        await self.room.call("link_rooms", source_room_id=room_id, target_room_id=tower_id, label="parent")
        self.airspace.open_conflict(conflict_id, collision, room_id)

        await self._say(
            self.room,
            TOWER_ROOM,
            "COLLISION",
            self._collision_text(collision, conflict_id),
            to=pilots,
        )
        link = self._join_conflict(room_id)
        await self._say(link, conflict_id, "DECISION", self._decision_card(collision, people))
        await self._update_board()

    def _collision_text(self, collision: Collision, conflict_id: str) -> str:
        breaks = collision["breaks"]
        if collision["kind"] != "contract":
            what = collision["reason"]
        elif collision["after"]:
            what = (
                f"{collision['changed_by']} changed {collision['before']} to {collision['after']}\n"
                f"{collision['caller']}'s {breaks['file']}:{breaks['line']} {collision['reason']}"
            )
        else:
            what = (
                f"{collision['changed_by']} removed {collision['symbol']}\n"
                f"{collision['caller']}'s {breaks['file']}:{breaks['line']} {collision['reason']}"
            )
        return f"{what}\nNothing pushed. Both flights holding.\nOpened {conflict_id}."

    def _decision_card(self, collision: Collision, people: list[str]) -> str:
        names = " or ".join(people) or "A person"
        lines = [f"{names}, reply A or B"]
        lines += [
            f"{option['key']}  {option['text']}  ({option['agent']} edits)"
            for option in collision["options"]
        ]
        return "\n".join(lines)

    async def on_conflict_message(self, event: Event) -> None:
        payload = event["payload"]
        room_id = event["room_id"]
        sender, body = payload["sender_name"], payload["body"]
        if sender == AGENT_NAME:
            return

        conflict = self.airspace.conflict_in_room(room_id)
        room = conflict["id"] if conflict else room_id
        if not self.airspace.record(room, sender, body, None, payload["message_id"]):
            return
        match = DECISION.fullmatch(body.strip())
        if conflict is None or match is None:
            return

        link = self.conflict_rooms[room_id]
        async with self._lock:
            if not await self._is_person(link, sender):
                await link.call(
                    "send_targeted_message",
                    body="Only a person can pick the fix.",
                    target_names=[sender],
                )
                return
            await self._decide(conflict, link, sender, match.group(1).upper())

    async def _decide(self, conflict: dict, link: RoomLink, person: str, key: str) -> None:
        option = next(item for item in conflict["options"] if item["key"] == key)
        self.airspace.decide(conflict["id"], person, key)
        pilots = (conflict["changed_by"], conflict["caller"])
        await self._say(
            link,
            conflict["id"],
            "DECIDED",
            f"by {person} ({key}): {option['text']}. {option['agent']} makes the edit.",
            to=pilots,
        )
        await self._say(
            self.room,
            TOWER_ROOM,
            "CLEARED",
            f"{' and '.join(pilots)} after {conflict['id']}. {option['agent']} fixes it.",
            to=pilots,
        )
        await self._update_board()

    async def _close_conflict(self, conflict: dict, why: str) -> None:
        self.airspace.resolve(conflict["id"])
        self.airspace.clear_traffic(conflict["changed_by"], conflict["caller"])
        remaining = len(self.airspace.conflicts("open", "decided"))
        await self._say(
            self.room,
            TOWER_ROOM,
            "RESOLVED",
            f"{conflict['id']}: {why}. {remaining} open collisions.",
        )
        await self.room.call("archive_room", room_id=conflict["room_id"])
        link = self.conflict_rooms.pop(conflict["room_id"], None)
        if link:
            await link.close()
        await self._update_board()

    # Airspace board

    def _board_text(self) -> str:
        lines = ["# Airspace", "", "## Active flights"]
        plans = self.airspace.plans()
        lines += [f"- {name}: {plan.task} ({', '.join(plan.edit)})" for name, plan in plans.items()]
        if not plans:
            lines.append("- None")
        lines += ["", "## Open collisions"]
        conflicts = self.airspace.conflicts("open", "decided")
        lines += [f"- {c['id']} ({c['status']}): {c['reason']}" for c in conflicts]
        if not conflicts:
            lines.append("- None")
        if self.airspace.get("ground_stop"):
            lines += ["", "**Ground stop in effect.**"]
        return "\n".join(lines) + "\n"

    async def _find_board(self) -> str | None:
        room = await self.room.call("connect_to_room", room_id=self.room.room_id)
        return next((d["id"] for d in room["documents"] if d["name"] == BOARD), None)

    async def _update_board(self) -> None:
        try:
            document = self.airspace.get("board_id") or await self._find_board()
            if document:
                await self.room.call(
                    "update_room_document", document_id=document, content=self._board_text()
                )
            else:
                result = await self.room.call(
                    "create_room_document",
                    name=BOARD,
                    description="Active flights, holds and open collisions",
                    instructions="Read this to see who is cleared for what. Detente keeps it current.",
                    content=self._board_text(),
                )
                document = result["document_id"]
            self.airspace.put("board_id", document)
        except FAILURES:
            log.exception("Couldn't update the Airspace board")
