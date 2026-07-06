"""Overlay action for highlighting elements and clearing highlights."""

from __future__ import annotations

from dataclasses import dataclass, field

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy


@dataclass
class OverlayParams:
    """Parameters for overlay operations.

    Attributes:
        url: URL to navigate to before overlay.
        selector: CSS selector for the element to highlight.
        color: RGBA color string for the highlight overlay.
        action: Overlay action — "highlight" or "clear".
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    selector: str | None = None
    color: str = "rgba(255,0,0,0.5)"
    action: str = "highlight"
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class OverlayAction(BaseAction[OverlayParams, None]):
    """Action for overlay highlight and clear operations."""

    async def execute(self, backend: AbstractBackend) -> None:
        """Execute the overlay action on the backend.

        Args:
            backend: The browser backend to use.

        Raises:
            ValueError: If the action is not recognized or selector is missing.
        """
        await backend.launch(self.params.browser)
        try:
            await backend.navigate(self.params.url, self.params.wait)
            await self._run_action(backend)
        finally:
            await backend.close()

    async def _run_action(self, backend: AbstractBackend) -> None:
        """Execute the overlay action against the backend.

        Args:
            backend: The browser backend to use.

        Raises:
            ValueError: If required parameters are missing or action is unknown.
        """
        action = self.params.action
        if action == "highlight":
            if not self.params.selector:
                raise ValueError("selector is required for highlight action")
            await backend.overlay_highlight(self.params.selector, self.params.color)
        elif action == "clear":
            await backend.overlay_clear()
        else:
            raise ValueError(f"Unknown overlay action: {action}")
