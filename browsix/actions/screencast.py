"""Screencast action for capturing video-like frame sequences."""

from __future__ import annotations

import os

from browsix.actions.base import BaseAction
from browsix.backend.base import AbstractBackend
from browsix.config import ScreencastParams


class ScreencastAction(BaseAction[ScreencastParams, list[str]]):
    """Action for capturing screencast frames and saving them to a directory."""

    def __init__(self, params: ScreencastParams, output_dir: str = "screencast") -> None:
        """Initialize the screencast action.

        Args:
            params: Screencast parameters including URL, format, and duration.
            output_dir: Directory to save captured frames.
        """
        self.params = params
        self._output_dir = output_dir

    async def execute(self, backend: AbstractBackend) -> list[str]:
        """Execute the screencast capture on the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            List of saved frame file paths.
        """
        await backend.launch(self.params.browser)
        try:
            await backend.navigate(self.params.url, self.params.wait)
            frames = await backend.screencast(self.params)
        finally:
            await backend.close()

        os.makedirs(self._output_dir, exist_ok=True)
        saved: list[str] = []
        for i, frame in enumerate(frames):
            ext = "png" if self.params.format == "png" else "jpg"
            fname = f"frame_{i:05d}.{ext}"
            fpath = os.path.join(self._output_dir, fname)
            with open(fpath, "wb") as f:  # noqa: ASYNC230
                f.write(frame)
            saved.append(fpath)
        return saved
