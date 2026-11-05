"""Talk to a team's tower over HTTP with a checkout's pilot token. Standard library only."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

TIMEOUT_SECONDS = 5.0


class TowerError(Exception):
    """The tower couldn't answer the question. The message says why, in plain words."""


class Unreachable(TowerError):
    pass


class Refused(TowerError):
    pass


class Tower:
    def __init__(self, url: str, token: str, timeout: float = TIMEOUT_SECONDS) -> None:
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _call(self, method: str, path: str, body: Any = None) -> Any:
        request = urllib.request.Request(
            self.url + path,
            data=None if body is None else json.dumps(body).encode(),
            method=method,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read() or b"null")
        except urllib.error.HTTPError as error:
            if error.code == 401:
                raise Refused(f"The tower at {self.url} refused the pilot token.") from None
            try:
                detail = json.loads(error.read()).get("detail")
            except (ValueError, AttributeError):
                detail = None
            raise TowerError(detail or f"The tower at {self.url} answered {error.code}.") from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise Unreachable(f"No tower answering at {self.url}.") from None

    def state(self) -> dict[str, Any]:
        return self._call("GET", "/radar/state")

    def conflict(self, conflict_id: str) -> dict[str, Any]:
        return self._call("GET", f"/radar/conflicts/{urllib.parse.quote(conflict_id)}")

    def refused(self, callsign: str, files: list[str]) -> dict[str, str]:
        """The files this callsign may not edit yet, each with the tower's reason."""
        return self._call("POST", "/clearance", {"callsign": callsign, "files": files})["refused"]
