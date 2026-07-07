"""Integration tests for storage actions against a real Chrome browser."""

import pytest

from wavexis.backend.cdp import CDPBackend
from wavexis.config import BrowserOptions, WaitStrategy

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


@pytest.fixture
def backend() -> CDPBackend:
    """Backend."""
    return CDPBackend()


@pytest.fixture
def browser_opts() -> BrowserOptions:
    """Browser opts."""
    return BrowserOptions(headless=True)


async def test_storage_set_and_get(
    backend: CDPBackend, browser_opts: BrowserOptions
) -> None:
    """Test storage set and get in a single browser session."""
    await backend.launch(browser_opts)
    try:
        await backend.navigate("https://example.com", WaitStrategy(strategy="load"))
        await backend.storage_set("test_key", "test_value")
        result = await backend.storage_get("test_key")
        assert result == "test_value"
    finally:
        await backend.close()


async def test_storage_list(
    backend: CDPBackend, browser_opts: BrowserOptions
) -> None:
    """Test storage list in a single browser session."""
    await backend.launch(browser_opts)
    try:
        await backend.navigate("https://example.com", WaitStrategy(strategy="load"))
        await backend.storage_set("list_key", "list_value")
        result = await backend.storage_list()
        assert "list_key" in result
        assert result["list_key"] == "list_value"
    finally:
        await backend.close()


async def test_storage_clear(
    backend: CDPBackend, browser_opts: BrowserOptions
) -> None:
    """Test storage clear in a single browser session."""
    await backend.launch(browser_opts)
    try:
        await backend.navigate("https://example.com", WaitStrategy(strategy="load"))
        await backend.storage_set("clear_key", "clear_value")
        await backend.storage_clear()
        result = await backend.storage_list()
        assert "clear_key" not in result
    finally:
        await backend.close()


async def test_storage_session_set_and_get(
    backend: CDPBackend, browser_opts: BrowserOptions
) -> None:
    """Test storage session set and get in a single browser session."""
    await backend.launch(browser_opts)
    try:
        await backend.navigate("https://example.com", WaitStrategy(strategy="load"))
        await backend.storage_set("session_key", "session_value", "session")
        result = await backend.storage_get("session_key", "session")
        assert result == "session_value"
    finally:
        await backend.close()
