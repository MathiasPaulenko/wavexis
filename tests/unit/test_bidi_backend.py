"""Unit tests for BiDiBackend."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from browsix.config import ScreenshotParams


@pytest.mark.unit
class TestBiDiBackend:
    def test_import_error(self) -> None:
        with patch("browsix.backend.bidi.BiDiClient", None):
            from browsix.backend.bidi import BiDiBackend

            with pytest.raises(ImportError, match="bidiwave"):
                BiDiBackend()

    async def test_unsupported_methods_raise_not_implemented(self) -> None:
        with patch("browsix.backend.bidi.BiDiClient", MagicMock()):
            from browsix.backend.bidi import BiDiBackend

            backend = BiDiBackend()
            with pytest.raises(NotImplementedError):
                await backend.pdf(MagicMock())
            with pytest.raises(NotImplementedError):
                await backend.screencast(MagicMock())
            with pytest.raises(NotImplementedError):
                await backend.capture_har(MagicMock())
            with pytest.raises(NotImplementedError):
                await backend.emulate_device("iphone-15")
            with pytest.raises(NotImplementedError):
                await backend.webauthn_add_virtual_authenticator("ctap2", "usb")
            with pytest.raises(NotImplementedError):
                await backend.webaudio_get_contexts()
            with pytest.raises(NotImplementedError):
                await backend.media_get_players()
            with pytest.raises(NotImplementedError):
                await backend.cast_list()
            with pytest.raises(NotImplementedError):
                await backend.bluetooth_emulate("test")

    async def test_implemented_methods_raise_runtime_without_launch(self) -> None:
        with patch("browsix.backend.bidi.BiDiClient", MagicMock()):
            from browsix.backend.bidi import BiDiBackend

            backend = BiDiBackend()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.activate_tab("x")
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.capture_console()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.capture_logs()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.get_cookies()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.set_cookie(MagicMock())
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.delete_cookie("x", "y")
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.clear_cookies()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.set_headers({})
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.set_user_agent("x")
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.browser_version()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.set_viewport(100, 100)
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.set_geolocation(0.0, 0.0)
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.set_timezone("UTC")
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.set_dark_mode(True)
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.screenshot_selector("h1")
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.set_locale("en-US")
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.set_touch_emulation(True)
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.throttle_network(MagicMock())
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.set_cache_disabled(True)
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.mock_response("https://example.com", {})

    async def test_bidi_paridad_methods_raise_runtime_without_launch(self) -> None:
        with patch("browsix.backend.bidi.BiDiClient", MagicMock()):
            from browsix.backend.bidi import BiDiBackend

            backend = BiDiBackend()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.go_back()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.go_forward()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.reload()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.stop_loading()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.list_tabs()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.new_tab()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.close_tab("x")
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.dom_get("h1")
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.new_context()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.list_contexts()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.close_context("x")
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.get_window_bounds()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.set_window_bounds(100, 100)

    async def test_navigate_without_launch(self) -> None:
        with patch("browsix.backend.bidi.BiDiClient", MagicMock()):
            from browsix.backend.bidi import BiDiBackend

            backend = BiDiBackend()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.navigate("https://example.com")

    async def test_eval_without_launch(self) -> None:
        with patch("browsix.backend.bidi.BiDiClient", MagicMock()):
            from browsix.backend.bidi import BiDiBackend

            backend = BiDiBackend()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.eval("document.title")

    async def test_raw_without_launch(self) -> None:
        with patch("browsix.backend.bidi.BiDiClient", MagicMock()):
            from browsix.backend.bidi import BiDiBackend

            backend = BiDiBackend()
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.raw("test.method")

    async def test_screenshot_without_launch(self) -> None:
        with patch("browsix.backend.bidi.BiDiClient", MagicMock()):
            from browsix.backend.bidi import BiDiBackend

            backend = BiDiBackend()
            params = ScreenshotParams(url="https://example.com")
            with pytest.raises(RuntimeError, match="not launched"):
                await backend.screenshot(params)

    async def test_close_without_launch(self) -> None:
        with patch("browsix.backend.bidi.BiDiClient", MagicMock()):
            from browsix.backend.bidi import BiDiBackend

            backend = BiDiBackend()
            await backend.close()
