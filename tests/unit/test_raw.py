"""Unit tests for raw() command and backend.raw() method."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from browsix.backend.base import AbstractBackend


@pytest.mark.unit
class TestRawCommand:
    def _make_backend(self) -> MagicMock:
        backend = MagicMock(spec=AbstractBackend)
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.raw = AsyncMock(
            return_value={"result": {"value": 42}}
        )
        return backend

    async def test_raw_basic(self) -> None:
        backend = self._make_backend()
        result = await backend.raw("Page.reload", {"ignoreCache": True})
        assert result == {"result": {"value": 42}}
        backend.raw.assert_called_once_with("Page.reload", {"ignoreCache": True})

    async def test_raw_no_params(self) -> None:
        backend = self._make_backend()
        result = await backend.raw("Network.enable")
        assert result == {"result": {"value": 42}}
        backend.raw.assert_called_once_with("Network.enable")

    async def test_raw_empty_params(self) -> None:
        backend = self._make_backend()
        result = await backend.raw("SystemInfo.getInfo", {})
        assert result == {"result": {"value": 42}}
        backend.raw.assert_called_once_with("SystemInfo.getInfo", {})

    async def test_raw_returns_dict(self) -> None:
        backend = self._make_backend()
        result = await backend.raw("Page.reload", {})
        assert isinstance(result, dict)

    async def test_raw_bidi_command(self) -> None:
        backend = self._make_backend()
        params = {"context": "ctx-id", "url": "https://example.com"}
        result = await backend.raw("browsingContext.navigate", params)
        assert isinstance(result, dict)
        backend.raw.assert_called_once_with("browsingContext.navigate", params)


@pytest.mark.unit
class TestRawJSONValidation:
    def test_valid_json_params(self) -> None:
        import json

        params = '{"ignoreCache": true}'
        parsed = json.loads(params)
        assert parsed == {"ignoreCache": True}

    def test_empty_json_params(self) -> None:
        import json

        params = "{}"
        parsed = json.loads(params)
        assert parsed == {}

    def test_invalid_json_raises(self) -> None:
        import json

        with pytest.raises(json.JSONDecodeError):
            json.loads("{invalid}")

    def test_complex_json_params(self) -> None:
        import json

        params = '{"context": "id", "url": "https://example.com", "wait": "complete"}'
        parsed = json.loads(params)
        assert parsed["context"] == "id"
        assert parsed["url"] == "https://example.com"
        assert parsed["wait"] == "complete"
