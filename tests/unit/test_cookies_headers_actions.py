"""Unit tests for CookieAction and HeaderAction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from browsix.actions.cookies import CookieAction
from browsix.actions.headers import HeaderAction
from browsix.config import CookieActionParams, CookieParams, HeaderParams


@pytest.mark.unit
class TestCookieAction:
    """Tests for CookieAction."""

    async def test_get_cookies(self) -> None:
        """Test get cookies action."""
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.get_cookies = AsyncMock(return_value=[{"name": "session", "value": "abc"}])
        backend.close = AsyncMock()

        params = CookieActionParams(url="https://example.com", action="get")
        result = await CookieAction(params).execute(backend)

        assert result == [{"name": "session", "value": "abc"}]
        backend.launch.assert_called_once()
        backend.navigate.assert_called_once()
        backend.get_cookies.assert_called_once()

    async def test_set_cookie(self) -> None:
        """Test set cookie action."""
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.set_cookie = AsyncMock()
        backend.close = AsyncMock()

        cookie = CookieParams(name="token", value="xyz", domain="example.com")
        params = CookieActionParams(url="https://example.com", action="set", cookie=cookie)
        result = await CookieAction(params).execute(backend)

        assert result is None
        backend.set_cookie.assert_called_once_with(cookie)

    async def test_delete_cookie(self) -> None:
        """Test delete cookie action."""
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.delete_cookie = AsyncMock()
        backend.close = AsyncMock()

        params = CookieActionParams(
            url="https://example.com", action="delete", name="token", domain="example.com"
        )
        result = await CookieAction(params).execute(backend)

        assert result is None
        backend.delete_cookie.assert_called_once_with("token", "example.com")

    async def test_delete_cookie_missing_name(self) -> None:
        """Test delete cookie raises ValueError without name."""
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.close = AsyncMock()

        params = CookieActionParams(url="https://example.com", action="delete")
        with pytest.raises(ValueError, match="name is required"):
            await CookieAction(params).execute(backend)

    async def test_clear_cookies(self) -> None:
        """Test clear cookies action."""
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.clear_cookies = AsyncMock()
        backend.close = AsyncMock()

        params = CookieActionParams(url="https://example.com", action="clear")
        result = await CookieAction(params).execute(backend)

        assert result is None
        backend.clear_cookies.assert_called_once()

    async def test_unknown_action(self) -> None:
        """Test unknown action raises ValueError."""
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.close = AsyncMock()

        params = CookieActionParams(url="https://example.com", action="invalid")
        with pytest.raises(ValueError, match="Unknown cookie action"):
            await CookieAction(params).execute(backend)

    async def test_no_url_skips_navigate(self) -> None:
        """Test that empty URL skips navigation."""
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.get_cookies = AsyncMock(return_value=[])
        backend.close = AsyncMock()

        params = CookieActionParams(url="", action="get")
        await CookieAction(params).execute(backend)

        backend.navigate.assert_not_called()


@pytest.mark.unit
class TestHeaderAction:
    """Tests for HeaderAction."""

    async def test_set_headers(self) -> None:
        """Test set headers action."""
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.set_headers = AsyncMock()
        backend.close = AsyncMock()

        headers = {"X-Custom": "value", "Authorization": "Bearer token"}
        params = HeaderParams(
            url="https://example.com", action="set-headers", headers=headers
        )
        result = await HeaderAction(params).execute(backend)

        assert result is None
        backend.set_headers.assert_called_once_with(headers)

    async def test_set_user_agent(self) -> None:
        """Test set user-agent action."""
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.set_user_agent = AsyncMock()
        backend.close = AsyncMock()

        params = HeaderParams(
            url="https://example.com",
            action="set-user-agent",
            user_agent="Mozilla/5.0 Custom",
        )
        result = await HeaderAction(params).execute(backend)

        assert result is None
        backend.set_user_agent.assert_called_once_with("Mozilla/5.0 Custom")

    async def test_set_headers_missing_headers(self) -> None:
        """Test set-headers raises ValueError without headers."""
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.close = AsyncMock()

        params = HeaderParams(url="https://example.com", action="set-headers")
        with pytest.raises(ValueError, match="headers is required"):
            await HeaderAction(params).execute(backend)

    async def test_set_user_agent_missing(self) -> None:
        """Test set-user-agent raises ValueError without user_agent."""
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.close = AsyncMock()

        params = HeaderParams(url="https://example.com", action="set-user-agent")
        with pytest.raises(ValueError, match="user-agent is required"):
            await HeaderAction(params).execute(backend)

    async def test_unknown_action(self) -> None:
        """Test unknown action raises ValueError."""
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.close = AsyncMock()

        params = HeaderParams(url="https://example.com", action="invalid")
        with pytest.raises(ValueError, match="Unknown header action"):
            await HeaderAction(params).execute(backend)
