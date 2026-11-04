"""Decide traffic, collisions and violations. Deterministic: no LLM call in here."""

from dataclasses import dataclass
from typing import Any

from backend.contracts import call_from, problem, signature_from
from backend.plans import FlightPlan, same_symbol

Report = dict[str, Any]
Collision = dict[str, Any]


@dataclass(frozen=True)
class Traffic:
    other: str
    reason: str


def _short(symbol: str) -> str:
    return symbol.rsplit(".", 1)[-1]


def check_plan(callsign: str, plan: FlightPlan, flights: dict[str, FlightPlan]) -> list[Traffic]:
    """Layer 1, plan against plan. A heads-up that stops nobody."""
    found: list[Traffic] = []
    for other, theirs in flights.items():
        if other == callsign:
            continue
        for path in sorted(set(plan.edit) & set(theirs.edit)):
            found.append(Traffic(other, f"{other} is also editing {path}"))
        for mine in plan.uses:
            for changed in theirs.changes:
                if same_symbol(mine, changed):
                    found.append(
                        Traffic(other, f"{callsign} uses {_short(mine)}, which {other} is changing")
                    )
        for used in theirs.uses:
            for mine in plan.changes:
                if same_symbol(used, mine):
                    found.append(
                        Traffic(other, f"{other} uses {_short(used)}, which {callsign} is changing")
                    )
        for mine in plan.changes:
            for changed in theirs.changes:
                if same_symbol(mine, changed):
                    found.append(Traffic(other, f"{other} is also changing {_short(mine)}"))
    return found


def _first_option(name: str, reason: str) -> str:
    if reason.endswith("a name that no longer exists"):
        return f"Bring {name} back"
    if "missing required argument" in reason:
        return f"Give {reason.rsplit(' ', 1)[-1]} a default"
    if "async now" in reason:
        return f"Keep {name} sync"
    if "isn't async" in reason:
        return f"Keep {name} async"
    if reason.startswith("passes") and "as argument" in reason:
        return f"Put {name}'s arguments back in their old order"
    return f"Accept the old call to {name}"


def _contract_collision(change: dict, changer: str, caller: str, call: Any, reason: str) -> Collision:
    name = _short(change["symbol"])
    return {
        "key": f"{change['symbol']}|{changer}|{caller}|{call.file}",
        "kind": "contract",
        "symbol": change["symbol"],
        "before": change["before"]["text"],
        "after": change["after"]["text"] if change["after"] else None,
        "changed_by": changer,
        "changed_file": change["file"],
        "caller": caller,
        "breaks": {"file": call.file, "line": call.line, "code": call.code},
        "reason": reason,
        "options": [
            {"key": "A", "text": _first_option(name, reason), "agent": changer},
            {"key": "B", "text": f"Update the {call.kind} at {call.file}:{call.line}", "agent": caller},
        ],
    }


def _both_changed(
    kind: str, symbol: str, file: str, line: int, left: str, right: str, reason: str,
    name: str | None = None,
) -> Collision:
    name = name or (_short(symbol) if kind == "same_function" else file)
    suffix = {"same_function": "same", "same_file": "file", "same_lines": "lines"}[kind]
    return {
        # One room per pair for line clashes, however many files they share.
        "key": f"lines|{left}|{right}" if kind == "same_lines" else f"{symbol}|{left}|{right}|{suffix}",
        "kind": kind,
        "symbol": symbol,
        "before": None,
        "after": None,
        "changed_by": left,
        "changed_file": file,
        "caller": right,
        "breaks": {"file": file, "line": line, "code": name},
        "reason": reason,
        "options": [
            {"key": "A", "text": f"Keep {left}'s version of {name}", "agent": right},
            {"key": "B", "text": f"Keep {right}'s version of {name}", "agent": left},
        ],
    }


def _touch(mine: list, theirs: list) -> bool:
    """Line spans [start, end) clash when they overlap or meet, as they do for git.

    The very same edit on both sides doesn't clash: git takes it once.
    """
    if len(mine) > 2 and mine == theirs:
        return False
    return mine[0] <= theirs[1] and theirs[0] <= mine[1]


def _same_content(mine: dict | list, theirs: dict | list, path: str) -> bool:
    """Both laptops created this file with the very same text, which git takes once."""
    return isinstance(mine, dict) and isinstance(theirs, dict) and mine[path] == theirs[path]


