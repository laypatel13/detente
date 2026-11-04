"""Everything Detente remembers, in SQLite so a restart keeps every hold in force."""

import json
import re
import secrets
import sqlite3
import time
from pathlib import PurePosixPath
from typing import Any

from backend.detector import Collision, Report
from backend.plans import FlightPlan

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS flights (
    callsign TEXT PRIMARY KEY, plan TEXT NOT NULL, landed REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS reports (callsign TEXT PRIMARY KEY, report TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS conflicts (
    id TEXT PRIMARY KEY,
    key TEXT NOT NULL,
    status TEXT NOT NULL,
    room_id TEXT,
    data TEXT NOT NULL,
    decision TEXT,
    opened_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS traffic (
    a TEXT NOT NULL, b TEXT NOT NULL, reason TEXT NOT NULL, PRIMARY KEY (a, b, reason)
);
CREATE TABLE IF NOT EXISTS seen (message_id TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS feed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room TEXT NOT NULL,
    sender TEXT NOT NULL,
    tag TEXT,
    face TEXT,
    body TEXT NOT NULL
);
"""

FEED_SIZE = 100
LANDED_SHOWN_SECONDS = 60
FACES = {
    "CLEARED": "[o_o]",
    "TRAFFIC": "[¬_¬]",
    "VIOLATION": "[¬_¬]",
    "COLLISION": "[O_O]!",
    "DECISION": "[O_O]!",
    "DECIDED": "[^_^]",
    "RESOLVED": "[^_^]",
    "GROUND STOP": "[ò_ó]",
    "RESUME": "[o_o]",
    "LANDED": "[^_^]",
}


def _plan_from(raw: str) -> FlightPlan:
    data = json.loads(raw)
    return FlightPlan(data["task"], *(tuple(data[key]) for key in ("edit", "changes", "uses")))


def _sector(path: str) -> str:
    parts = PurePosixPath(path).parts
    return parts[0] if len(parts) > 1 else "root"


class Airspace:
    def __init__(self, path: str) -> None:
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(SCHEMA)
        self.version = 0

    def _write(self, sql: str, *args: Any) -> None:
        self._db.execute(sql, args)
        self.version += 1

    def _read(self, sql: str, *args: Any) -> list[sqlite3.Row]:
        return self._db.execute(sql, args).fetchall()

    def get(self, key: str, default: Any = None) -> Any:
        rows = self._read("SELECT value FROM meta WHERE key = ?", key)
        return json.loads(rows[0]["value"]) if rows else default

    def put(self, key: str, value: Any) -> None:
        self._write("INSERT OR REPLACE INTO meta VALUES (?, ?)", key, json.dumps(value))

    # Flights

    def file(self, callsign: str, plan: FlightPlan) -> None:
        raw = json.dumps(
            {"task": plan.task, "edit": plan.edit, "changes": plan.changes, "uses": plan.uses}
        )
        self._write("INSERT OR REPLACE INTO flights VALUES (?, ?, 0)", callsign, raw)

    def land(self, callsign: str) -> None:
        plan = self.plans().get(callsign)
        if plan:
            # Landed work is still cleared until it's pushed. See landed_files.
            key = f"landed:{callsign}"
            self.put(key, sorted({*self.get(key, []), *plan.edit}))
        self._write("UPDATE flights SET landed = ? WHERE callsign = ?", time.time(), callsign)
        self._write("DELETE FROM reports WHERE callsign = ?", callsign)
        self._write("DELETE FROM traffic WHERE a = ? OR b = ?", callsign, callsign)

    def plans(self) -> dict[str, FlightPlan]:
        rows = self._read("SELECT callsign, plan FROM flights WHERE landed = 0")
        return {row["callsign"]: _plan_from(row["plan"]) for row in rows}

    def landed_files(self, callsign: str, unpushed: list[str]) -> list[str]:
        """Files a landed flight cleared that are still unpushed. Pushed ones need a new plan."""
        key = f"landed:{callsign}"
        kept = [path for path in self.get(key, []) if path in unpushed]
        self.put(key, kept)
        return kept

    def add_traffic(self, a: str, b: str, reason: str) -> None:
        self._write("INSERT OR IGNORE INTO traffic VALUES (?, ?, ?)", a, b, reason)

    def clear_traffic(self, a: str, b: str) -> None:
        self._write("DELETE FROM traffic WHERE (a = ? AND b = ?) OR (a = ? AND b = ?)", a, b, b, a)

    # Squawks

    def save_report(self, callsign: str, report: Report) -> None:
        self._write(
            "INSERT OR REPLACE INTO reports VALUES (?, ?)", callsign, json.dumps(report)
        )

    def reports(self) -> dict[str, Report]:
        rows = self._read("SELECT callsign, report FROM reports")
        return {row["callsign"]: json.loads(row["report"]) for row in rows}

    # Conflicts

    def _conflict(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            **json.loads(row["data"]),
            "id": row["id"],
            "status": row["status"],
            "room_id": row["room_id"],
            "decision": json.loads(row["decision"]) if row["decision"] else None,
        }

    def new_conflict_id(self, collision: Collision) -> str:
        name = re.sub(r"[^a-z0-9]+", "-", collision["symbol"].rsplit(".", 1)[-1].lower())
        return f"conflict-{name.strip('-')}-{secrets.token_hex(2)}"

    def open_conflict(self, conflict_id: str, collision: Collision, room_id: str | None) -> None:
        self._write(
            "INSERT INTO conflicts VALUES (?, ?, 'open', ?, ?, NULL, ?)",
            conflict_id,
            collision["key"],
            room_id,
            json.dumps(collision),
            time.time(),
        )

    def conflicts(self, *statuses: str) -> list[dict[str, Any]]:
        marks = ", ".join("?" for _ in statuses)
        rows = self._read(
            f"SELECT * FROM conflicts WHERE status IN ({marks}) ORDER BY opened_at", *statuses
        )
        return [self._conflict(row) for row in rows]

    def conflict(self, conflict_id: str) -> dict[str, Any] | None:
        rows = self._read("SELECT * FROM conflicts WHERE id = ?", conflict_id)
        return self._conflict(rows[0]) if rows else None

    def conflict_in_room(self, room_id: str) -> dict[str, Any] | None:
        rows = self._read(
            "SELECT * FROM conflicts WHERE room_id = ? AND status = 'open'", room_id
        )
        return self._conflict(rows[0]) if rows else None

    def decide(self, conflict_id: str, by: str, option: str) -> None:
        decision = json.dumps({"by": by, "option": option})
        self._write(
            "UPDATE conflicts SET status = 'decided', decision = ? WHERE id = ?",
            decision,
            conflict_id,
        )

    def resolve(self, conflict_id: str) -> None:
        self._write("UPDATE conflicts SET status = 'resolved' WHERE id = ?", conflict_id)
        self.put("last_resolved", conflict_id)

    # Feed

    def record(
        self,
        room: str,
        sender: str,
        body: str,
        tag: str | None = None,
        message_id: str | None = None,
    ) -> bool:
        """Add one message to the feed. False when this message was already seen."""
        if message_id and not self.mark_seen(message_id):
            return False
        self._write(
            "INSERT INTO feed (room, sender, tag, face, body) VALUES (?, ?, ?, ?, ?)",
            room,
            sender,
            tag,
            FACES.get(tag),
            body,
        )
        return True

    def mark_seen(self, message_id: str) -> bool:
        before = self._db.total_changes
        self._db.execute("INSERT OR IGNORE INTO seen VALUES (?)", (message_id,))
        return self._db.total_changes > before

    # Gates

    def clearance(self, callsign: str, path: str) -> str | None:
        """Why this file is refused, or None when the pilot may touch it."""
        if self.get("ground_stop"):
            return f"Ground stop in effect. Wait for a person to send resume. ({path})"
        plan = self.plans().get(callsign)
        if plan is None or path not in plan.edit:
            return f"No clearance for {path}. File a flight plan in the tower room."
        for conflict in self.conflicts("open"):
            if callsign in (conflict["changed_by"], conflict["caller"]):
                return f"Holding for {conflict['id']}. A person decides in that room."
        return None

    # Radar

    def _mood(self, flights: list, open_conflicts: list, links: list) -> str:
        if self.get("ground_stop"):
            return "stop"
        if open_conflicts:
            return "collision"
        if any(link["kind"] == "traffic" for link in links):
            return "traffic"
        if not any(flight["status"] != "landed" for flight in flights):
            return "resolved" if self.get("last_resolved") and flights else "resting"
        return "watching"

    def _headline(self, mood: str, open_conflicts: list) -> str:
        if mood == "stop":
            return "Ground stop. Every clearance is suspended."
        if open_conflicts:
            conflict = open_conflicts[0]
            breaks = conflict["breaks"]
            return f"{breaks['file']}:{breaks['line']} {conflict['reason']}."
        rows = self._read(
            "SELECT body FROM feed WHERE sender = 'Detente' ORDER BY id DESC LIMIT 1"
        )
        return rows[0]["body"].splitlines()[0] if rows else "All quiet. No flights in the air."

    def snapshot(self) -> dict[str, Any]:
        open_conflicts = self.conflicts("open")
        held = {
            callsign
            for conflict in open_conflicts
            for callsign in (conflict["changed_by"], conflict["caller"])
        }
        stopped = self.get("ground_stop", False)

        crew = self.get("crew", [])
        owners = {member["callsign"]: member["owner"] for member in crew}
        flights = []
        rows = self._read(
            "SELECT * FROM flights WHERE landed = 0 OR landed > ? ORDER BY callsign",
            time.time() - LANDED_SHOWN_SECONDS,
        )
        for row in rows:
            plan = _plan_from(row["plan"])
            if row["landed"]:
                status = "landed"
            elif row["callsign"] in held:
                status = "worried"
            else:
                status = "hold" if stopped else "cleared"
            flights.append(
                {
                    "callsign": row["callsign"],
                    "owner": owners.get(row["callsign"], "lay"),
                    "task": plan.task,
                    "files": list(plan.edit),
                    "sector": _sector(plan.edit[0]),
                    "status": status,
                }
            )

        links = [
            {"kind": "collision", "from": c["changed_by"], "to": c["caller"], "reason": c["reason"]}
            for c in open_conflicts
        ]
        pairs = {frozenset((link["from"], link["to"])) for link in links}
        for row in self._read("SELECT * FROM traffic"):
            if frozenset((row["a"], row["b"])) not in pairs:
                links.append(
                    {"kind": "traffic", "from": row["a"], "to": row["b"], "reason": row["reason"]}
                )
                pairs.add(frozenset((row["a"], row["b"])))

        mood = self._mood(flights, open_conflicts, links)
        feed = self._read("SELECT * FROM feed ORDER BY id DESC LIMIT ?", FEED_SIZE)
        return {
            "version": self.version,
            "mood": mood,
            "headline": self._headline(mood, open_conflicts),
            "crew": crew,
            "flights": flights,
            "links": links,
            "feed": [
                {
                    "id": row["id"],
                    "room": row["room"],
                    "sender": row["sender"],
                    "tag": row["tag"],
                    "face": row["face"],
                    "text": row["body"],
                }
                for row in reversed(feed)
            ],
            "conflicts": self.conflicts("open", "decided"),
        }
