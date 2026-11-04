"""Watch one checkout and tell Detente what its unpushed work changes and calls.

    python -m pilot.squawk /path/to/checkout
"""

import argparse
import hashlib
import json
import logging
import re
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Any

from backend.contracts import calls, changes, reexports

log = logging.getLogger("detente.squawk")

POLL_SECONDS = 1.0
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def git(root: Path, *args: str, check: bool = True) -> str:
    # A Latin-1 CSV or a stray binary in a diff must never stop the daemon.
    done = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, errors="replace", check=check
    )
    return done.stdout


def base_commit(root: Path) -> str:
    """Where unpushed work starts: the upstream if there is one, else HEAD."""
    upstream = subprocess.run(
        ["git", "merge-base", "HEAD", "@{upstream}"], cwd=root, capture_output=True, text=True
    )
    return upstream.stdout.strip() if upstream.returncode == 0 else "HEAD"


def changed_files(root: Path, base: str) -> list[str]:
    tracked = git(root, "diff", "--name-only", base).splitlines()
    untracked = git(root, "ls-files", "--others", "--exclude-standard").splitlines()
    return sorted({*tracked, *untracked} - {".detente"})


def fingerprint(root: Path, files: list[str]) -> tuple:
    stamps = []
    for name in files:
        path = root / name
        stamp = path.stat() if path.exists() else None
        stamps.append((name, stamp.st_mtime_ns if stamp else 0, stamp.st_size if stamp else 0))
    return tuple(stamps)


def base_blobs(root: Path, base: str, files: list[str]) -> dict[str, str]:
    """The version of each file at the base, for the files that existed there."""
    if not files:
        return {}
    listed = git(root, "ls-tree", "-r", "-z", base, "--", *files, check=False)
    blobs = {}
    for entry in listed.split("\0"):
        info, _, name = entry.partition("\t")
        if name:
            blobs[name] = info.split()[2]
    return blobs


def changed_lines(root: Path, base: str, name: str) -> tuple[list[list], list[list[int]]]:
    """What this checkout changed in one file, as line spans on both sides of the diff.

    The base side, [start, end, fingerprint], is what Detente compares between laptops.
    Only line numbers and a hash of the new text leave the laptop, never the text; the
    hash lets two laptops that made the very same edit pass, as they do in git. A pure
    insertion is an empty span where it lands, so two insertions at one spot still clash.
    The new side, [start, end), is which lines of the file as it is now this work wrote.
    """
    old: list[list] = []
    new: list[list[int]] = []
    added: list[str] = []

    def close() -> None:
        if old:
            old[-1][2] = hashlib.sha256("\n".join(added).encode()).hexdigest()[:12]

    for line in git(root, "diff", "-U0", "--no-color", "--no-ext-diff", base, "--", name).splitlines():
        found = HUNK.match(line)
        if found:
            close()
            added = []
            start, count = int(found[1]), int(found[2] or 1)
            begin = start if count else start + 1
            old.append([begin, begin + count, ""])
            written, size = int(found[3]), int(found[4] or 1)
            if size:
                new.append([written, written + size])
        elif old and line.startswith("+"):
            added.append(line[1:])
    close()
    return old, new


def module_source(root: Path, module: str) -> tuple[str, str] | None:
    relative = module.replace(".", "/")
    for name in (f"{relative}.py", f"{relative}/__init__.py", f"src/{relative}.py", f"src/{relative}/__init__.py"):
        try:
            return name, (root / name).read_text()
        except (OSError, UnicodeDecodeError):
            continue
    return None


class Reporter:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._last_good: dict[str, tuple[list, list]] = {}  # survives a half-typed file

    def _read_python(self, name: str, base: str, resolve, written) -> tuple[list, list]:
        path = self.root / name
        before = git(self.root, "show", f"{base}:{name}", check=False)
        after = path.read_text() if path.exists() else ""
        try:
            parsed = (
                changes(before, after, name),
                [asdict(call) for call in calls(after, name, resolve, written)],
            )
        except (SyntaxError, ValueError):
            return self._last_good.get(name, ([], []))
        self._last_good[name] = parsed
        return parsed

    def report(self, files: list[str], base: str) -> dict[str, Any]:
        resolve = reexports(lambda module: module_source(self.root, module))
        blobs = base_blobs(self.root, base, files)
        all_changes: list = []
        all_calls: list = []
        hunks: dict[str, dict] = {}
        for name in files:
            written = None  # a new file: every line in it is this work's
            if name in blobs:
                touched, written = changed_lines(self.root, base, name)
                hunks[name] = {"blob": blobs[name], "lines": touched}
            if name.endswith(".py"):
                changed, called = self._read_python(name, base, resolve, written)
                all_changes += changed
                all_calls += called
        # New files carry a hash of their text, so two laptops adding the same file pass.
        created = {
            name: hashlib.sha256((self.root / name).read_bytes()).hexdigest()[:12]
            for name in files
            if name not in blobs and (self.root / name).is_file()
        }
        return {
            "files": files,
            "changes": all_changes,
            "calls": all_calls,
            "created": created,
            "hunks": hunks,
        }


def send(config: dict, report: dict[str, Any]) -> None:
    request = urllib.request.Request(
        f"{config['url']}/squawk",
        data=json.dumps(
            {
                "callsign": config["callsign"],
                "person": config["person"],
                "vendor": config["vendor"],
                "report": report,
            }
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['token']}",
        },
    )
    with urllib.request.urlopen(request, timeout=10):
        pass


def watch(root: Path, config: dict) -> None:
    reporter = Reporter(root)
    sent = None
    while True:
        try:
            base = base_commit(root)
            files = changed_files(root, base)
            current = (base, fingerprint(root, files))
            if current != sent:
                send(config, reporter.report(files, base))
                sent = current
                log.info("Squawked %d changed files", len(files))
        except (urllib.error.URLError, TimeoutError, subprocess.CalledProcessError) as error:
            log.warning("Squawk failed, will retry: %s", error)
            sent = None
        time.sleep(POLL_SECONDS)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    root = parser.parse_args().repo.resolve()
    watch(root, json.loads((root / ".detente").read_text()))


if __name__ == "__main__":
    main()
