#!/usr/bin/env python3
"""Ask Detente before an edit or commit. Standard library only, and it fails closed.

    gate.py edit           Claude Code PreToolUse hook on edits: reads the hook's JSON on stdin.
    gate.py shell-before   Claude Code PreToolUse hook on Bash: notes what's changed so far.
    gate.py shell-after    Claude Code PostToolUse hook on Bash: checks what the command changed.
    gate.py commit         git pre-commit hook: checks every staged file.
"""

import hashlib
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


def dirty(root: Path) -> dict[str, str]:
    """Each changed or new file, with a hash of what's in it now ("" once it's deleted)."""
    # Not git(): its strip() would eat the space that starts " M path".
    listing = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=root, capture_output=True, text=True, check=True,
    ).stdout
    found, renamed = {}, False
    for entry in listing.split("\0"):
        if renamed or not entry:
            renamed = False
            continue
        path, file = entry[3:], root / entry[3:]
        renamed = entry[0] in "RC"  # a rename's old path comes next
        found[path] = hashlib.sha1(file.read_bytes()).hexdigest() if file.is_file() else ""
    return found


def shell_record(hook: dict) -> tuple[Path, Path]:
    start = Path(hook.get("cwd") or ".").resolve()
    root = Path(git(start, "rev-parse", "--show-toplevel"))
    folder = Path(git(root, "rev-parse", "--absolute-git-dir")) / "detente"
    return root, folder / f"shell-{hook.get('tool_use_id') or 'last'}.json"


def before_shell() -> int:
    root, record = shell_record(json.load(sys.stdin))
    record.parent.mkdir(exist_ok=True)
    record.write_text(json.dumps(dirty(root)))
    return 0


def after_shell() -> int:
    """A shell command can edit files too. It has already run, so ask the agent to undo it."""
    root, record = shell_record(json.load(sys.stdin))
    if not record.exists():
        return 0
    before = json.loads(record.read_text())
    record.unlink()
    touched = sorted(path for path, digest in dirty(root).items() if before.get(path) != digest)
    reasons = refused(load_config(root), touched) if touched else {}
    if not reasons:
        return 0
    # Exit code 2 on PostToolUse shows this text to the agent.
    print(
        "That command changed files without clearance. "
        "Undo it (git restore <file>, or delete a new file), then:",
        file=sys.stderr,
    )
    for reason in reasons.values():
        print(f"- {reason}", file=sys.stderr)
    return 2


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
    if mode == "shell-before":
        return before_shell()
    if mode == "shell-after":
        return after_shell()
    if mode == "commit":
        return check_commit()
    print(__doc__, file=sys.stderr)
    return 64


if __name__ == "__main__":
    sys.exit(main())
