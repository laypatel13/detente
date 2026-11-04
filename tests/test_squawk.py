import subprocess
from pathlib import Path

import pytest

from backend.detector import check_code
from pilot.squawk import Reporter, base_commit, changed_files


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
