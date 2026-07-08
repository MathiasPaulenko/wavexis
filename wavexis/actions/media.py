"""Media action for listing media players and messages (experimental)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy


@dataclass
class MediaParams:
    """Parameters for Media operations.

    Attributes:
        url: URL to navigate to before Media operations.
        action: Media action — "list", "messages".
        player_id: Media player ID for "messages" action.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    action: str = "list"
    player_id: str | None = None
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class MediaAction(BaseAction[MediaParams, Any]):
    """Action for Media operations (experimental)."""

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the Media action on the backend.

        Args:
            backend: An AbstractBackend instance.

        Returns:
            Result of the Media operation.
        """
        if self.params.url:
            await backend.navigate(self.params.url, self.params.wait)

        action = self.params.action

        if action == "list":
            return await backend.media_get_players()

        if action == "messages":
            if not self.params.player_id:
                raise ValueError("player_id is required for messages action")
            return await backend.media_get_messages(self.params.player_id)

        raise ValueError(f"Unknown Media action: {action}")
