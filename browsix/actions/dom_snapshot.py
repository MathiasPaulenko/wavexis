"""DOM snapshot action for capturing raw DOM snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from browsix.actions.base import BaseAction
from browsix.backend.base import AbstractBackend
from browsix.config import BrowserOptions, WaitStrategy


@dataclass
class DOMSnapshotParams:
    """Parameters for DOM snapshot operations.

    Attributes:
        url: URL to navigate to before capturing snapshot.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class DOMSnapshotAction(BaseAction[DOMSnapshotParams, dict[str, Any]]):
    """Action for capturing a DOM snapshot of a web page."""

    async def execute(self, backend: AbstractBackend) -> dict[str, Any]:
        """Execute the DOM snapshot action on the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            Dict containing the raw DOM snapshot.
        """
        await backend.launch(self.params.browser)
        try:
            await backend.navigate(self.params.url, self.params.wait)
            return await backend.dom_snapshot()
        finally:
            await backend.close()
