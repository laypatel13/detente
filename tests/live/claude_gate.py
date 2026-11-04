"""Does a real Claude Code agent get stopped by the edit gate? Costs a few cents of usage.

    uv run python -m tests.live.claude_gate
"""

import asyncio
import shutil
import subprocess

import httpx

from backend.switch import Switch
from tests.live.harness import ROOT, Checkout, Pilot, env_file, make_checkouts, temp_dir, unique, wait_for

API = "http://localhost:8100"
MARKER = "# expires after thirty minutes"
PROMPT = (
    f"Use the Edit tool to add this exact line at the very top of auth/session.py: {MARKER}\n"
    "Do nothing else. If the edit is refused, stop and repeat the refusal message."
)


def run_claude(root) -> str:
    done = subprocess.run(
        [
            "claude", "-p", PROMPT, "--model", "haiku", "--permission-mode", "acceptEdits",
            "--allowedTools", "Edit,Read", "--max-turns", "6",
        ],
        cwd=root, capture_output=True, text=True, timeout=180,
    )
    return done.stdout + done.stderr


async def main() -> None:
    env = env_file(ROOT / ".env")
    secrets = env_file(ROOT / "switch" / ".env")
    url, room_id = env["SWITCH_URL"], env["DETENTE_ROOM_ID"]
    host = Switch(url, env["DETENTE_AGENT_ID"], env["DETENTE_API_KEY"])
    base = temp_dir()
    left, _ = make_checkouts(base)

    callsign = unique("real-claude")
    pilot = await Pilot.join(url, secrets["AGENT_REGISTRATION_TOKEN"], callsign, room_id, host)
    checkout = Checkout(left, callsign, "user", "Claude Code")
    checkout.install(API, env["DETENTE_PILOT_TOKEN"])
    target = left / "auth" / "session.py"

    try:
        said = await asyncio.to_thread(run_claude, left)
        print("WITHOUT A PLAN, Claude said:\n", said.strip()[:400], "\n")
        assert MARKER not in target.read_text(), "the gate let an uncleared edit through"
        print("  ok  real Claude Code was refused with no flight plan\n")

        await pilot.say(
            "FLIGHT PLAN\ntask: note the session expiry\nedit: auth/session.py"
        )

        async def cleared() -> bool:
            pilot_token = {"Authorization": f"Bearer {env['DETENTE_PILOT_TOKEN']}"}
            async with httpx.AsyncClient(headers=pilot_token) as http:
                state = (await http.get(f"{API}/radar/state")).json()
            return any(flight["callsign"] == callsign for flight in state["flights"])

        await wait_for(cleared, "the clearance")
        said = await asyncio.to_thread(run_claude, left)
        print("WITH A PLAN, Claude said:\n", said.strip()[:300], "\n")
        assert MARKER in target.read_text(), "a cleared edit didn't land"
        print("  ok  real Claude Code made the edit once it was cleared")
    finally:
        await pilot.say("LANDED")
        await pilot.close()
        await host.close()
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
