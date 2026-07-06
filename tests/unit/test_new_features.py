"""Unit tests for session, extract, form, websocket, and lighthouse actions."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.actions.extract import ExtractAction, ExtractParams
from wavexis.actions.form import FormAction, FormParams
from wavexis.actions.lighthouse import LighthouseAction, LighthouseParams
from wavexis.actions.session import (
    SessionData,
    SessionLoadAction,
    SessionSaveAction,
)
from wavexis.actions.websocket import WebSocketInterceptAction, WebSocketParams
from wavexis.config import WaitStrategy

pytestmark = pytest.mark.unit


# ── Session ──────────────────────────────────────────────────────


class TestSessionSave:
    """Tests for SessionSaveAction."""

    async def test_save_captures_cookies_and_storage(self) -> None:
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.get_cookies = AsyncMock(
            return_value=[{"name": "session", "value": "abc", "domain": "example.com"}]
        )
        backend.storage_list = AsyncMock(
            side_effect=[
                {"token": "xyz"},
                {"temp": "123"},
            ]
        )
        backend.eval = AsyncMock(return_value="https://example.com/page")

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            path = Path(f.name)

        action = SessionSaveAction(path)
        await action.execute(backend)

        with open(path, encoding="utf-8") as f:  # noqa: ASYNC230
            data = json.load(f)
        assert len(data["cookies"]) == 1
        assert data["cookies"][0]["name"] == "session"
        assert data["local_storage"]["token"] == "xyz"
        assert data["session_storage"]["temp"] == "123"
        assert data["url"] == "https://example.com/page"
        os.remove(path)

    async def test_save_handles_eval_error(self) -> None:
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.get_cookies = AsyncMock(return_value=[])
        backend.storage_list = AsyncMock(side_effect=[{}, {}])
        backend.eval = AsyncMock(side_effect=Exception("no page"))

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            path = Path(f.name)

        action = SessionSaveAction(path)
        result = await action.execute(backend)

        data = json.loads(result)
        assert data["url"] == ""
        os.remove(path)


class TestSessionLoad:
    """Tests for SessionLoadAction."""

    async def test_load_restores_cookies_and_storage(self) -> None:
        session_data = SessionData(
            cookies=[{"name": "auth", "value": "token123", "domain": ".example.com"}],
            local_storage={"key1": "val1"},
            session_storage={"key2": "val2"},
            url="https://example.com",
        )

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            f.write(session_data.to_json())
            path = Path(f.name)

        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.set_cookie = AsyncMock()
        backend.storage_set = AsyncMock()

        action = SessionLoadAction(path)
        await action.execute(backend)

        assert backend.set_cookie.call_count == 1
        assert backend.storage_set.call_count == 2
        os.remove(path)

    async def test_load_empty_session(self) -> None:
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            f.write(SessionData(
                cookies=[], local_storage={}, session_storage={}, url=""
            ).to_json())
            path = Path(f.name)

        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.set_cookie = AsyncMock()
        backend.storage_set = AsyncMock()

        action = SessionLoadAction(path)
        await action.execute(backend)

        assert backend.set_cookie.call_count == 0
        assert backend.storage_set.call_count == 0
        os.remove(path)


class TestSessionData:
    """Tests for SessionData serialization."""

    def test_to_json_and_from_json_roundtrip(self) -> None:
        data = SessionData(
            cookies=[{"name": "a", "value": "b"}],
            local_storage={"k": "v"},
            session_storage={"s": "t"},
            url="https://test.com",
        )
        json_str = data.to_json()
        restored = SessionData.from_json(json_str)
        assert restored.cookies == data.cookies
        assert restored.local_storage == data.local_storage
        assert restored.session_storage == data.session_storage
        assert restored.url == data.url


# ── Extract ──────────────────────────────────────────────────────


class TestExtractAction:
    """Tests for ExtractAction."""

    async def test_extract_single_record(self) -> None:
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.eval = AsyncMock(
            return_value=[{"title": "Hello", "price": "$10"}]
        )

        params = ExtractParams(
            url="https://shop.com",
            schema={"title": "h1", "price": ".price"},
            wait=WaitStrategy(strategy="load"),
        )
        action = ExtractAction(params)
        results = await action.execute(backend)

        assert len(results) == 1
        assert results[0]["title"] == "Hello"
        assert results[0]["price"] == "$10"

    async def test_extract_multiple_records_with_selector(self) -> None:
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.eval = AsyncMock(
            return_value=[
                {"name": "Item 1", "price": "$10"},
                {"name": "Item 2", "price": "$20"},
            ]
        )

        params = ExtractParams(
            url="https://shop.com/products",
            schema={"name": ".name", "price": ".price"},
            selector=".product",
            wait=WaitStrategy(strategy="load"),
        )
        action = ExtractAction(params)
        results = await action.execute(backend)

        assert len(results) == 2
        assert results[0]["name"] == "Item 1"
        assert results[1]["price"] == "$20"

    async def test_extract_returns_empty_on_non_list(self) -> None:
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.eval = AsyncMock(return_value=None)

        params = ExtractParams(
            url="https://shop.com",
            schema={"title": "h1"},
        )
        action = ExtractAction(params)
        results = await action.execute(backend)

        assert results == []


# ── Form ─────────────────────────────────────────────────────────


class TestFormAction:
    """Tests for FormAction."""

    async def test_form_fills_all_fields(self) -> None:
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.fill = AsyncMock()

        params = FormParams(
            url="https://app.com/register",
            fields={"#name": "Mathias", "#email": "test@test.com"},
            wait=WaitStrategy(strategy="load"),
        )
        action = FormAction(params)
        result = await action.execute(backend)

        assert result["fields_filled"] == 2
        assert result["fields_total"] == 2
        assert result["submitted"] is False

    async def test_form_fills_and_submits(self) -> None:
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.fill = AsyncMock()
        backend.click = AsyncMock()

        params = FormParams(
            url="https://app.com/register",
            fields={"#name": "Mathias"},
            submit="#submit-btn",
            wait=WaitStrategy(strategy="load"),
        )
        action = FormAction(params)
        result = await action.execute(backend)

        assert result["fields_filled"] == 1
        assert result["submitted"] is True

    async def test_form_handles_fill_error(self) -> None:
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.fill = AsyncMock(side_effect=[None, Exception("not found")])

        params = FormParams(
            url="https://app.com/register",
            fields={"#name": "Mathias", "#missing": "val"},
            wait=WaitStrategy(strategy="load"),
        )
        action = FormAction(params)
        result = await action.execute(backend)

        assert result["fields_filled"] == 1
        assert result["fields_total"] == 2


# ── WebSocket ────────────────────────────────────────────────────


class TestWebSocketIntercept:
    """Tests for WebSocketInterceptAction."""

    async def test_ws_returns_frame_data(self) -> None:
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.eval = AsyncMock(
            return_value={
                "url": "wss://api.example.com/ws",
                "sent": [{"timestamp": 123, "data": "ping"}],
                "received": [{"timestamp": 124, "data": "pong"}],
                "errors": [],
            }
        )

        params = WebSocketParams(
            url="https://app.com",
            duration_ms=1000,
            wait=WaitStrategy(strategy="load"),
        )
        action = WebSocketInterceptAction(params)
        result = await action.execute(backend)

        assert result["url"] == "wss://api.example.com/ws"
        assert len(result["sent"]) == 1
        assert len(result["received"]) == 1

    async def test_ws_returns_empty_on_non_dict(self) -> None:
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.eval = AsyncMock(return_value=None)

        params = WebSocketParams(
            url="https://app.com",
            duration_ms=100,
        )
        action = WebSocketInterceptAction(params)
        result = await action.execute(backend)

        assert result["sent"] == []
        assert result["received"] == []

    async def test_ws_params_defaults(self) -> None:
        params = WebSocketParams(url="https://app.com")
        assert params.duration_ms == 5000
        assert params.url_pattern == ""
        assert params.mock_responses == {}


# ── Lighthouse ───────────────────────────────────────────────────


class TestLighthouseAction:
    """Tests for LighthouseAction."""

    async def test_lighthouse_all_categories(self) -> None:
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.perf_metrics = AsyncMock(
            return_value={"js_heap_size": 1000000}
        )
        backend.eval = AsyncMock(
            side_effect=[
                {
                    "domContentLoaded": 500,
                    "loadComplete": 1000,
                    "ttfb": 200,
                    "fcp": 800,
                    "domSize": 500,
                    "transferSize": 50000,
                    "encodedBodySize": 48000,
                },
                {
                    "issues": [],
                    "issue_count": 0,
                    "has_lang": True,
                    "has_viewport": True,
                },
                {
                    "title": "Test Page",
                    "title_length": 9,
                    "description": "A test page",
                    "description_length": 11,
                    "og_title": "Test",
                    "og_description": None,
                    "og_image": None,
                    "twitter_card": None,
                    "canonical": "https://example.com",
                    "h1_count": 1,
                    "has_robots_meta": True,
                    "has_sitemap_link": False,
                },
                {
                    "issues": [],
                    "is_https": True,
                    "console_errors": [],
                },
            ]
        )
        backend.capture_console = AsyncMock(return_value=[])

        params = LighthouseParams(
            url="https://example.com",
            categories=[],
            wait=WaitStrategy(strategy="load"),
        )
        action = LighthouseAction(params)
        result = await action.execute(backend)

        assert "categories" in result
        assert "performance" in result["categories"]
        assert "accessibility" in result["categories"]
        assert "seo" in result["categories"]
        assert "best-practices" in result["categories"]
        assert result["categories"]["performance"]["score"] == 100
        assert result["categories"]["accessibility"]["score"] == 100

    async def test_lighthouse_performance_only(self) -> None:
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.perf_metrics = AsyncMock(return_value={})
        backend.eval = AsyncMock(
            return_value={
                "domContentLoaded": 4000,
                "loadComplete": 6000,
                "ttfb": 2000,
                "fcp": 3500,
                "domSize": 3500,
                "transferSize": 500000,
                "encodedBodySize": 480000,
            }
        )

        params = LighthouseParams(
            url="https://slow.com",
            categories=["performance"],
            wait=WaitStrategy(strategy="load"),
        )
        action = LighthouseAction(params)
        result = await action.execute(backend)

        assert "performance" in result["categories"]
        assert "accessibility" not in result["categories"]
        perf = result["categories"]["performance"]
        assert perf["score"] < 100
        assert perf["ttfb_ms"] == 2000

    async def test_lighthouse_a11y_with_issues(self) -> None:
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.perf_metrics = AsyncMock(return_value={})
        backend.eval = AsyncMock(
            return_value={
                "issues": [
                    {"type": "image-alt"},
                    {"type": "input-label"},
                    {"type": "link-text"},
                ],
                "issue_count": 3,
                "has_lang": False,
                "has_viewport": True,
            }
        )

        params = LighthouseParams(
            url="https://bad-a11y.com",
            categories=["accessibility"],
            wait=WaitStrategy(strategy="load"),
        )
        action = LighthouseAction(params)
        result = await action.execute(backend)

        a11y = result["categories"]["accessibility"]
        assert a11y["score"] == 85  # 100 - 3*5
        assert a11y["issue_count"] == 3
