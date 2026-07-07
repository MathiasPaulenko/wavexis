"""Device emulation and permissions mixin."""

from __future__ import annotations

from abc import ABC, abstractmethod

from wavexis.config import SensorParams


class EmulationBackend(ABC):
    """Device emulation, viewport, geolocation, sensors, and permissions."""

    @abstractmethod
    async def emulate_device(self, device: str) -> None:
        """Emulate a device by preset name (e.g. 'iphone-15')."""

    @abstractmethod
    async def set_viewport(
        self, width: int, height: int, device_scale_factor: float = 1.0
    ) -> None:
        """Set a custom viewport with given dimensions and scale factor."""

    @abstractmethod
    async def set_geolocation(
        self, latitude: float, longitude: float, accuracy: float = 100.0
    ) -> None:
        """Override the geolocation position."""

    @abstractmethod
    async def set_timezone(self, timezone: str) -> None:
        """Override the system timezone (IANA timezone ID)."""

    @abstractmethod
    async def set_dark_mode(self, enabled: bool) -> None:
        """Enable or disable dark mode emulation."""

    @abstractmethod
    async def set_locale(self, locale: str) -> None:
        """Override the browser locale (e.g. 'en-US', 'fr-FR')."""

    @abstractmethod
    async def set_cpu_throttle(self, rate: float) -> None:
        """Throttle CPU performance by a rate multiplier (e.g. 4 = 4x slower)."""

    @abstractmethod
    async def set_touch_emulation(self, enabled: bool) -> None:
        """Enable or disable touch emulation."""

    @abstractmethod
    async def set_sensors(self, sensors: SensorParams) -> None:
        """Override sensor values (geolocation, device orientation, etc.)."""

    @abstractmethod
    async def grant_permission(self, permission: str) -> None:
        """Grant a browser permission (e.g. 'geolocation', 'notifications')."""

    @abstractmethod
    async def reset_permissions(self) -> None:
        """Reset all granted permissions."""
