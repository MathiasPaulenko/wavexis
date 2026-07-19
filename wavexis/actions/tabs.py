"""Tabs action for listing, creating, closing, and activating tabs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend


@dataclass
class TabsParams:
    """Parameters for tab operations.

    Attributes:
        action: Tab action — "list", "new", "close", or "activate".
        url: URL for new tab (when action="new").
        tab_id: Target ID for close/activate.
    """

    action: str = "list"
    url: str = "about:blank"
    tab_id: str = ""


class TabsAction(BaseAction[TabsParams, Any]):
    """Action for tab management operations.

    Supports listing, creating, closing, and activating tabs.
    """

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the tabs action.

        Args:
            backend: The browser backend to use.

        Returns:
            List of tabs for "list", target ID str for "new", None otherwise.
        """
        params = self.params
        if params.action == "list":
            return await backend.list_tabs()
        if params.action == "new":
            return await backend.new_tab(params.url)
        if params.action == "close":
            await backend.close_tab(params.tab_id)
            return None
        if params.action == "activate":
            await backend.activate_tab(params.tab_id)
            return None
        raise ValueError(f"Unknown tabs action: {params.action}")
