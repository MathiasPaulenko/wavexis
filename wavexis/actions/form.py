"""Form action for auto-filling and submitting forms from JSON data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy
from wavexis.exceptions import WavexisError


@dataclass
class FormParams:
    """Parameters for form auto-fill.

    Attributes:
        url: URL to navigate to.
        fields: Dict mapping CSS selectors to values to fill.
        submit: Optional CSS selector for submit button to click after filling.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    fields: dict[str, str] = field(default_factory=dict)
    submit: str | None = None
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class FormAction(BaseAction[FormParams, dict[str, Any]]):
    """Action for filling form fields and optionally submitting."""

    async def execute(
        self, backend: AbstractBackend
    ) -> dict[str, Any]:
        """Execute the form fill on the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            Dict with filled count and submit status.
        """
        await backend.navigate(self.params.url, self.params.wait)

        filled = 0
        for selector, value in self.params.fields.items():
            try:
                await backend.fill(selector, value)
                filled += 1
            except WavexisError:
                pass

        submitted = False
        if self.params.submit:
            try:
                await backend.click(self.params.submit)
                submitted = True
            except WavexisError:
                pass

        return {
            "url": self.params.url,
            "fields_filled": filled,
            "fields_total": len(self.params.fields),
            "submitted": submitted,
        }
