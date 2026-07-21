"""Input action for browser interactions (click, type, fill, select, hover, key, drag, tap)."""

from __future__ import annotations

from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import InputParams
from wavexis.exceptions import ActionError


class InputAction(BaseAction[InputParams, Any]):
    """Action for performing input interactions on a web page."""

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the input action on the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            None for most actions; the result of the interaction.
        """
        if self.params.url:
            await backend.navigate(self.params.url, self.params.wait)
        action = self.params.action
        if action == "click":
            if not self.params.selector:
                raise ActionError("selector is required for click action")
            await backend.click(
                self.params.selector,
                button=self.params.button,
                click_count=self.params.click_count,
            )
        elif action == "right_click":
            if not self.params.selector:
                raise ActionError("selector is required for right_click action")
            await backend.right_click(self.params.selector)
        elif action == "double_click":
            if not self.params.selector:
                raise ActionError("selector is required for double_click action")
            await backend.double_click(self.params.selector)
        elif action == "type":
            if not self.params.selector:
                raise ActionError("selector is required for type action")
            await backend.type_text(
                self.params.selector,
                self.params.text or "",
                delay=self.params.delay,
            )
        elif action == "fill":
            if not self.params.selector:
                raise ActionError("selector is required for fill action")
            await backend.fill(self.params.selector, self.params.value or "")
        elif action == "select":
            if not self.params.selector:
                raise ActionError("selector is required for select action")
            await backend.select_option(self.params.selector, self.params.value or "")
        elif action == "hover":
            if not self.params.selector:
                raise ActionError("selector is required for hover action")
            await backend.hover(self.params.selector)
        elif action == "key":
            await backend.key_press(self.params.key or "Enter")
        elif action == "drag":
            if not self.params.source or not self.params.target:
                raise ActionError("source and target are required for drag action")
            await backend.drag(self.params.source, self.params.target)
        elif action == "tap":
            if not self.params.selector:
                raise ActionError("selector is required for tap action")
            await backend.tap(self.params.selector)
        elif action == "scroll":
            await backend.dom_scroll(
                selector=self.params.selector or None,
                x=self.params.scroll_x,
                y=self.params.scroll_y,
            )
        elif action == "upload":
            if not self.params.selector:
                raise ActionError("selector is required for upload action")
            await backend.set_files(self.params.selector, self.params.files or [])
        else:
            raise ActionError(f"Unknown input action: {action}")
        return None
