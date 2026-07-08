"""axe-core accessibility audit action."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy


@dataclass
class AxeAuditParams:
    """Parameters for axe-core accessibility audit.

    Attributes:
        url: URL to navigate to before running the audit.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    wait: WaitStrategy | None = None
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class AxeAuditAction(BaseAction[AxeAuditParams, dict[str, Any]]):
    """Action for running axe-core accessibility audit.

    Navigates to the URL, injects axe-core, and runs the audit.
    Returns violations, passes, incomplete, and inapplicable results.
    """

    async def execute(self, backend: AbstractBackend) -> dict[str, Any]:
        """Execute the axe-core audit action.

        Args:
            backend: The browser backend to use.

        Returns:
            Dict with violations, passes, incomplete, and inapplicable lists.
        """
        if self.params.url:
            await backend.navigate(self.params.url, self.params.wait)
        return await backend.axe_audit()
