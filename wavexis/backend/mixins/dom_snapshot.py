"""DOMSnapshot mixin — DOM snapshot capture and retrieval."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DOMSnapshotBackend(ABC):
    """DOM snapshot operations."""

    @abstractmethod
    async def dom_snapshot_capture_snapshot(
        self,
        computed_styles: list[str] | None = None,
        include_paint_order: bool = False,
        include_dom_rects: bool = False,
        include_blended_background_colors: bool = False,
        include_text_color_opacity: bool = False,
    ) -> dict[str, Any]:
        """Capture a DOM snapshot of the current page."""

    @abstractmethod
    async def dom_snapshot_disable(self) -> None:
        """Disable the DOMSnapshot domain."""

    @abstractmethod
    async def dom_snapshot_enable(self) -> None:
        """Enable the DOMSnapshot domain."""

    @abstractmethod
    async def dom_snapshot_get_snapshot(
        self,
        computed_styles: list[str] | None = None,
        include_paint_order: bool = False,
        include_dom_rects: bool = False,
        include_blended_background_colors: bool = False,
        include_text_color_opacity: bool = False,
    ) -> dict[str, Any]:
        """Get a DOM snapshot of the current page."""
