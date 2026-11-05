"""The showcase in the terminal: a real recorded run, played back. Nothing here touches your checkouts."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import TextIO

from rich.console import Console
from rich.text import Text

from . import render as R

HERE = Path(__file__).resolve().parent
# Installed, the recordings ship inside the package. In a checkout they live with the web showcase.
PLACES = (HERE / "recordings", HERE.parent / "frontend" / "app" / "showcase" / "_story" / "recordings")
REPO = "https://github.com/laypatel13/detente"
LONGEST_PAUSE = 2.5
BETWEEN_MESSAGES = 0.4


def recording(choice: str) -> list[dict]:
    for place in PLACES:
        path = place / f"{choice.lower()}.json"
        if path.exists():
            return json.loads(path.read_text())["frames"]
    raise SystemExit("The showcase recordings are missing from this install.")


def decided_at(frames: list[dict]) -> int:
    return next(
        index
        for index, frame in enumerate(frames)
        if any(conflict["status"] == "decided" for conflict in frame["state"]["conflicts"])
    )


class Player:
    def __init__(self, console: Console, pace: float) -> None:
        self.console = console
        self.pace = pace
        self.feed = R.Feed(console)
        self.shown = 0
        self.clock: float | None = None

    def wait(self, seconds: float) -> None:
        if seconds > 0 and self.pace > 0:
            time.sleep(seconds * self.pace)

    def play(self, frames: list[dict]) -> None:
        for frame in frames:
            if self.clock is not None:
                self.wait(min(frame["at"] - self.clock, LONGEST_PAUSE))
            self.clock = frame["at"]
            for message in sorted(frame["state"]["feed"], key=lambda message: message["id"]):
                if message["id"] > self.shown:
                    self.shown = message["id"]
                    # The person's own pick is typed here, not replayed.
                    if message["sender"] != "you":
                        self.feed.say(message, mood="collision" if message["tag"] == "COLLISION" else None)
                        self.wait(BETWEEN_MESSAGES)

    def ask(self, answers: TextIO) -> str:
        self.console.print()
        self.console.print(Text.assemble(("You're the person on duty. ", "bold"), "Reply A or B: "), end="")
        while True:
            line = answers.readline()
            if not line:
                self.console.print("A (no answer, so A)")
                return "A"
            if not answers.isatty():
                self.console.print(line.rstrip("\n"))
            pick = line.strip().upper()
            if pick in ("A", "B"):
                return pick
            self.console.print("Reply A or B: ", end="")


def run(pace: float = 1.0, console: Console | None = None, answers: TextIO | None = None) -> None:
    console = console or R.out
    player = Player(console, pace)
    R.beside(
        "watching",
        [
            "",
            "[brand]The Detente showcase[/]",
            "Three coding agents on three laptops work on one project.",
            "They can't see each other's code. Detente can.",
            "[dim]A real run, recorded through Switch. Nothing here touches your checkouts.[/]",
        ],
        console,
    )
    first = recording("A")
    # Both recordings are the same flight until the person picks, then each is its own real run.
    player.play(first[: decided_at(first)])
    choice = player.ask(answers or sys.stdin)
    chosen = recording(choice)
    player.play(chosen[decided_at(chosen) :])
    console.print()
    R.beside(
        "resolved",
        ["", "[bold]Nobody pushed broken code.[/]", "Run Detente for your own team:", "", REPO],
        console,
    )
    console.print()
    R.hint("uv tool install detente", "detente connect", console=console)
