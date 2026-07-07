"""Accessibility mixin — tree, nodes, axe audit."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AccessibilityBackend(ABC):
    """Accessibility tree inspection and axe-core audits."""

    @abstractmethod
    async def a11y_tree(self) -> dict[str, Any]:
        """Get the full accessibility tree of the current page."""

    @abstractmethod
    async def a11y_node(self, node_id: str) -> dict[str, Any]:
        """Get a specific accessibility node by its node ID."""

    @abstractmethod
    async def a11y_ancestors(self, node_id: str) -> list[dict[str, Any]]:
        """Get ancestor nodes of an accessibility node."""

    @abstractmethod
    async def axe_audit(self) -> dict[str, Any]:
        """Run axe-core accessibility audit on the current page.

        Returns:
            Dict with violations, passes, incomplete, and inapplicable lists.
        """
