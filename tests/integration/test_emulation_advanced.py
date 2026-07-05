"""Integration tests for emulation advanced features against real Chrome."""

import pytest

from browsix.backend.cdp import CDPBackend
from browsix.config import BrowserOptions, SensorParams, WaitStrategy

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


@pytest.mark.integration
class TestEmulationAdvancedIntegration:
    async def test_set_locale(self) -> None:
        backend = CDPBackend(BrowserOptions(headless=True))
        async with backend:
            await backend.navigate(
                "data:text/html,<html></html>",
                WaitStrategy(strategy="load"),
            )
            await backend.set_locale("fr-FR")

    async def test_set_cpu_throttle(self) -> None:
        backend = CDPBackend(BrowserOptions(headless=True))
        async with backend:
            await backend.navigate(
                "data:text/html,<html></html>",
                WaitStrategy(strategy="load"),
            )
            await backend.set_cpu_throttle(2.0)

    async def test_set_touch_emulation(self) -> None:
        backend = CDPBackend(BrowserOptions(headless=True))
        async with backend:
            await backend.navigate(
                "data:text/html,<html></html>",
                WaitStrategy(strategy="load"),
            )
            await backend.set_touch_emulation(True)

    async def test_set_sensors_geolocation(self) -> None:
        backend = CDPBackend(BrowserOptions(headless=True))
        async with backend:
            await backend.navigate(
                "data:text/html,<html></html>",
                WaitStrategy(strategy="load"),
            )
            await backend.set_sensors(
                SensorParams(type="geolocation", values={"latitude": 37.77, "longitude": -122.41})
            )
