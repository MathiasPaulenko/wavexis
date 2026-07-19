"""Service Worker action for listing, unregistering, and updating SW registrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy


@dataclass
class ServiceWorkerParams:
    """Parameters for service worker operations.

    Attributes:
        url: URL to navigate to before SW operations.
        action: SW action — "list", "unregister", "update", "enable",
            "disable", "deliver-push", "dispatch-sync", "get-messages",
            "inspect", "skip-waiting", "start-worker", "stop-worker".
        registration_id: Service worker registration ID.
        worker_id: Service worker target ID (for get-messages, inspect, stop-worker).
        origin: Origin of the service worker (for deliver-push, dispatch-sync).
        scope_url: Scope URL (for skip-waiting, start-worker).
        data: Push message data (for deliver-push).
        tag: Sync tag (for dispatch-sync).
        last_chance: Whether this is the last chance (for dispatch-sync).
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    action: str = "list"
    registration_id: str | None = None
    worker_id: str | None = None
    origin: str | None = None
    scope_url: str | None = None
    data: str = ""
    tag: str = ""
    last_chance: bool = False
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class ServiceWorkerAction(BaseAction[ServiceWorkerParams, Any]):
    """Action for service worker operations."""

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the service worker action on the backend.

        Args:
            backend: An AbstractBackend instance.

        Returns:
            Result of the service worker operation.
        """
        if self.params.url:
            await backend.navigate(self.params.url, self.params.wait)

        action = self.params.action

        if action == "list":
            return await backend.sw_list()

        if action == "unregister":
            if not self.params.registration_id:
                raise ValueError("registration_id is required for unregister action")
            await backend.sw_unregister(self.params.registration_id)
            return None

        if action == "update":
            if not self.params.registration_id:
                raise ValueError("registration_id is required for update action")
            await backend.sw_update(self.params.registration_id)
            return None

        if action == "enable":
            await backend.sw_enable()
            return None

        if action == "disable":
            await backend.sw_disable()
            return None

        if action == "deliver-push":
            if not self.params.origin or not self.params.registration_id:
                raise ValueError("origin and registration_id are required for deliver-push")
            await backend.sw_deliver_push_message(
                self.params.origin,
                self.params.registration_id,
                self.params.data,
            )
            return None

        if action == "dispatch-sync":
            if not self.params.origin or not self.params.registration_id:
                raise ValueError("origin and registration_id are required for dispatch-sync")
            await backend.sw_dispatch_sync_event(
                self.params.origin,
                self.params.registration_id,
                self.params.tag,
                self.params.last_chance,
            )
            return None

        if action == "get-messages":
            if not self.params.worker_id:
                raise ValueError("worker_id is required for get-messages")
            return await backend.sw_get_messages(self.params.worker_id)

        if action == "inspect":
            if not self.params.worker_id:
                raise ValueError("worker_id is required for inspect")
            await backend.sw_inspect_worker(self.params.worker_id)
            return None

        if action == "skip-waiting":
            if not self.params.scope_url:
                raise ValueError("scope_url is required for skip-waiting")
            await backend.sw_skip_waiting(self.params.scope_url)
            return None

        if action == "start-worker":
            if not self.params.scope_url:
                raise ValueError("scope_url is required for start-worker")
            await backend.sw_start_worker(self.params.scope_url)
            return None

        if action == "stop-worker":
            if not self.params.worker_id:
                raise ValueError("worker_id is required for stop-worker")
            await backend.sw_stop_worker(self.params.worker_id)
            return None

        raise ValueError(f"Unknown service worker action: {action}")
