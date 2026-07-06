"""Integration tests for DOM snapshot action against a real Chrome browser."""

import pytest

from wavexis.actions.dom_snapshot import DOMSnapshotAction, DOMSnapshotParams
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


async def test_dom_snapshot(backend: CDPBackend, browser_opts: BrowserOptions) -> None:
    """Test dom snapshot."""
    params = DOMSnapshotParams(
        url="https://example.com",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await DOMSnapshotAction(params).execute(backend)
    assert isinstance(result, dict)
