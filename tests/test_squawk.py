import subprocess
import time
from pathlib import Path

import pytest

from backend.detector import check_code
from pilot.squawk import (
    PUSHED_SHOWN_SECONDS,
    Reporter,
    base_commit,
    changed_files,
    fetch,
    recent_pushes,
    upstream_commit,
)


def git(root: Path, *args: str) -> None:
    identity = ("-c", "user.name=test", "-c", "user.email=test@example.com")
    subprocess.run(["git", *identity, *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def checkouts(tmp_path):
    origin = tmp_path / "origin"
    (origin / "auth").mkdir(parents=True)
    (origin / "auth" / "__init__.py").write_text("from auth.session import create_session\n")
    (origin / "auth" / "session.py").write_text("def create_session(user):\n    return user\n")
    (origin / "settings.toml").write_text('ttl = 3600\ncookie = "sid"\n\n\ncurrency = "USD"\n')
    git(origin, "init", "-q", "-b", "main")
    git(origin, "add", "-A")
    git(origin, "commit", "-qm", "base")
    left, right = tmp_path / "a", tmp_path / "b"
    git(origin, "worktree", "add", "-q", "-b", "a", str(left))
    git(origin, "worktree", "add", "-q", "-b", "b", str(right))
    return left, right


def report(root: Path) -> dict:
    base = base_commit(root)
    return Reporter(root).report(changed_files(root, base), base)


def test_new_files_are_reported_as_created(checkouts):
    left, _ = checkouts
    (left / "refunds.py").write_text("x = 1\n")
    assert list(report(left)["created"]) == ["refunds.py"]


def test_changed_lines_carry_numbers_and_a_hash_not_the_text(checkouts):
    left, _ = checkouts
    (left / "settings.toml").write_text('ttl = 900\ncookie = "sid"\n\n\ncurrency = "USD"\n')
    hunk = report(left)["hunks"]["settings.toml"]
    [[start, end, fingerprint]] = hunk["lines"]
    assert (start, end) == (1, 2)
    assert "900" not in fingerprint


def test_the_same_edit_on_both_laptops_passes_and_a_different_one_clashes(checkouts):
    left, right = checkouts
    for root, ttl in ((left, "900"), (right, "900")):
        (root / "settings.toml").write_text(f'ttl = {ttl}\ncookie = "sid"\n\n\ncurrency = "USD"\n')
    assert check_code({"a": report(left), "b": report(right)}) == []
    (right / "settings.toml").write_text('ttl = 60\ncookie = "sid"\n\n\ncurrency = "USD"\n')
    assert [c["kind"] for c in check_code({"a": report(left), "b": report(right)})] == ["same_lines"]


def test_a_call_through_the_package_is_traced_to_the_definition(checkouts):
    left, right = checkouts
    (left / "auth" / "session.py").write_text("def create_session(user, ttl):\n    return user\n")
    (right / "refunds.py").write_text("from auth import create_session\n\ncreate_session('lay')\n")
    [collision] = check_code({"a": report(left), "b": report(right)})
    assert collision["reason"] == "is missing required argument ttl"


def test_a_file_that_isnt_utf8_doesnt_stop_the_daemon(checkouts):
    left, _ = checkouts
    (left / "settings.toml").write_bytes(b'ttl = 3600\ncookie = "s\xe9"\n\n\ncurrency = "USD"\n')
    assert report(left)["hunks"]["settings.toml"]["lines"]


@pytest.fixture
def team(tmp_path):
    """Two clones of one shared repo, as two laptops pushing to the same GitHub repo."""
    seed = tmp_path / "seed"
    (seed / "auth").mkdir(parents=True)
    (seed / "auth" / "session.py").write_text("def create_session(user):\n    return user\n")
    git(seed, "init", "-q", "-b", "main")
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "base")
    origin = tmp_path / "origin.git"
    git(tmp_path, "clone", "-q", "--bare", str(seed), str(origin))
    left, right = tmp_path / "left", tmp_path / "right"
    for root in (left, right):
        git(tmp_path, "clone", "-q", str(origin), str(root))
    return Reporter(left), Reporter(right)


def squawk(reporter: Reporter, later: float = 0.0) -> dict:
    """One turn of the daemon's loop, run `later` seconds from now."""
    root = reporter.root
    fetch(root)
    base = base_commit(root)
    files = changed_files(root, base)
    reporter.follow(base, files)
    pushes = recent_pushes(root, time.time() + later - PUSHED_SHOWN_SECONDS)
    return reporter.report(files, base, upstream_commit(root), pushes)


def write(root: Path, name: str, source: str) -> None:
    (root / name).write_text(source)


NEW_SIGNATURE = "def create_session(user, ttl):\n    return user\n"
STALE_CALL = "from auth.session import create_session\n\ncreate_session('lay')\n"
AUTHORS = {"auth.session.create_session": "left"}


def test_a_push_breaks_work_written_against_the_old_main(team):
    changer, caller = team
    # Edited, committed and pushed in one go, so no squawk saw the work before it left.
    write(changer.root, "auth/session.py", NEW_SIGNATURE)
    git(changer.root, "commit", "-qam", "ttl")
    git(changer.root, "push", "-q")
    pushed = squawk(changer)
    write(caller.root, "refunds.py", STALE_CALL)
    stale = squawk(caller)

    assert pushed["files"] == [] and pushed["pushed"]["changes"]
    [collision] = check_code({"left": pushed, "right": stale}, AUTHORS)
    assert collision["changed_by"] == "left"
    assert collision["commit"] == pushed["pushed"]["commit"]
    assert collision["options"][1]["text"] == "Pull main and update the call at refunds.py:3"

    # Once the push is old news, the caller's own view of main still carries it.
    later = squawk(changer, later=PUSHED_SHOWN_SECONDS + 1)
    assert "pushed" not in later
    assert len(check_code({"left": later, "right": stale}, AUTHORS)) == 1


def test_pulling_without_fixing_the_call_still_collides(team):
    changer, caller = team
    write(changer.root, "auth/session.py", NEW_SIGNATURE)
    git(changer.root, "commit", "-qam", "ttl")
    git(changer.root, "push", "-q")
    write(caller.root, "refunds.py", STALE_CALL)
    squawk(caller)
    git(caller.root, "pull", "-q")
    reports = {"left": squawk(changer), "right": squawk(caller)}
    assert len(check_code(reports, AUTHORS)) == 1

    write(caller.root, "refunds.py", STALE_CALL.replace("'lay'", "'lay', 60"))
    reports["right"] = squawk(caller)
    assert check_code(reports, AUTHORS) == []


def test_the_authors_unpushed_fix_on_main_settles_it(team):
    changer, caller = team
    write(changer.root, "auth/session.py", NEW_SIGNATURE)
    git(changer.root, "commit", "-qam", "ttl")
    git(changer.root, "push", "-q")
    write(caller.root, "refunds.py", STALE_CALL)
    write(changer.root, "auth/session.py", NEW_SIGNATURE.replace("ttl", "ttl=60"))
    assert check_code({"left": squawk(changer), "right": squawk(caller)}, AUTHORS) == []


def test_a_push_by_someone_detente_never_saw_is_credited_to_main(team):
    changer, caller = team
    write(changer.root, "auth/session.py", NEW_SIGNATURE)
    git(changer.root, "commit", "-qam", "ttl")
    git(changer.root, "push", "-q")
    write(caller.root, "refunds.py", STALE_CALL)
    [collision] = check_code({"right": squawk(caller)})
    assert collision["changed_by"] == "main"
    assert [option["agent"] for option in collision["options"]] == ["right", "right"]
    assert collision["options"][0]["text"] == "Give ttl a default on main"


def test_work_with_nothing_unpushed_reports_no_main_changes(team):
    changer, caller = team
    write(changer.root, "auth/session.py", NEW_SIGNATURE)
    git(changer.root, "commit", "-qam", "ttl")
    git(changer.root, "push", "-q")
    assert "upstream" not in squawk(caller)
