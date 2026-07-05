"""Integration tests for input actions against real Chrome."""

import pytest

from browsix.backend.cdp import CDPBackend
from browsix.config import BrowserOptions, WaitStrategy

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


@pytest.mark.integration
class TestInputIntegration:
    async def test_click_and_type(self) -> None:
        backend = CDPBackend(BrowserOptions(headless=True))
        async with backend:
            await backend.navigate(
                "data:text/html,<input id='q' type='text'><button id='btn'>Click</button>",
                WaitStrategy(strategy="load"),
            )
            await backend.click("#btn")
            await backend.type_text("#q", "hello world")

    async def test_fill_and_select(self) -> None:
        html = (
            "data:text/html,"
            "<input id='i' type='text'>"
            "<select id='s'><option value='a'>A</option><option value='b'>B</option></select>"
        )
        backend = CDPBackend(BrowserOptions(headless=True))
        async with backend:
            await backend.navigate(html, WaitStrategy(strategy="load"))
            await backend.fill("#i", "test value")
            await backend.select_option("#s", "b")

    async def test_hover_and_key(self) -> None:
        html = (
            "data:text/html,"
            "<div id='d' onmouseover='this.textContent=\"hovered\"'>Hover me</div>"
        )
        backend = CDPBackend(BrowserOptions(headless=True))
        async with backend:
            await backend.navigate(html, WaitStrategy(strategy="load"))
            await backend.hover("#d")
            await backend.key_press("Tab")
