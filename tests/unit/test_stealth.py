"""Unit tests for stealth mode."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.actions.stealth import STEALTH_JS, get_stealth_js
from wavexis.config import BrowserOptions


@pytest.mark.unit
class TestStealthJS:
    """Tests for stealth JS content."""

    def test_stealth_js_contains_webdriver_patch(self) -> None:
        """Stealth JS should hide navigator.webdriver."""
        js = get_stealth_js()
        assert "webdriver" in js
        assert "undefined" in js

    def test_stealth_js_contains_plugins_patch(self) -> None:
        """Stealth JS should fake navigator.plugins."""
        js = get_stealth_js()
        assert "plugins" in js
        assert "Chrome PDF Plugin" in js

    def test_stealth_js_contains_languages_patch(self) -> None:
        """Stealth JS should set navigator.languages."""
        js = get_stealth_js()
        assert "languages" in js
        assert "en-US" in js

    def test_stealth_js_contains_chrome_runtime(self) -> None:
        """Stealth JS should set window.chrome.runtime."""
        js = get_stealth_js()
        assert "chrome" in js
        assert "runtime" in js

    def test_stealth_js_contains_webgl_patch(self) -> None:
        """Stealth JS should fake WebGL vendor/renderer."""
        js = get_stealth_js()
        assert "WebGLRenderingContext" in js
        assert "Intel" in js

    def test_stealth_js_contains_permissions_patch(self) -> None:
        """Stealth JS should patch permissions API."""
        js = get_stealth_js()
        assert "permissions" in js
        assert "notifications" in js

    def test_stealth_js_contains_platform_patch(self) -> None:
        """Stealth JS should set navigator.platform."""
        js = get_stealth_js()
        assert "platform" in js
        assert "Win32" in js

    def test_stealth_js_is_iife(self) -> None:
        """Stealth JS should be wrapped in an IIFE."""
        js = get_stealth_js()
        assert js.startswith("(() => {") or js.startswith("(() => {")
        assert js.endswith("})()")

    def test_get_stealth_js_returns_constant(self) -> None:
        """get_stealth_js should return the same string as STEALTH_JS."""
        assert get_stealth_js() == STEALTH_JS


@pytest.mark.unit
class TestStealthBrowserOptions:
    """Tests for BrowserOptions.stealth field."""

    def test_default_stealth_false(self) -> None:
        """BrowserOptions.stealth defaults to False."""
        opts = BrowserOptions()
        assert opts.stealth is False

    def test_stealth_can_be_enabled(self) -> None:
        """BrowserOptions.stealth can be set to True."""
        opts = BrowserOptions(stealth=True)
        assert opts.stealth is True


@pytest.mark.unit
class TestStealthCDPLaunch:
    """Tests for stealth injection in CDP backend launch."""

    def test_cdp_launch_injects_stealth(self) -> None:
        """CDP backend should inject stealth JS when stealth=True."""
        from unittest.mock import patch

        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        mock_session = MagicMock()
        mock_session.runtime = MagicMock()
        mock_session.runtime.evaluate = AsyncMock()
        mock_client = MagicMock()
        mock_client.new_page = AsyncMock(return_value=mock_session)

        with patch(
            "wavexis.backend.cdp.CDPClient.connect",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            opts = BrowserOptions(stealth=True, browser_url="ws://localhost:9222")
            asyncio.run(backend.launch(opts))

        evaluate_calls = mock_session.runtime.evaluate.call_args_list
        assert len(evaluate_calls) >= 1
        js_arg = evaluate_calls[-1].args[0]
        assert "webdriver" in js_arg

    def test_cdp_launch_no_stealth_by_default(self) -> None:
        """CDP backend should not inject stealth JS when stealth=False."""
        from unittest.mock import patch

        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        mock_session = MagicMock()
        mock_session.runtime = MagicMock()
        mock_session.runtime.evaluate = AsyncMock()
        mock_client = MagicMock()
        mock_client.new_page = AsyncMock(return_value=mock_session)

        with patch(
            "wavexis.backend.cdp.CDPClient.connect",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            opts = BrowserOptions(stealth=False, browser_url="ws://localhost:9222")
            asyncio.run(backend.launch(opts))

        evaluate_calls = mock_session.runtime.evaluate.call_args_list
        stealth_calls = [c for c in evaluate_calls if "webdriver" in str(c.args)]
        assert len(stealth_calls) == 0


@pytest.mark.unit
class TestStealthBiDiLaunch:
    """Tests for stealth injection in BiDi backend launch."""

    def test_bidi_launch_injects_stealth(self) -> None:
        """BiDi backend should inject stealth JS when stealth=True."""
        from unittest.mock import patch

        from wavexis.backend.bidi import BiDiBackend

        backend = BiDiBackend()
        mock_client = MagicMock()
        mock_client.session = MagicMock()
        mock_client.session.new = AsyncMock()
        mock_client.browsing = MagicMock()
        mock_client.browsing.create_context = AsyncMock(return_value="ctx-123")
        mock_client.browsing.set_viewport = AsyncMock()
        mock_client.script = MagicMock()
        mock_client.script.evaluate = AsyncMock()
        mock_client.cdp = MagicMock()
        mock_client.cdp.send_command = AsyncMock()

        with patch(
            "wavexis.backend.bidi.BiDiClient.connect",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            opts = BrowserOptions(
                stealth=True,
                extra_headers={"ws_url": "ws://localhost:9222/session"},
            )
            asyncio.run(backend.launch(opts))

        evaluate_calls = mock_client.script.evaluate.call_args_list
        assert len(evaluate_calls) >= 1
        js_arg = evaluate_calls[-1].args[1]
        assert "webdriver" in js_arg
