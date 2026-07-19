"""Permissions action for granting and resetting browser permissions."""

from __future__ import annotations

from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import WaitStrategy


class PermissionsAction(BaseAction[str, None]):
    """Action for managing browser permissions."""

    def __init__(
        self,
        params: str,
        action: str = "grant",
        permission: str = "",
        url: str = "",
        wait: WaitStrategy | None = None,
    ) -> None:
        """Initialize the permissions action.

        Args:
            params: Permissions parameters.
            action: Permission action ("grant", "deny", "reset", or "query").
            permission: Permission name (e.g. "geolocation", "notifications").
            url: URL to navigate to before the action.
            wait: Wait strategy after navigation.
        """
        self.params = params
        self._action = action
        self._permission = permission
        self._url = url
        self._wait = wait or WaitStrategy(strategy="load")

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the permissions action on the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            None.
        """
        if self._url:
            await backend.navigate(self._url, self._wait)
        if self._action == "grant":
            await backend.grant_permission(self._permission)
        elif self._action == "reset":
            await backend.reset_permissions()
        else:
            raise ValueError(f"Unknown permissions action: {self._action}")
        return None
