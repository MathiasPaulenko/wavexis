"""Unit tests for v2.7.x features: live event streaming, extensions, prefs."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.unit
class TestExtensionInstall:
    """Tests for extension_install in CDP and BiDi backends."""

    def test_cdp_install_unpacked(self, tmp_path: Any) -> None:
        """CDP backend installs unpacked extension directory."""
        from wavexis.backend.cdp import CDPBackend

        ext_dir = tmp_path / "myext"
        ext_dir.mkdir()

        backend = CDPBackend()
        mock_session = MagicMock()
        mock_session.send = AsyncMock(return_value={})
        backend._session = mock_session

        ext_id = asyncio.run(backend.extension_install(str(ext_dir)))
        assert len(ext_id) == 32
        mock_session.send.assert_called_once()
        call_args = mock_session.send.call_args
        assert call_args.args[0] == "Extensions.loadUnpacked"

    def test_cdp_install_crx(self, tmp_path: Any) -> None:
        """CDP backend installs .crx file."""
        from wavexis.backend.cdp import CDPBackend

        crx_file = tmp_path / "ext.crx"
        crx_file.write_bytes(b"fake-crx-data")

        backend = CDPBackend()
        mock_session = MagicMock()
        mock_session.send = AsyncMock(return_value={})
        backend._session = mock_session

        ext_id = asyncio.run(backend.extension_install(str(crx_file)))
        assert len(ext_id) == 32
        call_args = mock_session.send.call_args
        assert call_args.args[0] == "Extensions.load"

    def test_bidi_install_unpacked(self, tmp_path: Any) -> None:
        """BiDi backend installs unpacked extension via CDP bridge."""
        from wavexis.backend.bidi import BiDiBackend

        ext_dir = tmp_path / "myext"
        ext_dir.mkdir()

        backend = BiDiBackend()
        mock_client = MagicMock()
        mock_client.cdp = MagicMock()
        mock_client.cdp.send_command = AsyncMock(return_value={})
        backend._client = mock_client

        ext_id = asyncio.run(backend.extension_install(str(ext_dir)))
        assert len(ext_id) == 32
        call_args = mock_client.cdp.send_command.call_args
        assert call_args.args[0] == "Extensions.loadUnpacked"

    def test_bidi_not_launched_raises(self) -> None:
        """BiDi backend raises if not launched."""
        from wavexis.backend.bidi import BiDiBackend

        backend = BiDiBackend()
        with pytest.raises(RuntimeError, match="not launched"):
            asyncio.run(backend.extension_install("/fake/path"))


@pytest.mark.unit
class TestExtensionUninstall:
    """Tests for extension_uninstall."""

    def test_cdp_uninstall(self) -> None:
        """CDP backend uninstalls extension by ID."""
        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        mock_session = MagicMock()
        mock_session.send = AsyncMock(return_value={})
        backend._session = mock_session

        asyncio.run(backend.extension_uninstall("ext-123"))
        call_args = mock_session.send.call_args
        assert call_args.args[0] == "Extensions.uninstall"
        assert call_args.args[1] == {"id": "ext-123"}

    def test_bidi_uninstall(self) -> None:
        """BiDi backend uninstalls extension via CDP bridge."""
        from wavexis.backend.bidi import BiDiBackend

        backend = BiDiBackend()
        mock_client = MagicMock()
        mock_client.cdp = MagicMock()
        mock_client.cdp.send_command = AsyncMock(return_value={})
        backend._client = mock_client

        asyncio.run(backend.extension_uninstall("ext-456"))
        call_args = mock_client.cdp.send_command.call_args
        assert call_args.args[0] == "Extensions.uninstall"


@pytest.mark.unit
class TestExtensionList:
    """Tests for extension_list."""

    def test_cdp_list(self) -> None:
        """CDP backend lists extensions."""
        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        mock_session = MagicMock()
        mock_session.send = AsyncMock(return_value={
            "extensions": [
                {"id": "ext1", "name": "AdBlock", "version": "1.0", "enabled": True},
                {"id": "ext2", "name": "DarkMode", "version": "2.0", "enabled": False},
            ]
        })
        backend._session = mock_session

        result = asyncio.run(backend.extension_list())
        assert len(result) == 2
        assert result[0]["id"] == "ext1"
        assert result[0]["name"] == "AdBlock"
        assert result[1]["enabled"] is False

    def test_cdp_list_empty(self) -> None:
        """CDP backend returns empty list when no extensions."""
        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        mock_session = MagicMock()
        mock_session.send = AsyncMock(return_value={})
        backend._session = mock_session

        result = asyncio.run(backend.extension_list())
        assert result == []


@pytest.mark.unit
class TestBrowserPrefs:
    """Tests for get_pref and set_pref."""

    def test_cdp_get_pref(self) -> None:
        """CDP backend gets a preference value."""
        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        mock_session = MagicMock()
        mock_session.send = AsyncMock(return_value={"value": "/downloads"})
        backend._session = mock_session

        result = asyncio.run(backend.get_pref("download.default_directory"))
        assert result == "/downloads"
        call_args = mock_session.send.call_args
        assert call_args.args[0] == "Browser.getPreference"

    def test_cdp_set_pref(self) -> None:
        """CDP backend sets a preference value."""
        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        mock_session = MagicMock()
        mock_session.send = AsyncMock(return_value={})
        backend._session = mock_session

        asyncio.run(backend.set_pref("download.default_directory", "/new/path"))
        call_args = mock_session.send.call_args
        assert call_args.args[0] == "Browser.setPreference"
        assert call_args.args[1] == {
            "name": "download.default_directory",
            "value": "/new/path",
        }

    def test_bidi_get_pref(self) -> None:
        """BiDi backend gets a preference via CDP bridge."""
        from wavexis.backend.bidi import BiDiBackend

        backend = BiDiBackend()
        mock_client = MagicMock()
        mock_client.cdp = MagicMock()
        mock_client.cdp.send_command = AsyncMock(return_value={"value": True})
        backend._client = mock_client

        result = asyncio.run(backend.get_pref("safebrowsing.enabled"))
        assert result is True

    def test_bidi_set_pref(self) -> None:
        """BiDi backend sets a preference via CDP bridge."""
        from wavexis.backend.bidi import BiDiBackend

        backend = BiDiBackend()
        mock_client = MagicMock()
        mock_client.cdp = MagicMock()
        mock_client.cdp.send_command = AsyncMock(return_value={})
        backend._client = mock_client

        asyncio.run(backend.set_pref("safebrowsing.enabled", False))
        call_args = mock_client.cdp.send_command.call_args
        assert call_args.args[0] == "Browser.setPreference"

    def test_bidi_get_pref_not_launched(self) -> None:
        """BiDi backend raises if not launched."""
        from wavexis.backend.bidi import BiDiBackend

        backend = BiDiBackend()
        with pytest.raises(RuntimeError, match="not launched"):
            asyncio.run(backend.get_pref("any.key"))


@pytest.mark.unit
class TestLiveEventStreaming:
    """Tests for extended WebSocket event types in serve.py."""

    def test_dom_mutation_stream_function_exists(self) -> None:
        """_stream_dom_mutations function should exist in serve.py."""
        from wavexis.serve import _stream_dom_mutations
        assert callable(_stream_dom_mutations)

    def test_perf_metrics_stream_function_exists(self) -> None:
        """_stream_perf_metrics function should exist in serve.py."""
        from wavexis.serve import _stream_perf_metrics
        assert callable(_stream_perf_metrics)

    def test_websocket_handler_supports_new_events(self) -> None:
        """handle_websocket should accept dom_mutation and perf_metrics events."""
        import inspect

        from wavexis.serve import handle_websocket
        source = inspect.getsource(handle_websocket)
        assert "dom_mutation" in source
        assert "perf_metrics" in source
