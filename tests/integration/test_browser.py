"""Integration tests for browser management commands."""

import pytest

from wavexis.backend.manager import BackendManager
from wavexis.config import BrowserOptions


@pytest.mark.integration
class TestBrowserIntegration:
    """Integration tests for browser management against real Chrome."""

    async def test_browser_version(self):
        """Test browser version."""
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            version = await backend.browser_version()
            assert isinstance(version, str)
            assert len(version) > 0
        finally:
            await backend.close()

    async def test_new_and_list_contexts(self):
        """Test new and list contexts."""
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            ctx_id = await backend.new_context()
            assert isinstance(ctx_id, str)
            assert len(ctx_id) > 0
            contexts = await backend.list_contexts()
            assert isinstance(contexts, list)
            ctx_ids = [c.get("contextId") for c in contexts]
            assert ctx_id in ctx_ids
            await backend.close_context(ctx_id)
        finally:
            await backend.close()

    async def test_get_window_bounds(self):
        """Test get window bounds."""
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            bounds = await backend.get_window_bounds()
            assert "width" in bounds
            assert "height" in bounds
            assert bounds["width"] > 0
            assert bounds["height"] > 0
        finally:
            await backend.close()

    async def test_set_window_bounds(self):
        """Test set window bounds."""
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            await backend.set_window_bounds(1024, 768, 0, 0)
            bounds = await backend.get_window_bounds()
            assert bounds["width"] == 1024
            assert bounds["height"] == 768
        finally:
            await backend.close()
