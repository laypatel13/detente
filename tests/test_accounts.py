import asyncio
import sqlite3
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend import accounts as accounts_module
from backend.accounts import (
    LOCK_SECONDS,
    MAX_FAILURES,
    SESSION_SECONDS,
    Accounts,
    TooManyTries,
)
from backend.airspace import Airspace
from backend.api import SESSION_COOKIE, create_app, radar_events

PASSWORD = "correct horse battery"
TOKEN = "pilot-token"


@pytest.fixture
def path(tmp_path):
    return str(tmp_path / "detente.db")


@pytest.fixture
def accounts(path):
    made = Accounts(path)
    made.add("lay", PASSWORD)
    return made


@pytest.fixture
def api(accounts, path):
    return TestClient(create_app(Airspace(path), SimpleNamespace(), accounts, TOKEN))


def later(monkeypatch, seconds):
    now = time.time() + seconds
    monkeypatch.setattr(accounts_module.time, "time", lambda: now)


def test_passwords_and_tokens_are_stored_hashed(accounts, path):
    token = accounts.sign_in("lay", PASSWORD)
    dump = "\n".join(sqlite3.connect(path).iterdump())
    assert PASSWORD not in dump
    assert token not in dump


def test_the_right_password_signs_in(accounts):
    assert accounts.session_user(accounts.sign_in("lay", PASSWORD)) == "lay"


def test_a_wrong_password_or_unknown_name_gets_nothing(accounts):
    assert accounts.sign_in("lay", "not the password") is None
    assert accounts.sign_in("nobody", PASSWORD) is None


def test_two_accounts_with_one_password_store_different_hashes(accounts, path):
    accounts.add("dev-a", PASSWORD)
    hashes = sqlite3.connect(path).execute("SELECT hash FROM accounts").fetchall()
    assert hashes[0] != hashes[1]


def test_weak_or_duplicate_accounts_are_refused(accounts):
    with pytest.raises(ValueError, match="at least"):
        accounts.add("dev-a", "short")
    with pytest.raises(ValueError, match="already"):
        accounts.add("lay", PASSWORD)
    with pytest.raises(ValueError, match="lowercase"):
        accounts.add("Bad Name", PASSWORD)


@pytest.mark.parametrize("username", ["lay", "nobody"])
def test_too_many_failures_lock_even_the_right_password(accounts, username):
    for _ in range(MAX_FAILURES):
        accounts.sign_in(username, "not the password")
    with pytest.raises(TooManyTries):
        accounts.sign_in(username, PASSWORD)


def test_the_lock_lifts_after_a_wait(accounts, monkeypatch):
    for _ in range(MAX_FAILURES):
        accounts.sign_in("lay", "not the password")
    later(monkeypatch, LOCK_SECONDS + 1)
    assert accounts.sign_in("lay", PASSWORD)


def test_a_good_sign_in_clears_the_failures(accounts):
    for _ in range(MAX_FAILURES - 1):
        accounts.sign_in("lay", "not the password")
    assert accounts.sign_in("lay", PASSWORD)
    assert accounts.sign_in("lay", "not the password") is None
    assert accounts.sign_in("lay", PASSWORD)


def test_sessions_expire(accounts, monkeypatch):
    token = accounts.sign_in("lay", PASSWORD)
    later(monkeypatch, SESSION_SECONDS + 1)
    assert accounts.session_user(token) is None


def test_signing_out_ends_the_session(accounts):
    token = accounts.sign_in("lay", PASSWORD)
    accounts.sign_out(token)
    assert accounts.session_user(token) is None


def test_a_new_password_ends_old_sessions_and_replaces_the_old_password(accounts):
    token = accounts.sign_in("lay", PASSWORD)
    accounts.set_password("lay", "a different long password")
    assert accounts.session_user(token) is None
    assert accounts.sign_in("lay", PASSWORD) is None
    assert accounts.sign_in("lay", "a different long password")


def test_removing_an_account_ends_its_sessions(accounts):
    token = accounts.sign_in("lay", PASSWORD)
    accounts.remove("lay")
    assert accounts.session_user(token) is None
    assert accounts.sign_in("lay", PASSWORD) is None


def test_sign_in_sets_a_cookie_scripts_cannot_read(api):
    reply = api.post("/auth/login", json={"username": "lay", "password": PASSWORD})
    cookie = reply.headers["set-cookie"].lower()
    assert reply.status_code == 200
    assert "httponly" in cookie and "samesite=lax" in cookie and "secure" not in cookie


def test_the_cookie_is_secure_behind_https(api):
    reply = api.post(
        "/auth/login",
        json={"username": "lay", "password": PASSWORD},
        headers={"X-Forwarded-Proto": "https"},
    )
    assert "secure" in reply.headers["set-cookie"].lower()


def test_a_session_opens_the_radar_and_signing_out_closes_it(api):
    assert api.get("/auth/me").status_code == 401
    assert api.get("/radar/state").status_code == 401

    api.post("/auth/login", json={"username": "lay", "password": PASSWORD})
    assert api.get("/auth/me").json() == {"username": "lay"}
    assert api.get("/radar/state").status_code == 200

    token = api.cookies[SESSION_COOKIE]
    api.post("/auth/logout")
    api.cookies.clear()
    assert api.get("/radar/state", cookies={SESSION_COOKIE: token}).status_code == 401


def test_a_bad_sign_in_says_nothing_about_which_part_was_wrong(api):
    wrong = api.post("/auth/login", json={"username": "lay", "password": "nope"})
    unknown = api.post("/auth/login", json={"username": "nobody", "password": "nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_repeated_failures_get_a_429(api):
    body = {"username": "lay", "password": "nope"}
    for _ in range(MAX_FAILURES):
        assert api.post("/auth/login", json=body).status_code == 401
    assert api.post("/auth/login", json=body).status_code == 429


def test_a_session_cannot_report_for_a_laptop(api):
    api.post("/auth/login", json={"username": "lay", "password": PASSWORD})
    assert api.post("/clearance", json={"callsign": "a", "files": []}).status_code == 401


def test_a_strange_authorization_header_is_refused_not_a_crash(api):
    reply = api.get("/radar/state", headers={b"Authorization": "Bearer caf\xe9".encode("latin-1")})
    assert reply.status_code == 401


def test_the_radar_stream_stops_when_access_ends(path):
    answers = iter([True, False])

    async def read() -> list[str]:
        return [
            event async for event in radar_events(Airspace(path), lambda: next(answers))
        ]

    assert len(asyncio.run(read())) == 1
