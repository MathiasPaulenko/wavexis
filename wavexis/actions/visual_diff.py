"""Visual diff action for comparing two screenshots and reporting differences."""

from __future__ import annotations

import asyncio
import base64
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, ScreenshotParams, WaitStrategy


@dataclass
class VisualDiffParams:
    """Parameters for visual diff.

    Attributes:
        url: URL to navigate to before capturing.
        baseline_path: Path to the baseline screenshot file.
        selector: Optional CSS selector to capture a specific element.
        threshold: Pixel difference threshold (0-255). Pixels with diff > threshold count.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    baseline_path: str = ""
    selector: str | None = None
    threshold: int = 10
    wait: WaitStrategy | None = None
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class VisualDiffAction(BaseAction[VisualDiffParams, dict[str, Any]]):
    """Action for comparing a live screenshot against a baseline.

    Captures a screenshot of the current page (or element), loads the baseline,
    and computes pixel-level differences.
    """

    async def execute(self, backend: AbstractBackend) -> dict[str, Any]:
        """Execute the visual diff action.

        Args:
            backend: The browser backend to use.

        Returns:
            Dict with diff_count, diff_percentage, total_pixels, and diff_base64.
        """
        if self.params.url:
            await backend.navigate(self.params.url, self.params.wait)

        if self.params.selector:
            current_bytes = await backend.screenshot_selector(self.params.selector, format="png")
        else:
            current_bytes = await backend.screenshot(ScreenshotParams(url="", format="png"))

        baseline_bytes = await asyncio.to_thread(Path(self.params.baseline_path).read_bytes)

        return self._compare(baseline_bytes, current_bytes)

    def _compare(self, baseline: bytes, current: bytes) -> dict[str, Any]:
        """Compare two PNG byte buffers and return diff metrics.

        Args:
            baseline: Baseline PNG bytes.
            current: Current PNG bytes.

        Returns:
            Dict with diff_count, diff_percentage, total_pixels, and diff_base64.
        """
        try:
            from PIL import Image, ImageChops
        except ImportError:
            return {
                "error": "Pillow is required for visual diff. Install: pip install Pillow",
            }

        baseline_img = Image.open(io.BytesIO(baseline)).convert("RGB")
        current_img = Image.open(io.BytesIO(current)).convert("RGB")

        if baseline_img.size != current_img.size:
            current_img = current_img.resize(baseline_img.size)

        diff = ImageChops.difference(baseline_img, current_img)

        diff_array = list(diff.getdata())  # noqa: SIM118
        total_pixels = len(diff_array)
        diff_count = sum(1 for r, g, b in diff_array if max(r, g, b) > self.params.threshold)

        diff_percentage = (diff_count / total_pixels * 100) if total_pixels else 0.0

        diff_img = diff.convert("L")
        diff_img = diff_img.point(lambda v: 255 if v > self.params.threshold else 0)
        diff_buffer = io.BytesIO()
        diff_img.save(diff_buffer, format="PNG")
        diff_b64 = base64.b64encode(diff_buffer.getvalue()).decode("ascii")

        return {
            "diff_count": diff_count,
            "diff_percentage": round(diff_percentage, 2),
            "total_pixels": total_pixels,
            "threshold": self.params.threshold,
            "diff_base64": diff_b64,
        }
