"""The Switch agent protocol: one event stream per room, HTTP for everything else."""

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from json import loads
from typing import Any

import httpx
from httpx_sse import aconnect_sse

log = logging.getLogger("detente.switch")

RECONNECT_SECONDS = 1.0
RECONNECT_WAIT_SECONDS = 15
Event = dict[str, Any]
Handler = Callable[[Event], Awaitable[None]]


class SwitchError(RuntimeError):
    def __init__(self, message: str, status: int = 0) -> None:
        super().__init__(message)
        self.status = status


async def register_agent(url: str, token: str, name: str, description: str) -> dict[str, str]:
    """Register Detente once. Returns {id, api_key}, and the key is only shown here."""
    async with httpx.AsyncClient(base_url=url, timeout=30) as http:
        response = await http.post(
            "/agents",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": name,
                "description": description,
                "display_name": "Detente",
                "connector_type": "external",
                "integration_profile": {
                    "connection_model": "always_on",
                    "message_exchange": True,
                    "pre_invocation_mediation": [],
                    "post_invocation_mediation": [],
                    "event_reporting": [],
                },
            },
        )
    if response.status_code != 200:
        raise SwitchError(f"Registering {name} failed: {response.status_code} {response.text}")
    return response.json()


class Switch:
    def __init__(self, url: str, agent_id: str, api_key: str) -> None:
        self.agent_id = agent_id
        self.http = httpx.AsyncClient(
            base_url=url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(30, read=None),
        )

    async def call(self, operation: str, connection: str | None = None, **arguments: Any) -> Any:
        headers = {"X-Switch-Connection-Id": connection} if connection else {}
        response = await self.http.post(
            f"/agents/{self.agent_id}/ops/{operation}", json=arguments, headers=headers
        )
        if response.status_code != 200:
            raise SwitchError(
                f"{operation} failed: {response.status_code} {response.text}",
                response.status_code,
            )
        return response.json()["result"]

    async def close(self) -> None:
        await self.http.aclose()


class RoomLink:
    """A live connection to one room. It reconnects until closed."""

    def __init__(self, switch: Switch, room_id: str, on_message: Handler) -> None:
        self.switch = switch
        self.room_id = room_id
        self.on_message = on_message
        self.connection_id = str(uuid.uuid4())  # reused across reconnects, per the protocol
        self.ready = asyncio.Event()
        self._last_event_id: str | None = None
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def close(self) -> None:
        if self._task:
            self._task.cancel()

    async def call(self, operation: str, **arguments: Any) -> Any:
        await self.ready.wait()
        try:
            return await self.switch.call(operation, self.connection_id, **arguments)
        except SwitchError as error:
            if error.status != 409:
                raise
        # 409 means the connection dropped. The stream loop reopens it, so wait and retry once.
        self.ready.clear()
        await asyncio.wait_for(self.ready.wait(), RECONNECT_WAIT_SECONDS)
        return await self.switch.call(operation, self.connection_id, **arguments)

    async def _run(self) -> None:
        while True:
            try:
                await self._stream()
            except (httpx.HTTPError, SwitchError) as error:
                log.warning("Stream for room %s dropped: %s", self.room_id, error)
            except Exception:
                # This loop is what keeps Detente listening, so it outlives any surprise.
                log.exception("Stream for room %s failed", self.room_id)
            self.ready.clear()
            await asyncio.sleep(RECONNECT_SECONDS)

    async def _stream(self) -> None:
        params = {
            "connection_id": self.connection_id,
            "scope": "single",
            "filter": "all",
            "rooms": self.room_id,
            "start_from": "head",
        }
        headers = {"Accept": "text/event-stream"}
        if self._last_event_id:
            headers["Last-Event-ID"] = self._last_event_id

        path = f"/agents/{self.switch.agent_id}/events"
        async with aconnect_sse(
            self.switch.http, "GET", path, params=params, headers=headers
        ) as source:
            if source.response.status_code != 200:
                await source.response.aread()
                raise SwitchError(
                    f"Opening the stream failed: {source.response.status_code} "
                    f"{source.response.text}"
                )

            beat: asyncio.Task | None = None
            try:
                async for frame in source.aiter_sse():
                    if frame.id:
                        self._last_event_id = frame.id
                    if frame.event == "connection_state":
                        state = loads(frame.data)
                        beat = asyncio.create_task(
                            self._beat(state["heartbeat_interval_seconds"], source.response)
                        )
                        self.ready.set()
                    elif frame.event == "evicted":
                        raise SwitchError(f"Evicted: {frame.data}")
                    elif frame.event == "gap":
                        log.warning("Event gap in room %s: %s", self.room_id, frame.data)
                    elif frame.event == "message" and frame.data:
                        # A keep-alive comment reaches here as a frame with no data.
                        await self._deliver(loads(frame.data))
            finally:
                if beat:
                    beat.cancel()

    async def _deliver(self, event: Event) -> None:
        try:
            await self.on_message(event)
        except Exception:
            # One bad message must not take down the room's stream.
            log.exception("Handling a message in room %s failed", self.room_id)

    async def _beat(self, interval: float, response: httpx.Response) -> None:
        path = f"/agents/{self.switch.agent_id}/connection/beat"
        while True:
            await asyncio.sleep(interval)
            body = {"connection_id": self.connection_id}
            if self._last_event_id:
                body["cursor"] = int(self._last_event_id)
            try:
                reply = await self.switch.http.post(path, json=body)
            except httpx.HTTPError as error:
                log.warning("Heartbeat failed: %s", error)
                continue
            if reply.status_code in (404, 409):
                # The protocol says reopen, not back off. Closing ends the stream loop.
                log.warning("Heartbeat refused with %s, reopening", reply.status_code)
                await response.aclose()
                return
