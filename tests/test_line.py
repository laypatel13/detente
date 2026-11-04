"""The line between the showcase and the real app. Crossing it fails the build."""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
SHOWCASE = FRONTEND / "app" / "showcase"
RECORDINGS = SHOWCASE / "_story" / "recordings"
SOURCE_SUFFIXES = {".ts", ".tsx"}
IGNORED = {"node_modules", ".next", "art"}
IMPORT = re.compile(r"""(?:from|import)\s+["']([^"']+)["']""")
NETWORK = re.compile(r"\bfetch\(|EventSource|WebSocket|XMLHttpRequest|sendBeacon|/api/")


def source_files() -> list[Path]:
    return [
        path
        for path in FRONTEND.rglob("*")
        if path.suffix in SOURCE_SUFFIXES and not IGNORED & set(path.parts)
    ]


def imported(path: Path) -> set[Path]:
    """The project files this file imports."""
    found = set()
    for name in IMPORT.findall(path.read_text()):
        if name.startswith("@/"):
            base = FRONTEND / name[2:]
        elif name.startswith("."):
            base = (path.parent / name).resolve()
        else:
            continue
        for candidate in (base.with_suffix(".ts"), base.with_suffix(".tsx"), base):
            if candidate.is_file():
                found.add(candidate)
                break
    return found


def reachable_from(start: list[Path]) -> set[Path]:
    seen: set[Path] = set()
    waiting = list(start)
    while waiting:
        path = waiting.pop()
        if path not in seen:
            seen.add(path)
            waiting.extend(imported(path) - seen)
    return seen


def showcase_files() -> list[Path]:
    return [path for path in source_files() if SHOWCASE in path.parents]


def real_files() -> list[Path]:
    return [path for path in source_files() if SHOWCASE not in path.parents]


def test_the_rules_can_see_the_files_they_guard():
    assert len(showcase_files()) >= 8
    assert FRONTEND / "lib" / "use-radar.ts" in real_files()
    assert imported(SHOWCASE / "radar" / "page.tsx") == {
        SHOWCASE / "_story" / "showcase-radar.tsx"
    }


def test_the_real_app_never_imports_the_showcase():
    for path in reachable_from(real_files()):
        assert SHOWCASE not in path.parents, f"{path} is showcase code in the real app"
    for path in real_files():
        assert "showcase/_story" not in path.read_text(), f"{path} reaches into the showcase"


def test_the_showcase_never_calls_a_server():
    for path in reachable_from(showcase_files()):
        match = NETWORK.search(path.read_text())
        assert not match, f"{path} is used by the showcase and calls {match.group()}"


def test_the_showcase_has_no_login():
    proxy = (FRONTEND / "proxy.ts").read_text()
    assert "showcase" not in proxy


def test_the_landing_picture_stays_on_the_landing_page():
    users = [path for path in source_files() if "hero-frame" in path.read_text()]
    assert users == [FRONTEND / "app" / "page.tsx"]


@pytest.mark.parametrize("folder", ["backend", "pilot"])
def test_the_engine_knows_nothing_about_the_showcase(folder):
    for path in (ROOT / folder).rglob("*.py"):
        assert "showcase" not in path.read_text().lower(), f"{path} mentions the showcase"


@pytest.mark.parametrize("name", ["a", "b"])
def test_each_recording_tells_the_whole_story(name):
    recording = json.loads((RECORDINGS / f"{name}.json").read_text())
    states = [frame["state"] for frame in recording["frames"]]
    tags = {message["tag"] for message in states[-1]["feed"]}
    decisions = [
        conflict["decision"] for state in states for conflict in state["conflicts"]
        if conflict["decision"]
    ]

    assert {"TRAFFIC", "COLLISION", "DECISION", "DECIDED", "RESOLVED"} <= tags
    assert decisions[0] == {"by": "you", "option": name.upper()}
    assert states[-1]["mood"] == "resolved"
    assert all(flight["status"] == "landed" for flight in states[-1]["flights"])
    times = [frame["at"] for frame in recording["frames"]]
    assert times == sorted(times)


def test_both_recordings_are_the_same_conflict():
    ids = set()
    for name in ("a", "b"):
        recording = json.loads((RECORDINGS / f"{name}.json").read_text())
        ids |= {c["id"] for frame in recording["frames"] for c in frame["state"]["conflicts"]}
    assert len(ids) == 1
