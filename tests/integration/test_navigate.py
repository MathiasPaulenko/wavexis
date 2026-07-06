"""Integration tests for navigation commands."""

import pytest

from wavexis.actions.navigate import NavigateAction, NavigateParams, ReloadAction
from wavexis.backend.manager import BackendManager
from wavexis.config import BrowserOptions, WaitStrategy


@pytest.mark.integration
class TestNavigateIntegration:
    """Integration tests for navigation against real Chrome."""

    async def test_navigate_basic(self):
        """Test navigate basic."""
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            action = NavigateAction(NavigateParams(
                url="https://example.com",
                wait=WaitStrategy(strategy="load"),
            ))
            await action.execute(backend)
        finally:
            await backend.close()

    async def test_navigate_wait_for_selector(self):
        """Test navigate wait for selector."""
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            action = NavigateAction(NavigateParams(
                url="https://example.com",
                wait=WaitStrategy(strategy="selector", selector="h1", timeout=10000),
            ))
            await action.execute(backend)
        finally:
            await backend.close()

    async def test_reload(self):
        """Test reload."""
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            await backend.navigate("https://example.com", WaitStrategy(strategy="load"))
            action = ReloadAction(False)
            await action.execute(backend)
        finally:
            await backend.close()
