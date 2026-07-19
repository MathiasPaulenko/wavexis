"""Navigation and browser lifecycle mixin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from wavexis.config import BrowserOptions, WaitStrategy


class NavigationBackend(ABC):
    """Navigation, tab, context, and browser lifecycle operations."""

    @abstractmethod
    async def launch(self, options: BrowserOptions) -> None:
        """Launch a browser instance with the given options."""

    @abstractmethod
    async def close(self) -> None:
        """Close the browser and release all resources."""

    @abstractmethod
    async def navigate(self, url: str, wait: WaitStrategy | None = None) -> None:
        """Navigate to a URL, optionally waiting for a condition."""

    @abstractmethod
    async def eval(self, expression: str, await_promise: bool = False) -> Any:
        """Evaluate a JavaScript expression and return the result."""

    @abstractmethod
    async def raw(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a raw protocol command (escape hatch)."""

    @abstractmethod
    async def go_back(self) -> None:
        """Navigate back in browser history."""

    @abstractmethod
    async def go_forward(self) -> None:
        """Navigate forward in browser history."""

    @abstractmethod
    async def reload(self, ignore_cache: bool = False) -> None:
        """Reload the current page."""

    @abstractmethod
    async def stop_loading(self) -> None:
        """Stop all pending navigations and resource loads."""

    @abstractmethod
    async def wait_for(self, strategy: WaitStrategy) -> None:
        """Wait for a specific condition (selector, load, url)."""

    @abstractmethod
    async def list_tabs(self) -> list[dict[str, Any]]:
        """List all open browser tabs/targets."""

    @abstractmethod
    async def new_tab(self, url: str = "about:blank") -> str:
        """Create a new tab and return its target ID."""

    @abstractmethod
    async def close_tab(self, tab_id: str) -> None:
        """Close a tab by its target ID."""

    async def new_tab_handle(self, url: str = "about:blank") -> Any:
        """Create a new tab with its own session for concurrent operations.

        Default implementation raises NotImplementedError. CDPBackend
        overrides this to return a TabHandle sharing the browser process.

        Args:
            url: Initial URL for the new tab.

        Returns:
            A backend-like object with its own session for the new tab.
        """
        raise NotImplementedError(
            "new_tab_handle is not supported by this backend. Use --mode processes for concurrency."
        )

    @abstractmethod
    async def activate_tab(self, tab_id: str) -> None:
        """Activate (focus) a tab by its target ID."""

    @abstractmethod
    async def new_context(self) -> str:
        """Create a new browser context and return its ID."""

    @abstractmethod
    async def list_contexts(self) -> list[dict[str, Any]]:
        """List all browser contexts."""

    @abstractmethod
    async def close_context(self, context_id: str) -> None:
        """Close a browser context by ID."""

    @abstractmethod
    async def new_user_context(self) -> str:
        """Create a new user context and return its ID."""

    @abstractmethod
    async def get_window_bounds(self) -> dict[str, Any]:
        """Get the current window bounds (width, height, x, y)."""

    @abstractmethod
    async def set_window_bounds(self, width: int, height: int, x: int = 0, y: int = 0) -> None:
        """Set the window bounds."""

    @abstractmethod
    async def browser_version(self) -> str:
        """Get the browser version string."""
