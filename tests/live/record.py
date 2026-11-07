"""Record the real flights the showcase plays back, one for each choice a person can make.

Starts its own Detente with an empty database and a new room, so nothing of yours is touched.
Needs `make switch-up` and `make setup`.

    uv run python -m tests.live.record
"""

import asyncio
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from httpx_sse import aconnect_sse

from backend.setup import INSTRUCTIONS
from backend.switch import Switch, register_agent
from tests.live.harness import (
    ROOT,
    Checkout,
    Person,
    Pilot,
    env_file,
    make_checkouts,
    temp_dir,
    unique,
    wait_for,
)
from tests.live.run import BROKEN_CALLER, FIXED_CALLER, NEW_SIGNATURE

PORT = 8101
API = f"http://localhost:{PORT}"
OUT = ROOT / "frontend" / "app" / "showcase" / "_story" / "recordings"
DEFAULTED_SIGNATURE = NEW_SIGNATURE.replace("create_session(user, ttl)", "create_session(user, ttl=3600)")


def start_detente(url: str, agent: dict, name: str, room_id: str, token: str, database: Path) -> subprocess.Popen:
    return subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(PORT),
            "--log-level", "warning", "--timeout-graceful-shutdown", "2",
        ],
        cwd=ROOT,
        env={
            **os.environ,
            "SWITCH_URL": url,
            "DETENTE_AGENT_NAME": name,
            "DETENTE_AGENT_ID": agent["id"],
            "DETENTE_API_KEY": agent["api_key"],
            "DETENTE_ROOM_ID": room_id,
            "DETENTE_PILOT_TOKEN": token,
            "DETENTE_DB": str(database),
        },
    )


def tower_started(database: Path) -> bool:
    connection = sqlite3.connect(database)
    try:
        return bool(connection.execute("SELECT 1 FROM meta WHERE key = 'started'").fetchall())
    except sqlite3.OperationalError:
        return False
    finally:
        connection.close()


async def is_up(http: httpx.AsyncClient) -> bool:
    try:
        return (await http.get("/health")).status_code == 200
    except httpx.HTTPError:
        return False


async def capture(http: httpx.AsyncClient, frames: list[dict]) -> None:
    started = time.monotonic()
    async with aconnect_sse(http, "GET", "/radar/stream") as source:
        async for event in source.aiter_sse():
            state = json.loads(event.data)
            unchanged = frames and {**frames[-1]["state"], "version": 0} == {**state, "version": 0}
            if not unchanged:
                frames.append({"at": round(time.monotonic() - started, 2), "state": state})


def third_checkout(base: Path) -> Path:
    path = base / "developer-b"
    subprocess.run(
        ["git", "worktree", "add", "-q", "-b", "developer-b", str(path)],
        cwd=base / "shoplite", check=True,
    )
    return path


