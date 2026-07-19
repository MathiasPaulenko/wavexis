"""CSS action for inspecting styles, stylesheets, rules, and computed styles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, CSSParams, WaitStrategy


@dataclass
class CSSActionParams:
    """Parameters for CSS inspection operations.

    Attributes:
        url: URL to navigate to before CSS inspection.
        selector: CSS selector for the target element.
        stylesheet_id: Stylesheet ID for rules action.
        action: CSS action — "styles", "stylesheets", "rules", "computed".
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    selector: str | None = None
    stylesheet_id: str | None = None
    action: str = "styles"
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class CSSAction(BaseAction[CSSActionParams, dict[str, Any] | list[dict[str, Any]]]):
    """Action for CSS inspection operations."""

    async def execute(self, backend: AbstractBackend) -> dict[str, Any] | list[dict[str, Any]]:
        """Execute the CSS action on the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            Dict or list of dicts containing CSS data.

        Raises:
            ValueError: If the action is not recognized or required params missing.
        """
        await backend.navigate(self.params.url, self.params.wait)
        return await self._run_action(backend)

    async def _run_action(self, backend: AbstractBackend) -> dict[str, Any] | list[dict[str, Any]]:
        """Execute the CSS action against the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            CSS data as a dict or list of dicts depending on the action.

        Raises:
            ValueError: If required parameters are missing for the action.
        """
        action = self.params.action
        if action == "styles":
            if not self.params.selector:
                raise ValueError("selector is required for styles action")
            return await backend.css_get_styles(self.params.selector)
        if action == "stylesheets":
            return await backend.css_get_stylesheets()
        if action == "rules":
            if not self.params.stylesheet_id:
                raise ValueError("stylesheet_id is required for rules action")
            return await backend.css_get_rules(self.params.stylesheet_id)
        if action == "computed":
            if not self.params.selector:
                raise ValueError("selector is required for computed action")
            return await backend.css_get_computed(self.params.selector)
        raise ValueError(f"Unknown CSS action: {action}")


def css_action_from_config(params: CSSParams) -> CSSAction:
    """Create a CSSAction from CSSParams config dataclass.

    Args:
        params: CSSParams from wavexis.config.

    Returns:
        CSSAction instance with mapped parameters.
    """
    action_params = CSSActionParams(
        url=params.url,
        selector=params.selector,
        stylesheet_id=params.stylesheet_id,
        action=params.action,
        wait=params.wait,
        browser=params.browser,
    )
    return CSSAction(action_params)
