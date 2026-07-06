"""Integration tests for screenshot command."""

import pytest

from wavexis.actions.screenshot import ScreenshotAction
from wavexis.backend.manager import BackendManager
from wavexis.config import BrowserOptions, ScreenshotParams, WaitStrategy


@pytest.mark.integration
class TestScreenshotIntegration:
    """Integration tests for screenshot against real Chrome."""

    async def test_basic_screenshot(self):
        """Test basic screenshot."""
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            params = ScreenshotParams(
                url="https://example.com",
                full_page=False,
                wait=WaitStrategy(strategy="load"),
            )
            action = ScreenshotAction(params)
            result = await action.execute(backend)
            assert len(result) > 0
            assert result[:4] == b"\x89PNG"
        finally:
            await backend.close()

    async def test_full_page_screenshot(self):
        """Test full page screenshot."""
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            params = ScreenshotParams(
                url="https://example.com",
                full_page=True,
                wait=WaitStrategy(strategy="load"),
            )
            action = ScreenshotAction(params)
            result = await action.execute(backend)
            assert len(result) > 0
            assert result[:4] == b"\x89PNG"
        finally:
            await backend.close()

    async def test_device_screenshot(self):
        """Test device screenshot."""
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            params = ScreenshotParams(
                url="https://example.com",
                full_page=False,
                device="iphone-15",
                wait=WaitStrategy(strategy="load"),
            )
            action = ScreenshotAction(params)
            result = await action.execute(backend)
            assert len(result) > 0
            assert result[:4] == b"\x89PNG"
        finally:
            await backend.close()
