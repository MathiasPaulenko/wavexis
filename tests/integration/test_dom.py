"""Integration tests for DOM operations."""

import pytest

from browsix.actions.dom import DOMAction
from browsix.backend.manager import BackendManager
from browsix.config import BrowserOptions, DOMParams, WaitStrategy


@pytest.mark.integration
class TestDOMIntegration:
    """Integration tests for DOM against real Chrome."""

    async def test_dom_get_outer(self):
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            await backend.navigate(
                "https://example.com", WaitStrategy(strategy="load")
            )
            html = await backend.dom_get("h1", outer=True)
            assert "<h1>" in html
            assert "Example Domain" in html
        finally:
            await backend.close()

    async def test_dom_get_inner(self):
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            await backend.navigate(
                "https://example.com", WaitStrategy(strategy="load")
            )
            html = await backend.dom_get("h1", outer=False)
            assert "Example Domain" in html
            assert "<h1>" not in html
        finally:
            await backend.close()

    async def test_dom_query_single(self):
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            await backend.navigate(
                "https://example.com", WaitStrategy(strategy="load")
            )
            node = await backend.dom_query("h1", all=False)
            assert isinstance(node, dict)
            assert "nodeName" in node
        finally:
            await backend.close()

    async def test_dom_query_all(self):
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            await backend.navigate(
                "https://example.com", WaitStrategy(strategy="load")
            )
            nodes = await backend.dom_query("p", all=True)
            assert isinstance(nodes, list)
            assert len(nodes) >= 1
        finally:
            await backend.close()

    async def test_dom_get_attr(self):
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            await backend.navigate(
                "https://example.com", WaitStrategy(strategy="load")
            )
            href = await backend.dom_get_attr("a", "href")
            assert "example.com" in href or "iana.org" in href
        finally:
            await backend.close()

    async def test_dom_set_attr(self):
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            await backend.navigate(
                "https://example.com", WaitStrategy(strategy="load")
            )
            await backend.dom_set_attr("h1", "data-test", "value123")
            val = await backend.dom_get_attr("h1", "data-test")
            assert val == "value123"
        finally:
            await backend.close()

    async def test_dom_scroll(self):
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            await backend.navigate(
                "https://example.com", WaitStrategy(strategy="load")
            )
            await backend.dom_scroll(x=0, y=100)
        finally:
            await backend.close()

    async def test_dom_action_via_action_class(self):
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            params = DOMParams(
                url="https://example.com",
                action="get",
                selector="h1",
                wait=WaitStrategy(strategy="load"),
            )
            action = DOMAction(params)
            result = await action.execute(backend)
            assert "Example Domain" in result
        finally:
            await backend.close()
