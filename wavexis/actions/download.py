"""Download action for intercepting file downloads."""

from __future__ import annotations

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import WaitStrategy


class DownloadAction(BaseAction[str, bytes]):
    """Action for intercepting file downloads."""

    def __init__(
        self,
        params: str,
        url: str = "",
        wait: WaitStrategy | None = None,
    ) -> None:
        """Initialize the download action.

        Args:
            params: Download parameters or URL filter.
            url: URL to navigate to before intercepting downloads.
            wait: Wait strategy after navigation.
        """
        self.params = params
        self._url = url
        self._wait = wait or WaitStrategy(strategy="load")

    async def execute(self, backend: AbstractBackend) -> bytes:
        """Execute the download interception on the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            Downloaded file bytes.
        """
        if self._url:
            await backend.navigate(self._url, self._wait)
        return await backend.intercept_download(self.params)
