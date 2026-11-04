import asyncio
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.accounts import Accounts
from backend.airspace import Airspace
from backend.api import create_app
from backend.contracts import calls, changes
from backend.plans import FlightPlan
from backend.switch import RoomLink, Switch, SwitchError
from backend.tower import Tower

TOKEN = "pilot-token"
PEOPLE = [{"name": "lay", "type": "user"}, {"name": "lay-claude", "type": "agent"}]


class FakeLink:
    """Stands in for a room: records what Detente says and answers operations."""

    log: list[tuple[str, dict]] = []

    def __init__(self, switch: Any, room_id: str, on_message: Any) -> None:
        self.room_id = room_id
        self.on_message = on_message

    def start(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def call(self, operation: str, **arguments: Any) -> Any:
        FakeLink.log.append((operation, arguments))
        if operation == "list_participants":
            return PEOPLE
        if operation == "create_room":
            return {"id": "conflict-room"}
        if operation == "create_room_document":
            return {"document_id": "board"}
        if operation == "connect_to_room":
            return {"documents": []}
        if operation == "list_roles":
            return []
        if operation == "read_context":
            return {"threads": []}
        return {}


def said() -> str:
    return "\n".join(args.get("body", "") for op, args in FakeLink.log)


def called(operation: str) -> list[dict]:
    return [args for op, args in FakeLink.log if op == operation]


@pytest.fixture
def tower() -> Tower:
    FakeLink.log = []
    return Tower(Airspace(":memory:"), None, "tower-room", link=FakeLink)


def message(tower: Tower, sender: str, body: str, message_id: str = "") -> None:
    event = {
        "room_id": "tower-room",
        "payload": {
            "sender_name": sender,
            "body": body,
            "message_id": message_id or body,
            "addressed": False,
        },
    }
    asyncio.run(tower.on_tower_message(event))


def conflict_message(tower: Tower, sender: str, body: str) -> None:
    event = {
        "room_id": "conflict-room",
        "payload": {"sender_name": sender, "body": body, "message_id": body + sender},
    }
    asyncio.run(tower.on_conflict_message(event))


PLAN_A = "FLIGHT PLAN\ntask: expiry\nedit: auth/session.py\nchanges: create_session"
PLAN_B = "FLIGHT PLAN\ntask: refunds\nedit: billing/refunds.py\nuses: create_session"
CHANGED = changes("def create_session(user): pass", "def create_session(user, ttl): pass", "auth/session.py")


def caller(source: str) -> dict:
    found = [asdict(call) for call in calls(source, "billing/refunds.py")]
    return {"files": ["billing/refunds.py"], "changes": [], "calls": found}


BROKEN = "from auth.session import create_session\ncreate_session(user)\n"
FIXED = "from auth.session import create_session\ncreate_session(user, 30)\n"
CHANGER = {"files": ["auth/session.py"], "changes": CHANGED, "calls": []}


def collide(tower: Tower) -> dict:
    message(tower, "lay-claude", PLAN_A)
    message(tower, "a-codex", PLAN_B)
    asyncio.run(tower.on_squawk("lay-claude", "lay", "Claude Code", CHANGER))
    asyncio.run(tower.on_squawk("a-codex", "developer", "Codex", caller(BROKEN)))
    conflict = tower.airspace.conflicts("open")[0]
    tower.conflict_rooms["conflict-room"] = FakeLink(None, "conflict-room", None)
    return conflict


def test_a_plan_with_clear_skies_is_cleared(tower):
    message(tower, "lay-claude", PLAN_A)
    assert "[o_o] CLEARED lay-claude · auth/session.py" in said()
    assert tower.airspace.clearance("lay-claude", "auth/session.py") is None


def test_a_bad_plan_gets_a_reply_and_no_clearance(tower):
    message(tower, "lay-claude", "FLIGHT PLAN\ntask: no files")
    assert "needs an edit line" in said()
    assert tower.airspace.plans() == {}


def test_the_same_message_is_only_handled_once(tower):
    message(tower, "lay-claude", PLAN_A, "one")
    message(tower, "lay-claude", PLAN_A, "one")
    assert len(called("send_targeted_message")) == 1


def test_detente_ignores_its_own_messages(tower):
    message(tower, "detente", PLAN_A)
    assert tower.airspace.plans() == {}


def test_overlapping_plans_raise_traffic(tower):
    message(tower, "lay-claude", PLAN_A)
    message(tower, "a-codex", PLAN_B)
    assert "TRAFFIC a-codex · cleared" in said()
    assert tower.airspace.snapshot()["mood"] == "traffic"


def test_collision_holds_both_flights_and_opens_a_linked_room(tower):
    conflict = collide(tower)
    assert conflict["reason"] == "is missing required argument ttl"
    assert "Holding" in tower.airspace.clearance("lay-claude", "auth/session.py")
    assert "Holding" in tower.airspace.clearance("a-codex", "billing/refunds.py")

    room = called("create_room")[0]
    assert room["agent_names"] == ["detente", "lay-claude", "a-codex"]
    assert room["user_names"] == ["lay", "developer"]
    labels = {link["label"] for link in called("link_rooms")}
    assert labels == {"active conflict", "parent"}


def test_a_repeat_squawk_opens_no_second_conflict(tower):
    collide(tower)
    asyncio.run(tower.on_squawk("a-codex", "developer", "Codex", caller(BROKEN)))
    assert len(called("create_room")) == 1


def test_an_agent_cannot_pick_the_fix(tower):
    collide(tower)
    conflict_message(tower, "lay-claude", "B")
    assert tower.airspace.conflicts("open")
    assert "Only a person" in said()


def test_chatter_decides_nothing(tower):
    collide(tower)
    conflict_message(tower, "lay", "maybe B would work?")
    assert tower.airspace.conflicts("open")


@pytest.mark.parametrize("reply", ["B", "b", "B.", "@detente B"])
def test_a_person_picks_and_the_holds_lift(tower, reply):
    collide(tower)
    conflict_message(tower, "lay", reply)
    assert tower.airspace.conflicts("decided")[0]["decision"] == {"by": "lay", "option": "B"}
    assert tower.airspace.clearance("a-codex", "billing/refunds.py") is None


def test_talk_after_the_pick_stays_under_the_conflicts_name(tower):
    conflict = collide(tower)
    conflict_message(tower, "lay", "B")
    conflict_message(tower, "a-codex", "On it.")
    conflict_message(tower, "lay", "A")
    rooms = {row["room"] for row in tower.airspace._read("SELECT room FROM feed")}
    assert "conflict-room" not in rooms and conflict["id"] in rooms
    # The pick stands. Changing it would leave the first fixer cleared for nothing.
    assert tower.airspace.conflicts("decided")[0]["decision"]["option"] == "B"


def test_fixed_code_resolves_and_archives(tower):
    collide(tower)
    conflict_message(tower, "lay", "B")
    asyncio.run(tower.on_squawk("a-codex", "developer", "Codex", caller(FIXED)))
    assert tower.airspace.conflicts("open", "decided") == []
    assert called("archive_room") == [{"room_id": "conflict-room"}]
    assert "RESOLVED" in said()


def test_a_resolved_conflict_ends_the_traffic_warning_between_those_flights(tower):
    collide(tower)
    tower.airspace.add_traffic("a-codex", "lay-claude", "uses create_session")
    conflict_message(tower, "lay", "B")
    asyncio.run(tower.on_squawk("a-codex", "developer", "Codex", caller(FIXED)))
    assert tower.airspace.snapshot()["links"] == []


def test_only_a_person_can_call_a_ground_stop(tower):
    message(tower, "lay-claude", "@detente ground stop")
    assert not tower.airspace.get("ground_stop")
    message(tower, "lay", "@detente ground stop please")
    assert tower.airspace.get("ground_stop")


def test_ground_stop_closes_gates_and_resume_opens_them(tower):
    message(tower, "lay-claude", PLAN_A)
    message(tower, "lay", "@detente ground stop")
    assert "Ground stop" in tower.airspace.clearance("lay-claude", "auth/session.py")
    message(tower, "lay", "@detente resume")
    assert tower.airspace.clearance("lay-claude", "auth/session.py") is None


def test_a_person_can_land_a_dead_agents_flight(tower):
    message(tower, "lay-claude", PLAN_A)
    message(tower, "lay", "@detente land lay-claude")
    assert tower.airspace.plans() == {}


def test_landing_takes_a_mention_as_the_callsign(tower):
    # Mattermost's autocomplete writes the agent's name as a mention.
    message(tower, "lay-claude", PLAN_A)
    message(tower, "lay", "@detente land @lay-claude.")
    assert tower.airspace.plans() == {}


def test_an_agent_cannot_land_another_flight(tower):
    message(tower, "lay-claude", PLAN_A)
    message(tower, "a-codex", "@detente land lay-claude")
    assert "lay-claude" in tower.airspace.plans()


def test_landed_but_unpushed_work_still_collides(tower):
    message(tower, "lay-claude", PLAN_A)
    asyncio.run(tower.on_squawk("lay-claude", "lay", "Claude Code", CHANGER))
    message(tower, "lay-claude", "LANDED")
    # Agents land seconds after editing. The break shows up when the old call is written later.
    message(tower, "a-codex", PLAN_B)
    asyncio.run(tower.on_squawk("a-codex", "developer", "Codex", caller(BROKEN)))
    assert len(tower.airspace.conflicts("open")) == 1


def test_an_agent_cannot_land_while_a_person_decides(tower):
    collide(tower)
    message(tower, "a-codex", "LANDED")
    assert "a-codex" in tower.airspace.plans()
    assert "Holding for" in said()


def test_the_picked_fixer_cannot_land_before_the_fix(tower):
    collide(tower)
    conflict_message(tower, "lay", "B")
    message(tower, "a-codex", "LANDED", "fixer")
    message(tower, "lay-claude", "LANDED", "other")
    assert list(tower.airspace.plans()) == ["a-codex"]
    assert "You're fixing" in said()


def test_a_fixer_that_landed_is_cleared_for_its_fix(tower):
    # In the first real run the fixer had landed, so its gate refused the fix it was
    # picked for, it undid it, and the collision opened a new room every round.
    message(tower, "lay-claude", PLAN_A)
    asyncio.run(tower.on_squawk("lay-claude", "lay", "Claude Code", CHANGER))
    message(tower, "lay-claude", "LANDED")
    message(tower, "a-codex", PLAN_B)
    asyncio.run(tower.on_squawk("a-codex", "developer", "Codex", caller(BROKEN)))
    tower.conflict_rooms["conflict-room"] = FakeLink(None, "conflict-room", None)
    conflict_message(tower, "lay", "A")
    assert tower.airspace.clearance("lay-claude", "auth/session.py") is None
    assert "lay-claude fixes it in auth/session.py" in said()


def test_a_decision_wakes_the_agents_only_in_the_conflict_room(tower):
    # Switch runs one session per room, so telling the fixer in both rooms woke two of
    # its sessions and both went to make the same fix.
    collide(tower)
    FakeLink.log = []
    conflict_message(tower, "lay", "B")
    targeted = [args["body"] for args in called("send_targeted_message")]
    assert len(targeted) == 1 and "DECIDED" in targeted[0]
    assert any("CLEARED" in args["body"] for args in called("post_message"))


def test_a_landed_flight_in_a_collision_stays_on_the_radar_holding(tower, monkeypatch):
    message(tower, "lay-claude", PLAN_A)
    asyncio.run(tower.on_squawk("lay-claude", "lay", "Claude Code", CHANGER))
    message(tower, "lay-claude", "LANDED")
    message(tower, "a-codex", PLAN_B)
    asyncio.run(tower.on_squawk("a-codex", "developer", "Codex", caller(BROKEN)))
    later = time.time() + 120
    monkeypatch.setattr(time, "time", lambda: later)
    statuses = {f["callsign"]: f["status"] for f in tower.airspace.snapshot()["flights"]}
    assert statuses == {"a-codex": "worried", "lay-claude": "worried"}


def test_a_person_landing_a_flight_dismisses_its_collision(tower):
    collide(tower)
    message(tower, "lay-claude", "LANDED")
    message(tower, "lay", "@detente land lay-claude")
    assert tower.airspace.conflicts("open", "decided") == []
    assert "landed without a fix" in said()


def test_changing_an_uncleared_file_is_a_violation_once(tower):
    report = {"files": ["cart/totals.py"], "changes": [], "calls": []}
    asyncio.run(tower.on_squawk("lay-claude", "lay", "Claude Code", report))
    asyncio.run(tower.on_squawk("lay-claude", "lay", "Claude Code", report))
    assert said().count("VIOLATION") == 1


def test_landed_work_stays_cleared_until_it_is_pushed(tower):
    plan = "FLIGHT PLAN\ntask: discount\nedit: cart/totals.py"
    unpushed = {"files": ["cart/totals.py"], "changes": [], "calls": []}
    message(tower, "lay-claude", plan, "first")
    message(tower, "lay-claude", "LANDED", "landed")
    asyncio.run(tower.on_squawk("lay-claude", "lay", "Claude Code", unpushed))
    assert "VIOLATION" not in said()

    # Once pushed, the file is no longer cleared: changing it again needs a new plan.
    asyncio.run(tower.on_squawk("lay-claude", "lay", "Claude Code", {**unpushed, "files": []}))
    asyncio.run(tower.on_squawk("lay-claude", "lay", "Claude Code", unpushed))
    assert said().count("VIOLATION") == 1


def test_a_failed_room_call_is_retried_on_the_next_squawk(tower, monkeypatch):
    original = FakeLink.call

    async def fails(self, operation, **arguments):
        if operation == "create_room":
            raise SwitchError("Switch is down")
        return await original(self, operation, **arguments)

    monkeypatch.setattr(FakeLink, "call", fails)
    message(tower, "lay-claude", PLAN_A)
    message(tower, "a-codex", PLAN_B)
    asyncio.run(tower.on_squawk("lay-claude", "lay", "Claude Code", CHANGER))
    asyncio.run(tower.on_squawk("a-codex", "developer", "Codex", caller(BROKEN)))
    assert tower.airspace.conflicts("open") == []

    monkeypatch.setattr(FakeLink, "call", original)
    asyncio.run(tower.on_squawk("a-codex", "developer", "Codex", caller(BROKEN)))
    assert len(tower.airspace.conflicts("open")) == 1


def test_a_first_start_acts_on_no_old_messages(tower, monkeypatch):
    # An old ground stop in the room's history must not fire on a fresh install.
    old = {"id": "old", "kind": "message", "sender_name": "lay", "body": "@detente ground stop"}
    original = FakeLink.call

    async def history(self, operation, **arguments):
        if operation == "read_context":
            return {"threads": [{"root": old, "replies": []}]}
        return await original(self, operation, **arguments)

    monkeypatch.setattr(FakeLink, "call", history)
    asyncio.run(tower._catch_up())
    assert not tower.airspace.get("ground_stop")


def test_a_restart_catches_up_on_what_it_missed(tower, monkeypatch):
    tower.airspace.put("started", True)
    missed = {"id": "new", "kind": "message", "sender_name": "lay-claude", "body": PLAN_A}
    original = FakeLink.call

    async def history(self, operation, **arguments):
        if operation == "read_context":
            return {"threads": [{"root": missed, "replies": []}]}
        return await original(self, operation, **arguments)

    monkeypatch.setattr(FakeLink, "call", history)
    asyncio.run(tower._catch_up())
    assert "lay-claude" in tower.airspace.plans()


def test_holds_survive_a_restart(tmp_path: Path):
    FakeLink.log = []
    path = str(tmp_path / "detente.db")
    tower = Tower(Airspace(path), None, "tower-room", link=FakeLink)
    collide(tower)

    reopened = Airspace(path)
    assert "Holding" in reopened.clearance("lay-claude", "auth/session.py")


def test_conflict_ids_never_repeat():
    airspace = Airspace(":memory:")
    collision = {"symbol": "auth.session.create_session"}
    assert airspace.new_conflict_id(collision) != airspace.new_conflict_id(collision)


def test_a_landed_flight_leaves_the_radar_after_a_minute(monkeypatch):
    airspace = Airspace(":memory:")
    airspace.file("a", FlightPlan("x", ("a.py",)))
    airspace.land("a")
    assert airspace.snapshot()["flights"][0]["status"] == "landed"

    later = time.time() + 61
    monkeypatch.setattr(time, "time", lambda: later)
    assert airspace.snapshot()["flights"] == []


def test_landing_keeps_a_report_until_it_is_dropped():
    airspace = Airspace(":memory:")
    airspace.file("a", FlightPlan("x", ("a.py",)))
    airspace.save_report("a", {"files": [], "changes": [], "calls": []})
    airspace.land("a")
    assert list(airspace.reports()) == ["a"]
    airspace.drop_report("a")
    assert airspace.reports() == {}


def test_a_keep_alive_does_not_kill_the_room_stream():
    # httpx-sse hands a keep-alive over as a message frame with no data once an
    # event id has been seen. It killed the stream after 15 quiet seconds.
    body = (
        'event: connection_state\ndata: {"heartbeat_interval_seconds": 60}\n\n'
        'id: 1\nevent: message\ndata: {"room_id": "r", "payload": {}}\n\n'
        ": keep-alive\n\n"
        'id: 2\nevent: message\ndata: {"room_id": "r", "payload": {}}\n\n'
    )
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, headers={"content-type": "text/event-stream"}, text=body
        )
    )
    received = []

    async def run() -> None:
        switch = Switch("http://switch", "agent", "key")
        switch.http = httpx.AsyncClient(base_url="http://switch", transport=transport)

        async def on_message(event: dict) -> None:
            received.append(event)

        link = RoomLink(switch, "r", on_message)
        await link._stream()

    asyncio.run(run())
    assert len(received) == 2


