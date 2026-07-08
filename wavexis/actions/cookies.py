"""Cookie action for browser cookie operations."""

from __future__ import annotations

from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import CookieActionParams


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
            await backend.set_cookie(self.params.cookie)
            return None

        if action == "delete":
            if not self.params.name:
                raise ValueError("name is required for delete action")
            await backend.delete_cookie(self.params.name, self.params.domain)
            return None

        if action == "clear":
            await backend.clear_cookies()
            return None

        raise ValueError(f"Unknown cookie action: {action}")
