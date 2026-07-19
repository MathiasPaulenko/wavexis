"""HeadlessExperimental mixin — headless rendering operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class HeadlessExperimentalBackend(ABC):
    """Headless experimental operations."""

    @abstractmethod
    async def headless_experimental_begin_frame(
        self,
        frame_time_ticks: float | None = None,
        interval: float | None = None,
        no_display_updates: bool = False,
        screenshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Begin a new frame in headless mode."""

    @abstractmethod
    async def headless_experimental_disable(self) -> None:
        """Disable the HeadlessExperimental domain."""

    @abstractmethod
    async def headless_experimental_enable(self) -> None:
        """Enable the HeadlessExperimental domain."""
