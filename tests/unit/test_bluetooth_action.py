"""Unit tests for BluetoothAction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.actions.bluetooth import BluetoothAction, BluetoothParams


@pytest.mark.unit
class TestBluetoothAction:
    """Test suite for bluetoothaction."""
    def _make_backend(self) -> MagicMock:
        """Create a mock backend for testing.

            Returns:
                A MagicMock backend instance.
            """
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.close = AsyncMock()
        backend.bluetooth_emulate = AsyncMock()
        backend.bluetooth_stop = AsyncMock()
        return backend

    async def test_emulate(self) -> None:
        """Test emulate."""
        backend = self._make_backend()
        params = BluetoothParams(
            url="https://example.com", action="emulate", name="Test Device"
        )
        result = await BluetoothAction(params).execute(backend)
        assert result is None
        backend.bluetooth_emulate.assert_called_once_with(
            "Test Device", "00:00:00:00:00:01"
        )

    async def test_emulate_custom_address(self) -> None:
        """Test emulate custom address."""
        backend = self._make_backend()
        params = BluetoothParams(
            url="https://example.com",
            action="emulate",
            name="My Device",
            address="AA:BB:CC:DD:EE:FF",
        )
        await BluetoothAction(params).execute(backend)
        backend.bluetooth_emulate.assert_called_once_with(
            "My Device", "AA:BB:CC:DD:EE:FF"
        )

    async def test_emulate_missing_name_raises(self) -> None:
        """Test that emulate missing name raises raises an appropriate error."""
        backend = self._make_backend()
        params = BluetoothParams(url="https://example.com", action="emulate")
        with pytest.raises(ValueError, match="name is required"):
            await BluetoothAction(params).execute(backend)

    async def test_stop(self) -> None:
        """Test stop."""
        backend = self._make_backend()
        params = BluetoothParams(url="https://example.com", action="stop")
        result = await BluetoothAction(params).execute(backend)
        assert result is None
        backend.bluetooth_stop.assert_called_once()

    async def test_unknown_action_raises(self) -> None:
        """Test that unknown action raises raises an appropriate error."""
        backend = self._make_backend()
        params = BluetoothParams(url="https://example.com", action="invalid")
        with pytest.raises(ValueError, match="Unknown Bluetooth action"):
            await BluetoothAction(params).execute(backend)

    async def test_lifecycle(self) -> None:
        """Test the action lifecycle (launch, execute, close)."""
        backend = self._make_backend()
        params = BluetoothParams(
            url="https://example.com", action="emulate", name="Test"
        )
        await BluetoothAction(params).execute(backend)
        backend.launch.assert_called_once()
        backend.close.assert_called_once()
