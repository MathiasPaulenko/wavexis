"""Service Worker action for listing, unregistering, and updating SW registrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from browsix.actions.base import BaseAction
from browsix.backend.base import AbstractBackend
from browsix.config import BrowserOptions, WaitStrategy


@dataclass
class ServiceWorkerParams:
    """Parameters for service worker operations.

    Attributes:
        url: URL to navigate to before SW operations.
        action: SW action — "list", "unregister", "update".
        registration_id: Service worker registration ID.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    action: str = "list"
    registration_id: str | None = None
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
        try:
            await backend.launch(self.params.browser)
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

            raise ValueError(f"Unknown service worker action: {action}")

        finally:
            await backend.close()
