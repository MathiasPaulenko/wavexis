"""Screencast action for capturing video-like frame sequences."""

from __future__ import annotations

import asyncio
from pathlib import Path

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import ScreencastParams


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
        await backend.navigate(self.params.url, self.params.wait)
        frames = await backend.screencast(self.params)

        await asyncio.to_thread(lambda: Path(self._output_dir).mkdir(parents=True, exist_ok=True))
        saved: list[str] = []
        for i, frame in enumerate(frames):
            ext = "png" if self.params.format == "png" else "jpg"
            fname = f"frame_{i:05d}.{ext}"
            fpath = str(Path(self._output_dir) / fname)
            await asyncio.to_thread(Path(fpath).write_bytes, frame)
            saved.append(fpath)
        return saved
