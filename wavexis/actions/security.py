"""Security action for getting security state and ignoring certificate errors."""

from __future__ import annotations

from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy


class SecurityAction(BaseAction[str, Any]):
    """Action for security-related operations."""

    def __init__(
        self,
        params: str,
        action: str = "state",
        ignore: bool = True,
        url: str = "",
        wait: WaitStrategy | None = None,
    ) -> None:
        """Initialize the security action.

        Args:
            params: Security parameters.
            action: Security action ("state" or "ignore-cert-errors").
            ignore: Whether to ignore certificate errors.
            url: URL to navigate to before the action.
            wait: Wait strategy after navigation.
        """
        self.params = params
        self._action = action
        self._ignore = ignore
        self._url = url
        self._wait = wait or WaitStrategy(strategy="load")

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the security action on the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            Security state dict for "state" action; None for "ignore_cert".
        """
        if self._url:
            await backend.navigate(self._url, self._wait)
        if self._action == "state":
            return await backend.get_security_state()
        elif self._action == "ignore_cert":
            await backend.ignore_cert_errors(self._ignore)
            return None
        else:
            raise ValueError(f"Unknown security action: {self._action}")
