"""Unit tests for WebAudioAction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from browsix.actions.webaudio import WebAudioAction, WebAudioParams


@pytest.mark.unit
class TestWebAudioAction:
    def _make_backend(self) -> MagicMock:
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.close = AsyncMock()
        backend.webaudio_get_contexts = AsyncMock(
            return_value=[{"contextId": "ctx1", "contextType": "realtime"}]
        )
        backend.webaudio_get_context = AsyncMock(
            return_value={"contextId": "ctx1", "contextType": "realtime"}
        )
        return backend

    async def test_list_contexts(self) -> None:
        backend = self._make_backend()
        params = WebAudioParams(url="https://example.com", action="list")
        result = await WebAudioAction(params).execute(backend)
        assert len(result) == 1
        assert result[0]["contextId"] == "ctx1"
        backend.webaudio_get_contexts.assert_called_once()

    async def test_get_context(self) -> None:
        backend = self._make_backend()
        params = WebAudioParams(
            url="https://example.com", action="get", context_id="ctx1"
        )
        result = await WebAudioAction(params).execute(backend)
        assert result["contextId"] == "ctx1"
        backend.webaudio_get_context.assert_called_once_with("ctx1")

    async def test_get_context_missing_id_raises(self) -> None:
        backend = self._make_backend()
        params = WebAudioParams(url="https://example.com", action="get")
        with pytest.raises(ValueError, match="context_id is required"):
            await WebAudioAction(params).execute(backend)

    async def test_unknown_action_raises(self) -> None:
        backend = self._make_backend()
        params = WebAudioParams(url="https://example.com", action="invalid")
        with pytest.raises(ValueError, match="Unknown WebAudio action"):
            await WebAudioAction(params).execute(backend)

    async def test_lifecycle(self) -> None:
        backend = self._make_backend()
        params = WebAudioParams(url="https://example.com", action="list")
        await WebAudioAction(params).execute(backend)
        backend.launch.assert_called_once()
        backend.close.assert_called_once()
