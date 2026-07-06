"""Wait action for multi-action configs."""

from __future__ import annotations

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import WaitStrategy


class WaitAction(BaseAction[WaitStrategy, None]):
    """Action that waits for a condition on the current page.

    Supports waiting for page load, DOM content loaded, network idle,
    a CSS selector to appear, or a URL pattern to match.
    """

    async def execute(self, backend: AbstractBackend) -> None:
        """Execute the wait action on the backend.

        Args:
            backend: The backend to execute the wait on.
        """
        await backend.wait_for(self.params)