def _clashes(mine: Report, theirs: Report) -> tuple[dict[str, list[int]], set[str]]:
    """Base-file lines both laptops changed, per file, and which files could be compared.

    Line numbers only line up when both started from the same version of the file.
    """
    their_hunks = theirs.get("hunks", {})
    clashes: dict[str, list[int]] = {}
    compared: set[str] = set()
    for path, hunk in sorted(mine.get("hunks", {}).items()):
        other = their_hunks.get(path)
        if not other or other["blob"] != hunk["blob"]:
            continue
        compared.add(path)
        lines = sorted({max(a[0], b[0]) for a in hunk["lines"] for b in other["lines"] if _touch(a, b)})
        if lines:
            clashes[path] = lines
    return clashes, compared


def _home(line: int, changes: list[dict]) -> str | None:
    """The innermost definition around a base-file line, so a method beats its class."""
    around = [
        change
        for change in changes
        if change.get("lines") and change["lines"][0] <= line < change["lines"][1]
    ]
    if not around:
        return None
    return min(around, key=lambda change: change["lines"][1] - change["lines"][0])["symbol"]


def _pair_collisions(left: str, right: str, mine: Report, theirs: Report) -> list[Collision]:
    """What git would trip on, plus two agents defining one new name.

    Editing different lines of one function merges cleanly, so it isn't stopped here;
    the flight plans' heads-up covers it. Where line numbers can't be compared, any
    shared change still stops, to be safe.
    """
    found: list[Collision] = []
    made, their_made = mine.get("created", {}), theirs.get("created", {})
    created = {path for path in set(made) & set(their_made) if not _same_content(made, their_made, path)}
    for path in sorted(created):
        found.append(
            _both_changed("same_file", path, path, 0, left, right, f"{left} and {right} both created {path}")
        )

    def same_function(change: dict, line: int) -> Collision:
        name = _short(change["symbol"])
        reason = f"{left} and {right} both changed {name}"
        return _both_changed("same_function", change["symbol"], change["file"], line, left, right, reason)

    clashes, compared = _clashes(mine, theirs)
    both_changes = [*mine["changes"], *theirs["changes"]]
    unnamed: list[tuple[str, int]] = []
    for path, lines in clashes.items():
        for line in lines:
            symbol = _home(line, [change for change in both_changes if change["file"] == path])
            if symbol is None:
                unnamed.append((path, line))
            else:
                change = next(change for change in both_changes if change["symbol"] == symbol)
                found.append(same_function(change, line))
    if unnamed:
        path, line = unnamed[0]
        more = len({other for other, _ in unnamed}) - 1
        where = f"{path} at line {line}" + (f" and {more} other file{'s' * (more > 1)}" if more else "")
        name = path if not more else "those files"
        reason = f"{left} and {right} both changed {where}"
        found.append(_both_changed("same_lines", path, path, line, left, right, reason, name))

    ours = {change["symbol"]: change for change in mine["changes"]}
    for change in theirs["changes"]:
        twin = ours.get(change["symbol"])
        if twin is None or change["file"] in created:
            continue
        # Both making the very same edit, or both deleting it, is one change to git.
        if "fingerprint" in twin and "fingerprint" in change and twin["fingerprint"] == change["fingerprint"]:
            continue
        # Two new definitions of one name merge cleanly, and the later one silently wins.
        both_new = twin["before"] is None and change["before"] is None
        if both_new or change["file"] not in compared:
            found.append(same_function(change, 0))
    return found


def check_code(reports: dict[str, Report]) -> list[Collision]:
    """Layer 2, code against code, across every laptop's unpushed work."""
    found: dict[str, Collision] = {}

    for changer, report in reports.items():
        for change in report["changes"]:
            if not change["before"] or change["before"] == change["after"]:
                continue
            before = signature_from(change["before"])
            after = signature_from(change["after"])
            for caller, theirs in reports.items():
                if caller == changer:
                    continue
                for raw in theirs["calls"]:
                    call = call_from(raw)
                    if call.symbol != change["symbol"]:
                        continue
                    reason = problem(after, call, before)
                    if reason:
                        collision = _contract_collision(change, changer, caller, call, reason)
                        found.setdefault(collision["key"], collision)

    callsigns = sorted(reports)
    for index, left in enumerate(callsigns):
        for right in callsigns[index + 1 :]:
            for collision in _pair_collisions(left, right, reports[left], reports[right]):
                found.setdefault(collision["key"], collision)

    return list(found.values())


def check_violations(report: Report, plan: FlightPlan | None) -> list[str]:
    """Layer 3, plan against code. Files changed outside the clearance."""
    allowed = set(plan.edit) if plan else set()
    return sorted(set(report["files"]) - allowed)
