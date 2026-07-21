"""Session action for saving and loading browser state (cookies + storage)."""

from __future__ import annotations

import asyncio
import contextlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import CookieParams
from wavexis.exceptions import WavexisError
from wavexis.output import validate_path


@dataclass
class SessionData:
    """Serialized browser session state.

    Attributes:
        cookies: List of cookie dicts.
        local_storage: Dict of localStorage key-value pairs.
        session_storage: Dict of sessionStorage key-value pairs.
        url: URL at which the session was captured.
    """

    cookies: list[dict[str, Any]]
    local_storage: dict[str, str]
    session_storage: dict[str, str]
    url: str

    def to_json(self) -> str:
        """Serialize session data to JSON string."""
        return json.dumps(
            {
                "cookies": self.cookies,
                "local_storage": self.local_storage,
                "session_storage": self.session_storage,
                "url": self.url,
            },
            indent=2,
        )

    @classmethod
    def from_json(cls, data: str) -> SessionData:
        """Deserialize session data from JSON string.

        Args:
            data: JSON string produced by ``to_json`` or compatible format.

        Returns:
            Parsed SessionData instance.

        Raises:
            WavexisError: If the JSON is not an object or has invalid field types.
        """
        obj = json.loads(data)
        if not isinstance(obj, dict):
            raise WavexisError("Session data must be a JSON object")

        cookies = obj.get("cookies", [])
        local_storage = obj.get("local_storage", {})
        session_storage = obj.get("session_storage", {})
        url = obj.get("url", "")

        if not isinstance(cookies, list):
            raise WavexisError("Session field 'cookies' must be a list")
        if not isinstance(local_storage, dict):
            raise WavexisError("Session field 'local_storage' must be an object")
        if not isinstance(session_storage, dict):
            raise WavexisError("Session field 'session_storage' must be an object")
        if not isinstance(url, str):
            raise WavexisError("Session field 'url' must be a string")

        return cls(
            cookies=cookies,
            local_storage=local_storage,
            session_storage=session_storage,
            url=url,
        )


class SessionSaveAction(BaseAction[Path, str]):
    """Action for saving browser session state to a file."""

    async def execute(self, backend: AbstractBackend) -> str:
        """Save cookies and storage from the current backend session.

        Args:
            backend: The browser backend with an active session.

        Returns:
            JSON string of the session data.
        """
        cookies = await backend.get_cookies()
        local_storage = await backend.storage_list("local")
        session_storage = await backend.storage_list("session")
        url = ""
        with contextlib.suppress(WavexisError):
            url = await backend.eval("window.location.href", await_promise=False)

        data = SessionData(
            cookies=cookies,
            local_storage=dict(local_storage),
            session_storage=dict(session_storage),
            url=str(url) if url else "",
        )
        json_str = data.to_json()
        try:
            session_path = validate_path(self.params)
            await asyncio.to_thread(session_path.write_text, json_str, encoding="utf-8")
        except OSError as e:
            raise WavexisError(f"Failed to write session file: {e}") from e
        return json_str


class SessionLoadAction(BaseAction[Path, None]):
    """Action for loading browser session state from a file."""

    async def execute(self, backend: AbstractBackend) -> None:
        """Load cookies and storage into the backend session.

        Args:
            backend: The browser backend with an active session.
        """
        try:
            raw = await asyncio.to_thread(validate_path(self.params).read_text, encoding="utf-8")
            data = SessionData.from_json(raw)
        except OSError as e:
            raise WavexisError(f"Failed to read session file: {e}") from e
        except json.JSONDecodeError as e:
            raise WavexisError(f"Invalid session JSON: {e}") from e

        for cookie in data.cookies:
            cp = CookieParams(
                name=cookie.get("name", ""),
                value=cookie.get("value", ""),
                domain=cookie.get("domain", ""),
                path=cookie.get("path", "/"),
                secure=cookie.get("secure", True),
                http_only=cookie.get("httpOnly", False),
                same_site=cookie.get("sameSite", "Lax"),
            )
            await backend.set_cookie(cp)

        for key, value in data.local_storage.items():
            await backend.storage_set(key, value, "local")
        for key, value in data.session_storage.items():
            await backend.storage_set(key, value, "session")
