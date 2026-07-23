"""Unit tests for Shadow DOM support — shadow_eval, shadow_click, shadow_fill."""

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
    backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": True}})
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
class TestShadowEval:
    """Tests for shadow_eval in both backends."""

    def test_cdp_shadow_eval_returns_value(self) -> None:
        """Test CDP shadow_eval returns the evaluated value."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": 42}})
        result = asyncio.run(backend.shadow_eval(["my-component", "button"], "1 + 1"))
        assert result == 42

    def test_cdp_shadow_eval_null_element_not_found(self) -> None:
        """Test CDP shadow_eval returns None when element is not found."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": None}})
        result = asyncio.run(backend.shadow_eval(["missing", "button"], "this.textContent"))
        assert result is None

    def test_bidi_shadow_eval_returns_value(self) -> None:
        """Test BiDi shadow_eval returns the evaluated value."""
        backend = _make_bidi_backend()
        result_mock = MagicMock()
        result_mock.value = "hello"
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        result = asyncio.run(backend.shadow_eval(["my-component", "button"], "this.textContent"))
        assert result == "hello"

    def test_cdp_shadow_eval_uses_function_constructor(self) -> None:
        """Regression: shadow_eval must evaluate the expression, not return it as a string."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": 42}})
        asyncio.run(backend.shadow_eval(["my-component"], "1 + 1"))
        expression = backend._session.runtime.evaluate.call_args[0][0]
        assert "new Function(" in expression
        assert '"1 + 1"' in expression

    def test_bidi_shadow_eval_uses_function_constructor(self) -> None:
        """Regression: shadow_eval must evaluate the expression, not return it as a string."""
        backend = _make_bidi_backend()
        result_mock = MagicMock()
        result_mock.value = 42
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        asyncio.run(backend.shadow_eval(["my-component"], "1 + 1"))
        expression = backend._client.script.evaluate.call_args[0][1]
        assert "new Function(" in expression
        assert '"1 + 1"' in expression


@pytest.mark.unit
class TestShadowClick:
    """Tests for shadow_click in both backends."""

    def test_cdp_shadow_click_success(self) -> None:
        """Test CDP shadow_click dispatches click inside shadow DOM."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": True}})
        asyncio.run(backend.shadow_click(["my-component", "button"], auto_wait=False))
        backend._session.runtime.evaluate.assert_called()

    def test_cdp_shadow_click_element_not_found(self) -> None:
        """Test CDP shadow_click raises ElementNotFoundError when element missing."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": False}})
        with pytest.raises(ElementNotFoundError):
            asyncio.run(backend.shadow_click(["missing", "btn"], auto_wait=False))

    def test_bidi_shadow_click_success(self) -> None:
        """Test BiDi shadow_click dispatches click inside shadow DOM."""
        backend = _make_bidi_backend()
        result_mock = MagicMock()
        result_mock.value = True
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        asyncio.run(backend.shadow_click(["my-component", "button"], auto_wait=False))
        backend._client.script.evaluate.assert_called()

    def test_bidi_shadow_click_element_not_found(self) -> None:
        """Test BiDi shadow_click raises ElementNotFoundError when element missing."""
        backend = _make_bidi_backend()
        result_mock = MagicMock()
        result_mock.value = False
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        with pytest.raises(ElementNotFoundError):
            asyncio.run(backend.shadow_click(["missing", "btn"], auto_wait=False))


@pytest.mark.unit
class TestShadowFill:
    """Tests for shadow_fill in both backends."""

    def test_cdp_shadow_fill_success(self) -> None:
        """Test CDP shadow_fill sets value inside shadow DOM."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": True}})
        asyncio.run(backend.shadow_fill(["my-component", "input"], "test value", auto_wait=False))
        backend._session.runtime.evaluate.assert_called()

    def test_cdp_shadow_fill_element_not_found(self) -> None:
        """Test CDP shadow_fill raises ElementNotFoundError when element missing."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": False}})
        with pytest.raises(ElementNotFoundError):
            asyncio.run(backend.shadow_fill(["missing", "input"], "val", auto_wait=False))

    def test_bidi_shadow_fill_success(self) -> None:
        """Test BiDi shadow_fill sets value inside shadow DOM."""
        backend = _make_bidi_backend()
        result_mock = MagicMock()
        result_mock.value = True
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        asyncio.run(backend.shadow_fill(["my-component", "input"], "test value", auto_wait=False))
        backend._client.script.evaluate.assert_called()

    def test_bidi_shadow_fill_element_not_found(self) -> None:
        """Test BiDi shadow_fill raises ElementNotFoundError when element missing."""
        backend = _make_bidi_backend()
        result_mock = MagicMock()
        result_mock.value = False
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        with pytest.raises(ElementNotFoundError):
            asyncio.run(backend.shadow_fill(["missing", "input"], "val", auto_wait=False))


@pytest.mark.unit
class TestShadowAutoWait:
    """Tests for auto_wait in shadow operations."""

    def test_cdp_shadow_click_auto_wait_false_skips_wait(self) -> None:
        """Test that shadow_click with auto_wait=False skips _wait_for_element_in_shadow."""
        backend = _make_cdp_backend()
        call_order: list[str] = []

        async def _mock_wait(selectors: list[str], timeout_ms: int = 30000) -> None:
            call_order.append("wait")

        backend._wait_for_element_in_shadow = _mock_wait  # type: ignore[assignment]
        backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": True}})

        asyncio.run(backend.shadow_click(["my-component", "btn"], auto_wait=False))
        assert "wait" not in call_order

    def test_cdp_shadow_click_auto_wait_true_calls_wait(self) -> None:
        """Test that shadow_click with auto_wait=True calls _wait_for_element_in_shadow."""
        backend = _make_cdp_backend()
        call_order: list[str] = []

        async def _mock_wait(selectors: list[str], timeout_ms: int = 30000) -> None:
            call_order.append("wait")

        backend._wait_for_element_in_shadow = _mock_wait  # type: ignore[assignment]
        backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": True}})

        asyncio.run(backend.shadow_click(["my-component", "btn"], auto_wait=True))
        assert "wait" in call_order


@pytest.mark.unit
class TestBuildShadowPierceJs:
    """Tests for _build_shadow_pierce_js helper."""

    def test_single_selector(self) -> None:
        """Test JS generation for a single selector (no shadow piercing)."""
        from wavexis.backend.cdp import CDPBackend

        js = CDPBackend._build_shadow_pierce_js(["#my-element"])
        assert "document.querySelector" in js
        assert "shadowRoot" not in js

    def test_nested_selectors(self) -> None:
        """Test JS generation for nested shadow piercing."""
        from wavexis.backend.cdp import CDPBackend

        js = CDPBackend._build_shadow_pierce_js(["my-component", "inner", "button"])
        assert js.count("shadowRoot") == 4
        assert "inner" in js
        assert "button" in js

    def test_selector_escaping(self) -> None:
        """Test that selectors with single quotes are properly handled."""
        from wavexis.backend.cdp import CDPBackend

        js = CDPBackend._build_shadow_pierce_js(["[data-test='foo']"])
        # json.dumps produces a valid JS string literal with double quotes
        assert '"[data-test=' in js or "'[data-test=" in js
        assert "foo" in js
