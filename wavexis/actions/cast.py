"""Cast action for listing sinks and controlling tab mirroring (experimental)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy


@dataclass
class CastParams:
    """Parameters for Cast operations.

    Attributes:
        url: URL to navigate to before Cast operations.
        action: Cast action — "list", "start-tab", "stop".
        sink_name: Cast sink name for "start-tab" action.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    action: str = "list"
    sink_name: str | None = None
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class CastAction(BaseAction[CastParams, Any]):
    """Action for Cast operations (experimental)."""

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the Cast action on the backend.

        Args:
            backend: An AbstractBackend instance.

        Returns:
            Result of the Cast operation.
        """
        if self.params.url:
            await backend.navigate(self.params.url, self.params.wait)

        action = self.params.action

        if action == "list":
            return await backend.cast_list()

        if action == "start-tab":
            if not self.params.sink_name:
                raise ValueError("sink_name is required for start-tab action")
            await backend.cast_start_tab(self.params.sink_name)
            return None

        if action == "stop":
            await backend.cast_stop()
            return None

        raise ValueError(f"Unknown Cast action: {action}")
