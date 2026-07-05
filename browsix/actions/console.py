"""Console action for capturing console messages and browser logs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from browsix.actions.base import BaseAction
from browsix.backend.base import AbstractBackend
from browsix.config import WaitStrategy


@dataclass
class ConsoleParams:
    """Parameters for console capture.

    Attributes:
        url: URL to navigate to before capturing.
        level: Minimum log level — "all", "error", "warning", "info".
        wait: Wait strategy after navigation.
        capture: What to capture — "console", "logs", or "both".
    """

    url: str = ""
    level: str = "all"
    wait: WaitStrategy | None = None
    capture: str = "console"


class ConsoleAction(BaseAction[ConsoleParams, dict[str, Any]]):
    """Action for capturing console messages and browser logs.

    Navigates to the URL, then captures console messages and/or log entries.
    """

    async def execute(self, backend: AbstractBackend) -> dict[str, Any]:
        """Execute the console action.

        Args:
            backend: The browser backend to use.

        Returns:
            Dict with "console" and/or "logs" keys containing entry lists.
        """
        params = self.params
        if params.url:
            await backend.navigate(params.url, params.wait)

        result: dict[str, Any] = {}

        if params.capture in ("console", "both"):
            result["console"] = await backend.capture_console(level=params.level)

        if params.capture in ("logs", "both"):
            result["logs"] = await backend.capture_logs()

        return result
