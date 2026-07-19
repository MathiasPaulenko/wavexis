"""Integration tests for dialog handling against real Chrome."""

import asyncio

import pytest

from wavexis.backend.cdp import CDPBackend
from wavexis.config import BrowserOptions, WaitStrategy

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


@pytest.mark.integration
class TestDialogIntegration:
    """Test suite for dialogintegration."""

    async def test_dialog_accept(self) -> None:
        """Test dialog accept."""
        backend = CDPBackend()
        async with backend:
            await backend.launch(BrowserOptions(headless=True))
            await backend.navigate(
                "data:text/html,<script>alert('test')</script>",
                WaitStrategy(strategy="none"),
            )
            await asyncio.sleep(1)
            await backend.dialog_accept()

    async def test_dialog_dismiss(self) -> None:
        """Test dialog dismiss."""
        backend = CDPBackend()
        async with backend:
            await backend.launch(BrowserOptions(headless=True))
            await backend.navigate(
                "data:text/html,<script>confirm('test')</script>",
                WaitStrategy(strategy="none"),
            )
            await asyncio.sleep(1)
            await backend.dialog_dismiss()
