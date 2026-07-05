"""Integration tests for security operations against real Chrome."""

import pytest

from browsix.backend.cdp import CDPBackend
from browsix.config import BrowserOptions, WaitStrategy

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


@pytest.mark.integration
class TestSecurityIntegration:
    async def test_ignore_cert_errors(self) -> None:
        backend = CDPBackend(BrowserOptions(headless=True))
        async with backend:
            await backend.navigate(
                "data:text/html,<html></html>",
                WaitStrategy(strategy="load"),
            )
            await backend.ignore_cert_errors(True)
