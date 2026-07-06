"""WebAudio action for listing audio contexts (experimental)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy


@dataclass
class WebAudioParams:
    """Parameters for WebAudio operations.

    Attributes:
        url: URL to navigate to before WebAudio operations.
        action: WebAudio action — "list", "get".
        context_id: Audio context ID for "get" action.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    action: str = "list"
    context_id: str | None = None
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class WebAudioAction(BaseAction[WebAudioParams, Any]):
    """Action for WebAudio operations (experimental)."""

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the WebAudio action on the backend.

        Args:
            backend: An AbstractBackend instance.

        Returns:
            Result of the WebAudio operation.
        """
        try:
            await backend.launch(self.params.browser)
            if self.params.url:
                await backend.navigate(self.params.url, self.params.wait)

            action = self.params.action

            if action == "list":
                return await backend.webaudio_get_contexts()

            if action == "get":
                if not self.params.context_id:
                    raise ValueError("context_id is required for get action")
                return await backend.webaudio_get_context(self.params.context_id)

            raise ValueError(f"Unknown WebAudio action: {action}")

        finally:
            await backend.close()
