"""Browser action for context and window management."""

from __future__ import annotations

from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend


class BrowserAction(BaseAction[str, Any]):
    """Action for browser management operations.

    Supports contexts (new/list/close), window bounds (get/set), and version.
    The params string specifies the action: "new_context", "list_contexts",
    "close_context", "get_window", "set_window", or "version".
    """

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the browser action.

        Args:
            backend: The browser backend to use.

        Returns:
            Action-dependent result (str, list, dict, or None).
        """
        action = self.params

        if action == "version":
            return await backend.browser_version()

        if action == "new_context":
            return await backend.new_context()

        if action == "list_contexts":
            return await backend.list_contexts()

        if action == "close_context":
            raise NotImplementedError("close_context action not yet implemented")

        if action == "get_window":
            raise NotImplementedError("get_window action not yet implemented")

        if action == "set_window":
            raise NotImplementedError("set_window action not yet implemented")

        return None
