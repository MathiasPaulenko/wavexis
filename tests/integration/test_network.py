"""Integration tests for cookies, headers, and user-agent."""

import pytest

from wavexis.backend.manager import BackendManager
from wavexis.config import BrowserOptions, CookieParams, WaitStrategy


@pytest.mark.integration
class TestCookiesIntegration:
    """Integration tests for cookie management against real Chrome."""

    async def test_get_cookies(self):
        """Test get cookies."""
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            await backend.navigate("https://example.com", WaitStrategy(strategy="load"))
            cookies = await backend.get_cookies()
            assert isinstance(cookies, list)
        finally:
            await backend.close()

    async def test_set_and_get_cookie(self):
        """Test set and get cookie."""
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            await backend.navigate("https://example.com", WaitStrategy(strategy="load"))
            cookie = CookieParams(
                name="test-cookie",
                value="test-value",
                domain=".example.com",
                path="/",
            )
            await backend.set_cookie(cookie)
            cookies = await backend.get_cookies()
            names = [c.get("name") for c in cookies]
            assert "test-cookie" in names
        finally:
            await backend.close()

    async def test_delete_cookie(self):
        """Test delete cookie."""
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            await backend.navigate("https://example.com", WaitStrategy(strategy="load"))
            cookie = CookieParams(
                name="del-cookie",
                value="val",
                domain=".example.com",
                path="/",
            )
            await backend.set_cookie(cookie)
            await backend.delete_cookie("del-cookie", ".example.com")
            cookies = await backend.get_cookies()
            names = [c.get("name") for c in cookies]
            assert "del-cookie" not in names
        finally:
            await backend.close()

    async def test_clear_cookies(self):
        """Test clear cookies."""
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            await backend.navigate("https://example.com", WaitStrategy(strategy="load"))
            await backend.clear_cookies()
            cookies = await backend.get_cookies()
            assert len(cookies) == 0
        finally:
            await backend.close()


@pytest.mark.integration
class TestHeadersIntegration:
    """Integration tests for HTTP headers against real Chrome."""

    async def test_set_headers(self):
        """Test set headers."""
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            await backend.set_headers({"X-Test-Header": "wavexis-test"})
            await backend.navigate("https://example.com", WaitStrategy(strategy="load"))
        finally:
            await backend.close()


@pytest.mark.integration
class TestUserAgentIntegration:
    """Integration tests for user-agent override."""

    async def test_set_user_agent(self):
        """Test set user agent."""
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            await backend.set_user_agent("wavexisTestBot/1.0")
            await backend.navigate("https://example.com", WaitStrategy(strategy="load"))
            ua = await backend.eval("navigator.userAgent", await_promise=False)
            assert "wavexisTestBot" in ua
        finally:
            await backend.close()
