"""Event subscription and console capture mixin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class EventsBackend(ABC):
    """Real-time event subscription and console/log capture."""

    @abstractmethod
    async def subscribe_events(
        self,
        event_types: list[str],
        callback: Any,
    ) -> str:
        """Subscribe to real-time browser events.

        Args:
            event_types: List of event types to subscribe to
                ('console', 'network_request', 'network_response',
                 'dom_mutation', 'dialog', 'navigation').
            callback: Callable that receives event dicts.

        Returns:
            A subscription ID for later unsubscription.
        """

    @abstractmethod
    async def unsubscribe_events(self, subscription_id: str) -> None:
        """Unsubscribe from events by subscription ID.

        Args:
            subscription_id: The ID returned by subscribe_events.
        """

    @abstractmethod
    async def capture_console(self, level: str = "all") -> list[dict[str, Any]]:
        """Capture console messages at or above the given level."""

    @abstractmethod
    async def capture_logs(self) -> list[dict[str, Any]]:
        """Capture browser log entries."""
