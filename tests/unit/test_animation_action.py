"""Unit tests for AnimationAction."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from browsix.actions.animation import AnimationAction
from browsix.backend.base import AbstractBackend
from browsix.config import AnimationParams


@pytest.mark.unit
class TestAnimationAction:
    """Test suite for animationaction."""
    def _make_backend(self) -> MagicMock:
        """Create a mock backend for testing.

            Returns:
                A MagicMock backend instance.
            """
        backend = MagicMock(spec=AbstractBackend)
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.animation_list = AsyncMock(
            return_value=[{"id": "anim1", "name": "fade"}]
        )
        backend.animation_pause = AsyncMock()
        backend.animation_play = AsyncMock()
        backend.animation_seek = AsyncMock()
        return backend

    async def test_list_action(self) -> None:
        """Test list action."""
        backend = self._make_backend()
        params = AnimationParams(url="https://example.com", action="list")
        result = await AnimationAction(params).execute(backend)
        assert result == [{"id": "anim1", "name": "fade"}]
        backend.animation_list.assert_called_once()

    async def test_pause_action(self) -> None:
        """Test pause action."""
        backend = self._make_backend()
        params = AnimationParams(
            url="https://example.com", action="pause", animation_id="anim1"
        )
        result = await AnimationAction(params).execute(backend)
        assert result is None
        backend.animation_pause.assert_called_once_with("anim1")

    async def test_play_action(self) -> None:
        """Test play action."""
        backend = self._make_backend()
        params = AnimationParams(
            url="https://example.com", action="play", animation_id="anim1"
        )
        result = await AnimationAction(params).execute(backend)
        assert result is None
        backend.animation_play.assert_called_once_with("anim1")

    async def test_seek_action(self) -> None:
        """Test seek action."""
        backend = self._make_backend()
        params = AnimationParams(
            url="https://example.com", action="seek", animation_id="anim1", time_ms=500
        )
        result = await AnimationAction(params).execute(backend)
        assert result is None
        backend.animation_seek.assert_called_once_with("anim1", 500)

    async def test_pause_missing_id_raises(self) -> None:
        """Test that pause missing id raises raises an appropriate error."""
        backend = self._make_backend()
        params = AnimationParams(url="https://example.com", action="pause")
        with pytest.raises(ValueError, match="animation_id is required"):
            await AnimationAction(params).execute(backend)

    async def test_seek_missing_time_raises(self) -> None:
        """Test that seek missing time raises raises an appropriate error."""
        backend = self._make_backend()
        params = AnimationParams(
            url="https://example.com", action="seek", animation_id="anim1"
        )
        with pytest.raises(ValueError, match="animation_id and time_ms are required"):
            await AnimationAction(params).execute(backend)

    async def test_unknown_action_raises(self) -> None:
        """Test that unknown action raises raises an appropriate error."""
        backend = self._make_backend()
        params = AnimationParams(url="https://example.com", action="unknown")
        with pytest.raises(ValueError, match="Unknown animation action"):
            await AnimationAction(params).execute(backend)

    async def test_lifecycle(self) -> None:
        """Test the action lifecycle (launch, execute, close)."""
        backend = self._make_backend()
        params = AnimationParams(url="https://example.com", action="list")
        await AnimationAction(params).execute(backend)
        backend.launch.assert_called_once()
        backend.navigate.assert_called_once()
        backend.close.assert_called_once()
