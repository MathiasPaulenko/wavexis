"""Cookie action for browser cookie operations."""

from __future__ import annotations

from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import CookieActionParams
from wavexis.exceptions import ActionError


class CookieAction(BaseAction[CookieActionParams, Any]):
    """Action for cookie operations: get, set, delete, clear.

    Navigates to the URL in params, then performs the requested
    cookie operation against the backend.
    """

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the cookie action on the backend.

        Args:
            backend: An AbstractBackend instance.

        Returns:
            Result of the cookie operation.

        Raises:
            ValueError: If required parameters are missing.
        """
        if self.params.url:
            await backend.navigate(self.params.url, self.params.wait)

        action = self.params.action

        if action == "get":
            return await backend.get_cookies()

        if action == "set":
            cookie = self.params.cookie
            if cookie is None or not cookie.name or not cookie.value:
                raise ActionError("name and value are required for set action")
            await backend.set_cookie(cookie)
            return None

        if action == "delete":
            if not self.params.name:
                raise ActionError("name is required for delete action")
            if not self.params.domain:
                raise ActionError("domain is required for delete action")
            await backend.delete_cookie(self.params.name, self.params.domain)
            return None

        if action == "clear":
            await backend.clear_cookies()
            return None

        raise ActionError(f"Unknown cookie action: {action}")
