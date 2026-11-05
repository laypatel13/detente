"""Everything the detente command prints, in the website's colours. Plain text when it isn't a terminal."""

from __future__ import annotations

import json
import sys
from functools import cache
from pathlib import Path
from typing import Any

from rich.console import Console, Group, RenderableType
from rich.padding import Padding
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

HERE = Path(__file__).resolve().parent
# Installed, Roger ships inside the package. In a checkout he lives with the website's art.
ART = (HERE / "art", HERE.parent / "frontend" / "lib" / "art")
HEAD_ROWS = 14  # the same crop the website uses for Roger's head

# The website's colours (frontend/app/globals.css), so the terminal and the radar read as one product.
RUNWAY, BEACON = "#ffc417", "#ff6b62"
THEME = Theme({"brand": f"bold {RUNWAY}", "warn": RUNWAY, "alert": f"bold {BEACON}", "good": "bold"})
TAGS = {
    "COLLISION": "alert",
    "DECISION": "alert",
    "VIOLATION": "alert",
    "GROUND STOP": "alert",
    "TRAFFIC": "warn",
    "FLIGHT PLAN": "bold dim",
}
MOODS = {"collision": "alert", "stop": "alert", "traffic": "warn"}
FLIGHTS = {"hold": "alert", "worried": "warn", "cleared": "good", "landed": "dim"}
SENDER_WIDTH = 12

out = Console(highlight=False, theme=THEME)
err = Console(stderr=True, highlight=False, theme=THEME)


def as_json(result: Any) -> None:
    sys.stdout.write(json.dumps(result, indent=2, default=str) + "\n")


def hint(*commands: str, console: Console | None = None) -> None:
    """Answers end with what to run next, so the command teaches itself."""
    for command in commands:
        (console or out).print(Text.assemble(("─▶ ", "dim"), (command, "brand")))


@cache
def _roger() -> dict:
    for place in ART:
        path = place / "roger.json"
        if path.exists():
            return json.loads(path.read_text())
    return {}


def face(mood: str) -> str:
    return _roger().get("moods", {}).get(mood, {}).get("face", "")


def roger(mood: str) -> list[Text]:
    """Roger's head in half blocks: each character is two of the website's pixels, top and bottom."""
    art = _roger()
    if not art:
        return []
    mood = mood if mood in art["moods"] else "watching"
    colours = {**art["palette"], **art["accent"][mood]}
    rows = art["moods"][mood]["frames"][0][:HEAD_ROWS]
    lines = []
    for top, bottom in zip(rows[0::2], rows[1::2]):
        line = Text()
        for upper, lower in zip(top, bottom):
            if upper == "." and lower == ".":
                line.append(" ")
            elif upper == ".":
                line.append("▄", style=colours[lower])
            elif lower == ".":
                line.append("▀", style=colours[upper])
            else:
                line.append("▀", style=f"{colours[upper]} on {colours[lower]}")
        lines.append(line)
    return lines


def fancy(console: Console) -> bool:
    return console.is_terminal and console.color_system is not None and console.width >= 72


def beside(mood: str, content: list[Text | str] | RenderableType, console: Console | None = None) -> None:
    """Roger with lines, or any block, to his right. Just the content when the terminal can't draw him."""
    console = console or out
    art = roger(mood) if fancy(console) else []
    if isinstance(content, list):
        content = Group(*(line if isinstance(line, Text) else Text.from_markup(line) for line in content))
    if not art:
        console.print(content)
        return
    width = art[0].cell_len
    # Laid out at the width left beside him, so wrapped lines keep their indent.
    wrapped = [
        Text.assemble(*((segment.text, segment.style) for segment in line))
        for line in console.render_lines(content, console.options.update_width(console.width - width - 3), pad=False)
    ]
    for index in range(max(len(art), len(wrapped))):
        row = art[index].copy() if index < len(art) else Text(" " * width)
        if index < len(wrapped):
            row.append("   ")
            row.append_text(wrapped[index])
        console.print(row, no_wrap=True, overflow="crop")


def _body(message: dict) -> tuple[Text, list[str]]:
    tag = message.get("tag") or ""
    lines = message["text"].splitlines()
    if tag and lines and lines[0] == tag:
        lines = lines[1:]
    if not tag:
        return Text(lines[0] if lines else ""), lines[1:]
    first = Text(tag, style=TAGS.get(tag, "bold"))
    if message.get("face"):
        first.append(" " + message["face"], style="dim")
    return first, lines


def _sender(message: dict) -> Text:
    return Text(message["sender"], style="brand" if message["sender"] == "Detente" else "bold")


