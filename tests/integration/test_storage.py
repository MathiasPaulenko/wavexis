"""Integration tests for storage actions against a real Chrome browser."""

import pytest

from browsix.actions.storage import StorageAction
from browsix.backend.cdp import CDPBackend
from browsix.config import BrowserOptions, StorageParams, WaitStrategy

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
    """Test storage set and get."""
    params = StorageParams(
        url="https://example.com",
        action="set",
        key="test_key",
        value="test_value",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    await StorageAction(params).execute(backend)

    params_get = StorageParams(
        url="https://example.com",
        action="get",
        key="test_key",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await StorageAction(params_get).execute(backend)
    assert result == "test_value"


async def test_storage_list(
    backend: CDPBackend, browser_opts: BrowserOptions
) -> None:
    """Test storage list."""
    params = StorageParams(
        url="https://example.com",
        action="set",
        key="list_key",
        value="list_value",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    await StorageAction(params).execute(backend)

    params_list = StorageParams(
        url="https://example.com",
        action="list",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await StorageAction(params_list).execute(backend)
    assert "list_key" in result
    assert result["list_key"] == "list_value"


async def test_storage_clear(
    backend: CDPBackend, browser_opts: BrowserOptions
) -> None:
    """Test storage clear."""
    params_set = StorageParams(
        url="https://example.com",
        action="set",
        key="clear_key",
        value="clear_value",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    await StorageAction(params_set).execute(backend)

    params_clear = StorageParams(
        url="https://example.com",
        action="clear",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    await StorageAction(params_clear).execute(backend)

    params_list = StorageParams(
        url="https://example.com",
        action="list",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await StorageAction(params_list).execute(backend)
    assert "clear_key" not in result


async def test_storage_session_set_and_get(
    backend: CDPBackend, browser_opts: BrowserOptions
) -> None:
    """Test storage session set and get."""
    params = StorageParams(
        url="https://example.com",
        action="set",
        key="session_key",
        value="session_value",
        storage_type="session",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    await StorageAction(params).execute(backend)

    params_get = StorageParams(
        url="https://example.com",
        action="get",
        key="session_key",
        storage_type="session",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await StorageAction(params_get).execute(backend)
    assert result == "session_value"
