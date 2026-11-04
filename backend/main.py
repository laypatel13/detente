"""Run Detente: the tower agent and its HTTP API, in one process.

    uv run uvicorn backend.main:app --env-file .env
"""

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.accounts import Accounts
from backend.airspace import Airspace
from backend.api import create_app
from backend.switch import Switch
from backend.tower import Tower

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

DATABASE = os.environ.get("DETENTE_DB", "detente.db")
airspace = Airspace(DATABASE)
switch = Switch(
    os.environ["SWITCH_URL"], os.environ["DETENTE_AGENT_ID"], os.environ["DETENTE_API_KEY"]
)
tower = Tower(airspace, switch, os.environ["DETENTE_ROOM_ID"])


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # In the background, so the API and the radar still come up while Switch is down.
    starting = asyncio.create_task(tower.start())
    yield
    starting.cancel()
    await switch.close()


app = create_app(airspace, tower, Accounts(DATABASE), os.environ["DETENTE_PILOT_TOKEN"], lifespan)
