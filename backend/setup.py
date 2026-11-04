"""First-time setup: register Detente on Switch, create the tower room, write .env.

    uv run python -m backend.setup --registration-token <token>
"""

import argparse
import asyncio
import secrets
from pathlib import Path

from backend.switch import Switch, register_agent
from backend.tower import AGENT_NAME, TOWER_ROOM

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
INSTRUCTIONS = ROOT / "switch" / "pilot-instructions.md"


async def setup(url: str, token: str, pilots: list[str]) -> None:
    agent = await register_agent(
        url, token, AGENT_NAME, "Traffic control for the coding agents on your team's laptops."
    )
    switch = Switch(url, agent["id"], agent["api_key"])
    room = await switch.call(
        "create_room",
        name=TOWER_ROOM,
        description="Flight plans, clearances and the live Airspace board",
        agent_names=[AGENT_NAME, *pilots],
        instructions=INSTRUCTIONS.read_text(),
    )
    await switch.close()

    ENV_FILE.write_text(
        f"SWITCH_URL={url}\n"
        f"DETENTE_AGENT_ID={agent['id']}\n"
        f"DETENTE_API_KEY={agent['api_key']}\n"
        f"DETENTE_ROOM_ID={room['id']}\n"
        f"DETENTE_PILOT_TOKEN={secrets.token_hex(24)}\n"
    )
    print(f"Registered {AGENT_NAME}, created room {TOWER_ROOM}, wrote {ENV_FILE}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--registration-token", required=True)
    parser.add_argument("--pilot", action="append", default=[], help="Agent to add to the room")
    args = parser.parse_args()
    if ENV_FILE.exists():
        raise SystemExit(f"{ENV_FILE} already exists. Delete it to set up again.")
    asyncio.run(setup(args.url, args.registration_token, args.pilot))


if __name__ == "__main__":
    main()
