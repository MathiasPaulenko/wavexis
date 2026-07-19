"""Unit tests for suggest_locator in both backends."""

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
    backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": None}})
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
class TestSuggestLocatorCDP:
    """Tests for suggest_locator in CDP backend."""

    def test_returns_best_selector(self) -> None:
        """Test that suggest_locator returns the first (best) suggestion."""
        backend = _make_cdp_backend()
        suggestions = ["#login-btn", "button.primary", "button"]
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": json.dumps(suggestions)}}
        )
        result = asyncio.run(backend.suggest_locator("#login-btn"))
        assert result == "#login-btn"

    def test_returns_all_suggestions(self) -> None:
        """Test that suggest_locator with all=True returns all suggestions."""
        backend = _make_cdp_backend()
        suggestions = ["#my-id", "[data-testid='btn']", "button.clickable", "button"]
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": json.dumps(suggestions)}}
        )
        result = asyncio.run(backend.suggest_locator("button", all=True))
        assert isinstance(result, list)
        assert len(result) == 4
        assert result[0] == "#my-id"

    def test_raises_on_element_not_found(self) -> None:
        """Test that suggest_locator raises ElementNotFoundError when element missing."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": None}})
        with pytest.raises(ElementNotFoundError):
            asyncio.run(backend.suggest_locator("#missing"))


@pytest.mark.unit
class TestSuggestLocatorBiDi:
    """Tests for suggest_locator in BiDi backend."""

    def test_returns_best_selector(self) -> None:
        """Test that suggest_locator returns the first (best) suggestion."""
        backend = _make_bidi_backend()
        suggestions = ["#submit", "button[type='submit']", "button"]
        result_mock = MagicMock()
        result_mock.value = json.dumps(suggestions)
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        result = asyncio.run(backend.suggest_locator("#submit"))
        assert result == "#submit"

    def test_returns_all_suggestions(self) -> None:
        """Test that suggest_locator with all=True returns all suggestions."""
        backend = _make_bidi_backend()
        suggestions = ["#email", "[data-testid='email']", "input.email", "input"]
        result_mock = MagicMock()
        result_mock.value = json.dumps(suggestions)
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        result = asyncio.run(backend.suggest_locator("input", all=True))
        assert isinstance(result, list)
        assert len(result) == 4

    def test_raises_on_element_not_found(self) -> None:
        """Test that suggest_locator raises ElementNotFoundError when element missing."""
        backend = _make_bidi_backend()
        result_mock = MagicMock()
        result_mock.value = None
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        with pytest.raises(ElementNotFoundError):
            asyncio.run(backend.suggest_locator("#missing"))
