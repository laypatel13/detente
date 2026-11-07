"""Parse the flight plans and landings pilots post in the tower room."""

import re
from dataclasses import dataclass

FIELDS = ("task", "edit", "changes", "uses")


@dataclass(frozen=True)
class FlightPlan:
    task: str
    edit: tuple[str, ...]
    changes: tuple[str, ...] = ()
    uses: tuple[str, ...] = ()


class PlanError(ValueError):
    """A flight plan Detente can't accept. The message goes back to the pilot."""


def _items(value: str) -> list[str]:
    """Split on commas outside brackets, so hash_password(password, salt) stays one item."""
    items, depth, start = [], 0, 0
    for index, char in enumerate(value):
        depth += (char == "(") - (char == ")")
        if char == "," and depth <= 0:
            items.append(value[start:index])
            start = index + 1
    items.append(value[start:])
    return [item.strip().strip("`").strip() for item in items]


def _split(value: str) -> tuple[str, ...]:
    """Symbols: a call such as hash_password(password, salt) becomes hash_password."""
    names = []
    for item in _items(value):
        call = re.match(r"([A-Za-z_][\w.]*)\s*\(", item)
        names.append(call.group(1) if call else item.removesuffix("()"))
    return tuple(name for name in names if name and name.lower() != "none")


def _files(value: str) -> tuple[str, ...]:
    """Paths: notes after a path, such as auth/signup.py (new file), are dropped."""
    paths = (re.sub(r"\([^)]*\)", " ", item).split() for item in _items(value))
    return tuple(path[0].strip("`") for path in paths if path and path[0].lower() != "none")


def _lines_after(body: str, marker: str) -> list[str] | None:
    lines = body.strip().splitlines()
    for index, line in enumerate(lines):
        if line.strip().strip("*`").upper().startswith(marker):
            return lines[index:]
    return None


def parse_plan(body: str) -> FlightPlan | None:
    """Return the plan in a message, None if it isn't one, or raise PlanError."""
    lines = _lines_after(body, "FLIGHT PLAN")
    if lines is None:
        return None

    fields: dict[str, str] = {}
    for line in lines[1:]:
        key, separator, value = line.partition(":")
        key = key.strip().strip("*-` ").lower()
        if separator and key in FIELDS:
            fields[key] = value.strip()

    if not fields.get("task"):
        raise PlanError("Flight plan needs a task line.")
    edit = _files(fields.get("edit", ""))
    if not edit:
        raise PlanError("Flight plan needs an edit line listing the files you will change.")

    return FlightPlan(
        task=fields["task"],
        edit=edit,
        changes=_split(fields.get("changes", "")),
        uses=_split(fields.get("uses", "")),
    )


def parse_landed(body: str) -> bool:
    return _lines_after(body, "LANDED") is not None


def same_symbol(left: str, right: str) -> bool:
    """Plans may say create_session or auth.session.create_session."""
    return left == right or left.endswith(f".{right}") or right.endswith(f".{left}")
