import io
import json
import subprocess
from pathlib import Path

import pytest

from pilot import gate, install
from pilot.squawk import changed_files


def git(root: Path, *args: str) -> None:
    identity = ("-c", "user.name=test", "-c", "user.email=test@example.com")
    subprocess.run(["git", *identity, *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "cart").mkdir()
    (tmp_path / "cart" / "totals.py").write_text("def cart_total(lines):\n    return 0\n")
    (tmp_path / "cart" / "items.py").write_text("x = 1\n")
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "base")
    config = {"url": "http://detente.test", "callsign": "lay-claude", "token": "t"}
    (tmp_path / ".detente").write_text(json.dumps(config))
    install.ignore_locally(tmp_path)
    return tmp_path


def run_shell(repo, monkeypatch, command, cleared=()):
    """Run a 'shell command' between the two Bash hooks. Returns the exit code and what was asked."""
    asked = []

    def refused(config, files):
        asked.extend(files)
        return {path: f"No clearance for {path}." for path in files if path not in cleared}

    monkeypatch.setattr(gate, "refused", refused)
    hook = json.dumps({"cwd": str(repo), "tool_use_id": "toolu_1"})
    monkeypatch.setattr("sys.stdin", io.StringIO(hook))
    gate.before_shell()
    command()
    monkeypatch.setattr("sys.stdin", io.StringIO(hook))
    return gate.after_shell(), asked


def test_console_files_and_bytecode_are_not_edits(repo):
    (repo / ".switch" / "config").mkdir(parents=True)
    (repo / ".switch" / "config" / "lay-claude.json").write_text("{}")
    (repo / "cart" / "__pycache__").mkdir()
    (repo / "cart" / "__pycache__" / "totals.cpython-312.pyc").write_bytes(b"\0")
    assert changed_files(repo, "HEAD") == []


def test_a_read_only_command_asks_nothing(repo, monkeypatch):
    assert run_shell(repo, monkeypatch, lambda: None) == (0, [])


def test_a_shell_edit_to_an_uncleared_file_is_sent_back(repo, monkeypatch, capsys):
    code, asked = run_shell(repo, monkeypatch, lambda: (repo / "cart/items.py").write_text("x = 2\n"))
    assert (code, asked) == (2, ["cart/items.py"])
    assert "No clearance for cart/items.py." in capsys.readouterr().err


def test_a_shell_edit_to_a_cleared_file_passes(repo, monkeypatch):
    def edit():
        (repo / "cart/totals.py").write_text("def cart_total(lines, discount):\n    return 0\n")

    assert run_shell(repo, monkeypatch, edit, cleared=["cart/totals.py"]) == (0, ["cart/totals.py"])


def test_only_files_the_command_changed_are_checked(repo, monkeypatch):
    (repo / "cart/totals.py").write_text("changed earlier, already cleared\n")
    code, asked = run_shell(repo, monkeypatch, lambda: (repo / "new.py").write_text("y = 1\n"))
    assert (code, asked) == (2, ["new.py"])


def test_undoing_a_change_is_not_an_edit(repo, monkeypatch):
    (repo / "cart/items.py").write_text("x = 2\n")
    assert run_shell(repo, monkeypatch, lambda: git(repo, "restore", "cart/items.py")) == (0, [])


def test_install_adds_each_claude_hook_once(repo):
    install.install_edit_gate(repo)
    install.install_edit_gate(repo)
    hooks = json.loads((repo / ".claude" / "settings.local.json").read_text())["hooks"]
    matchers = {event: [entry["matcher"] for entry in entries] for event, entries in hooks.items()}
    assert matchers == {
        "PreToolUse": ["Edit|Write|MultiEdit|NotebookEdit", "Bash"],
        "PostToolUse": ["Bash"],
    }
