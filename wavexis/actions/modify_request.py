"""Request modification action for intercepting and modifying requests in-flight."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy


@dataclass
class ModifyRequestParams:
    """Parameters for request modification.

    Attributes:
        url: URL to navigate to after setting up interception.
        pattern: Pattern dict with optional keys: urlPattern, resourceType,
            requestStage.
        modifications: Dict with optional keys: headers, url, method, post_data.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    pattern: dict[str, Any] = field(default_factory=dict)
    modifications: dict[str, Any] = field(default_factory=dict)
    wait: WaitStrategy | None = None
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class ModifyRequestAction(BaseAction[ModifyRequestParams, dict[str, Any]]):
    """Action for intercepting and modifying requests in-flight.

    Sets up request interception with the given pattern and modifications,
    then navigates to the URL.
    """

    async def execute(self, backend: AbstractBackend) -> dict[str, Any]:
        """Execute the request modification action.

        Args:
            backend: The browser backend to use.

        Returns:
            Dict with status indicating interception was set up.
        """
        await backend.modify_request(self.params.pattern, self.params.modifications)
        if self.params.url:
            await backend.navigate(self.params.url, self.params.wait)
        return {"status": "ok", "pattern": self.params.pattern}
