"""Integration tests for raw() protocol access against a real Chrome browser."""

import pytest

from wavexis.backend.cdp import CDPBackend
from wavexis.config import BrowserOptions

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


@pytest.fixture
def backend() -> CDPBackend:
    """Backend."""
    return CDPBackend()


@pytest.fixture
def browser_opts() -> BrowserOptions:
    """Browser opts."""
    return BrowserOptions(headless=True)


async def test_raw_cdp_command(
    backend: CDPBackend, browser_opts: BrowserOptions
) -> None:
    """Test raw cdp command."""
    await backend.launch(browser_opts)
    try:
        result = await backend.raw("SystemInfo.getInfo", {})
        assert isinstance(result, dict)
    finally:
        await backend.close()


async def test_raw_page_reload(
    backend: CDPBackend, browser_opts: BrowserOptions
) -> None:
    """Test raw page reload."""
    await backend.launch(browser_opts)
    try:
        result = await backend.raw("Page.reload", {"ignoreCache": True})
        assert isinstance(result, dict)
    finally:
        await backend.close()


async def test_raw_network_enable(
    backend: CDPBackend, browser_opts: BrowserOptions
) -> None:
    """Test raw network enable."""
    await backend.launch(browser_opts)
    try:
        result = await backend.raw("Network.enable", {})
        assert isinstance(result, dict)
    finally:
        await backend.close()


async def test_raw_get_cookies(
    backend: CDPBackend, browser_opts: BrowserOptions
) -> None:
    """Test raw get cookies."""
    await backend.launch(browser_opts)
    try:
        await backend.navigate("https://example.com")
        result = await backend.raw("Network.getCookies", {})
        assert isinstance(result, dict)
    finally:
        await backend.close()


async def test_raw_bidi_command() -> None:
    """Test raw() with BiDi backend."""
    try:
        from wavexis.backend.bidi import BiDiBackend
    except ImportError:
        pytest.skip("bidiwave not installed")

    backend = BiDiBackend()
    opts = BrowserOptions(headless=True)
    await backend.launch(opts)
    try:
        result = await backend.raw("session.status", {})
        assert isinstance(result, dict)
    finally:
        await backend.close()
