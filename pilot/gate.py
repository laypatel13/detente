#!/usr/bin/env python3
"""Ask Detente before an edit or commit. Standard library only, and it fails closed.

    gate.py edit     Claude Code PreToolUse hook: reads the hook's JSON on stdin.
    gate.py commit   git pre-commit hook: checks every staged file.
"""

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

CONFIG = ".detente"
TIMEOUT_SECONDS = 5


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def refused(config: dict, files: list[str]) -> dict[str, str]:
    request = urllib.request.Request(
        f"{config['url']}/clearance",
        data=json.dumps({"callsign": config["callsign"], "files": files}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['token']}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.load(response)["refused"]
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as error:
        return {path: f"Can't reach Detente at {config['url']} ({error})." for path in files}


def load_config(root: Path) -> dict:
    return json.loads((root / CONFIG).read_text())


def check_edit() -> int:
    hook = json.load(sys.stdin)
    target = hook.get("tool_input", {}).get("file_path")
    if not target:
        return 0
    start = Path(hook.get("cwd") or ".").resolve()
    root = Path(git(start, "rev-parse", "--show-toplevel"))
    path = (start / target).resolve()
    if not path.is_relative_to(root):
        return 0

    relative = path.relative_to(root).as_posix()
    if relative == CONFIG:
        print("The Detente config can't be edited by an agent.", file=sys.stderr)
        return 2
    reasons = refused(load_config(root), [relative])
    if reasons:
        # Exit code 2 blocks the tool call and shows this text to the agent.
        print(reasons[relative], file=sys.stderr)
        return 2
    return 0


def check_commit() -> int:
    root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel"))
    files = git(root, "diff", "--cached", "--name-only").splitlines()
    if not files:
        return 0
    reasons = refused(load_config(root), files)
    for reason in reasons.values():
        print(f"detente: {reason}", file=sys.stderr)
    return 1 if reasons else 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "edit":
        return check_edit()
    if mode == "commit":
        return check_commit()
    print(__doc__, file=sys.stderr)
    return 64


if __name__ == "__main__":
    sys.exit(main())
