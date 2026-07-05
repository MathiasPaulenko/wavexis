"""Header action for setting HTTP headers and user-agent."""

from __future__ import annotations

from typing import Any

from browsix.actions.base import BaseAction
from browsix.backend.base import AbstractBackend
from browsix.config import HeaderParams


class HeaderAction(BaseAction[HeaderParams, Any]):
    """Action for setting extra HTTP headers and user-agent override.

    Navigates to the URL in params, then applies the requested
    header or user-agent configuration against the backend.
    """

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the header action on the backend.

        Args:
            backend: An AbstractBackend instance.

        Returns:
            None on success.

        Raises:
            ValueError: If required parameters are missing.
        """
        try:
            await backend.launch(self.params.browser)
            if self.params.url:
                await backend.navigate(self.params.url, self.params.wait)

            action = self.params.action

            if action == "set-headers":
                if not self.params.headers:
                    raise ValueError("headers is required for set-headers action")
                await backend.set_headers(self.params.headers)
                return None

            if action == "set-user-agent":
                if not self.params.user_agent:
                    raise ValueError("user-agent is required for set-user-agent action")
                await backend.set_user_agent(self.params.user_agent)
                return None

            raise ValueError(f"Unknown header action: {action}")
        finally:
            await backend.close()
