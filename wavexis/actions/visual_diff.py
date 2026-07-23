"""Visual diff action for comparing two screenshots and reporting differences."""

from __future__ import annotations

import asyncio
import base64
import io
from dataclasses import dataclass, field
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, ScreenshotParams, WaitStrategy
from wavexis.exceptions import ActionError
from wavexis.output import validate_path


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

        Raises:
            ActionError: If baseline_path is missing, the baseline image does not
                exist, or the threshold is out of range.
        """
        if not self.params.baseline_path:
            raise ActionError("baseline_path is required for visual diff")

        if not 0 <= self.params.threshold <= 255:
            raise ActionError(f"threshold must be between 0 and 255, got {self.params.threshold}")

        baseline_path = validate_path(self.params.baseline_path)
        if not await asyncio.to_thread(baseline_path.is_file):
            raise ActionError(f"Baseline image not found: {self.params.baseline_path}")

        if self.params.url:
            await backend.navigate(self.params.url, self.params.wait)

        if self.params.selector:
            current_bytes = await backend.screenshot_selector(self.params.selector, format="png")
        else:
            current_bytes = await backend.screenshot(ScreenshotParams(url="", format="png"))

        baseline_bytes = await asyncio.to_thread(baseline_path.read_bytes)

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

        try:
            baseline_img = Image.open(io.BytesIO(baseline)).convert("RGB")
            current_img = Image.open(io.BytesIO(current)).convert("RGB")
        except Exception as exc:
            return {"error": f"Failed to decode image: {exc}"}

        if baseline_img.size != current_img.size:
            current_img = current_img.resize(baseline_img.size)

        diff = ImageChops.difference(baseline_img, current_img)

        diff_bytes = diff.tobytes()
        total_pixels = len(diff_bytes) // 3
        diff_count = sum(
            1
            for i in range(0, len(diff_bytes), 3)
            if max(diff_bytes[i], diff_bytes[i + 1], diff_bytes[i + 2]) > self.params.threshold
        )

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
