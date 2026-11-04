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
    for entry in (".detente", ".claude/settings.local.json"):
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


def install_edit_gate(root: Path) -> None:
    settings_file = root / ".claude" / "settings.local.json"
    settings_file.parent.mkdir(exist_ok=True)
    settings = json.loads(settings_file.read_text()) if settings_file.exists() else {}
    command = f'"{sys.executable}" "{GATE}" edit'
    hooks = settings.setdefault("hooks", {}).setdefault("PreToolUse", [])
    if not any(MARKER in json.dumps(entry) and "gate.py" in json.dumps(entry) for entry in hooks):
        hooks.append(
            {
                "matcher": "Edit|Write|MultiEdit|NotebookEdit",
                "hooks": [{"type": "command", "command": command}],
            }
        )
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
    config = {key: getattr(args, key) for key in ("callsign", "person", "vendor", "url", "token")}
    (root / ".detente").write_text(json.dumps(config, indent=2) + "\n")
    ignore_locally(root)
    install_commit_gate(root)
    install_edit_gate(root)
    print(f"Connected {root} as {args.callsign}. Now run: python -m pilot.squawk {root}")


if __name__ == "__main__":
    main()
