"""Integration tests for overlay actions against a real Chrome browser."""

import pytest

from browsix.actions.overlay import OverlayAction, OverlayParams
from browsix.backend.cdp import CDPBackend
from browsix.config import BrowserOptions, WaitStrategy

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


@pytest.fixture
def backend() -> CDPBackend:
    """Backend."""
    return CDPBackend()


@pytest.fixture
def browser_opts() -> BrowserOptions:
    """Browser opts."""
    return BrowserOptions(headless=True)


async def test_overlay_highlight(backend: CDPBackend, browser_opts: BrowserOptions) -> None:
    """Test overlay highlight."""
    params = OverlayParams(
        url="https://example.com",
        action="highlight",
        selector="body",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    await OverlayAction(params).execute(backend)


async def test_overlay_clear(backend: CDPBackend, browser_opts: BrowserOptions) -> None:
    """Test overlay clear."""
    params = OverlayParams(
        url="https://example.com",
        action="clear",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    await OverlayAction(params).execute(backend)
