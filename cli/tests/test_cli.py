import io
import json
import subprocess
from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

from cli import render, showcase
from cli.app import app
from cli.tower import Refused, Tower, Unreachable

RECORDINGS = Path(__file__).resolve().parents[2] / "frontend" / "app" / "showcase" / "_story" / "recordings"
# A real recorded moment: three flights, one of them worried, and a collision nobody has picked a fix for.
OPEN_CONFLICT = json.loads((RECORDINGS / "a.json").read_text())["frames"][7]["state"]
CONNECT = ["--callsign", "lay-claude", "--person", "lay", "--vendor", "Claude Code", "--url", "http://localhost:8100"]

runner = CliRunner()
# Rich wraps at the terminal's width, which differs between machines and CI. Fix it, so a phrase
# the tests look for never splits across two lines.
render.out.width = render.err.width = 200


def detente(*args: str):
    return runner.invoke(app, list(args), catch_exceptions=False)


def play(answers: str) -> str:
    console = Console(file=io.StringIO(), width=100)
    showcase.run(pace=0, console=console, answers=io.StringIO(answers))
    return console.file.getvalue()


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    return tmp_path.resolve()


@pytest.fixture
def asked(monkeypatch):
    """A tower answering from the recorded moment. Remembers which files it was asked about."""
    asked: dict = {}

    def refused(_tower, callsign, files):
        asked["files"] = files
        return {path: f"No clearance for {path}." for path in files if path.startswith("cart/")}

    monkeypatch.setattr(Tower, "state", lambda _tower: OPEN_CONFLICT)
    monkeypatch.setattr(Tower, "conflict", lambda _tower, name: next(
        conflict for conflict in OPEN_CONFLICT["conflicts"] if conflict["id"] == name))
    monkeypatch.setattr(Tower, "refused", refused)
    return asked


@pytest.fixture
def connected(repo, asked, monkeypatch):
    monkeypatch.setenv("DETENTE_TOKEN", "pilot-token")
    assert detente("connect", "-r", str(repo), *CONNECT).exit_code == 0
    return repo


def test_the_showcase_plays_the_fix_the_person_picks():
    a, b = play("A\n"), play("b\n")
    for run in (a, b):
        assert "missing required argument ttl" in run
        assert "the code fits again" in run
        assert run.count("LANDED") == 3
    assert "lay-claude makes the edit" in a and "a-codex makes the edit" not in a
    assert "a-codex makes the edit" in b and "lay-claude makes the edit" not in b


def test_the_showcase_asks_again_until_it_gets_a_or_b():
    run = play("maybe\nB\n")
    assert run.count("Reply A or B") == 2
    assert "a-codex makes the edit" in run


def test_the_showcase_picks_a_when_nobody_answers():
    assert "lay-claude makes the edit" in play("")


def test_connect_checks_the_token_before_writing_the_gates(repo, asked, monkeypatch):
    monkeypatch.setenv("DETENTE_TOKEN", "pilot-token")
    result = detente("connect", "-r", str(repo), *CONNECT)
    assert result.exit_code == 0
    assert "Connected" in result.output
    assert asked["files"] == []
    assert json.loads((repo / ".detente").read_text())["token"] == "pilot-token"
    assert "detente commit gate" in (repo / ".git" / "hooks" / "pre-commit").read_text()


def test_connect_writes_nothing_when_the_tower_refuses_the_token(repo, monkeypatch):
    def refuse(_tower, callsign, files):
        raise Refused("The tower at http://localhost:8100 refused the pilot token.")

    monkeypatch.setattr(Tower, "refused", refuse)
    monkeypatch.setenv("DETENTE_TOKEN", "wrong")
    result = detente("connect", "-r", str(repo), *CONNECT)
    assert result.exit_code == 3
    assert "refused the pilot token" in result.output
    assert not (repo / ".detente").exists()


