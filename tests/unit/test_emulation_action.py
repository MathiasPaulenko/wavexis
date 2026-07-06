"""Unit tests for EmulationAction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.actions.emulation import EmulationAction
from wavexis.config import EmulationParams


@pytest.mark.unit
class TestEmulationAction:
    """Test suite for emulationaction."""
    async def test_device_action(self) -> None:
        """Test device action."""
        backend = MagicMock()
        backend.emulate_device = AsyncMock()
        params = EmulationParams(action="device", device="iphone-15")
        action = EmulationAction(params)
        await action.execute(backend)
        backend.emulate_device.assert_called_once_with("iphone-15")

    async def test_viewport_action(self) -> None:
        """Test viewport action."""
        backend = MagicMock()
        backend.set_viewport = AsyncMock()
        params = EmulationParams(
            action="viewport", width=375, height=812, device_scale_factor=3.0
        )
        action = EmulationAction(params)
        await action.execute(backend)
        backend.set_viewport.assert_called_once_with(375, 812, 3.0)

    async def test_geolocation_action(self) -> None:
        """Test geolocation action."""
        backend = MagicMock()
        backend.set_geolocation = AsyncMock()
        params = EmulationParams(
            action="geolocation",
            latitude=40.7128,
            longitude=-74.0060,
            accuracy=50.0,
        )
        action = EmulationAction(params)
        await action.execute(backend)
        backend.set_geolocation.assert_called_once_with(40.7128, -74.0060, 50.0)

    async def test_timezone_action(self) -> None:
        """Test timezone action."""
        backend = MagicMock()
        backend.set_timezone = AsyncMock()
        params = EmulationParams(action="timezone", timezone="America/New_York")
        action = EmulationAction(params)
        await action.execute(backend)
        backend.set_timezone.assert_called_once_with("America/New_York")

    async def test_dark_mode_action(self) -> None:
        """Test dark mode action."""
        backend = MagicMock()
        backend.set_dark_mode = AsyncMock()
        params = EmulationParams(action="dark_mode", dark_mode=True)
        action = EmulationAction(params)
        await action.execute(backend)
        backend.set_dark_mode.assert_called_once_with(True)

    async def test_device_action_missing_device(self) -> None:
        """Test that device action missing device raises an appropriate error."""
        backend = MagicMock()
        params = EmulationParams(action="device", device=None)
        action = EmulationAction(params)
        with pytest.raises(ValueError, match="device is required"):
            await action.execute(backend)

    async def test_unknown_action(self) -> None:
        """Test unknown action."""
        backend = MagicMock()
        params = EmulationParams(action="unknown")
        action = EmulationAction(params)
        with pytest.raises(ValueError, match="Unknown emulation action"):
            await action.execute(backend)
