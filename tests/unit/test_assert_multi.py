"""Unit tests for --assert in eval and multi dispatch for cookies/headers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.cli.app import _check_assertion


@pytest.mark.unit
class TestCheckAssertion:
    """Tests for _check_assertion function."""

    def test_equals_pass(self) -> None:
        """Test == assertion passes when values match."""
        passed, msg = _check_assertion("Expected Title", "== Expected Title")
        assert passed is True
        assert msg == ""

    def test_equals_fail(self) -> None:
        """Test == assertion fails when values don't match."""
        passed, msg = _check_assertion("Actual Title", "== Expected Title")
        assert passed is False
        assert "Expected 'Expected Title'" in msg

    def test_not_equals_pass(self) -> None:
        """Test != assertion passes when values differ."""
        passed, msg = _check_assertion("Actual", "!= Expected")
        assert passed is True
        assert msg == ""

    def test_not_equals_fail(self) -> None:
        """Test != assertion fails when values match."""
        passed, msg = _check_assertion("Same", "!= Same")
        assert passed is False
        assert "Expected not 'Same'" in msg

    def test_contains_pass(self) -> None:
        """Test contains assertion passes when substring is present."""
        passed, msg = _check_assertion("Hello World", "contains World")
        assert passed is True
        assert msg == ""

    def test_contains_fail(self) -> None:
        """Test contains assertion fails when substring is absent."""
        passed, msg = _check_assertion("Hello", "contains World")
        assert passed is False
        assert "does not contain" in msg

    def test_matches_pass(self) -> None:
        """Test matches assertion passes when regex matches."""
        passed, msg = _check_assertion("Error 404: Not Found", "matches Error \\d+")
        assert passed is True
        assert msg == ""

    def test_matches_fail(self) -> None:
        """Test matches assertion fails when regex doesn't match."""
        passed, msg = _check_assertion("All good", "matches Error \\d+")
        assert passed is False
        assert "does not match" in msg

    def test_unknown_operator(self) -> None:
        """Test unknown assertion operator returns failure."""
        passed, msg = _check_assertion("value", "> 5")
        assert passed is False
        assert "Unknown assertion" in msg

    def test_numeric_result_equals(self) -> None:
        """Test == with numeric result converts to string."""
        passed, msg = _check_assertion(42, "== 42")
        assert passed is True
        assert msg == ""

    def test_none_result(self) -> None:
        """Test assertion with None result."""
        passed, msg = _check_assertion(None, "== None")
        assert passed is True
        assert msg == ""

    def test_matches_invalid_regex(self) -> None:
        """Test matches assertion with invalid regex returns error message."""
        passed, msg = _check_assertion("test", "matches [unclosed")
        assert passed is False
        assert "Invalid regex pattern" in msg


@pytest.mark.unit
class TestMultiDispatchCookies:
    """Tests for cookies action dispatch in multi."""

    async def test_cookies_get_dispatch(self) -> None:
        """Test cookies get action is dispatched correctly in multi."""
        from wavexis.multi import _dispatch

        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.get_cookies = AsyncMock(return_value=[{"name": "session"}])
        backend.close = AsyncMock()

        result = await _dispatch(
            "cookies",
            {"url": "https://example.com", "action": "get"},
            backend,
        )
        assert result == [{"name": "session"}]
        backend.get_cookies.assert_called_once()

    async def test_cookies_set_dispatch(self) -> None:
        """Test cookies set action is dispatched correctly in multi."""
        from wavexis.multi import _dispatch

        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.set_cookie = AsyncMock()
        backend.close = AsyncMock()

        result = await _dispatch(
            "cookies",
            {
                "url": "https://example.com",
                "action": "set",
                "cookie": {
                    "name": "token",
                    "value": "abc",
                    "domain": "example.com",
                    "path": "/",
                },
            },
            backend,
        )
        assert result is None
        backend.set_cookie.assert_called_once()

    async def test_cookies_clear_dispatch(self) -> None:
        """Test cookies clear action is dispatched correctly in multi."""
        from wavexis.multi import _dispatch

        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.clear_cookies = AsyncMock()
        backend.close = AsyncMock()

        result = await _dispatch(
            "cookies",
            {"url": "https://example.com", "action": "clear"},
            backend,
        )
        assert result is None
        backend.clear_cookies.assert_called_once()


@pytest.mark.unit
class TestMultiDispatchHeaders:
    """Tests for headers action dispatch in multi."""

    async def test_headers_set_headers_dispatch(self) -> None:
        """Test headers set-headers action is dispatched correctly in multi."""
        from wavexis.multi import _dispatch

        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.set_headers = AsyncMock()
        backend.close = AsyncMock()

        result = await _dispatch(
            "headers",
            {
                "url": "https://example.com",
                "action": "set-headers",
                "headers": {"X-Custom": "value"},
            },
            backend,
        )
        assert result is None
        backend.set_headers.assert_called_once_with({"X-Custom": "value"})

    async def test_headers_set_user_agent_dispatch(self) -> None:
        """Test headers set-user-agent action is dispatched correctly in multi."""
        from wavexis.multi import _dispatch

        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.set_user_agent = AsyncMock()
        backend.close = AsyncMock()

        result = await _dispatch(
            "headers",
            {
                "url": "https://example.com",
                "action": "set-user-agent",
                "user_agent": "Mozilla/5.0 Custom",
            },
            backend,
        )
        assert result is None
        backend.set_user_agent.assert_called_once_with("Mozilla/5.0 Custom")
