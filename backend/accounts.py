"""Who may sign in to the radar. Accounts are made on the server, so nobody can sign up.

    uv run python -m backend.accounts add lay
"""

import argparse
import getpass
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    username TEXT PRIMARY KEY, salt BLOB NOT NULL, hash BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, expires REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS failed_sign_ins (username TEXT NOT NULL, at REAL NOT NULL);
"""

USERNAME = re.compile(r"[a-z0-9._-]{1,64}")
MIN_PASSWORD_LENGTH = 12
SESSION_SECONDS = 14 * 24 * 3600
MAX_FAILURES = 5
LOCK_SECONDS = 300
NO_ACCOUNT_SALT = bytes(16)


class TooManyTries(Exception):
    pass


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**15, r=8, p=1, maxmem=2**26)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Accounts:
    def __init__(self, path: str) -> None:
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._db.executescript(SCHEMA)

    def _stored(self, password: str) -> tuple[bytes, bytes]:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Use at least {MIN_PASSWORD_LENGTH} characters.")
        salt = secrets.token_bytes(16)
        return salt, _hash(password, salt)

    def usernames(self) -> list[str]:
        rows = self._db.execute("SELECT username FROM accounts ORDER BY username").fetchall()
        return [row[0] for row in rows]

    def add(self, username: str, password: str) -> None:
        if not USERNAME.fullmatch(username):
            raise ValueError("Use lowercase letters, numbers, dots, dashes or underscores.")
        if username in self.usernames():
            raise ValueError(f"{username} already has an account.")
        self._db.execute("INSERT INTO accounts VALUES (?, ?, ?)", (username, *self._stored(password)))

    def set_password(self, username: str, password: str) -> None:
        if username not in self.usernames():
            raise ValueError(f"{username} has no account.")
        salt, hashed = self._stored(password)
        self._db.execute(
            "UPDATE accounts SET salt = ?, hash = ? WHERE username = ?", (salt, hashed, username)
        )
        self._db.execute("DELETE FROM sessions WHERE username = ?", (username,))

    def remove(self, username: str) -> None:
        if username not in self.usernames():
            raise ValueError(f"{username} has no account.")
        self._db.execute("DELETE FROM accounts WHERE username = ?", (username,))
        self._db.execute("DELETE FROM sessions WHERE username = ?", (username,))

    def sign_in(self, username: str, password: str) -> str | None:
        """A new session token, or None when the name or password is wrong."""
        now = time.time()
        self._db.execute("DELETE FROM failed_sign_ins WHERE at < ?", (now - LOCK_SECONDS,))
        failures = self._db.execute(
            "SELECT COUNT(*) FROM failed_sign_ins WHERE username = ?", (username,)
        ).fetchone()[0]
        if failures >= MAX_FAILURES:
            raise TooManyTries

        row = self._db.execute(
            "SELECT salt, hash FROM accounts WHERE username = ?", (username,)
        ).fetchone()
        # An unknown name still costs a hash, so timing can't reveal which names exist.
        salt, expected = row or (NO_ACCOUNT_SALT, b"")
        if not hmac.compare_digest(_hash(password, salt), expected):
            self._db.execute("INSERT INTO failed_sign_ins VALUES (?, ?)", (username, now))
            return None

        self._db.execute("DELETE FROM failed_sign_ins WHERE username = ?", (username,))
        token = secrets.token_urlsafe(32)
        self._db.execute(
            "INSERT INTO sessions VALUES (?, ?, ?)",
            (_token_hash(token), username, now + SESSION_SECONDS),
        )
        return token

    def session_user(self, token: str) -> str | None:
        self._db.execute("DELETE FROM sessions WHERE expires < ?", (time.time(),))
        row = self._db.execute(
            "SELECT username FROM sessions WHERE token_hash = ?", (_token_hash(token),)
        ).fetchone()
        return row[0] if row else None

    def sign_out(self, token: str) -> None:
        self._db.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))


def _new_password() -> str:
    password = getpass.getpass("Password: ")
    if getpass.getpass("Again: ") != password:
        raise SystemExit("Those passwords don't match.")
    return password


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage who can sign in to the radar.")
    parser.add_argument("action", choices=["add", "password", "remove", "list"])
    parser.add_argument("username", nargs="?")
    args = parser.parse_args()
    if args.action != "list" and not args.username:
        parser.error(f"{args.action} needs a username")

    accounts = Accounts(os.environ.get("DETENTE_DB", "detente.db"))
    try:
        if args.action == "add":
            accounts.add(args.username, _new_password())
            print(f"{args.username} can sign in now.")
        elif args.action == "password":
            accounts.set_password(args.username, _new_password())
            print(f"Changed the password and signed {args.username} out everywhere.")
        elif args.action == "remove":
            accounts.remove(args.username)
            print(f"Removed {args.username}.")
        else:
            print("\n".join(accounts.usernames()) or "No accounts yet.")
    except ValueError as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()
