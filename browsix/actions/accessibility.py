"""Accessibility action for retrieving a11y tree, node, and ancestors."""

from __future__ import annotations

from typing import Any

from browsix.actions.base import BaseAction
from browsix.backend.base import AbstractBackend
from browsix.config import WaitStrategy


class AccessibilityAction(BaseAction[Any, Any]):
    """Action for accessibility tree operations."""

    def __init__(
        self,
        params: Any,
        action: str = "tree",
        node_id: str = "",
        url: str = "",
        wait: WaitStrategy | None = None,
    ) -> None:
        self.params = params
        self._action = action
        self._node_id = node_id
        self._url = url
        self._wait = wait or WaitStrategy(strategy="load")

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the accessibility action on the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            Accessibility tree dict, node dict, or list of ancestor dicts.
        """
        from browsix.config import BrowserOptions

        await backend.launch(BrowserOptions())
        try:
            if self._url:
                await backend.navigate(self._url, self._wait)
            if self._action == "tree":
                return await backend.a11y_tree()
            elif self._action == "node":
                return await backend.a11y_node(self._node_id)
            elif self._action == "ancestors":
                return await backend.a11y_ancestors(self._node_id)
            else:
                raise ValueError(f"Unknown a11y action: {self._action}")
        finally:
            await backend.close()
