"""Drive a real Switch server, Mattermost, git worktrees, gates and squawk daemons."""

import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from backend.switch import RoomLink, Switch, register_agent

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "shoplite"
MATTERMOST = "http://localhost:8065"


def env_file(path: Path) -> dict[str, str]:
    lines = (line.split("=", 1) for line in path.read_text().splitlines() if "=" in line)
    return {key: value for key, value in lines}


async def wait_for(check: Callable, what: str, seconds: float = 30) -> Any:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = check()
        if asyncio.iscoroutine(result):
            result = await result
        if result:
            return result
        await asyncio.sleep(0.25)
    raise AssertionError(f"Timed out waiting for {what}")


async def nothing(_: dict) -> None:
    pass


class Pilot:
    """A real Switch agent. It speaks the protocol the way a Console session does."""

    def __init__(self, switch: Switch, name: str, room_id: str) -> None:
        self.name = name
        self.switch = switch
        self.link = RoomLink(switch, room_id, nothing)

    @classmethod
    async def join(cls, url: str, token: str, name: str, room_id: str, host: Switch) -> "Pilot":
        agent = await register_agent(url, token, name, "Test pilot")
        switch = Switch(url, agent["id"], agent["api_key"])
        await host.call("invite_agent_to_room", room_id=room_id, agent_name=name)
        pilot = cls(switch, name, room_id)
        pilot.link.start()
        await pilot.link.ready.wait()
        return pilot

    async def say(self, body: str) -> None:
        await self.link.call("post_message", body=body)

    async def close(self) -> None:
        await self.link.close()
        await self.switch.close()


class Person:
    """A real person's Mattermost account."""

    def __init__(self, http: httpx.AsyncClient, username: str) -> None:
        self.http = http
        self.username = username

    @classmethod
    async def sign_in(cls, username: str, password: str) -> "Person":
        http = httpx.AsyncClient(base_url=f"{MATTERMOST}/api/v4", timeout=15)
        reply = await http.post("/users/login", json={"login_id": username, "password": password})
        reply.raise_for_status()
        http.headers["Authorization"] = f"Bearer {reply.headers['Token']}"
        return cls(http, username)

    async def channel(self, display_name: str) -> str | None:
        teams = (await self.http.get("/users/me/teams")).json()
        for team in teams:
            channels = (await self.http.get(f"/users/me/teams/{team['id']}/channels")).json()
            for channel in channels:
                if channel["display_name"] == display_name:
                    return channel["id"]
        return None

    async def post(self, channel_id: str, message: str) -> None:
        reply = await self.http.post(
            "/posts", json={"channel_id": channel_id, "message": message}
        )
        reply.raise_for_status()


class Checkout:
    """One laptop: a git worktree, connected the way a teammate would connect it."""

    def __init__(self, root: Path, callsign: str, person: str, vendor: str) -> None:
        self.root = root
        self.callsign = callsign
        self.person = person
        self.vendor = vendor
        self.daemon: subprocess.Popen | None = None

    def install(self, url: str, token: str) -> None:
        subprocess.run(
            [
                sys.executable, "-m", "pilot.install", str(self.root),
                "--callsign", self.callsign, "--person", self.person,
                "--vendor", self.vendor, "--url", url, "--token", token,
            ],
            cwd=ROOT, check=True, capture_output=True,
        )

    def start_squawk(self) -> None:
        self.daemon = subprocess.Popen(
            [sys.executable, "-m", "pilot.squawk", str(self.root)],
            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def stop(self) -> None:
        if self.daemon:
            self.daemon.terminate()
            self.daemon.wait()

    def write(self, path: str, text: str) -> None:
        (self.root / path).write_text(text)

    def edit_gate(self, path: str) -> subprocess.CompletedProcess:
        """Run the gate exactly as Claude Code runs a PreToolUse hook."""
        hook = {"cwd": str(self.root), "tool_input": {"file_path": path}}
        settings = json.loads((self.root / ".claude/settings.local.json").read_text())
        command = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        return subprocess.run(
            command, shell=True, input=json.dumps(hook), capture_output=True, text=True
        )

    def commit(self, message: str) -> subprocess.CompletedProcess:
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", message],
            cwd=self.root, capture_output=True, text=True,
        )


def make_checkouts(base: Path) -> tuple[Path, Path]:
    origin = base / "shoplite"
    shutil.copytree(FIXTURE, origin)
    for command in (
        ["git", "init", "-q", "-b", "main"],
        ["git", "add", "-A"],
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "ShopLite"],
    ):
        subprocess.run(command, cwd=origin, check=True)
    left, right = base / "lay", base / "developer-a"
    for path, branch in ((left, "lay"), (right, "developer-a")):
        subprocess.run(
            ["git", "worktree", "add", "-q", "-b", branch, str(path)], cwd=origin, check=True
        )
    return left, right


def temp_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="detente-live-"))


def unique(name: str) -> str:
    return f"{name}-{uuid.uuid4().hex[:6]}"

