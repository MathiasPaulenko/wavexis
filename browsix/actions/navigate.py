"""Navigation actions for back, forward, reload, stop, and wait."""

from __future__ import annotations

from dataclasses import dataclass

from browsix.actions.base import BaseAction
from browsix.backend.base import AbstractBackend
from browsix.config import WaitStrategy


@dataclass
class NavigateParams:
    """Parameters for navigation actions.

    Attributes:
        url: URL to navigate to (for navigate action).
        wait: Wait strategy after navigation.
    """

    url: str = ""
    wait: WaitStrategy | None = None


class NavigateAction(BaseAction[NavigateParams, None]):
    """Action for navigating to a URL."""

    async def execute(self, backend: AbstractBackend) -> None:
        """Execute the navigate action.

        Args:
            backend: The browser backend to use.
        """
        params = self.params
        await backend.navigate(params.url, params.wait)


class BackAction(BaseAction[None, None]):
    """Action for navigating back in history."""

    async def execute(self, backend: AbstractBackend) -> None:
        """Execute the back action.

        Args:
            backend: The browser backend to use.
        """
        await backend.go_back()


class ForwardAction(BaseAction[None, None]):
    """Action for navigating forward in history."""

    async def execute(self, backend: AbstractBackend) -> None:
        """Execute the forward action.

        Args:
            backend: The browser backend to use.
        """
        await backend.go_forward()


class ReloadAction(BaseAction[bool, None]):
    """Action for reloading the current page.

    Params is a bool indicating whether to ignore cache.
    """

    async def execute(self, backend: AbstractBackend) -> None:
        """Execute the reload action.

        Args:
            backend: The browser backend to use.
        """
        await backend.reload(ignore_cache=self.params)


class StopAction(BaseAction[None, None]):
    """Action for stopping all pending navigations."""

    async def execute(self, backend: AbstractBackend) -> None:
        """Execute the stop action.

        Args:
            backend: The browser backend to use.
        """
        await backend.stop_loading()


class WaitAction(BaseAction[WaitStrategy, None]):
    """Action for waiting for a condition."""

    async def execute(self, backend: AbstractBackend) -> None:
        """Execute the wait action.

        Args:
            backend: The browser backend to use.
        """
        await backend.wait_for(self.params)
