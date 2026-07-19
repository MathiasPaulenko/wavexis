"""DeviceOrientation mixin — device orientation overrides."""

from __future__ import annotations

from abc import ABC, abstractmethod


class DeviceOrientationBackend(ABC):
    """Device orientation override operations."""

    @abstractmethod
    async def device_orientation_clear_override(self) -> None:
        """Clear device orientation override."""

    @abstractmethod
    async def device_orientation_set_override(
        self, alpha: float, beta: float, gamma: float
    ) -> None:
        """Set device orientation override."""