def client(tower: Tower) -> TestClient:
    return TestClient(create_app(tower.airspace, tower, Accounts(":memory:"), TOKEN))


AUTH = {"Authorization": f"Bearer {TOKEN}"}


def test_clearance_needs_the_pilot_token(tower):
    body = {"callsign": "a", "files": ["a.py"]}
    assert client(tower).post("/clearance", json=body).status_code == 401
    assert client(tower).post("/clearance", json=body, headers=AUTH).status_code == 200


def test_clearance_lists_refused_files(tower):
    message(tower, "a", "FLIGHT PLAN\ntask: x\nedit: a.py")
    body = {"callsign": "a", "files": ["a.py", "b.py"]}
    reply = client(tower).post("/clearance", json=body, headers=AUTH).json()
    assert list(reply["refused"]) == ["b.py"]


def test_squawk_needs_the_pilot_token(tower):
    body = {"callsign": "a", "person": "p", "vendor": "v", "report": CHANGER}
    assert client(tower).post("/squawk", json=body).status_code == 401
    assert client(tower).post("/squawk", json=body, headers=AUTH).status_code == 200


def test_radar_reads_need_access_and_unknown_conflicts_are_404(tower):
    api = client(tower)
    assert api.get("/radar/state").status_code == 401
    assert api.get("/radar/stream").status_code == 401
    assert api.get("/radar/conflicts/nope").status_code == 401
    assert api.get("/radar/state", headers=AUTH).json()["mood"] == "resting"
    assert api.get("/radar/conflicts/nope", headers=AUTH).status_code == 404


def test_radar_marks_collision_flights_and_owner_colors(tower):
    collide(tower)
    state = client(tower).get("/radar/state", headers=AUTH).json()
    assert state["mood"] == "collision"
    assert {f["owner"] for f in state["flights"]} == {"lay", "a"}
    assert {f["status"] for f in state["flights"]} == {"worried"}
    assert state["links"][0]["kind"] == "collision"


def test_eight_people_get_eight_plane_colors(tower):
    for index in range(8):
        tower._add_crew(f"developer{index}-claude", f"developer{index}", "Claude Code")
    assert len({member["owner"] for member in tower.airspace.get("crew", [])}) == 8
