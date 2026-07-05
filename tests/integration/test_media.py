"""Integration tests for Media actions against a real Chrome browser."""

import pytest

from browsix.actions.media import MediaAction, MediaParams
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


async def test_media_get_players(
    backend: CDPBackend, browser_opts: BrowserOptions
) -> None:
    """Test media get players."""
    params = MediaParams(
        url="https://example.com",
        action="list",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await MediaAction(params).execute(backend)
    assert isinstance(result, list)
