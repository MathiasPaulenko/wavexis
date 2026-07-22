"""Dialog, security, and download interception mixin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DialogBackend(ABC):
    """JavaScript dialogs, security state, and download interception."""

    @abstractmethod
    async def dialog_accept(self, prompt_text: str | None = None) -> None:
        """Accept a JavaScript dialog (alert, confirm, prompt)."""

    @abstractmethod
    async def dialog_dismiss(self) -> None:
        """Dismiss a JavaScript dialog."""

    @abstractmethod
    async def dialog_wait_for_opening(self, timeout: float = 30.0) -> dict[str, Any]:
        """Wait for a JavaScript dialog to open and return its event params.

        Args:
            timeout: Maximum seconds to wait for the dialog.

        Returns:
            The dialog event parameters (message, type, etc.).

        Raises:
            TimeoutError: If no dialog opens within ``timeout``.
        """

    @abstractmethod
    async def get_security_state(self) -> dict[str, Any]:
        """Get the current security state of the page."""

    @abstractmethod
    async def ignore_cert_errors(self, ignore: bool = True) -> None:
        """Enable or disable ignoring of certificate errors."""

    @abstractmethod
    async def intercept_download(
        self, pattern: str = ".*", timeout: float | None = None
    ) -> bytes:
        """Intercept a file download matching a URL pattern and return bytes."""
