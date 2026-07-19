"""Integration tests for emulation methods."""

from __future__ import annotations

import pytest

from wavexis.backend.cdp import CDPBackend
from wavexis.config import BrowserOptions, ScreenshotParams, WaitStrategy


@pytest.mark.integration
class TestEmulationIntegration:
    """Test suite for emulationintegration."""

    async def test_emulate_device(self) -> None:
        """Test emulate device."""
        backend = CDPBackend()
        await backend.launch(BrowserOptions())
        try:
            await backend.navigate("https://example.com", WaitStrategy(strategy="load"))
            await backend.emulate_device("iphone-15")
            params = ScreenshotParams(url="https://example.com", full_page=True)
            result = await backend.screenshot(params)
            assert isinstance(result, bytes)
            assert len(result) > 0
        finally:
            await backend.close()

    async def test_set_viewport(self) -> None:
        """Test set viewport."""
        backend = CDPBackend()
        await backend.launch(BrowserOptions())
        try:
            await backend.set_viewport(375, 812, 3.0)
            await backend.navigate("https://example.com", WaitStrategy(strategy="load"))
            params = ScreenshotParams(url="https://example.com", full_page=True)
            result = await backend.screenshot(params)
            assert isinstance(result, bytes)
            assert len(result) > 0
        finally:
            await backend.close()

    async def test_set_geolocation(self) -> None:
        """Test set geolocation."""
        backend = CDPBackend()
        await backend.launch(BrowserOptions())
        try:
            await backend.navigate("https://example.com", WaitStrategy(strategy="load"))
            await backend.set_geolocation(40.7128, -74.0060, 50.0)
            params = ScreenshotParams(url="https://example.com", full_page=True)
            result = await backend.screenshot(params)
            assert isinstance(result, bytes)
            assert len(result) > 0
        finally:
            await backend.close()

    async def test_set_timezone(self) -> None:
        """Test set timezone."""
        backend = CDPBackend()
        await backend.launch(BrowserOptions())
        try:
            await backend.navigate("https://example.com", WaitStrategy(strategy="load"))
            await backend.set_timezone("America/New_York")
            params = ScreenshotParams(url="https://example.com", full_page=True)
            result = await backend.screenshot(params)
            assert isinstance(result, bytes)
            assert len(result) > 0
        finally:
            await backend.close()

    async def test_set_dark_mode(self) -> None:
        """Test set dark mode."""
        backend = CDPBackend()
        await backend.launch(BrowserOptions())
        try:
            await backend.navigate("https://example.com", WaitStrategy(strategy="load"))
            await backend.set_dark_mode(True)
            params = ScreenshotParams(url="https://example.com", full_page=True)
            result = await backend.screenshot(params)
            assert isinstance(result, bytes)
            assert len(result) > 0
        finally:
            await backend.close()

    async def test_emulate_device_invalid(self) -> None:
        """Test that emulate device invalid raises an appropriate error."""
        backend = CDPBackend()
        await backend.launch(BrowserOptions())
        try:
            with pytest.raises(ValueError, match="Unknown device"):
                await backend.emulate_device("nonexistent-device")
        finally:
            await backend.close()
