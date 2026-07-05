"""Integration tests for network advanced features against real Chrome."""

import pytest

from browsix.backend.cdp import CDPBackend
from browsix.config import BrowserOptions, ThrottleParams, WaitStrategy

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


@pytest.mark.integration
class TestNetworkAdvancedIntegration:
    """Test suite for networkadvancedintegration."""
    async def test_block_requests(self) -> None:
        """Test block requests."""
        backend = CDPBackend(BrowserOptions(headless=True))
        async with backend:
            await backend.navigate(
                "data:text/html,<html></html>",
                WaitStrategy(strategy="load"),
            )
            await backend.block_requests(["*.png", "*.jpg"])

    async def test_throttle_network(self) -> None:
        """Test throttle network."""
        backend = CDPBackend(BrowserOptions(headless=True))
        async with backend:
            await backend.navigate(
                "data:text/html,<html></html>",
                WaitStrategy(strategy="load"),
            )
            await backend.throttle_network(
                ThrottleParams(offline=False, latency_ms=100, download_bps=50000, upload_bps=20000)
            )

    async def test_set_cache_disabled(self) -> None:
        """Test set cache disabled."""
        backend = CDPBackend(BrowserOptions(headless=True))
        async with backend:
            await backend.navigate(
                "data:text/html,<html></html>",
                WaitStrategy(strategy="load"),
            )
            await backend.set_cache_disabled(True)
