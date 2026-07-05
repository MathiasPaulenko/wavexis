"""Unit tests for MediaAction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from browsix.actions.media import MediaAction, MediaParams


@pytest.mark.unit
class TestMediaAction:
    def _make_backend(self) -> MagicMock:
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
        backend = self._make_backend()
        params = MediaParams(url="https://example.com", action="list")
        result = await MediaAction(params).execute(backend)
        assert len(result) == 1
        assert result[0]["playerId"] == "p1"
        backend.media_get_players.assert_called_once()

    async def test_get_messages(self) -> None:
        backend = self._make_backend()
        params = MediaParams(
            url="https://example.com", action="messages", player_id="p1"
        )
        result = await MediaAction(params).execute(backend)
        assert len(result) == 1
        assert result[0]["message"] == "loaded"
        backend.media_get_messages.assert_called_once_with("p1")

    async def test_messages_missing_player_id_raises(self) -> None:
        backend = self._make_backend()
        params = MediaParams(url="https://example.com", action="messages")
        with pytest.raises(ValueError, match="player_id is required"):
            await MediaAction(params).execute(backend)

    async def test_unknown_action_raises(self) -> None:
        backend = self._make_backend()
        params = MediaParams(url="https://example.com", action="invalid")
        with pytest.raises(ValueError, match="Unknown Media action"):
            await MediaAction(params).execute(backend)

    async def test_lifecycle(self) -> None:
        backend = self._make_backend()
        params = MediaParams(url="https://example.com", action="list")
        await MediaAction(params).execute(backend)
        backend.launch.assert_called_once()
        backend.close.assert_called_once()
