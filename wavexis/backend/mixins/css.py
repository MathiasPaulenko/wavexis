"""CSS inspection and overlay highlight mixin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CSSBackend(ABC):
    """CSS styles, stylesheets, rules, computed styles, and overlay highlights."""

    @abstractmethod
    async def css_get_styles(self, selector: str) -> dict[str, Any]:
        """Get inline and matched styles for an element by CSS selector.

        Args:
            selector: CSS selector for the target element.

        Returns:
            Dict containing inlineStyles and matchedStyles.
        """

    @abstractmethod
    async def css_get_stylesheets(self) -> list[dict[str, Any]]:
        """List all stylesheets in the current page.

        Returns:
            List of stylesheet header dicts (styleSheetId, origin, sourceURL, etc.).
        """

    @abstractmethod
    async def css_get_rules(self, stylesheet_id: str) -> list[dict[str, Any]]:
        """Get CSS rules from a specific stylesheet.

        Args:
            stylesheet_id: The styleSheetId from css_get_stylesheets.

        Returns:
            List of CSS rule dicts.
        """

    @abstractmethod
    async def css_get_computed(self, selector: str) -> dict[str, Any]:
        """Get computed styles for an element by CSS selector.

        Args:
            selector: CSS selector for the target element.

        Returns:
            Dict mapping CSS property names to computed values.
        """

    @abstractmethod
    async def overlay_highlight(
        self, selector: str, color: str = "rgba(255,0,0,0.5)"
    ) -> None:
        """Highlight an element with a colored overlay.

        Args:
            selector: CSS selector for the element to highlight.
            color: RGBA color string for the highlight overlay.
        """

    @abstractmethod
    async def overlay_clear(self) -> None:
        """Clear all highlight overlays from the page."""
