"""Integration tests for WebAudio actions against a real Chrome browser."""

import pytest

from browsix.actions.webaudio import WebAudioAction, WebAudioParams
from browsix.backend.cdp import CDPBackend
from browsix.config import BrowserOptions, WaitStrategy

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


@pytest.fixture
def backend() -> CDPBackend:
    return CDPBackend()


@pytest.fixture
def browser_opts() -> BrowserOptions:
    return BrowserOptions(headless=True)


async def test_webaudio_get_contexts(
    backend: CDPBackend, browser_opts: BrowserOptions
) -> None:
    params = WebAudioParams(
        url="https://example.com",
        action="list",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await WebAudioAction(params).execute(backend)
    assert isinstance(result, list)
