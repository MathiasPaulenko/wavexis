"""Unit tests for BiDiBackend Phase 5 methods — verify NotImplementedError and supported methods."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.config import SensorParams, ThrottleParams


@pytest.mark.unit
class TestBiDiBackendPhase5:
    """Test suite for bidibackendphase5."""
    def _make_bidi_backend(self) -> Any:
        """ make bidi backend."""
        from wavexis.backend.bidi import BiDiBackend

        backend = BiDiBackend()
        backend._client = MagicMock()
        backend._context = MagicMock()
        backend._client.script = MagicMock()
        result = MagicMock()
        result.value = True
        backend._client.script.evaluate = AsyncMock(return_value=result)
        backend._client._connection = MagicMock()
        backend._client._connection.send_command = AsyncMock()
        return backend

    def test_throttle_network_supported(self) -> None:
        """Test throttle network supported."""
        backend = self._make_bidi_backend()
        backend._client.emulation = MagicMock()
        backend._client.emulation.set_network_conditions = AsyncMock()
        asyncio.run(backend.throttle_network(ThrottleParams()))
        backend._client.emulation.set_network_conditions.assert_called_once()

    def test_set_cache_disabled_supported(self) -> None:
        """Test set cache disabled supported."""
        backend = self._make_bidi_backend()
        backend._client.cdp = MagicMock()
        backend._client.cdp.send_command = AsyncMock()
        asyncio.run(backend.set_cache_disabled(True))
        backend._client.cdp.send_command.assert_called_once()

    def test_mock_response_supported(self) -> None:
        """Test mock response supported."""
        backend = self._make_bidi_backend()
        backend._client.network = MagicMock()
        backend._client.network.add_cache_override = AsyncMock()
        asyncio.run(backend.mock_response("https://example.com", {}))
        backend._client.network.add_cache_override.assert_called_once()

    def test_a11y_tree_supported(self) -> None:
        """Test a11y tree supported."""
        backend = self._make_bidi_backend()
        backend._client.cdp = MagicMock()
        backend._client.cdp.send_command = AsyncMock(
            return_value={"nodes": []}
        )
        result = asyncio.run(backend.a11y_tree())
        assert isinstance(result, dict)
        backend._client.cdp.send_command.assert_called_once()

    def test_a11y_node_supported(self) -> None:
        """Test a11y node supported."""
        backend = self._make_bidi_backend()
        backend._client.cdp = MagicMock()
        backend._client.cdp.send_command = AsyncMock(
            return_value={"nodes": []}
        )
        result = asyncio.run(backend.a11y_node("1"))
        assert isinstance(result, dict)
        backend._client.cdp.send_command.assert_called_once()

    def test_intercept_download_supported(self) -> None:
        """Test intercept download supported."""
        backend = self._make_bidi_backend()
        backend._client.cdp = MagicMock()
        backend._client.cdp.send_command = AsyncMock()
        result = asyncio.run(backend.intercept_download())
        assert result == b""
        backend._client.cdp.send_command.assert_called_once()

    def test_get_security_state_supported(self) -> None:
        """Test get security state supported."""
        backend = self._make_bidi_backend()
        backend._client.cdp = MagicMock()
        backend._client.cdp.send_command = AsyncMock(return_value={"securityState": "secure"})
        asyncio.run(backend.get_security_state())
        backend._client.cdp.send_command.assert_called_once()

    def test_ignore_cert_errors_supported(self) -> None:
        """Test ignore cert errors supported."""
        backend = self._make_bidi_backend()
        backend._client.cdp = MagicMock()
        backend._client.cdp.send_command = AsyncMock()
        asyncio.run(backend.ignore_cert_errors(True))
        backend._client.cdp.send_command.assert_called_once()

    def test_set_locale_supported(self) -> None:
        """Test set locale supported."""
        backend = self._make_bidi_backend()
        backend._client.cdp = MagicMock()
        backend._client.cdp.send_command = AsyncMock()
        asyncio.run(backend.set_locale("en-US"))
        backend._client.cdp.send_command.assert_called_once()

    def test_set_cpu_throttle_supported(self) -> None:
        """Test set cpu throttle supported."""
        backend = self._make_bidi_backend()
        backend._client.cdp = MagicMock()
        backend._client.cdp.send_command = AsyncMock()
        asyncio.run(backend.set_cpu_throttle(4.0))
        backend._client.cdp.send_command.assert_called_once()

    def test_set_touch_emulation_supported(self) -> None:
        """Test set touch emulation supported."""
        backend = self._make_bidi_backend()
        backend._client.cdp = MagicMock()
        backend._client.cdp.send_command = AsyncMock()
        asyncio.run(backend.set_touch_emulation(True))
        backend._client.cdp.send_command.assert_called_once()

    def test_set_sensors_supported(self) -> None:
        """Test set sensors supported."""
        backend = self._make_bidi_backend()
        backend._client.cdp = MagicMock()
        backend._client.cdp.send_command = AsyncMock()
        asyncio.run(backend.set_sensors(SensorParams(
            type="device-orientation",
            values={"alpha": 0, "beta": 0, "gamma": 0},
        )))
        backend._client.cdp.send_command.assert_called_once()

    def test_click_supported(self) -> None:
        """Test click supported."""
        backend = self._make_bidi_backend()
        asyncio.run(backend.click("#btn"))
        backend._client.script.evaluate.assert_called()

    def test_dialog_accept_supported(self) -> None:
        """Test dialog accept supported."""
        backend = self._make_bidi_backend()
        asyncio.run(backend.dialog_accept("yes"))
        backend._client._connection.send_command.assert_called()

    def test_grant_permission_supported(self) -> None:
        """Test grant permission supported."""
        backend = self._make_bidi_backend()
        asyncio.run(backend.grant_permission("geolocation"))
        backend._client._connection.send_command.assert_called()
