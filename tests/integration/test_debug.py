"""Integration tests for debug actions against a real Chrome browser."""

import pytest

from browsix.actions.debug import DebugAction, DebugActionParams
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


async def test_debug_pause_resume(backend: CDPBackend, browser_opts: BrowserOptions) -> None:
    """Test debug pause resume."""
    params = DebugActionParams(
        url="https://example.com",
        action="pause",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    await DebugAction(params).execute(backend)


async def test_debug_step_over(backend: CDPBackend, browser_opts: BrowserOptions) -> None:
    """Test debug step over."""
    params = DebugActionParams(
        url="https://example.com",
        action="step_over",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    await DebugAction(params).execute(backend)


async def test_debug_listeners(backend: CDPBackend, browser_opts: BrowserOptions) -> None:
    """Test debug listeners."""
    params = DebugActionParams(
        url="https://example.com",
        action="listeners",
        selector="body",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await DebugAction(params).execute(backend)
    assert isinstance(result, list)
