"""Animation control mixin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AnimationBackend(ABC):
    """Animation listing, pause, play, and seek."""

    @abstractmethod
    async def animation_list(self) -> list[dict[str, Any]]:
        """List all active animations on the page.

        Returns:
            List of animation dicts (id, name, state, etc.).
        """

    @abstractmethod
    async def animation_pause(self, animation_id: str) -> None:
        """Pause an animation by ID.

        Args:
            animation_id: The animation ID to pause.
        """

    @abstractmethod
    async def animation_play(self, animation_id: str) -> None:
        """Play/resume an animation by ID.

        Args:
            animation_id: The animation ID to play.
        """

    @abstractmethod
    async def animation_seek(self, animation_id: str, time_ms: int) -> None:
        """Seek an animation to a specific time.

        Args:
            animation_id: The animation ID to seek.
            time_ms: Target time in milliseconds.
        """
