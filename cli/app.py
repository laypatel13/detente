"""The detente commands. Each is a thin front over the pilot code or one question to the tower: the
tower decides, this file only asks and prints. Decisions stay in chat, so nothing here picks a fix."""

from __future__ import annotations

import logging
import os
import shutil
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated, NoReturn, Optional

import typer
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text
from typer import rich_utils

from pilot import install, squawk

from . import checkout
from . import render as R
from . import showcase as S
from .tower import Refused, Tower, TowerError, Unreachable

app = typer.Typer(
    add_completion=False,
    rich_markup_mode="rich",
    pretty_exceptions_show_locals=False,  # a crash must never print the pilot token from a local variable
    help="Traffic control for coding agents. Detente catches the moment one agent's change breaks code "
    "another agent is writing, before anyone pushes.",
)

# The help screen in the website's colours too, like every other screen.
rich_utils.STYLE_OPTION = rich_utils.STYLE_SWITCH = f"bold {R.RUNWAY}"
rich_utils.STYLE_COMMANDS_TABLE_FIRST_COLUMN = f"bold {R.RUNWAY}"
rich_utils.STYLE_USAGE = R.RUNWAY

EXIT_FINDING, EXIT_USAGE, EXIT_ENV = 1, 2, 3
DEFAULT_URL = "http://localhost:8100"

Repo = Annotated[
    Path, typer.Option("--repo", "-r", help="The checkout to use (default: the one you're in).", show_default=False)
]
Json = Annotated[bool, typer.Option("--json", help="Print the raw result as JSON, for scripts.")]


def fail(message: str, code: int = EXIT_USAGE) -> NoReturn:
    R.err.print(Text.assemble(("error ", "alert"), message))
    raise typer.Exit(code)


def installed_version() -> str:
    try:
        return version("detente")
    except PackageNotFoundError:
        return "from source"


def connected(repo: Path) -> tuple[Path, dict]:
    """The checkout a command is about and its config, or a clear way out."""
    top = checkout.root(repo)
    if top is None:
        fail(f"{checkout.short(repo.resolve())} isn't in a git checkout. cd into your repo, or pass --repo.")
    config = checkout.config(top)
    if config is None:
        fail(f"{checkout.short(top)} isn't connected to a tower yet. Run: detente connect")
    return top, config


def tower_of(config: dict, timeout: float | None = None) -> Tower:
    return Tower(config["url"], config["token"], *(() if timeout is None else (timeout,)))


def ask(question, *args):
    """One question to the tower. When it can't answer, say why and stop."""
    try:
        return question(*args)
    except (Unreachable, Refused) as error:
        fail(f"{error} Check with: detente doctor", EXIT_ENV)
    except TowerError as error:
        fail(str(error))


# ---------- home -----------------------------------------------------------------------------

# What `detente` alone lists: the commands people use most. `detente --help` has every one.
HOME_COMMANDS = (
    ("detente showcase", "watch a real recorded run, no setup"),
    ("detente connect", "connect this checkout to your team's tower"),
    ("detente watch", "keep the tower told what this checkout changes"),
    ("detente status", "flights in the air and open conflicts"),
    ("detente check <file>", "is this checkout cleared to edit it?"),
    ("detente doctor", "check the gates, the token and the tower"),
)


def _show_version(value: bool) -> None:
    if value:
        R.out.print(f"detente {installed_version()}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def _home(
    ctx: typer.Context,
    _version: Annotated[
        bool, typer.Option("--version", callback=_show_version, is_eager=True, help="Print the version.")
    ] = False,
) -> None:
    if ctx.invoked_subcommand is None:
        home()


