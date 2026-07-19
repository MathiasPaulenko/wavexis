"""Integration tests for WebAudio actions against a real Chrome browser."""

import pytest

from wavexis.actions.webaudio import WebAudioAction, WebAudioParams
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


async def test_webaudio_get_contexts(backend: CDPBackend, browser_opts: BrowserOptions) -> None:
    """Test webaudio get contexts."""
    params = WebAudioParams(
        url="https://example.com",
        action="list",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await WebAudioAction(params).execute(backend)
    assert isinstance(result, list)