async def fly(choice: str) -> tuple[list[dict], dict[str, str]]:
    env = env_file(ROOT / ".env")
    switch_env = env_file(ROOT / "switch" / ".env")
    url, registration = env["SWITCH_URL"], switch_env["AGENT_REGISTRATION_TOKEN"]
    username = switch_env["MATTERMOST_USER"]
    base = temp_dir()

    # Its own agent, because the Detente you have running already holds the tower role.
    agent_name = unique("detente")
    agent = await register_agent(url, registration, agent_name, "Records flights for the showcase")
    host = Switch(url, agent["id"], agent["api_key"])
    room = await host.call(
        "create_room",
        name=unique("recording"),
        description="A recorded flight for the showcase",
        agent_names=[agent_name],
        instructions=INSTRUCTIONS.read_text(),
    )
    room_id = room["id"]
    await host.call("add_users_to_room", room_id=room_id, user_names=[username])

    database = base / "detente.db"
    token = os.urandom(24).hex()
    server = start_detente(url, agent, agent_name, room_id, token, database)
    http = httpx.AsyncClient(
        base_url=API, timeout=None, headers={"Authorization": f"Bearer {token}"}
    )
    frames: list[dict] = []
    pilots: list[Pilot] = []
    laptops: list[Checkout] = []
    capturing = None

    async def said(tag: str, text: str = "") -> bool:
        feed = (await http.get("/radar/state")).json()["feed"]
        return any(item["tag"] == tag and text in item["text"] for item in feed)

    async def join(name: str) -> Pilot:
        pilot = await Pilot.join(url, registration, name, room_id, host)
        pilots.append(pilot)
        return pilot

    try:
        await wait_for(lambda: is_up(http), "Detente to start")
        await wait_for(lambda: tower_started(database), "the tower to join its room")
        capturing = asyncio.create_task(capture(http, frames))
        await wait_for(lambda: frames, "the first frame")

        person = await Person.sign_in(username, switch_env["MATTERMOST_USER_PASSWORD"])
        lay_name, developer_name, third_name = unique("lay-claude"), unique("a-codex"), unique("b-opencode")
        lay, developer, third = await join(lay_name), await join(developer_name), await join(third_name)

        left, right = make_checkouts(base)
        lay_checkout = Checkout(left, lay_name, username, "Claude Code")
        developer_checkout = Checkout(right, developer_name, "developer-a", "Codex")
        third_path = third_checkout(base)
        third_laptop = Checkout(third_path, third_name, "developer-b", "OpenCode")
        laptops.extend((lay_checkout, developer_checkout, third_laptop))
        for laptop in laptops:
            laptop.install(API, token)
            laptop.start_squawk()

        await lay.say(
            "FLIGHT PLAN\ntask: session expiry\nedit: auth/session.py\n"
            "changes: auth.session.create_session"
        )
        await wait_for(lambda: said("CLEARED", lay_name), "the first clearance")
        await third.say("FLIGHT PLAN\ntask: cart rounding\nedit: cart/totals.py")
        await wait_for(lambda: said("CLEARED", third_name), "the second clearance")
        await developer.say(
            "FLIGHT PLAN\ntask: refunds\nedit: billing/refunds.py\n"
            "uses: auth.session.create_session"
        )
        await wait_for(lambda: said("CLEARED", developer_name), "the clearance with traffic")
        await asyncio.sleep(1.5)

        totals = third_path / "cart" / "totals.py"
        third_laptop.write("cart/totals.py", f"{totals.read_text()}\n# rounds to two places\n")
        lay_checkout.write("auth/session.py", NEW_SIGNATURE)
        developer_checkout.write("billing/refunds.py", BROKEN_CALLER)
        await wait_for(lambda: said("COLLISION"), "the collision")
        await wait_for(lambda: said("DECISION"), "the decision card")
        conflict = (await http.get("/radar/state")).json()["conflicts"][0]
        channel = await wait_for(lambda: person.channel(conflict["id"]), "the conflict channel")
        await asyncio.sleep(1.5)

        await person.post(channel, choice)
        await wait_for(lambda: said("DECIDED", f"({choice})"), "the decision")
        await asyncio.sleep(1.5)

        if choice == "A":
            lay_checkout.write("auth/session.py", DEFAULTED_SIGNATURE)
        else:
            developer_checkout.write("billing/refunds.py", FIXED_CALLER)
        await wait_for(lambda: said("RESOLVED"), "the fix")
        await asyncio.sleep(1.5)

        for laptop in laptops:
            laptop.stop()
        for pilot in (third, lay, developer):
            await pilot.say("LANDED")
            await asyncio.sleep(1)

        async def everyone_landed() -> bool:
            flights = (await http.get("/radar/state")).json()["flights"]
            return bool(flights) and all(flight["status"] == "landed" for flight in flights)

        await wait_for(everyone_landed, "every flight to land")
        await asyncio.sleep(1)
    finally:
        # The radar stream holds the server open, so it has to close before the server can.
        if capturing:
            capturing.cancel()
            await asyncio.gather(capturing, return_exceptions=True)
        for laptop in laptops:
            laptop.stop()
        for pilot in pilots:
            await pilot.close()
        server.terminate()
        await asyncio.to_thread(server.wait)
        await http.aclose()
        await host.call("archive_room", room_id=room_id)
        await host.close()
        shutil.rmtree(base, ignore_errors=True)

    return frames, {
        agent_name: "detente",
        lay_name: "lay-claude",
        developer_name: "a-codex",
        third_name: "b-opencode",
        f'"by":"{username}"': '"by":"you"',
        f"by {username} (": "by you (",
        f'"sender":"{username}"': '"sender":"you"',
        f'"person":"{username}"': '"person":"lay"',
        f"{username} or developer-a, reply": "lay or developer-a, reply",
        conflict["id"]: "conflict-create-session-3f1a",
    }


def tidy(frames: list[dict], names: dict[str, str]) -> list[dict]:
    """Agent names need a unique suffix on a shared server, so the showcase drops it."""
    for frame in frames:
        for conflict in frame["state"]["conflicts"]:
            conflict.pop("room_id")
    text = json.dumps(frames, ensure_ascii=False, separators=(",", ":"))
    for real, shown in names.items():
        text = text.replace(real, shown)
    return json.loads(text)


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for choice in ("A", "B"):
        frames, names = await fly(choice)
        recording: dict[str, Any] = {"choice": choice, "frames": tidy(frames, names)}
        path = OUT / f"{choice.lower()}.json"
        path.write_text(json.dumps(recording, ensure_ascii=False, separators=(",", ":")) + "\n")
        print(f"Recorded choice {choice}: {len(frames)} frames in {path.relative_to(ROOT)}")


if __name__ == "__main__":
    asyncio.run(main())
