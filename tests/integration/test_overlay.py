"""Integration tests for overlay actions against a real Chrome browser."""

import pytest

from wavexis.actions.overlay import OverlayAction, OverlayParams
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


async def test_overlay_highlight(
    backend: CDPBackend, browser_opts: BrowserOptions, local_http_server: str
) -> None:
    """Test overlay highlight."""
    try:
        await backend.launch(browser_opts)
        params = OverlayParams(
            url=local_http_server,
            action="highlight",
            selector="body",
            wait=WaitStrategy(strategy="load"),
            browser=browser_opts,
        )
        await OverlayAction(params).execute(backend)
    finally:
        await backend.close()


async def test_overlay_clear(
    backend: CDPBackend, browser_opts: BrowserOptions, local_http_server: str
) -> None:
    """Test overlay clear."""
    try:
        await backend.launch(browser_opts)
        params = OverlayParams(
            url=local_http_server,
            action="clear",
            wait=WaitStrategy(strategy="load"),
            browser=browser_opts,
        )
        await OverlayAction(params).execute(backend)
    finally:
        await backend.close()
