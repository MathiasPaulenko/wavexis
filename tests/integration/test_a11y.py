"""Integration tests for accessibility tree operations against real Chrome."""

import pytest

from browsix.backend.cdp import CDPBackend
from browsix.config import BrowserOptions, WaitStrategy

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


@pytest.mark.integration
class TestA11yIntegration:
    """Test suite for a11yintegration."""
    async def test_a11y_tree(self) -> None:
        """Test a11y tree."""
        backend = CDPBackend(BrowserOptions(headless=True))
        async with backend:
            await backend.navigate(
                "data:text/html,<h1>Title</h1><p>Paragraph</p>",
                WaitStrategy(strategy="load"),
            )
            tree = await backend.a11y_tree()
            assert "nodes" in tree
            assert len(tree["nodes"]) > 0

    async def test_a11y_node(self) -> None:
        """Test a11y node."""
        backend = CDPBackend(BrowserOptions(headless=True))
        async with backend:
            await backend.navigate(
                "data:text/html,<h1>Title</h1>",
                WaitStrategy(strategy="load"),
            )
            tree = await backend.a11y_tree()
            nodes = tree.get("nodes", [])
            if nodes:
                node_id = nodes[0].get("nodeId", "")
                if node_id:
                    node = await backend.a11y_node(node_id)
                    assert isinstance(node, dict)