def home() -> None:
    """Roger, where you are (one quick question to the tower, never a long wait), and what to run next."""
    top = checkout.root(Path.cwd())
    config = checkout.config(top) if top else None
    mood = "resting"
    if config:
        where = f"[bold]{config['callsign']}[/] on {checkout.short(top)}"
        try:
            state = tower_of(config, timeout=2).state()
            mood = state.get("mood", "watching")
            flying = sum(flight["status"] != "landed" for flight in state.get("flights", []))
            open_conflicts = sum(conflict["status"] == "open" for conflict in state.get("conflicts", []))
            style = R.MOODS.get(mood, "bold")
            here = [
                where,
                Text.assemble((f"{R.face(mood)} ", style), (state.get("headline", ""), style)),
                f"[dim]{flying} in the air · {open_conflicts} open conflicts · tower at {config['url']}[/]",
            ]
        except TowerError as error:
            here = [where, Text(str(error), style="alert"), "[dim]detente doctor says what's wrong[/]"]
    elif top:
        here = [f"[bold]{checkout.short(top)}[/] isn't connected to a tower.", "[dim]detente connect sets it up[/]"]
    else:
        here = ["[dim]Not in a git checkout: cd into your repo,[/]", "[dim]or watch a real recorded run: detente showcase[/]"]
    R.beside(mood, ["", "[brand]Detente[/] [dim]· traffic control for coding agents[/]", *here])
    R.out.print()
    table = Table(box=None, pad_edge=False, show_header=False)
    table.add_column(style="brand", no_wrap=True)
    table.add_column(style="dim")
    for command, what in HOME_COMMANDS:
        table.add_row(command, what)
    R.out.print(table)
    R.out.print("\n[dim]Decisions happen in chat: reply A or B in the conflict room.\nEvery command: detente --help[/]")


# ---------- start ----------------------------------------------------------------------------


@app.command(rich_help_panel="Start")
def connect(
    callsign: Annotated[Optional[str], typer.Option(help="The agent's name in Switch, e.g. lay-claude.")] = None,
    person: Annotated[Optional[str], typer.Option(help="Your username in the chat app, e.g. lay.")] = None,
    vendor: Annotated[Optional[str], typer.Option(help='The agent tool: "Claude Code", "Codex", "OpenCode"…')] = None,
    url: Annotated[Optional[str], typer.Option(help=f"Your tower's address, e.g. {DEFAULT_URL}.")] = None,
    token: Annotated[
        Optional[str],
        typer.Option(help="The pilot token. Leave it out to be asked, so it stays out of your shell history, "
                     "or set DETENTE_TOKEN."),
    ] = None,
    repo: Repo = Path("."),
) -> None:
    """Connect a checkout to your team's tower: its gates, its callsign and the pilot token.

    Asks for anything you leave out. The token is checked with the tower before anything is written.
    """
    top = checkout.root(repo)
    if top is None:
        fail(f"{checkout.short(repo.resolve())} isn't in a git checkout. cd into your repo, or pass --repo.")
    interactive = sys.stdin.isatty()

    def need(value: str | None, flag: str, question: str, default: str | None = None, secret: bool = False) -> str:
        if value:
            return value
        if not interactive:
            fail(f"--{flag} is needed: there's no terminal to ask in.")
        answer = Prompt.ask(question, default=default, password=secret, console=R.out)
        if not answer:
            fail(f"No {flag} given.")
        return answer

    callsign = need(callsign, "callsign", "Agent's name in Switch (callsign)")
    person = need(person, "person", "Your username in the chat app")
    vendor = need(vendor, "vendor", "Agent tool", default="Claude Code")
    url = need(url, "url", "Tower address", default=DEFAULT_URL).rstrip("/")
    token = need(token or os.environ.get("DETENTE_TOKEN"), "token", "Pilot token", secret=True)

    # One harmless question first, so a mistyped token shows up now and not at the agent's first edit.
    reachable = True
    try:
        Tower(url, token).refused(callsign, [])
    except Refused as error:
        fail(f"{error} Nothing was changed. The token is DETENTE_PILOT_TOKEN in the tower's .env.", EXIT_ENV)
    except TowerError:
        reachable = False

    again = checkout.config(top) is not None
    install.connect(top, {"callsign": callsign, "person": person, "vendor": vendor, "url": url, "token": token})
    R.out.print(
        f"[good]✓[/] {'Reconnected' if again else 'Connected'} {checkout.short(top)} as [bold]{callsign}[/]"
        f" · tower at {url}"
    )
    if not reachable:
        R.out.print(
            f"[warn]No tower answering at {url} right now.[/] The gates refuse every edit until it does."
        )
    if vendor.lower() != "claude code":
        R.out.print(
            f"[dim]{vendor} doesn't run Claude Code's hooks, so the commit gate guards this checkout. "
            "The agent can ask first with detente check <file>.[/]"
        )
    R.out.print()
    R.hint(f"detente watch{'' if repo == Path('.') else f' -r {checkout.short(top)}'}   (leave it running)")
    R.out.print("[dim]Then add the agent to the tower room in Switch. It learns the rules from the room.[/]")


