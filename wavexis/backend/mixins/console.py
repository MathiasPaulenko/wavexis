"""Console domain mixin for AbstractBackend."""

from __future__ import annotations

from abc import abstractmethod


class ConsoleBackend:
    """Console domain for message inspection and control."""

    @abstractmethod
    async def console_clear_messages(self) -> None:
        """Clear all console messages."""

    @abstractmethod
    async def console_disable(self) -> None:
        """Disable the Console domain."""

    @abstractmethod
    async def console_enable(self) -> None:
        """Enable the Console domain."""
