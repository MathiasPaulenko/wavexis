"""Emulation action for device, viewport, geolocation, timezone, and dark mode."""

from __future__ import annotations

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import EmulationParams


class EmulationAction(BaseAction[EmulationParams, None]):
    """Action for browser emulation operations.

    Supports device emulation, viewport override, geolocation override,
    timezone override, and dark mode emulation.
    """

    async def execute(self, backend: AbstractBackend) -> None:
        """Execute the emulation action on the backend.

        Args:
            backend: The backend to execute the action on.
        """
        params = self.params
        if params.action == "device":
            if params.device is None:
                raise ValueError("device is required for 'device' action")
            await backend.emulate_device(params.device)
        elif params.action == "viewport":
            await backend.set_viewport(
                params.width,
                params.height,
                params.device_scale_factor,
            )
        elif params.action == "geolocation":
            await backend.set_geolocation(
                params.latitude,
                params.longitude,
                params.accuracy,
            )
        elif params.action == "timezone":
            await backend.set_timezone(params.timezone)
        elif params.action == "dark_mode":
            await backend.set_dark_mode(params.dark_mode)
        else:
            raise ValueError(f"Unknown emulation action: {params.action}")
