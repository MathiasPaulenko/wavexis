"""Integration tests for permissions against real Chrome."""

import pytest

from browsix.backend.cdp import CDPBackend
from browsix.config import BrowserOptions, WaitStrategy

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


@pytest.mark.integration
class TestPermissionsIntegration:
    """Test suite for permissionsintegration."""
    async def test_grant_and_reset(self) -> None:
        """Test grant and reset."""
        backend = CDPBackend(BrowserOptions(headless=True))
        async with backend:
            await backend.navigate(
                "data:text/html,<html></html>",
                WaitStrategy(strategy="load"),
            )
            await backend.grant_permission("geolocation")
            await backend.reset_permissions()