def test_connect_still_connects_when_the_tower_is_down(repo, monkeypatch):
    def down(_tower, callsign, files):
        raise Unreachable("No tower answering at http://localhost:8100.")

    monkeypatch.setattr(Tower, "refused", down)
    monkeypatch.setenv("DETENTE_TOKEN", "pilot-token")
    result = detente("connect", "-r", str(repo), *CONNECT)
    assert result.exit_code == 0
    assert "refuse every edit until it does" in " ".join(result.output.split())
    assert (repo / ".detente").exists()


def test_connect_asks_nothing_without_a_terminal(repo, monkeypatch):
    monkeypatch.setenv("DETENTE_TOKEN", "pilot-token")
    result = detente("connect", "-r", str(repo), "--person", "lay")
    assert result.exit_code == 2
    assert "--callsign is needed" in result.output


def test_connect_refuses_a_folder_that_isnt_a_checkout(tmp_path, monkeypatch):
    monkeypatch.setenv("DETENTE_TOKEN", "pilot-token")
    result = detente("connect", "-r", str(tmp_path), *CONNECT)
    assert result.exit_code == 2
    assert "isn't in a git checkout" in result.output
    assert not (tmp_path / ".detente").exists()


def test_commands_on_the_tower_need_a_connected_checkout(repo):
    for command in ("status", "watch", "conflict", "doctor"):
        result = detente(command, "-r", str(repo))
        assert result.exit_code in (2, 3), command
    assert "isn't connected to a tower yet" in detente("status", "-r", str(repo)).output


def test_status_shows_the_flights_and_the_open_conflict(connected):
    result = detente("status", "-r", str(connected))
    assert result.exit_code == 0
    assert "worried" in result.output
    assert "conflict-create-session-3f1a" in result.output
    assert "detente conflict conflict-create-session-3f1a" in result.output


def test_status_json_is_the_towers_own_state(connected):
    assert json.loads(detente("status", "-r", str(connected), "--json").output) == OPEN_CONFLICT


def test_conflict_shows_the_open_one_and_its_fixes(connected):
    result = detente("conflict", "-r", str(connected))
    assert result.exit_code == 0
    assert "Give ttl a default" in result.output
    assert "Nobody has picked yet" in result.output


def test_check_names_files_from_where_you_stand(connected, asked, monkeypatch):
    (connected / "cart").mkdir()
    monkeypatch.chdir(connected / "cart")
    result = detente("check", "totals.py", "../billing/refunds.py")
    assert asked["files"] == ["cart/totals.py", "billing/refunds.py"]
    assert result.exit_code == 1
    assert "✗ cart/totals.py" in result.output
    assert "✓ billing/refunds.py" in result.output


def test_a_tower_that_cant_answer_points_to_doctor(connected, monkeypatch):
    def down(_tower):
        raise Unreachable("No tower answering at http://localhost:8100.")

    monkeypatch.setattr(Tower, "state", down)
    result = detente("status", "-r", str(connected))
    assert result.exit_code == 3
    assert "detente doctor" in result.output


def test_doctor_finds_a_gate_pointing_at_a_python_thats_gone(connected):
    assert detente("doctor", "-r", str(connected)).exit_code == 0
    hook = connected / ".git" / "hooks" / "pre-commit"
    hook.write_text('#!/bin/sh\n# detente commit gate\nexec "/gone/python" "/gone/gate.py" commit\n')
    result = detente("doctor", "-r", str(connected))
    assert result.exit_code == 3
    assert "✗ Commit gate" in result.output


def test_disconnect_removes_only_detentes_gates(connected):
    settings_file = connected / ".claude" / "settings.local.json"
    settings = json.loads(settings_file.read_text())
    theirs = {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo mine"}]}
    settings["hooks"]["PreToolUse"].append(theirs)
    settings_file.write_text(json.dumps(settings))

    result = detente("disconnect", "-r", str(connected), "--yes")
    assert result.exit_code == 0
    assert not (connected / ".detente").exists()
    assert not (connected / ".git" / "hooks" / "pre-commit").exists()
    assert json.loads(settings_file.read_text())["hooks"] == {"PreToolUse": [theirs]}


def test_home_outside_a_checkout_points_to_the_showcase(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = detente()
    assert result.exit_code == 0
    assert "Not in a git checkout" in result.output
    assert "detente showcase" in result.output