@app.command(rich_help_panel="Start")
def watch(repo: Repo = Path(".")) -> None:
    """Keep the tower told what this checkout's unpushed work changes and calls. Leave it running.

    It also fetches main every few seconds while there's unpushed work, so a teammate's push that breaks
    this work collides too. Ctrl+C stops it.
    """
    top, config = connected(repo)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    R.out.print(
        f"Watching [bold]{config['callsign']}[/] on {checkout.short(top)} · tower at {config['url']}"
        "  [dim]Ctrl+C stops[/]"
    )
    try:
        squawk.watch(top, config)
    except KeyboardInterrupt:
        R.out.print("\nStopped watching.")


@app.command(rich_help_panel="Start")
def doctor(repo: Repo = Path("."), json_out: Json = False) -> None:
    """Check this checkout's setup: git, its config, both gates, and that the tower answers and takes the token."""
    checks: list[tuple[bool, str, str]] = []
    checks.append((sys.version_info >= (3, 12), "Python", sys.version.split()[0]))
    checks.append((shutil.which("git") is not None, "git", shutil.which("git") or "not found"))
    top = checkout.root(repo)
    checks.append((top is not None, "Git checkout", checkout.short(top) if top else "not in one: cd into your repo"))
    config = checkout.config(top) if top else None
    if top:
        checks.append(
            (config is not None, "Connected", f"as {config['callsign']}" if config else "not yet: run detente connect")
        )
    if config:
        for what, gate in (("Commit gate", checkout.commit_gate), ("Claude Code edit gate", checkout.edit_gate)):
            ok, detail = gate(top)
            checks.append((ok, what, detail))
        try:
            tower_of(config).refused(config["callsign"], [])
            checks.append((True, "Tower", f"answers at {config['url']} and takes the pilot token"))
        except TowerError as error:
            checks.append((False, "Tower", str(error)))
    healthy = all(ok for ok, _, _ in checks)
    if json_out:
        R.as_json({"ok": healthy, "checks": [{"ok": ok, "check": what, "detail": detail} for ok, what, detail in checks]})
    else:
        for ok, what, detail in checks:
            mark = Text("✓", style="good") if ok else Text("✗", style="alert")
            R.out.print(Text.assemble(mark, " ", what, "  ", (detail, "dim")))
    if not healthy:
        raise typer.Exit(EXIT_ENV)


@app.command(rich_help_panel="Start")
def disconnect(
    repo: Repo = Path("."),
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Don't ask first.")] = False,
) -> None:
    """Take a checkout off the tower: removes its gates and its config. Your code and commits aren't touched."""
    top, config = connected(repo)
    if not yes:
        if not sys.stdin.isatty():
            fail("Add --yes to disconnect: there's no terminal to ask in.")
        if not Confirm.ask(f"Disconnect {checkout.short(top)} ({config['callsign']}) from its tower?", console=R.out):
            R.out.print("Still connected.")
            return
    for what in install.disconnect(top):
        R.out.print(f"[good]✓[/] Removed {what}")
    R.out.print(f"{checkout.short(top)} is off the tower. Stop its detente watch if one is running.")


