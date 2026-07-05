"""Integration tests for dialog handling against real Chrome."""

import pytest

from browsix.backend.cdp import CDPBackend
from browsix.config import BrowserOptions, WaitStrategy

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


@pytest.mark.integration
class TestDialogIntegration:
    """Test suite for dialogintegration."""
    async def test_dialog_accept(self) -> None:
        """Test dialog accept."""
        backend = CDPBackend(BrowserOptions(headless=True))
        async with backend:
            await backend.navigate(
                "data:text/html,<script>alert('test')</script>",
                WaitStrategy(strategy="load"),
            )
            await backend.dialog_accept()

    async def test_dialog_dismiss(self) -> None:
        """Test dialog dismiss."""
        backend = CDPBackend(BrowserOptions(headless=True))
        async with backend:
            await backend.navigate(
                "data:text/html,<script>confirm('test')</script>",
                WaitStrategy(strategy="load"),
            )
            await backend.dialog_dismiss()
