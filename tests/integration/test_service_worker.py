"""Integration tests for service worker actions against a real Chrome browser."""

import pytest

from wavexis.actions.service_worker import ServiceWorkerAction, ServiceWorkerParams
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


async def test_sw_list(backend: CDPBackend, browser_opts: BrowserOptions) -> None:
    """Test sw list."""
    params = ServiceWorkerParams(
        url="https://example.com",
        action="list",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await ServiceWorkerAction(params).execute(backend)
    assert isinstance(result, list)
