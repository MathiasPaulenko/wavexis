"""HAR replay action for replaying network requests from a HAR file."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy
from wavexis.exceptions import ActionError
from wavexis.output import validate_path


@dataclass
class HARReplayParams:
    """Parameters for HAR replay.

    Attributes:
        har_path: Path to the HAR file to replay.
        url_filter: Optional URL pattern to filter which entries to replay.
        url: URL to navigate to before replaying.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    har_path: str = ""
    url_filter: str = ""
    url: str = ""
    wait: WaitStrategy | None = None
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class HARReplayAction(BaseAction[HARReplayParams, dict[str, Any]]):
    """Action for replaying network requests from a HAR file.

    Navigates to the URL, then replays each request from the HAR file
    using the browser's fetch API.
    """

    async def execute(self, backend: AbstractBackend) -> dict[str, Any]:
        """Execute the HAR replay action.

        Args:
            backend: The browser backend to use.

        Returns:
            Dict with replayed count and any errors.
        """
        if not self.params.har_path:
            raise ActionError("har_path is required for har_replay action")
        har_path = validate_path(self.params.har_path)
        if not await asyncio.to_thread(har_path.is_file):
            raise ActionError(f"HAR file not found: {self.params.har_path}")
        if self.params.url:
            await backend.navigate(self.params.url, self.params.wait)
        await backend.replay_har(str(har_path), self.params.url_filter)
        return {"status": "ok", "har_path": self.params.har_path}
