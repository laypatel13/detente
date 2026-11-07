"""The full flight, against live services. Needs `make switch-up`, `make setup`, `make api`.

    uv run python -m tests.live.run
"""

import asyncio
import shutil
import subprocess
import sys

import httpx

from backend.switch import Switch
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

API = "http://localhost:8100"


def _restart_detente() -> None:
    # By name, never by port: with Docker, the process holding 8100 is Docker itself.
    subprocess.run(["pkill", "-9", "-f", "uvicorn backend.main:app"], check=True)
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", "8100",
         "--env-file", ".env", "--log-level", "warning"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )


RESTART = _restart_detente if "--restart" in sys.argv else None
NEW_SIGNATURE = '''import secrets

SESSIONS: dict[str, str] = {}


def create_session(user, ttl):
    token = secrets.token_hex(16)
    SESSIONS[token] = user
    return token


def end_session(token):
    SESSIONS.pop(token, None)


def current_user(token):
    return SESSIONS.get(token)
'''
BROKEN_CALLER = "from auth.session import create_session\n\n\ndef refund(user):\n    return create_session(user)\n"
FIXED_CALLER = "from auth.session import create_session\n\n\ndef refund(user):\n    return create_session(user, 30)\n"


START = [0]  # the feed id this run began at, so old runs' messages don't count


def step(text: str) -> None:
    print(f"  ok  {text}", flush=True)


async def state(http: httpx.AsyncClient) -> dict:
    return (await http.get("/radar/state")).json()


async def feed_has(http: httpx.AsyncClient, tag: str, *texts: str) -> bool:
    return any(
        item["id"] > START[0] and item["tag"] == tag and all(text in item["text"] for text in texts)
        for item in (await state(http))["feed"]
    )


