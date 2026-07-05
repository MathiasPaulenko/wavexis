"""Integration tests for tabs commands."""

import pytest

from browsix.actions.tabs import TabsAction, TabsParams
from browsix.backend.manager import BackendManager
from browsix.config import BrowserOptions


@pytest.mark.integration
class TestTabsIntegration:
    """Integration tests for tab management against real Chrome."""

    async def test_list_tabs(self):
        """Test list tabs."""
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            action = TabsAction(TabsParams(action="list"))
            result = await action.execute(backend)
            assert isinstance(result, list)
            assert len(result) >= 1
        finally:
            await backend.close()

    async def test_new_and_close_tab(self):
        """Test new and close tab."""
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            action = TabsAction(TabsParams(action="new", url="about:blank"))
            tab_id = await action.execute(backend)
            assert isinstance(tab_id, str)
            assert len(tab_id) > 0

            close_action = TabsAction(TabsParams(action="close", tab_id=tab_id))
            await close_action.execute(backend)
        finally:
            await backend.close()
