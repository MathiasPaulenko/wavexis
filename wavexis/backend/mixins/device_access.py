"""DeviceAccess mixin — device prompt management."""

from __future__ import annotations

from abc import ABC, abstractmethod


class DeviceAccessBackend(ABC):
    """Device access prompt operations."""

    @abstractmethod
    async def device_access_cancel_prompt(self, id: str) -> None:
        """Cancel a device access prompt by ID."""

    @abstractmethod
    async def device_access_disable(self) -> None:
        """Disable the DeviceAccess domain."""

    @abstractmethod
    async def device_access_enable(self) -> None:
        """Enable the DeviceAccess domain."""

    @abstractmethod
    async def device_access_select_prompt(self, id: str, device_id: str) -> None:
        """Select a device in a device access prompt."""
