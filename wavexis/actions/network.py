"""Network action for cookies, headers, and user-agent management."""

from __future__ import annotations

from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import NetworkParams
from wavexis.exceptions import ActionError


class NetworkAction(BaseAction[NetworkParams, Any]):
    """Action for network operations.

    Supports cookies get/set/delete/clear, headers, and user-agent override.
    """

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the network action.

        Args:
            backend: The browser backend to use.

        Returns:
            List of cookies for "cookies_get", None for other actions.
        """
        params = self.params

        if params.action == "cookies_get":
            return await backend.get_cookies()

        if params.action == "cookies_set":
            if params.cookie:
                if not params.cookie.name or not params.cookie.value:
                    raise ActionError("name and value are required for cookies_set")
                await backend.set_cookie(params.cookie)
            elif params.cookies:
                from wavexis.config import CookieParams

                for cookie_dict in params.cookies:
                    name = str(cookie_dict.get("name", ""))
                    value = str(cookie_dict.get("value", ""))
                    if not name or not value:
                        raise ActionError(
                            "name and value are required for each cookie in cookies_set"
                        )
                    cookie = CookieParams(
                        name=name,
                        value=value,
                        domain=str(cookie_dict.get("domain", "")),
                        path=str(cookie_dict.get("path", "/")),
                        secure=bool(cookie_dict.get("secure", True)),
                        http_only=bool(cookie_dict.get("http_only", False)),
                        same_site=str(cookie_dict.get("same_site", "Lax")),
                    )
                    await backend.set_cookie(cookie)
            else:
                raise ActionError("cookie or cookies is required for cookies_set action")
            return None

        if params.action == "cookies_delete":
            if not params.name:
                raise ActionError("name is required for cookies_delete action")
            if not params.domain:
                raise ActionError("domain is required for cookies_delete action")
            await backend.delete_cookie(params.name, params.domain)
            return None

        if params.action == "cookies_clear":
            await backend.clear_cookies()
            return None

        if params.action == "headers":
            if params.headers:
                await backend.set_headers(params.headers)
            return None

        if params.action == "user_agent":
            if params.user_agent:
                await backend.set_user_agent(params.user_agent)
            return None

        raise ActionError(f"Unknown network action: {params.action}")
