"""Unit tests for BiDiBackend Phase 5 methods — verify NotImplementedError and supported methods."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from browsix.config import SensorParams, ThrottleParams


@pytest.mark.unit
class TestBiDiBackendPhase5:
    def _make_bidi_backend(self) -> Any:
        from browsix.backend.bidi import BiDiBackend

        backend = BiDiBackend()
        backend._client = MagicMock()
        backend._context = MagicMock()
        backend._client.script = MagicMock()
        backend._client.script.evaluate = AsyncMock()
        backend._client._connection = MagicMock()
        backend._client._connection.send_command = AsyncMock()
        return backend

    def test_throttle_network_raises(self) -> None:
        backend = self._make_bidi_backend()
        with pytest.raises(NotImplementedError):
            asyncio.run(backend.throttle_network(ThrottleParams()))

    def test_set_cache_disabled_raises(self) -> None:
        backend = self._make_bidi_backend()
        with pytest.raises(NotImplementedError):
            asyncio.run(backend.set_cache_disabled(True))

    def test_mock_response_raises(self) -> None:
        backend = self._make_bidi_backend()
        with pytest.raises(NotImplementedError):
            asyncio.run(backend.mock_response("https://example.com", {}))

    def test_a11y_tree_raises(self) -> None:
        backend = self._make_bidi_backend()
        with pytest.raises(NotImplementedError):
            asyncio.run(backend.a11y_tree())

    def test_a11y_node_raises(self) -> None:
        backend = self._make_bidi_backend()
        with pytest.raises(NotImplementedError):
            asyncio.run(backend.a11y_node("1"))

    def test_intercept_download_raises(self) -> None:
        backend = self._make_bidi_backend()
        with pytest.raises(NotImplementedError):
            asyncio.run(backend.intercept_download())

    def test_get_security_state_raises(self) -> None:
        backend = self._make_bidi_backend()
        with pytest.raises(NotImplementedError):
            asyncio.run(backend.get_security_state())

    def test_ignore_cert_errors_raises(self) -> None:
        backend = self._make_bidi_backend()
        with pytest.raises(NotImplementedError):
            asyncio.run(backend.ignore_cert_errors(True))

    def test_set_locale_raises(self) -> None:
        backend = self._make_bidi_backend()
        with pytest.raises(NotImplementedError):
            asyncio.run(backend.set_locale("en-US"))

    def test_set_cpu_throttle_raises(self) -> None:
        backend = self._make_bidi_backend()
        with pytest.raises(NotImplementedError):
            asyncio.run(backend.set_cpu_throttle(4.0))

    def test_set_touch_emulation_raises(self) -> None:
        backend = self._make_bidi_backend()
        with pytest.raises(NotImplementedError):
            asyncio.run(backend.set_touch_emulation(True))

    def test_set_sensors_raises(self) -> None:
        backend = self._make_bidi_backend()
        with pytest.raises(NotImplementedError):
            asyncio.run(backend.set_sensors(SensorParams()))

    def test_click_supported(self) -> None:
        backend = self._make_bidi_backend()
        asyncio.run(backend.click("#btn"))
        backend._client.script.evaluate.assert_called()

    def test_dialog_accept_supported(self) -> None:
        backend = self._make_bidi_backend()
        asyncio.run(backend.dialog_accept("yes"))
        backend._client._connection.send_command.assert_called()

    def test_grant_permission_supported(self) -> None:
        backend = self._make_bidi_backend()
        asyncio.run(backend.grant_permission("geolocation"))
        backend._client._connection.send_command.assert_called()
