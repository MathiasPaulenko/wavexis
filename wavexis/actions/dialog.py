"""Dialog action for accepting or dismissing JavaScript dialogs."""

from __future__ import annotations

import asyncio
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import WaitStrategy
from wavexis.exceptions import ActionError, WavexisError


class DialogAction(BaseAction[str, None]):
    """Action for handling JavaScript dialogs (alert, confirm, prompt)."""

    def __init__(
        self,
        params: str,
        action: str = "accept",
        prompt_text: str | None = None,
        url: str = "",
        wait: WaitStrategy | None = None,
        timeout: float | None = None,
    ) -> None:
        """Initialize the dialog action.

        Args:
            params: Dialog parameters or selector.
            action: Dialog action ("accept" or "dismiss").
            prompt_text: Text to enter in prompt dialogs.
            url: URL to navigate to before the action.
            wait: Wait strategy after navigation.
            timeout: Seconds to wait for a dialog to open before handling it.
                When ``None``, the dialog is handled immediately without
                waiting (legacy behaviour).
        """
        self.params = params
        self._action = action
        self._prompt_text = prompt_text
        self._url = url
        self._wait = wait or WaitStrategy(strategy="load")
        self._timeout = timeout

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the dialog action on the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            None.

        Raises:
            WavexisError: If no dialog opens within the configured timeout.
            ActionError: If the action is not ``accept`` or ``dismiss``.
        """
        if self._url and self._timeout is not None:
            await self._navigate_and_wait_for_dialog(backend)
        elif self._url:
            await backend.navigate(self._url, self._wait)

        if self._action == "accept":
            await backend.dialog_accept(self._prompt_text)
        elif self._action == "dismiss":
            await backend.dialog_dismiss()
        else:
            raise ActionError(f"Unknown dialog action: {self._action}")
        return None

    async def _navigate_and_wait_for_dialog(self, backend: AbstractBackend) -> None:
        """Enable Page events, navigate, and wait for a dialog to open.

        The Page domain is enabled and the dialog-event listener is
        registered **before** navigation so the event is not missed.

        Args:
            backend: The browser backend to use.

        Raises:
            WavexisError: If no dialog opens within the configured timeout.
        """
        await backend.page_enable()
        timeout = self._timeout
        assert timeout is not None  # narrowed by caller
        wait_task = asyncio.create_task(
            backend.dialog_wait_for_opening(timeout)
        )
        # Yield so the task registers its event handler before navigation.
        await asyncio.sleep(0)
        await backend.navigate(self._url, self._wait)
        try:
            await wait_task
        except TimeoutError:
            raise WavexisError(
                f"No JavaScript dialog opened within {self._timeout:.1f}s. "
                "Verify the page triggers a dialog (alert, confirm, prompt) "
                "or increase --timeout."
            ) from None
