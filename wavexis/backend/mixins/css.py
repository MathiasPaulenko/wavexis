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
    async def overlay_highlight(self, selector: str, color: str = "rgba(255,0,0,0.5)") -> None:
        """Highlight an element with a colored overlay.

        Args:
            selector: CSS selector for the element to highlight.
            color: RGBA color string for the highlight overlay.
        """

    @abstractmethod
    async def overlay_clear(self) -> None:
        """Clear all highlight overlays from the page."""

    @abstractmethod
    async def css_add_rule(self, stylesheet_id: str, rule_text: str, location: int = 0) -> str:
        """Add a new CSS rule to a stylesheet. Returns the new rule ID."""

    @abstractmethod
    async def css_create_style_sheet(self, frame_id: str) -> str:
        """Create a new stylesheet in the given frame. Returns the stylesheet ID."""

    @abstractmethod
    async def css_get_media_queries(self) -> list[dict[str, Any]]:
        """Get all media queries in the current page."""

    @abstractmethod
    async def css_get_style_sheet_text(self, stylesheet_id: str) -> str:
        """Get the text content of a stylesheet by ID."""

    @abstractmethod
    async def css_set_style_sheet_text(self, stylesheet_id: str, text: str) -> None:
        """Set the text content of a stylesheet by ID."""

    @abstractmethod
    async def css_set_rule_selector(self, stylesheet_id: str, rule_id: str, selector: str) -> None:
        """Set the selector text of a CSS rule."""

    @abstractmethod
    async def css_set_media_text(self, stylesheet_id: str, media_id: str, text: str) -> None:
        """Set the text of a media rule."""

    @abstractmethod
    async def css_force_pseudo_state(self, node_id: int, pseudo_state: list[str]) -> None:
        """Force a pseudo state on a node (e.g. ['hover', 'focus'])."""

    @abstractmethod
    async def css_get_background_colors(self, node_id: int) -> dict[str, Any]:
        """Get background colors for a node."""

    @abstractmethod
    async def css_start_rule_usage_tracking(self) -> None:
        """Start tracking CSS rule usage."""

    @abstractmethod
    async def css_stop_rule_usage_tracking(self) -> None:
        """Stop tracking CSS rule usage."""

    @abstractmethod
    async def css_take_coverage_delta(self) -> dict[str, Any]:
        """Get the coverage delta since the last call."""

    @abstractmethod
    async def css_collect_class_names(self, node_id: int) -> list[str]:
        """Collect class names from the subtree of a node by ID."""

    @abstractmethod
    async def css_disable(self) -> None:
        """Disable the CSS domain."""

    @abstractmethod
    async def css_enable(self) -> None:
        """Enable the CSS domain."""

    @abstractmethod
    async def css_force_starting_style(
        self, node_id: int, starting_style_id: dict[str, Any]
    ) -> None:
        """Force a starting style for a node."""

    @abstractmethod
    async def css_get_animated_styles_for_node(self, node_id: int) -> dict[str, Any]:
        """Get animated styles for a node by ID."""

    @abstractmethod
    async def css_get_computed_style_for_node(self, node_id: int) -> list[dict[str, Any]]:
        """Get computed style for a node by ID."""

    @abstractmethod
    async def css_get_environment_variables(self) -> list[dict[str, Any]]:
        """Get environment variables for the CSS domain."""

    @abstractmethod
    async def css_get_inline_styles(self, node_id: int) -> dict[str, Any]:
        """Get inline styles for a node by ID."""

    @abstractmethod
    async def css_get_inline_styles_for_node(self, node_id: int) -> dict[str, Any]:
        """Get inline styles for a node by ID (alias)."""

    @abstractmethod
    async def css_get_layers_for_node(self, node_id: int) -> list[dict[str, Any]]:
        """Get CSS layers for a node by ID."""

    @abstractmethod
    async def css_get_location_for_selector(
        self, selector: str, stylesheet_id: str
    ) -> dict[str, Any]:
        """Get the location of a CSS selector in a stylesheet."""

    @abstractmethod
    async def css_get_longhand_properties(
        self, shorthand_id: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Get longhand properties for a shorthand property."""

    @abstractmethod
    async def css_get_matched_styles_for_node(self, node_id: int) -> dict[str, Any]:
        """Get matched styles for a node by ID."""

    @abstractmethod
    async def css_get_platform_fonts_for_node(self, node_id: int) -> list[dict[str, Any]]:
        """Get platform fonts for a node by ID."""

    @abstractmethod
    async def css_get_stylesheet_text(self, stylesheet_id: str) -> str:
        """Get the text content of a stylesheet by ID."""

    @abstractmethod
    async def css_resolve_values(self, values: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Resolve CSS values."""

    @abstractmethod
    async def css_set_container_query_condition_text(
        self, stylesheet_id: str, container_query_id: dict[str, Any], text: str
    ) -> None:
        """Set the condition text of a container query."""

    @abstractmethod
    async def css_set_effective_property_value_for_node(
        self, node_id: int, property_name: str, value: str
    ) -> None:
        """Set the effective property value for a node."""

    @abstractmethod
    async def css_set_keyframe_key(
        self, stylesheet_id: str, keyframe_id: dict[str, Any], key_text: str
    ) -> None:
        """Set the key text of a keyframe rule."""

    @abstractmethod
    async def css_set_local_fonts_enabled(self, enabled: bool) -> None:
        """Enable or disable local fonts."""

    @abstractmethod
    async def css_set_navigation_text(
        self, stylesheet_id: str, navigation_id: dict[str, Any], text: str
    ) -> None:
        """Set the text of a navigation rule."""

    @abstractmethod
    async def css_set_property_rule_property_name(
        self, stylesheet_id: str, property_rule_id: dict[str, Any], name: str
    ) -> None:
        """Set the property name of a property rule."""

    @abstractmethod
    async def css_set_rule_style(
        self, stylesheet_id: str, rule_id: dict[str, Any], style_text: str
    ) -> None:
        """Set the style text of a CSS rule."""

    @abstractmethod
    async def css_set_scope_text(
        self, stylesheet_id: str, scope_id: dict[str, Any], text: str
    ) -> None:
        """Set the text of a scope rule."""

    @abstractmethod
    async def css_set_style_text(self, edits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Set style texts for multiple edits."""

    @abstractmethod
    async def css_set_style_texts(self, edits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Set style texts for multiple edits (batch)."""

    @abstractmethod
    async def css_set_stylesheet_text(self, stylesheet_id: str, text: str) -> None:
        """Set the text content of a stylesheet by ID (alias)."""

    @abstractmethod
    async def css_set_supports_text(
        self, stylesheet_id: str, supports_id: dict[str, Any], text: str
    ) -> None:
        """Set the text of a supports rule."""

    @abstractmethod
    async def css_take_computed_style_updates(self) -> list[dict[str, Any]]:
        """Take computed style updates."""

    @abstractmethod
    async def css_track_computed_style_updates(self, track_properties: bool = True) -> None:
        """Track computed style updates."""

    @abstractmethod
    async def css_track_computed_style_updates_for_node(
        self, node_id: int, track_properties: bool = True
    ) -> None:
        """Track computed style updates for a specific node."""
