"""Connect one checkout to Detente: its config, the commit gate and the Claude edit gate.

    python -m pilot.install /path/to/checkout --callsign lay-claude --person lay \\
        --vendor "Claude Code" --url http://localhost:8100 --token <pilot token>
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

GATE = Path(__file__).resolve().parent / "gate.py"
MARKER = "detente"


def git_path(root: Path, name: str) -> Path:
    found = subprocess.run(
        ["git", "rev-parse", "--git-path", name],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return root / found


def ignore_locally(root: Path) -> None:
    exclude = git_path(root, "info/exclude")
    exclude.parent.mkdir(parents=True, exist_ok=True)
    lines = exclude.read_text().splitlines() if exclude.exists() else []
    # Nobody edits the last three: Switch Console keeps each agent's settings in .switch/,
    # and Python writes bytecode whenever an agent runs the code.
    for entry in (".detente", ".claude/settings.local.json", ".switch/", "__pycache__/", "*.pyc"):
        if entry not in lines:
            lines.append(entry)
    exclude.write_text("\n".join(lines) + "\n")


def install_commit_gate(root: Path) -> None:
    hook = git_path(root, "hooks/pre-commit")
    hook.parent.mkdir(parents=True, exist_ok=True)
    if hook.exists() and MARKER not in hook.read_text():
        raise SystemExit(f"{hook} already exists. Add this line to it: {sys.executable} {GATE} commit")
    hook.write_text(f'#!/bin/sh\n# {MARKER} commit gate\nexec "{sys.executable}" "{GATE}" commit\n')
    hook.chmod(0o755)


CLAUDE_HOOKS = (
    ("PreToolUse", "Edit|Write|MultiEdit|NotebookEdit", "edit"),
    # Agents edit with shell commands too, so Bash is checked before and after.
    ("PreToolUse", "Bash", "shell-before"),
    ("PostToolUse", "Bash", "shell-after"),
)


def ours(entry: dict, mode: str) -> bool:
    return any(hook.get("command", "").endswith(f'gate.py" {mode}') for hook in entry["hooks"])


def install_edit_gate(root: Path) -> None:
    settings_file = root / ".claude" / "settings.local.json"
    settings_file.parent.mkdir(exist_ok=True)
    settings = json.loads(settings_file.read_text()) if settings_file.exists() else {}
    hooks = settings.setdefault("hooks", {})
    for event, matcher, mode in CLAUDE_HOOKS:
        command = f'"{sys.executable}" "{GATE}" {mode}'
        # Replace our own entry rather than skipping it, so a moved checkout gets fresh paths.
        others = [entry for entry in hooks.get(event, []) if not ours(entry, mode)]
        hook = {"type": "command", "command": command}
        hooks[event] = [*others, {"matcher": matcher, "hooks": [hook]}]
    settings_file.write_text(json.dumps(settings, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--callsign", required=True)
    parser.add_argument("--person", required=True, help="Your username in the chat app")
    parser.add_argument("--vendor", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args()

    root = args.repo.resolve()
    connect(root, {key: getattr(args, key) for key in CONFIG})
    print(f"Connected {root} as {args.callsign}. Now run: python -m pilot.squawk {root}")


CONFIG = ("callsign", "person", "vendor", "url", "token")


def connect(root: Path, config: dict) -> None:
    # First, so a folder that isn't a checkout fails before the token is written into it.
    ignore_locally(root)
    (root / ".detente").write_text(json.dumps(config, indent=2) + "\n")
    install_commit_gate(root)
    install_edit_gate(root)


def disconnect(root: Path) -> list[str]:
    """Undo connect: the gates and the config, never anyone else's hooks. Says what it removed."""
    removed = []
    hook = git_path(root, "hooks/pre-commit")
    if hook.exists() and f"# {MARKER} commit gate" in hook.read_text():
        hook.unlink()
        removed.append("the commit gate")
    settings_file = root / ".claude" / "settings.local.json"
    if settings_file.exists():
        settings = json.loads(settings_file.read_text())
        hooks = settings.get("hooks", {})
        before = json.dumps(hooks)
        for event, _matcher, mode in CLAUDE_HOOKS:
            kept = [entry for entry in hooks.get(event, []) if not ours(entry, mode)]
            if kept:
                hooks[event] = kept
            else:
                hooks.pop(event, None)
        if json.dumps(hooks) != before:
            if not hooks:
                settings.pop("hooks", None)
            if settings:
                settings_file.write_text(json.dumps(settings, indent=2) + "\n")
            else:
                settings_file.unlink()
            removed.append("the Claude Code edit gate")
    config = root / ".detente"
    if config.exists():
        config.unlink()
        removed.append("the callsign and pilot token")
    return removed


if __name__ == "__main__":
    main()
