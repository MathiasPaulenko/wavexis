"""Unit tests for auto-waiting before click/fill/hover."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.exceptions import WaitTimeoutError


@pytest.mark.unit
class TestAutoWait:
    """Tests for auto-waiting before input actions."""

    def test_cdp_wait_for_element_found(self) -> None:
        """Test _wait_for_element returns when element is visible."""
        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        backend._session = MagicMock()
        backend._session.runtime = MagicMock()
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": True}}
        )
        asyncio.run(backend._wait_for_element("#btn", timeout_ms=100))
        assert backend._session.runtime.evaluate.call_count >= 1

    def test_cdp_wait_for_element_timeout(self) -> None:
        """Test _wait_for_element raises WaitTimeoutError on timeout."""
        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        backend._session = MagicMock()
        backend._session.runtime = MagicMock()
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": False}}
        )
        with pytest.raises(WaitTimeoutError):
            asyncio.run(backend._wait_for_element("#missing", timeout_ms=50))

    def test_cdp_click_calls_wait_for_element(self) -> None:
        """Test that click calls _wait_for_element before acting."""
        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        backend._session = MagicMock()
        backend._session.input = MagicMock()
        backend._session.input.dispatch_mouse_event = AsyncMock()

        call_order: list[str] = []

        async def _mock_wait(selector: str, timeout_ms: int = 30000) -> None:
            call_order.append("wait")

        async def _mock_scroll(selector: str) -> None:
            call_order.append("scroll")

        async def _mock_box(selector: str) -> tuple[float, float]:
            call_order.append("box")
            return 50.0, 25.0

        backend._wait_for_element = _mock_wait  # type: ignore[assignment]
        backend._scroll_into_view_if_needed = _mock_scroll  # type: ignore[assignment]
        backend._get_box_center = _mock_box  # type: ignore[assignment]

        asyncio.run(backend.click("#btn"))
        assert call_order == ["wait", "scroll", "box"]

    def test_cdp_click_auto_wait_false_skips_wait(self) -> None:
        """Test that click with auto_wait=False skips _wait_for_element."""
        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        backend._session = MagicMock()
        backend._session.input = MagicMock()
        backend._session.input.dispatch_mouse_event = AsyncMock()

        call_order: list[str] = []

        async def _mock_wait(selector: str, timeout_ms: int = 30000) -> None:
            call_order.append("wait")

        async def _mock_scroll(selector: str) -> None:
            call_order.append("scroll")

        async def _mock_box(selector: str) -> tuple[float, float]:
            call_order.append("box")
            return 50.0, 25.0

        backend._wait_for_element = _mock_wait  # type: ignore[assignment]
        backend._scroll_into_view_if_needed = _mock_scroll  # type: ignore[assignment]
        backend._get_box_center = _mock_box  # type: ignore[assignment]

        asyncio.run(backend.click("#btn", auto_wait=False))
        assert "wait" not in call_order
        assert call_order == ["scroll", "box"]

    def test_bidi_wait_for_element_found(self) -> None:
        """Test BiDi _wait_for_element returns when element is visible."""
        from wavexis.backend.bidi import BiDiBackend

        backend = BiDiBackend()
        backend._client = MagicMock()
        backend._context = MagicMock()
        backend._client.script = MagicMock()
        result = MagicMock()
        result.value = True
        backend._client.script.evaluate = AsyncMock(return_value=result)
        asyncio.run(backend._wait_for_element("#btn", timeout_ms=100))
        assert backend._client.script.evaluate.call_count >= 1

    def test_bidi_wait_for_element_timeout(self) -> None:
        """Test BiDi _wait_for_element raises WaitTimeoutError on timeout."""
        from wavexis.backend.bidi import BiDiBackend

        backend = BiDiBackend()
        backend._client = MagicMock()
        backend._context = MagicMock()
        backend._client.script = MagicMock()
        result = MagicMock()
        result.value = False
        backend._client.script.evaluate = AsyncMock(return_value=result)
        with pytest.raises(WaitTimeoutError):
            asyncio.run(backend._wait_for_element("#missing", timeout_ms=50))
