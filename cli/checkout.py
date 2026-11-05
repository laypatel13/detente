"""Find the checkout a command is about, the way git does, and read how it's connected."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from pilot import install

CONFIG = ".detente"
QUOTED = re.compile(r'"([^"]+)"')


def root(start: Path) -> Path | None:
    """The top of the git checkout that holds start, or None outside one."""
    if not start.is_dir():
        return None
    found = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=start, capture_output=True, text=True
    )
    return Path(found.stdout.strip()).resolve() if found.returncode == 0 else None


def config(top: Path) -> dict | None:
    try:
        return json.loads((top / CONFIG).read_text())
    except (OSError, ValueError):
        return None


def short(path: Path) -> str:
    home = str(Path.home())
    text = str(path)
    return "~" + text[len(home):] if text.startswith(home) else text


def in_checkout(top: Path, name: Path) -> str | None:
    """A file named on the command line, as the path the tower knows: relative to the checkout."""
    full = (Path.cwd() / name).resolve()
    if full.is_relative_to(top):
        return full.relative_to(top).as_posix()
    # Named from outside the checkout with --repo: read it as a path inside the checkout.
    return None if name.is_absolute() else name.as_posix()


def _runs(command: str) -> tuple[bool, str]:
    """A gate's command names a Python and the gate script. Both must still be there."""
    missing = [part for part in QUOTED.findall(command) if not Path(part).exists()]
    if missing:
        return False, f"points at {missing[0]}, which is gone: run detente connect again"
    return True, ""


def commit_gate(top: Path) -> tuple[bool, str]:
    hook = install.git_path(top, "hooks/pre-commit")
    text = hook.read_text() if hook.exists() else ""
    if f"# {install.MARKER} commit gate" not in text:
        return False, "not installed: run detente connect"
    ok, problem = _runs(text)
    return ok, problem or "every commit is checked"


def edit_gate(top: Path) -> tuple[bool, str]:
    settings_file = top / ".claude" / "settings.local.json"
    try:
        hooks = json.loads(settings_file.read_text()).get("hooks", {})
    except (OSError, ValueError):
        hooks = {}
    for event, _matcher, mode in install.CLAUDE_HOOKS:
        entry = next((entry for entry in hooks.get(event, []) if install.ours(entry, mode)), None)
        if entry is None:
            return False, "not installed: run detente connect"
        ok, problem = _runs(entry["hooks"][0]["command"])
        if not ok:
            return False, problem
    return True, "edits and shell commands are checked"
