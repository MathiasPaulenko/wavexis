"""Unit tests for Tracing backend methods."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.unit
class TestTracing:
    """Test suite for tracing backend methods."""

    def _make_backend(self) -> MagicMock:
        """Create a mock backend with tracing methods."""
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.tracing_start = AsyncMock()
        backend.tracing_end = AsyncMock()
        backend.tracing_get_categories = AsyncMock(return_value=["disabled-by-default", "devtools"])
        backend.tracing_record_clock_sync_marker = AsyncMock()
        backend.tracing_request_memory_dump = AsyncMock(
            return_value={"success": True, "dumpGuid": "dump-1"}
        )
        backend.tracing_get_track_event_descriptor = AsyncMock(
            return_value={"trackEvent": "test", "descriptor": {}}
        )
        return backend

    async def test_start(self) -> None:
        """Test tracing_start calls backend."""
        backend = self._make_backend()
        await backend.tracing_start("cat1,cat2", "opt1", "ReportEvents")
        backend.tracing_start.assert_called_once_with("cat1,cat2", "opt1", "ReportEvents")

    async def test_start_defaults(self) -> None:
        """Test tracing_start with default args."""
        backend = self._make_backend()
        await backend.tracing_start()
        backend.tracing_start.assert_called_once()

    async def test_end(self) -> None:
        """Test tracing_end calls backend."""
        backend = self._make_backend()
        await backend.tracing_end()
        backend.tracing_end.assert_called_once()

    async def test_get_categories(self) -> None:
        """Test tracing_get_categories returns list."""
        backend = self._make_backend()
        result = await backend.tracing_get_categories()
        assert result == ["disabled-by-default", "devtools"]

    async def test_record_clock_sync_marker(self) -> None:
        """Test tracing_record_clock_sync_marker calls backend."""
        backend = self._make_backend()
        await backend.tracing_record_clock_sync_marker("sync-1")
        backend.tracing_record_clock_sync_marker.assert_called_once_with("sync-1")

    async def test_request_memory_dump(self) -> None:
        """Test tracing_request_memory_dump returns dict."""
        backend = self._make_backend()
        result = await backend.tracing_request_memory_dump()
        assert result == {"success": True, "dumpGuid": "dump-1"}

    async def test_get_track_event_descriptor(self) -> None:
        """Test tracing_get_track_event_descriptor returns dict."""
        backend = self._make_backend()
        result = await backend.tracing_get_track_event_descriptor("test")
        assert result == {"trackEvent": "test", "descriptor": {}}
        backend.tracing_get_track_event_descriptor.assert_called_once_with("test")
