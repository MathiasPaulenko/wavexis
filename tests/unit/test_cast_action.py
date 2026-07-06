"""Unit tests for CastAction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.actions.cast import CastAction, CastParams


@pytest.mark.unit
class TestCastAction:
    """Test suite for castaction."""
    def _make_backend(self) -> MagicMock:
        """Create a mock backend for testing.

            Returns:
                A MagicMock backend instance.
            """
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.close = AsyncMock()
        backend.cast_list = AsyncMock(
            return_value=[{"name": "Chromecast", "id": "sink1"}]
        )
        backend.cast_start_tab = AsyncMock()
        backend.cast_stop = AsyncMock()
        return backend

    async def test_list_sinks(self) -> None:
        """Test list sinks."""
        backend = self._make_backend()
        params = CastParams(url="", action="list")
        result = await CastAction(params).execute(backend)
        assert len(result) == 1
        assert result[0]["name"] == "Chromecast"
        backend.cast_list.assert_called_once()

    async def test_start_tab(self) -> None:
        """Test start tab."""
        backend = self._make_backend()
        params = CastParams(url="", action="start-tab", sink_name="sink1")
        result = await CastAction(params).execute(backend)
        assert result is None
        backend.cast_start_tab.assert_called_once_with("sink1")

    async def test_start_tab_missing_sink_raises(self) -> None:
        """Test that start tab missing sink raises raises an appropriate error."""
        backend = self._make_backend()
        params = CastParams(url="", action="start-tab")
        with pytest.raises(ValueError, match="sink_name is required"):
            await CastAction(params).execute(backend)

    async def test_stop(self) -> None:
        """Test stop."""
        backend = self._make_backend()
        params = CastParams(url="", action="stop")
        result = await CastAction(params).execute(backend)
        assert result is None
        backend.cast_stop.assert_called_once()

    async def test_unknown_action_raises(self) -> None:
        """Test that unknown action raises raises an appropriate error."""
        backend = self._make_backend()
        params = CastParams(url="", action="invalid")
        with pytest.raises(ValueError, match="Unknown Cast action"):
            await CastAction(params).execute(backend)

    async def test_lifecycle(self) -> None:
        """Test the action lifecycle (launch, execute, close)."""
        backend = self._make_backend()
        params = CastParams(url="https://example.com", action="list")
        await CastAction(params).execute(backend)
        backend.launch.assert_called_once()
        backend.close.assert_called_once()
