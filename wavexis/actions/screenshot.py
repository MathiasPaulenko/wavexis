"""Screenshot action for capturing page screenshots."""

from __future__ import annotations

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import ScreenshotParams


class ScreenshotAction(BaseAction[ScreenshotParams, bytes]):
    """Action for taking a screenshot of a web page.

    Navigates to the URL in params, optionally executes JS, and captures
    a screenshot.
    """

    async def execute(self, backend: AbstractBackend) -> bytes:
        """Execute the screenshot action.

        Args:
            backend: The browser backend to use.

        Returns:
            Screenshot image bytes.
        """
        params = self.params
        await backend.navigate(params.url, params.wait)

        if params.js:
            await backend.eval(params.js, await_promise=True)

        if params.selector:
            return await backend.screenshot_selector(params.selector, params.format, params.quality)

        return await backend.screenshot(params)
