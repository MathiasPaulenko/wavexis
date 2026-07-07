"""Unit tests for natural language selector — find_by_text, nl_click, nl_fill."""

from __future__ import annotations

import asyncio
import json
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
        return_value={"result": {"value": None}}
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
    return backend


@pytest.mark.unit
class TestFindByTextCDP:
    """Tests for find_by_text in CDP backend."""

    def test_returns_best_selector(self) -> None:
        """Test that find_by_text returns the best match."""
        backend = _make_cdp_backend()
        selectors = ["#login-btn", "button.primary"]
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": json.dumps(selectors)}}
        )
        result = asyncio.run(backend.find_by_text("login button"))
        assert result == "#login-btn"

    def test_returns_all_selectors(self) -> None:
        """Test that find_by_text with all=True returns all matches."""
        backend = _make_cdp_backend()
        selectors = ["#login-btn", "button.primary", "button"]
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": json.dumps(selectors)}}
        )
        result = asyncio.run(backend.find_by_text("login", all=True))
        assert isinstance(result, list)
        assert len(result) == 3

    def test_raises_on_no_match(self) -> None:
        """Test that find_by_text raises ElementNotFoundError when no match."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": json.dumps([])}}
        )
        with pytest.raises(ElementNotFoundError):
            asyncio.run(backend.find_by_text("nonexistent"))

    def test_raises_on_null_result(self) -> None:
        """Test that find_by_text raises when JS returns null."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": None}}
        )
        with pytest.raises(ElementNotFoundError):
            asyncio.run(backend.find_by_text("anything"))


@pytest.mark.unit
class TestFindByTextBiDi:
    """Tests for find_by_text in BiDi backend."""

    def test_returns_best_selector(self) -> None:
        """Test that find_by_text returns the best match."""
        backend = _make_bidi_backend()
        selectors = ["#email-input", "input.email"]
        result_mock = MagicMock()
        result_mock.value = json.dumps(selectors)
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        result = asyncio.run(backend.find_by_text("email field"))
        assert result == "#email-input"

    def test_returns_all_selectors(self) -> None:
        """Test that find_by_text with all=True returns all matches."""
        backend = _make_bidi_backend()
        selectors = ["#email", "input[placeholder='email']", "input"]
        result_mock = MagicMock()
        result_mock.value = json.dumps(selectors)
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        result = asyncio.run(backend.find_by_text("email", all=True))
        assert isinstance(result, list)
        assert len(result) == 3

    def test_raises_on_no_match(self) -> None:
        """Test that find_by_text raises ElementNotFoundError when no match."""
        backend = _make_bidi_backend()
        result_mock = MagicMock()
        result_mock.value = json.dumps([])
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        with pytest.raises(ElementNotFoundError):
            asyncio.run(backend.find_by_text("nonexistent"))


@pytest.mark.unit
class TestNlClick:
    """Tests for nl_click in both backends."""

    def test_cdp_nl_click_calls_click(self) -> None:
        """Test that nl_click finds element and calls click."""
        backend = _make_cdp_backend()
        selectors = ["#submit-btn"]
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": json.dumps(selectors)}}
        )
        backend.click = AsyncMock()
        asyncio.run(backend.nl_click("submit button", auto_wait=False))
        backend.click.assert_called_once_with(
            "#submit-btn", auto_wait=False
        )

    def test_bidi_nl_click_calls_click(self) -> None:
        """Test that nl_click finds element and calls click."""
        backend = _make_bidi_backend()
        selectors = ["#submit-btn"]
        result_mock = MagicMock()
        result_mock.value = json.dumps(selectors)
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        backend.click = AsyncMock()
        asyncio.run(backend.nl_click("submit button", auto_wait=False))
        backend.click.assert_called_once_with(
            "#submit-btn", auto_wait=False
        )


@pytest.mark.unit
class TestNlFill:
    """Tests for nl_fill in both backends."""

    def test_cdp_nl_fill_calls_fill(self) -> None:
        """Test that nl_fill finds element and calls fill."""
        backend = _make_cdp_backend()
        selectors = ["#email-field"]
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": json.dumps(selectors)}}
        )
        backend.fill = AsyncMock()
        asyncio.run(backend.nl_fill("email field", "test@test.com", auto_wait=False))
        backend.fill.assert_called_once_with(
            "#email-field", "test@test.com", auto_wait=False
        )

    def test_bidi_nl_fill_calls_fill(self) -> None:
        """Test that nl_fill finds element and calls fill."""
        backend = _make_bidi_backend()
        selectors = ["#email-field"]
        result_mock = MagicMock()
        result_mock.value = json.dumps(selectors)
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        backend.fill = AsyncMock()
        asyncio.run(backend.nl_fill("email field", "test@test.com", auto_wait=False))
        backend.fill.assert_called_once_with(
            "#email-field", "test@test.com", auto_wait=False
        )
