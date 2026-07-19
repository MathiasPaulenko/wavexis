"""Service worker mixin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ServiceWorkerBackend(ABC):
    """Service worker registration, unregistration, updates, and lifecycle."""

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

    @abstractmethod
    async def sw_enable(self) -> None:
        """Enable the ServiceWorker domain."""

    @abstractmethod
    async def sw_disable(self) -> None:
        """Disable the ServiceWorker domain."""

    @abstractmethod
    async def sw_deliver_push_message(self, origin: str, registration_id: str, data: str) -> None:
        """Deliver a push message to a service worker.

        Args:
            origin: Origin of the service worker.
            registration_id: Service worker registration ID.
            data: Push message data.
        """

    @abstractmethod
    async def sw_dispatch_sync_event(
        self, origin: str, registration_id: str, tag: str, last_chance: bool
    ) -> None:
        """Dispatch a sync event to a service worker.

        Args:
            origin: Origin of the service worker.
            registration_id: Service worker registration ID.
            tag: Sync tag.
            last_chance: Whether this is the last chance to run the sync.
        """

    @abstractmethod
    async def sw_get_messages(self, worker_id: str) -> list[dict[str, Any]]:
        """Get messages from a service worker.

        Args:
            worker_id: Service worker target ID.

        Returns:
            List of message dicts.
        """

    @abstractmethod
    async def sw_inspect_worker(self, worker_id: str) -> None:
        """Inspect a service worker by opening a DevTools window.

        Args:
            worker_id: Service worker target ID.
        """

    @abstractmethod
    async def sw_skip_waiting(self, scope_url: str) -> None:
        """Skip waiting for a service worker to become active.

        Args:
            scope_url: Scope URL of the service worker.
        """

    @abstractmethod
    async def sw_start_worker(self, scope_url: str) -> None:
        """Start a service worker by scope URL.

        Args:
            scope_url: Scope URL of the service worker.
        """

    @abstractmethod
    async def sw_stop_worker(self, worker_id: str) -> None:
        """Stop a running service worker.

        Args:
            worker_id: Service worker target ID.
        """