class Feed:
    """Chat messages as the tower room reads them, with a header whenever the room changes."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or out
        self.room = ""

    def say(self, message: dict, mood: str | None = None) -> None:
        if message["room"] != self.room:
            self.room = message["room"]
            self.console.print()
            self.console.print(Text(f"#{self.room}", style="bold"))
        first, rest = _body(message)
        grid = Table.grid(padding=(0, 1))
        grid.add_column(no_wrap=True, min_width=SENDER_WIDTH)
        grid.add_column()
        grid.add_row(_sender(message), Text("\n").join([first, *(Text(line) for line in rest)]))
        if mood and fancy(self.console):
            beside(mood, grid, self.console)
        else:
            self.console.print(Padding(grid, (0, 0, 0, 2)))


def summary(conflict: dict) -> str:
    """One line on what broke, from the conflict record."""
    breaks = conflict.get("breaks") or {}
    if conflict.get("before") and breaks:
        return (
            f"{conflict['changed_by']} changed {conflict['before']} to {conflict['after']}; "
            f"{conflict['caller']}'s {breaks['file']}:{breaks['line']} {conflict['reason']}"
        )
    return conflict.get("reason") or conflict.get("symbol", "")


def status(state: dict, messages: int, me: str) -> None:
    mood = state.get("mood", "watching")
    style = MOODS.get(mood, "bold")
    out.print(Text.assemble((face(mood) + " ", style), (state.get("headline", ""), style)))

    flights = state.get("flights", [])
    flying = [flight for flight in flights if flight["status"] != "landed"]
    landed = [flight["callsign"] for flight in flights if flight["status"] == "landed"]
    out.print()
    if flying:
        out.print(Text("In the air", style="bold"))
        table = Table(box=None, pad_edge=False, show_edge=False, header_style="dim")
        # The task gets only the width left, so callsigns, statuses and paths stay whole on one line.
        callsign_width = max(len(flight["callsign"]) for flight in flying)
        files_width = max(len(", ".join(flight["files"])) for flight in flying)
        left = out.width - 2 - callsign_width - 8 - files_width - 6
        table.add_column("callsign", no_wrap=True, min_width=callsign_width)
        table.add_column("status", no_wrap=True, min_width=8)
        table.add_column("files", overflow="fold")
        table.add_column("task", no_wrap=True, overflow="ellipsis", max_width=max(left, 12))
        for flight in flying:
            who = Text(flight["callsign"], style="brand" if flight["callsign"] == me else "bold")
            table.add_row(
                who,
                Text(flight["status"], style=FLIGHTS.get(flight["status"], "")),
                ", ".join(flight["files"]),
                flight.get("task", ""),
            )
        out.print(Padding(table, (0, 0, 0, 2)))
    else:
        out.print(Text("No flights in the air.", style="dim"))
    if landed:
        out.print(Text("Landed: " + ", ".join(landed), style="dim"))

    conflicts = [conflict for conflict in state.get("conflicts", []) if conflict["status"] == "open"]
    out.print()
    if conflicts:
        out.print(Text("Open conflicts", style="alert"))
        for conflict in conflicts:
            out.print(Padding(Text.assemble((conflict["id"], "bold"), "  ", summary(conflict)), (0, 0, 0, 2)))
    else:
        out.print(Text("No open conflicts.", style="dim"))

    if messages and state.get("feed"):
        out.print()
        out.print(Text("Latest messages", style="bold"))
        feed = Feed(out)
        for message in state["feed"][-messages:]:
            feed.say(message)


def conflict(record: dict) -> None:
    style = "alert" if record["status"] == "open" else "good"
    out.print(Text.assemble((record["id"], "bold"), "  ", (record["status"], style)))
    breaks = record.get("breaks") or {}
    if record.get("before") and breaks:
        # Built as Text, not markup: code can hold square brackets.
        out.print(
            Text.assemble(
                f"{record['changed_by']} changed ",
                (record["before"], "bold"),
                " to ",
                (record["after"], "bold"),
                f" in {record.get('changed_file', '')}",
            )
        )
        if record.get("commit"):
            out.print(Text(f"Already on main in {record['commit']}.", style="warn"))
        out.print(f"{record['caller']}'s {breaks['file']}:{breaks['line']} {record['reason']}")
        if breaks.get("code"):
            out.print(Padding(Text(breaks["code"], style="dim"), (0, 0, 0, 4)))
    else:
        out.print(summary(record))

    options = record.get("options") or []
    if options:
        out.print()
        out.print(Text("Fixes on offer", style="bold"))
        table = Table(box=None, pad_edge=False, show_header=False)
        table.add_column(style="brand", no_wrap=True)
        table.add_column()
        table.add_column(style="dim", no_wrap=True)
        for option in options:
            table.add_row(option["key"], option["text"], f"{option['agent']} edits")
        out.print(Padding(table, (0, 0, 0, 2)))
    out.print()
    decision = record.get("decision")
    if decision:
        picked = next((option for option in options if option["key"] == decision["option"]), None)
        what = f": {picked['text']}" if picked else ""
        out.print(f"Decided by {decision['by']} ({decision['option']}){what}.")
    elif record["status"] == "open":
        out.print(Text(f"Nobody has picked yet. Reply A or B in #{record['id']} in Switch.", style="warn"))
