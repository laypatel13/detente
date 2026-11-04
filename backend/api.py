"""HTTP API. Laptops report and ask here; the radar only reads. Decisions stay in chat."""

import asyncio
import hmac
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.accounts import SESSION_SECONDS, Accounts, TooManyTries
from backend.airspace import Airspace

CHECK_SECONDS = 0.25
KEEPALIVE_SECONDS = 15
SESSION_COOKIE = "detente_session"


class Squawk(BaseModel):
    callsign: str
    person: str
    vendor: str
    report: dict[str, Any]


class ClearanceRequest(BaseModel):
    callsign: str
    files: list[str]


class SignIn(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=256)


async def radar_events(airspace: Airspace, allowed: Callable[[], bool]) -> AsyncIterator[str]:
    last_version = None
    quiet = 0.0
    while allowed():
        if airspace.version != last_version:
            last_version = airspace.version
            quiet = 0.0
            state = json.dumps(airspace.snapshot(), ensure_ascii=False)
            yield f"data: {state}\n\n"
        elif quiet >= KEEPALIVE_SECONDS:
            quiet = 0.0
            yield ": keep-alive\n\n"
        await asyncio.sleep(CHECK_SECONDS)
        quiet += CHECK_SECONDS


def create_app(
    airspace: Airspace, tower: Any, accounts: Accounts, pilot_token: str, lifespan: Any = None
) -> FastAPI:
    app = FastAPI(title="Detente", lifespan=lifespan)

    def has_pilot_token(request: Request) -> bool:
        sent = request.headers.get("authorization", "").encode()
        return hmac.compare_digest(sent, f"Bearer {pilot_token}".encode())

    def signed_in_as(request: Request) -> str | None:
        return accounts.session_user(request.cookies.get(SESSION_COOKIE, ""))

    def may_read(request: Request) -> bool:
        return has_pilot_token(request) or signed_in_as(request) is not None

    def pilot(request: Request) -> None:
        if not has_pilot_token(request):
            raise HTTPException(status_code=401, detail="Bad pilot token")

    def reader(request: Request) -> None:
        if not may_read(request):
            raise HTTPException(status_code=401, detail="Sign in first")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/auth/login")
    def login(body: SignIn, request: Request, response: Response) -> dict[str, str]:
        try:
            token = accounts.sign_in(body.username, body.password)
        except TooManyTries:
            raise HTTPException(status_code=429, detail="Too many tries. Wait five minutes.") from None
        if token is None:
            raise HTTPException(status_code=401, detail="Wrong username or password")
        response.set_cookie(
            SESSION_COOKIE,
            token,
            max_age=SESSION_SECONDS,
            httponly=True,
            samesite="lax",
            secure=request.headers.get("x-forwarded-proto", request.url.scheme) == "https",
        )
        return {"username": body.username}

    @app.post("/auth/logout")
    def logout(request: Request, response: Response) -> dict[str, bool]:
        accounts.sign_out(request.cookies.get(SESSION_COOKIE, ""))
        response.delete_cookie(SESSION_COOKIE)
        return {"ok": True}

    @app.get("/auth/me")
    def me(request: Request) -> dict[str, str]:
        username = signed_in_as(request)
        if username is None:
            raise HTTPException(status_code=401, detail="Sign in first")
        return {"username": username}

    @app.post("/squawk", dependencies=[Depends(pilot)])
    async def squawk(body: Squawk) -> dict[str, bool]:
        await tower.on_squawk(body.callsign, body.person, body.vendor, body.report)
        return {"ok": True}

    @app.post("/clearance", dependencies=[Depends(pilot)])
    def clearance(body: ClearanceRequest) -> dict[str, dict[str, str]]:
        reasons = {path: airspace.clearance(body.callsign, path) for path in body.files}
        return {"refused": {path: reason for path, reason in reasons.items() if reason}}

    @app.get("/radar/state", dependencies=[Depends(reader)])
    def radar_state() -> dict[str, Any]:
        return airspace.snapshot()

    @app.get("/radar/stream", dependencies=[Depends(reader)])
    def radar_stream(request: Request) -> StreamingResponse:
        return StreamingResponse(
            radar_events(airspace, lambda: may_read(request)),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
        )

    @app.get("/radar/conflicts/{conflict_id}", dependencies=[Depends(reader)])
    def radar_conflict(conflict_id: str) -> dict[str, Any]:
        found = airspace.conflict(conflict_id)
        if found is None:
            raise HTTPException(status_code=404, detail=f"No conflict named {conflict_id}")
        return found

    return app
