"""Overlay mixin — visual highlights, debug overlays, and inspect mode."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class OverlayBackend(ABC):
    """Visual highlight and debug overlay operations."""

    @abstractmethod
    async def overlay_highlight(self, selector: str, color: str = "rgba(255,0,0,0.5)") -> None:
        """Highlight an element with a colored overlay.

        Args:
            selector: CSS selector for the element to highlight.
            color: RGBA color string for the highlight.
        """

    @abstractmethod
    async def overlay_clear(self) -> None:
        """Clear all highlight overlays from the page."""

    @abstractmethod
    async def overlay_enable(self) -> None:
        """Enable the overlay domain."""

    @abstractmethod
    async def overlay_disable(self) -> None:
        """Disable the overlay domain."""

    @abstractmethod
    async def overlay_highlight_node(self, node_id: int, color: str = "rgba(255,0,0,0.5)") -> None:
        """Highlight a DOM node by node ID."""

    @abstractmethod
    async def overlay_highlight_quad(
        self, quad: list[float], color: str = "rgba(255,0,0,0.5)"
    ) -> None:
        """Highlight a quad region on the page."""

    @abstractmethod
    async def overlay_highlight_rect(
        self, x: float, y: float, width: float, height: float, color: str = "rgba(255,0,0,0.5)"
    ) -> None:
        """Highlight a rectangular region on the page."""

    @abstractmethod
    async def overlay_set_inspect_mode(self, mode: str = "searchForNode") -> None:
        """Set the inspect mode for element selection.

        Args:
            mode: Inspect mode: searchForNode, searchForUAShadowDOM,
                captureAreaScreenshot, showDistances, none.
        """

    @abstractmethod
    async def overlay_set_show_fps_counter(self, show: bool) -> None:
        """Show or hide the FPS counter overlay."""

    @abstractmethod
    async def overlay_set_show_paint_rects(self, show: bool) -> None:
        """Show or hide paint rectangles overlay."""

    @abstractmethod
    async def overlay_set_show_debug_borders(self, show: bool) -> None:
        """Show or hide debug borders overlay."""

    @abstractmethod
    async def overlay_set_show_ad_highlights(self, show: bool) -> None:
        """Show or hide ad highlights overlay."""

    @abstractmethod
    async def overlay_get_grid_highlight_objects_for_test(self, node_id: int) -> dict[str, Any]:
        """Get grid highlight objects for testing."""

    @abstractmethod
    async def overlay_get_highlight_object_for_test(
        self,
        node_id: int,
        include_distance: bool = False,
        include_style: bool = False,
        color_format: str = "hex",
    ) -> dict[str, Any]:
        """Get highlight object for testing."""

    @abstractmethod
    async def overlay_get_source_order_highlight_object_for_test(
        self, node_id: int
    ) -> dict[str, Any]:
        """Get source order highlight object for testing."""

    @abstractmethod
    async def overlay_hide_highlight(self) -> None:
        """Hide any highlight overlay."""

    @abstractmethod
    async def overlay_highlight_source_order(self, source_order_config: dict[str, Any]) -> None:
        """Highlight the source order of a node."""

    @abstractmethod
    async def overlay_set_paused_in_debugger_message(self, message: str = "") -> None:
        """Set the message displayed when paused in the debugger."""

    @abstractmethod
    async def overlay_set_show_container_query_overlays(self, show: bool) -> None:
        """Show or hide container query overlays."""

    @abstractmethod
    async def overlay_set_show_display_cutout(self, show: bool) -> None:
        """Show or hide display cutout overlay."""

    @abstractmethod
    async def overlay_set_show_flex_overlays(self, show: bool) -> None:
        """Show or hide flex overlays."""

    @abstractmethod
    async def overlay_set_show_grid_overlays(
        self, show_grid_overlays: list[dict[str, Any]]
    ) -> None:
        """Show grid overlays for the given configurations."""

    @abstractmethod
    async def overlay_set_show_hinge(self, hinge_config: dict[str, Any] | None = None) -> None:
        """Show or hide the hinge overlay."""

    @abstractmethod
    async def overlay_set_show_inspected_element_anchor(self, show: bool) -> None:
        """Show or hide the inspected element anchor."""

    @abstractmethod
    async def overlay_set_show_isolated_elements(
        self, isolated_element_highlight_configs: list[dict[str, Any]]
    ) -> None:
        """Show isolated elements with the given highlight configurations."""

    @abstractmethod
    async def overlay_set_show_layout_shift_regions(self, show: bool) -> None:
        """Show or hide layout shift regions."""

    @abstractmethod
    async def overlay_set_show_scroll_bottleneck_rects(self, show: bool) -> None:
        """Show or hide scroll bottleneck rects."""

    @abstractmethod
    async def overlay_set_show_scroll_snap_overlays(self, show: bool) -> None:
        """Show or hide scroll snap overlays."""

    @abstractmethod
    async def overlay_set_show_viewport_size_on_resize(self, show: bool) -> None:
        """Show or hide viewport size on resize."""

    @abstractmethod
    async def overlay_set_show_window_controls_overlay(self, show: bool) -> None:
        """Show or hide window controls overlay."""
