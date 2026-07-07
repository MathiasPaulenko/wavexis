"""Unit tests for iframe support — iframe_eval, iframe_click, iframe_fill."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.exceptions import ElementNotFoundError


def _make_cdp_backend() -> Any:
    """Create a CDPBackend with mocked session."""
    from wavexis.backend.cdp import CDPBackend

    backend = CDPBackend()
    backend._session = MagicMock()
    backend._session.runtime = MagicMock()
    backend._session.runtime.evaluate = AsyncMock(
        return_value={"result": {"value": True}}
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
    result.value = True
    backend._client.script.evaluate = AsyncMock(return_value=result)
    return backend


@pytest.mark.unit
class TestIframeEval:
    """Tests for iframe_eval in both backends."""

    def test_cdp_iframe_eval_returns_value(self) -> None:
        """Test CDP iframe_eval returns the evaluated value."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": 42}}
        )
        result = asyncio.run(
            backend.iframe_eval("#myframe", "1 + 1", await_promise=False)
        )
        assert result == 42

    def test_cdp_iframe_eval_null_iframe_not_found(self) -> None:
        """Test CDP iframe_eval returns None when iframe is not found."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": None}}
        )
        result = asyncio.run(
            backend.iframe_eval("#missing", "document.title")
        )
        assert result is None

    def test_bidi_iframe_eval_returns_value(self) -> None:
        """Test BiDi iframe_eval returns the evaluated value."""
        backend = _make_bidi_backend()
        result_mock = MagicMock()
        result_mock.value = "hello"
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        result = asyncio.run(
            backend.iframe_eval("#myframe", "document.title")
        )
        assert result == "hello"


@pytest.mark.unit
class TestIframeClick:
    """Tests for iframe_click in both backends."""

    def test_cdp_iframe_click_success(self) -> None:
        """Test CDP iframe_click dispatches click inside iframe."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": True}}
        )
        asyncio.run(backend.iframe_click("#myframe", "#btn", auto_wait=False))
        backend._session.runtime.evaluate.assert_called()

    def test_cdp_iframe_click_element_not_found(self) -> None:
        """Test CDP iframe_click raises ElementNotFoundError when element missing."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": False}}
        )
        with pytest.raises(ElementNotFoundError):
            asyncio.run(backend.iframe_click("#myframe", "#missing", auto_wait=False))

    def test_bidi_iframe_click_success(self) -> None:
        """Test BiDi iframe_click dispatches click inside iframe."""
        backend = _make_bidi_backend()
        result_mock = MagicMock()
        result_mock.value = True
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        asyncio.run(backend.iframe_click("#myframe", "#btn", auto_wait=False))
        backend._client.script.evaluate.assert_called()

    def test_bidi_iframe_click_element_not_found(self) -> None:
        """Test BiDi iframe_click raises ElementNotFoundError when element missing."""
        backend = _make_bidi_backend()
        result_mock = MagicMock()
        result_mock.value = False
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        with pytest.raises(ElementNotFoundError):
            asyncio.run(backend.iframe_click("#myframe", "#missing", auto_wait=False))


@pytest.mark.unit
class TestIframeFill:
    """Tests for iframe_fill in both backends."""

    def test_cdp_iframe_fill_success(self) -> None:
        """Test CDP iframe_fill sets value inside iframe."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": True}}
        )
        asyncio.run(
            backend.iframe_fill("#myframe", "#input", "test value", auto_wait=False)
        )
        backend._session.runtime.evaluate.assert_called()

    def test_cdp_iframe_fill_element_not_found(self) -> None:
        """Test CDP iframe_fill raises ElementNotFoundError when element missing."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": False}}
        )
        with pytest.raises(ElementNotFoundError):
            asyncio.run(
                backend.iframe_fill("#myframe", "#missing", "val", auto_wait=False)
            )

    def test_bidi_iframe_fill_success(self) -> None:
        """Test BiDi iframe_fill sets value inside iframe."""
        backend = _make_bidi_backend()
        result_mock = MagicMock()
        result_mock.value = True
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        asyncio.run(
            backend.iframe_fill("#myframe", "#input", "test value", auto_wait=False)
        )
        backend._client.script.evaluate.assert_called()

    def test_bidi_iframe_fill_element_not_found(self) -> None:
        """Test BiDi iframe_fill raises ElementNotFoundError when element missing."""
        backend = _make_bidi_backend()
        result_mock = MagicMock()
        result_mock.value = False
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        with pytest.raises(ElementNotFoundError):
            asyncio.run(
                backend.iframe_fill("#myframe", "#missing", "val", auto_wait=False)
            )


@pytest.mark.unit
class TestIframeAutoWait:
    """Tests for auto_wait in iframe operations."""

    def test_cdp_iframe_click_auto_wait_false_skips_wait(self) -> None:
        """Test that iframe_click with auto_wait=False skips _wait_for_element_in_iframe."""
        backend = _make_cdp_backend()
        call_order: list[str] = []

        async def _mock_wait(iframe_sel: str, sel: str, timeout_ms: int = 30000) -> None:
            call_order.append("wait")

        backend._wait_for_element_in_iframe = _mock_wait  # type: ignore[assignment]
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": True}}
        )

        asyncio.run(backend.iframe_click("#myframe", "#btn", auto_wait=False))
        assert "wait" not in call_order

    def test_cdp_iframe_click_auto_wait_true_calls_wait(self) -> None:
        """Test that iframe_click with auto_wait=True calls _wait_for_element_in_iframe."""
        backend = _make_cdp_backend()
        call_order: list[str] = []

        async def _mock_wait(iframe_sel: str, sel: str, timeout_ms: int = 30000) -> None:
            call_order.append("wait")

        backend._wait_for_element_in_iframe = _mock_wait  # type: ignore[assignment]
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": True}}
        )

        asyncio.run(backend.iframe_click("#myframe", "#btn", auto_wait=True))
        assert "wait" in call_order
