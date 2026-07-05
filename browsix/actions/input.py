"""Input action for browser interactions (click, type, fill, select, hover, key, drag, tap)."""

from __future__ import annotations

from typing import Any

from browsix.actions.base import BaseAction
from browsix.backend.base import AbstractBackend
from browsix.config import InputParams


class InputAction(BaseAction[InputParams, Any]):
    """Action for performing input interactions on a web page."""

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the input action on the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            None for most actions; the result of the interaction.
        """
        await backend.launch(self.params.browser)
        try:
            await backend.navigate(self.params.url, self.params.wait)
            action = self.params.action
            if action == "click":
                await backend.click(
                    self.params.selector,
                    button=self.params.button,
                    click_count=self.params.click_count,
                )
            elif action == "type":
                await backend.type_text(
                    self.params.selector,
                    self.params.text or "",
                    delay=self.params.delay,
                )
            elif action == "fill":
                await backend.fill(
                    self.params.selector, self.params.value or ""
                )
            elif action == "select":
                await backend.select_option(
                    self.params.selector, self.params.value or ""
                )
            elif action == "hover":
                await backend.hover(self.params.selector)
            elif action == "key":
                await backend.key_press(self.params.key or "Enter")
            elif action == "drag":
                await backend.drag(
                    self.params.source or "", self.params.target or ""
                )
            elif action == "tap":
                await backend.tap(self.params.selector)
            else:
                raise ValueError(f"Unknown input action: {action}")
        finally:
            await backend.close()
        return None
