"""Service worker mixin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ServiceWorkerBackend(ABC):
    """Service worker registration, unregistration, and updates."""

    @abstractmethod
    async def sw_list(self) -> list[dict[str, Any]]:
        """List registered service workers.

        Returns:
            List of service worker registration dicts.
        """

    @abstractmethod
    async def sw_unregister(self, registration_id: str) -> None:
        """Unregister a service worker by registration ID.

        Args:
            registration_id: The service worker registration ID.
        """

    @abstractmethod
    async def sw_update(self, registration_id: str) -> None:
        """Trigger an update for a service worker registration.

        Args:
            registration_id: The service worker registration ID.
        """
