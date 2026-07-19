"""Unit tests for annotated_screenshot in CDP and BiDi backends."""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_cdp_backend() -> Any:
    """Create a CDPBackend with mocked session."""
    from wavexis.backend.cdp import CDPBackend

    backend = CDPBackend()
    backend._session = MagicMock()
    backend._session.runtime = MagicMock()
    backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": None}})
    backend._session.page = MagicMock()
    backend._session.page.capture_screenshot = AsyncMock(
        return_value={"data": base64.b64encode(b"fake_png").decode()}
    )
    return backend


def _make_bidi_backend() -> Any:
    """Create a BiDiBackend with mocked client."""
    from wavexis.backend.bidi import BiDiBackend

    backend = BiDiBackend()
    backend._client = MagicMock()
    backend._context = MagicMock()
    backend._client.script = MagicMock()
    result = MagicMock()
    result.value = None
    backend._client.script.evaluate = AsyncMock(return_value=result)
    backend._client.browsing = MagicMock()
    screenshot_result = MagicMock()
    screenshot_result.data = base64.b64encode(b"fake_png").decode()
    backend._client.browsing.screenshot = AsyncMock(return_value=screenshot_result)
    return backend


@pytest.mark.unit
class TestAnnotatedScreenshotCDP:
    """Tests for annotated_screenshot in CDP backend."""

    def test_returns_image_and_label_map(self) -> None:
        """Test that annotated_screenshot returns image bytes and label map."""
        backend = _make_cdp_backend()
        label_map = {"e1": "button", "e2": "#email"}
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": json.dumps(label_map)}}
        )
        image_bytes, labels = asyncio.run(backend.annotated_screenshot(["button", "#email"]))
        assert isinstance(image_bytes, bytes)
        assert len(image_bytes) > 0
        assert labels == label_map

    def test_returns_empty_map_for_no_matches(self) -> None:
        """Test that annotated_screenshot returns empty map when no elements match."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": json.dumps({})}}
        )
        image_bytes, labels = asyncio.run(backend.annotated_screenshot([".nonexistent"]))
        assert isinstance(image_bytes, bytes)
        assert labels == {}

    def test_cleans_up_overlays(self) -> None:
        """Test that annotated_screenshot removes overlays after capture."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": json.dumps({"e1": "button"})}}
        )
        asyncio.run(backend.annotated_screenshot(["button"]))
        evaluate_calls = backend._session.runtime.evaluate.call_args_list
        assert len(evaluate_calls) == 2
        second_call = evaluate_calls[1]
        assert "__wavexis_annotate" in second_call.args[0]


@pytest.mark.unit
class TestAnnotatedScreenshotBiDi:
    """Tests for annotated_screenshot in BiDi backend."""

    def test_returns_image_and_label_map(self) -> None:
        """Test that annotated_screenshot returns image bytes and label map."""
        backend = _make_bidi_backend()
        label_map = {"e1": "button", "e2": "#email"}
        result_mock = MagicMock()
        result_mock.value = json.dumps(label_map)
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        image_bytes, labels = asyncio.run(backend.annotated_screenshot(["button", "#email"]))
        assert isinstance(image_bytes, bytes)
        assert len(image_bytes) > 0
        assert labels == label_map

    def test_returns_empty_map_for_no_matches(self) -> None:
        """Test that annotated_screenshot returns empty map when no elements match."""
        backend = _make_bidi_backend()
        result_mock = MagicMock()
        result_mock.value = json.dumps({})
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        image_bytes, labels = asyncio.run(backend.annotated_screenshot([".nonexistent"]))
        assert isinstance(image_bytes, bytes)
        assert labels == {}

    def test_cleans_up_overlays(self) -> None:
        """Test that annotated_screenshot removes overlays after capture."""
        backend = _make_bidi_backend()
        result_mock = MagicMock()
        result_mock.value = json.dumps({"e1": "button"})
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        asyncio.run(backend.annotated_screenshot(["button"]))
        evaluate_calls = backend._client.script.evaluate.call_args_list
        assert len(evaluate_calls) == 2
        second_call = evaluate_calls[1]
        assert "__wavexis_annotate" in second_call.args[1]
