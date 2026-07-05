"""Integration tests for security operations against real Chrome."""

import pytest

from browsix.backend.cdp import CDPBackend
from browsix.config import BrowserOptions, WaitStrategy

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


@pytest.mark.integration
class TestSecurityIntegration:
    """Test suite for securityintegration."""
    async def test_ignore_cert_errors(self) -> None:
        """Test ignore cert errors."""
        backend = CDPBackend(BrowserOptions(headless=True))
        async with backend:
            await backend.navigate(
                "data:text/html,<html></html>",
                WaitStrategy(strategy="load"),
            )
            await backend.ignore_cert_errors(True)