# ---------- the tower ------------------------------------------------------------------------


@app.command(rich_help_panel="The tower")
def status(
    repo: Repo = Path("."),
    messages: Annotated[int, typer.Option("--messages", "-n", help="How many recent messages to show.")] = 5,
    json_out: Json = False,
) -> None:
    """What the tower sees right now: flights in the air, open conflicts and the latest messages."""
    _top, config = connected(repo)
    state = ask(tower_of(config).state)
    if json_out:
        R.as_json(state)
        return
    R.status(state, messages, config["callsign"])
    R.out.print()
    open_conflicts = [conflict["id"] for conflict in state.get("conflicts", []) if conflict["status"] == "open"]
    R.hint(f"detente conflict {open_conflicts[0]}" if open_conflicts else "detente check <file>")


@app.command(rich_help_panel="The tower")
def conflict(
    conflict_id: Annotated[
        Optional[str],
        typer.Argument(metavar="[CONFLICT]", help="A conflict's name, e.g. conflict-create-session-3f1a. "
                       "Leave it out for the open one.", show_default=False),
    ] = None,
    repo: Repo = Path("."),
    json_out: Json = False,
) -> None:
    """One conflict in full: what changed, what it breaks, the fixes on offer and who picked."""
    _top, config = connected(repo)
    tower = tower_of(config)
    if conflict_id is None:
        state = ask(tower.state)
        open_conflicts = [conflict["id"] for conflict in state.get("conflicts", []) if conflict["status"] == "open"]
        if not open_conflicts:
            if json_out:
                R.as_json(None)
            else:
                R.out.print("No open conflicts.")
            return
        if len(open_conflicts) > 1:
            fail(f"{len(open_conflicts)} conflicts are open: {', '.join(open_conflicts)}. Name one.")
        conflict_id = open_conflicts[0]
    record = ask(tower.conflict, conflict_id)
    if json_out:
        R.as_json(record)
        return
    R.conflict(record)


@app.command(rich_help_panel="The tower")
def check(
    files: Annotated[list[Path], typer.Argument(metavar="FILE...", help="Files to check, e.g. billing/refunds.py.")],
    repo: Repo = Path("."),
    json_out: Json = False,
) -> None:
    """Is this checkout cleared to edit these files? Exits 1 if any isn't.

    For agents that don't run Claude Code's hooks, and for scripts: ask before editing.
    """
    top, config = connected(repo)
    paths = []
    for name in files:
        path = checkout.in_checkout(top, name)
        if path is None:
            fail(f"{name} isn't in {checkout.short(top)}.")
        paths.append(path)
    refused = ask(tower_of(config).refused, config["callsign"], paths)
    if json_out:
        cleared = [path for path in paths if path not in refused]
        R.as_json({"callsign": config["callsign"], "cleared": cleared, "refused": refused})
    else:
        for path in paths:
            if path in refused:
                R.out.print(Text.assemble(("✗ ", "alert"), (path, "bold"), "  ", (refused[path], "dim")))
            else:
                R.out.print(Text.assemble(("✓ ", "good"), (path, "bold"), "  ", ("cleared", "dim")))
    if refused:
        raise typer.Exit(EXIT_FINDING)


# ---------- the showcase, kept apart from your checkouts --------------------------------------


@app.command(rich_help_panel="Showcase")
def showcase(fast: Annotated[bool, typer.Option("--fast", help="Play without pauses.")] = False) -> None:
    """A real recorded run: two agents collide, you pick the fix, and the flights land.

    No tower, no setup, and nothing here touches your checkouts.
    """
    try:
        S.run(pace=0 if fast else 1)
    except KeyboardInterrupt:
        R.out.print()
