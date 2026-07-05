"""Dialog action for accepting or dismissing JavaScript dialogs."""

from __future__ import annotations

from typing import Any

from browsix.actions.base import BaseAction
from browsix.backend.base import AbstractBackend
from browsix.config import BrowserOptions, WaitStrategy


class DialogAction(BaseAction[str, None]):
    """Action for handling JavaScript dialogs (alert, confirm, prompt)."""

    def __init__(
        self,
        params: str,
        action: str = "accept",
        prompt_text: str | None = None,
        url: str = "",
        wait: WaitStrategy | None = None,
    ) -> None:
        """Initialize the dialog action.

        Args:
            params: Dialog parameters or selector.
            action: Dialog action ("accept" or "dismiss").
            prompt_text: Text to enter in prompt dialogs.
            url: URL to navigate to before the action.
            wait: Wait strategy after navigation.
        """
        self.params = params
        self._action = action
        self._prompt_text = prompt_text
        self._url = url
        self._wait = wait or WaitStrategy(strategy="load")

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the dialog action on the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            None.
        """
        await backend.launch(BrowserOptions())
        try:
            if self._url:
                await backend.navigate(self._url, self._wait)
            if self._action == "accept":
                await backend.dialog_accept(self._prompt_text)
            elif self._action == "dismiss":
                await backend.dialog_dismiss()
            else:
                raise ValueError(f"Unknown dialog action: {self._action}")
        finally:
            await backend.close()
        return None
