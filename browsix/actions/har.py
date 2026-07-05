"""HAR action for capturing network traffic as HAR 1.2."""

from __future__ import annotations

from typing import Any

from browsix.actions.base import BaseAction
from browsix.backend.base import AbstractBackend
from browsix.config import HarParams


class HARAction(BaseAction[HarParams, dict[str, Any]]):
    """Action for capturing HAR data.

    Navigates to a URL, captures network traffic, and returns a HAR 1.2 dict.
    """

    async def execute(self, backend: AbstractBackend) -> dict[str, Any]:
        """Execute the HAR capture action.

        Args:
            backend: The browser backend to use.

        Returns:
            HAR 1.2 compliant dict with log.entries.
        """
        return await backend.capture_har(self.params)
