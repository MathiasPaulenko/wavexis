"""Integration tests for animation actions against a real Chrome browser."""

import pytest

from browsix.actions.animation import AnimationAction
from browsix.backend.cdp import CDPBackend
from browsix.config import AnimationParams, BrowserOptions, WaitStrategy

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


@pytest.fixture
def backend() -> CDPBackend:
    """Backend."""
    return CDPBackend()


@pytest.fixture
def browser_opts() -> BrowserOptions:
    """Browser opts."""
    return BrowserOptions(headless=True)


async def test_animation_list(
    backend: CDPBackend, browser_opts: BrowserOptions
) -> None:
    """Test animation list."""
    params = AnimationParams(
        url="https://example.com",
        action="list",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await AnimationAction(params).execute(backend)
    assert isinstance(result, list)
