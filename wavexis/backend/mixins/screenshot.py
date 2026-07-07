"""Screenshot and PDF capture mixin."""

from __future__ import annotations

from abc import ABC, abstractmethod

from wavexis.config import PDFParams, ScreencastParams, ScreenshotParams


class ScreenshotBackend(ABC):
    """Screenshot, PDF, and screencast capture operations."""

    @abstractmethod
    async def screenshot(self, params: ScreenshotParams) -> bytes:
        """Take a screenshot and return the image bytes."""

    @abstractmethod
    async def screenshot_selector(
        self, selector: str, format: str = "png", quality: int = 80
    ) -> bytes:
        """Take a screenshot of an element matching a CSS selector."""

    @abstractmethod
    async def annotated_screenshot(
        self,
        selectors: list[str],
        format: str = "png",
    ) -> tuple[bytes, dict[str, str]]:
        """Take a screenshot with numbered labels overlaid on elements.

        Injects overlay divs with labels @e1, @e2, ... on each element
        matching the selectors, captures a screenshot, removes the overlays,
        and returns the image bytes plus a label-to-selector mapping.

        Args:
            selectors: List of CSS selectors to annotate.
            format: Image format: "png" or "jpeg".

        Returns:
            Tuple of (image_bytes, label_map) where label_map is
            {"e1": "selector1", "e2": "selector2", ...}.
        """

    @abstractmethod
    async def pdf(self, params: PDFParams) -> bytes:
        """Generate a PDF of the current page and return the bytes."""

    @abstractmethod
    async def screencast(self, params: ScreencastParams) -> list[bytes]:
        """Capture a screencast and return a list of frame bytes."""
