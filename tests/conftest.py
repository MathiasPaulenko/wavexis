"""Pytest configuration and shared fixtures for wavexis tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: fast isolated tests with mocks")
    config.addinivalue_line("markers", "integration: tests against a real Chrome browser")
    config.addinivalue_line("markers", "slow: tests that take more than 5 seconds")
    config.addinivalue_line("markers", "chrome: tests that require Chrome specifically")
    config.addinivalue_line("markers", "e2e: end-to-end CLI tests against a real browser")


class MockBackend:
    """Reusable mock backend for unit tests.

    Provides AsyncMock stubs for all common AbstractBackend methods.
    Tests can override specific return values as needed.
    """

    def __init__(self) -> None:
        self.navigate = AsyncMock()
        self.screenshot = AsyncMock(return_value=b"png-bytes")
        self.screenshot_selector = AsyncMock(return_value=b"selector-bytes")
        self.eval = AsyncMock(return_value="eval-result")
        self.close = AsyncMock()
        self.launch = AsyncMock()
        self.raw = AsyncMock(return_value={})
        self.go_back = AsyncMock()
        self.go_forward = AsyncMock()
        self.reload = AsyncMock()
        self.stop_loading = AsyncMock()
        self.wait_for = AsyncMock()
        self.pdf = AsyncMock(return_value=b"pdf-bytes")
        self.screencast = AsyncMock(return_value=[b"frame1"])
        self.list_tabs = AsyncMock(return_value=[{"targetId": "tab1"}])
        self.new_tab = AsyncMock(return_value="new-tab-id")
        self.close_tab = AsyncMock()
        self.activate_tab = AsyncMock()
        self.capture_console = AsyncMock(return_value=[{"type": "log"}])
        self.capture_logs = AsyncMock(return_value=[{"level": "info"}])
        self.dom_get = AsyncMock(return_value="<div>html</div>")
        self.dom_query = AsyncMock(return_value={"nodeId": 1})
        self.dom_set_attr = AsyncMock()
        self.dom_get_attr = AsyncMock(return_value="class-value")
        self.dom_remove_attr = AsyncMock()
        self.dom_remove = AsyncMock()
        self.dom_focus = AsyncMock()
        self.dom_scroll = AsyncMock()
        self.capture_har = AsyncMock(return_value={"log": {"entries": []}})
        self.get_cookies = AsyncMock(return_value=[{"name": "session"}])
        self.set_cookie = AsyncMock()
        self.delete_cookie = AsyncMock()
        self.clear_cookies = AsyncMock()
        self.set_headers = AsyncMock()
        self.set_user_agent = AsyncMock()
        self.new_context = AsyncMock(return_value="ctx-1")
        self.list_contexts = AsyncMock(return_value=[{"contextId": "ctx-1"}])
        self.close_context = AsyncMock()
        self.get_window_bounds = AsyncMock(
            return_value={"width": 1280, "height": 800, "x": 0, "y": 0}
        )
        self.set_window_bounds = AsyncMock()
        self.browser_version = AsyncMock(return_value="Chrome/120.0")
        self.emulate_device = AsyncMock()
        self.set_viewport = AsyncMock()
        self.set_timezone = AsyncMock()
        self.set_dark_mode = AsyncMock()
        self.set_geolocation = AsyncMock()
        self.new_tab_handle = AsyncMock(return_value=AsyncMock())
        self.click = AsyncMock()
        self.type = AsyncMock()
        self.fill = AsyncMock()
        self.scroll = AsyncMock()
        self.hover = AsyncMock()
        self.focus = AsyncMock()
        self.select = AsyncMock()
        self.press_key = AsyncMock()


@pytest.fixture
def mock_backend() -> MockBackend:
    """Return a reusable MockBackend instance for unit tests."""
    return MockBackend()


@pytest.fixture
def mock_backend_factory() -> Any:
    """Return a callable that creates fresh MockBackend instances."""
    return MockBackend