async def main() -> None:
    env = env_file(ROOT / ".env")
    secrets = env_file(ROOT / "switch" / ".env")
    url, room_id, token = env["SWITCH_URL"], env["DETENTE_ROOM_ID"], secrets["AGENT_REGISTRATION_TOKEN"]
    host = Switch(url, env["DETENTE_AGENT_ID"], env["DETENTE_API_KEY"])
    pilot_token = {"Authorization": f"Bearer {env['DETENTE_PILOT_TOKEN']}"}
    http = httpx.AsyncClient(base_url=API, timeout=15, headers=pilot_token)
    base = temp_dir()
    START[0] = max((item["id"] for item in (await state(http))["feed"]), default=0)

    username = secrets["MATTERMOST_USER"]
    await host.call("add_users_to_room", room_id=room_id, user_names=[username])
    person = await Person.sign_in(username, secrets["MATTERMOST_USER_PASSWORD"])
    tower_channel = await wait_for(lambda: person.channel("tower"), "the tower channel")
    step("a person is in the tower channel on Mattermost")

    lay_name, developer_name = unique("lay-claude"), unique("a-codex")
    lay = await Pilot.join(url, token, lay_name, room_id, host)
    developer = await Pilot.join(url, token, developer_name, room_id, host)
    step("two real agents joined the tower room")

    left, right = make_checkouts(base)
    lay_checkout = Checkout(left, lay_name, username, "Claude Code")
    developer_checkout = Checkout(right, developer_name, username, "Codex")
    for checkout in (lay_checkout, developer_checkout):
        checkout.install(API, env["DETENTE_PILOT_TOKEN"])
        checkout.start_squawk()

    try:
        assert lay_checkout.edit_gate("auth/session.py").returncode == 2
        step("edit gate refuses a file with no flight plan")

        await lay.say(
            "FLIGHT PLAN\ntask: session expiry\nedit: auth/session.py\n"
            "changes: auth.session.create_session"
        )
        await wait_for(lambda: feed_has(http, "CLEARED", lay_name), "CLEARED")
        step("flight plan posted in Switch came back CLEARED")

        assert lay_checkout.edit_gate("auth/session.py").returncode == 0
        refused = lay_checkout.edit_gate("billing/api.py")
        assert refused.returncode == 2 and "No clearance" in refused.stderr
        step("edit gate allows the cleared file and refuses another")

        await developer.say(
            "FLIGHT PLAN\ntask: refunds\nedit: billing/refunds.py\n"
            "uses: auth.session.create_session"
        )
        # A related plan is still cleared; the traffic rides inside the clearance.
        await wait_for(lambda: feed_has(http, "CLEARED", developer_name, "Traffic:"), "CLEARED with traffic")
        step("second plan was cleared with a traffic note before any code existed")

        lay_checkout.write("auth/session.py", NEW_SIGNATURE)
        developer_checkout.write("billing/refunds.py", BROKEN_CALLER)
        await wait_for(lambda: feed_has(http, "COLLISION"), "COLLISION")
        conflict = (await state(http))["conflicts"][0]
        assert conflict["reason"] == "is missing required argument ttl"
        assert conflict["breaks"]["line"] == 5
        assert conflict["room_id"]
        step(f"COLLISION caught across two checkouts, nothing pushed: {conflict['id']}")

        assert (await state(http))["mood"] == "collision"
        held = lay_checkout.edit_gate("auth/session.py")
        assert held.returncode == 2 and "Holding" in held.stderr
        assert developer_checkout.edit_gate("billing/refunds.py").returncode == 2
        assert developer_checkout.commit("broken").returncode == 1
        step("both flights hold: edit gates and the commit gate refuse")

        if RESTART:
            RESTART()
            await wait_for(lambda: _is_up(http), "Detente to come back", 20)
            assert lay_checkout.edit_gate("auth/session.py").returncode == 2
            step("after a crash and restart, the hold is still in force")

        room_channel = await wait_for(lambda: person.channel(conflict["id"]), "the conflict channel")
        await wait_for(lambda: feed_has(http, "DECISION"), "the decision card")
        step("conflict room opened on Mattermost with the decision card")

        await person.post(room_channel, "hello, what happened here?")
        await asyncio.sleep(1)
        assert (await state(http))["conflicts"][0]["status"] == "open"
        step("ordinary chat in the conflict room decides nothing")

        await person.post(room_channel, "B")
        await wait_for(lambda: feed_has(http, "DECIDED", "(B)"), "the decision")
        assert developer_checkout.edit_gate("billing/refunds.py").returncode == 0
        step("a person picked B on Mattermost and the holds lifted")

        developer_checkout.write("billing/refunds.py", FIXED_CALLER)
        await wait_for(lambda: feed_has(http, "RESOLVED"), "RESOLVED")
        assert (await state(http))["conflicts"] == []
        rooms = await host.call("list_rooms", include_archived=True)
        archived = next(room for room in rooms if room["room_id"] == conflict["room_id"])
        assert archived["archived"] is True
        step("the fix resolved the collision and the conflict room was archived")

        await lay.say("@detente ground stop")
        await asyncio.sleep(2)
        assert (await state(http))["mood"] != "stop"
        step("an agent can't call a ground stop")

        await person.post(tower_channel, "@detente ground stop")
        await wait_for(lambda: feed_has(http, "GROUND STOP"), "GROUND STOP")
        stopped = lay_checkout.edit_gate("auth/session.py")
        assert stopped.returncode == 2 and "Ground stop" in stopped.stderr
        step("a person's ground stop closed every gate")

        await person.post(tower_channel, "@detente resume")
        await wait_for(lambda: feed_has(http, "RESUME"), "RESUME")
        assert lay_checkout.edit_gate("auth/session.py").returncode == 0
        step("resume reopened the gates")

        lay_checkout.write("cart/totals.py", "def line_total(price, quantity):\n    return 0\n")
        await wait_for(lambda: feed_has(http, "VIOLATION", "cart/totals.py"), "VIOLATION")
        step("a file changed outside the clearance raised VIOLATION")

        await lay.say("LANDED\nfiles: auth/session.py")
        await wait_for(
            lambda: _landed(http, lay_name), "the landing"
        )
        step("LANDED closed the flight")

        documents = (await lay.link.call("connect_to_room", room_id=room_id))["documents"]
        assert any(document["name"] == "Airspace" for document in documents)
        step("the Airspace board is a live room document")
        print("\nEverything passed.")
    finally:
        for checkout in (lay_checkout, developer_checkout):
            checkout.stop()
        await lay.say("LANDED")
        await developer.say("LANDED")
        await lay.close()
        await developer.close()
        await host.close()
        await http.aclose()
        shutil.rmtree(base, ignore_errors=True)


async def _is_up(http: httpx.AsyncClient) -> bool:
    try:
        return (await http.get("/health")).status_code == 200
    except httpx.HTTPError:
        return False


async def _landed(http: httpx.AsyncClient, callsign: str) -> bool:
    flights = (await state(http))["flights"]
    return any(f["callsign"] == callsign and f["status"] == "landed" for f in flights)


if __name__ == "__main__":
    asyncio.run(main())
