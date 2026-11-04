"""Parse the flight plans and landings pilots post in the tower room."""

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


def _split(value: str) -> tuple[str, ...]:
    items = (item.strip().strip("`").removesuffix("()") for item in value.split(","))
    return tuple(item for item in items if item and item.lower() != "none")


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
    edit = _split(fields.get("edit", ""))
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
