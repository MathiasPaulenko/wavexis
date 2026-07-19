"""Unit tests for MediaAction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.actions.media import MediaAction, MediaParams


@pytest.mark.unit
class TestMediaAction:
    """Test suite for mediaaction."""

    def _make_backend(self) -> MagicMock:
        """Create a mock backend for testing.

        Returns:
            A MagicMock backend instance.
        """
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.close = AsyncMock()
        backend.media_get_players = AsyncMock(
            return_value=[{"playerId": "p1", "mediaType": "video"}]
        )
        backend.media_get_messages = AsyncMock(
            return_value=[{"level": "info", "message": "loaded"}]
        )
        return backend

    async def test_list_players(self) -> None:
        """Test list players."""
        backend = self._make_backend()
        params = MediaParams(url="https://example.com", action="list")
        result = await MediaAction(params).execute(backend)
        assert len(result) == 1
        assert result[0]["playerId"] == "p1"
        backend.media_get_players.assert_called_once()

    async def test_get_messages(self) -> None:
        """Test get messages."""
        backend = self._make_backend()
        params = MediaParams(url="https://example.com", action="messages", player_id="p1")
        result = await MediaAction(params).execute(backend)
        assert len(result) == 1
        assert result[0]["message"] == "loaded"
        backend.media_get_messages.assert_called_once_with("p1")

    async def test_messages_missing_player_id_raises(self) -> None:
        """Test that messages missing player id raises raises an appropriate error."""
        backend = self._make_backend()
        params = MediaParams(url="https://example.com", action="messages")
        with pytest.raises(ValueError, match="player_id is required"):
            await MediaAction(params).execute(backend)

    async def test_unknown_action_raises(self) -> None:
        """Test that unknown action raises raises an appropriate error."""
        backend = self._make_backend()
        params = MediaParams(url="https://example.com", action="invalid")
        with pytest.raises(ValueError, match="Unknown Media action"):
            await MediaAction(params).execute(backend)

    async def test_lifecycle(self) -> None:
        """Test the action lifecycle (launch, execute, close)."""
        backend = self._make_backend()
        params = MediaParams(url="https://example.com", action="list")
        await MediaAction(params).execute(backend)
        backend.navigate.assert_called_once()
