"""Animation action for listing, pausing, playing, and seeking animations."""

from __future__ import annotations

from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import AnimationParams


class AnimationAction(BaseAction[AnimationParams, Any]):
    """Action for animation operations."""

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the animation action on the backend.

        Args:
            backend: An AbstractBackend instance.

        Returns:
            Result of the animation operation.
        """
        try:
            await backend.launch(self.params.browser)
            if self.params.url:
                await backend.navigate(self.params.url, self.params.wait)

            action = self.params.action

            if action == "list":
                return await backend.animation_list()

            if action == "pause":
                if not self.params.animation_id:
                    raise ValueError("animation_id is required for pause action")
                await backend.animation_pause(self.params.animation_id)
                return None

            if action == "play":
                if not self.params.animation_id:
                    raise ValueError("animation_id is required for play action")
                await backend.animation_play(self.params.animation_id)
                return None

            if action == "seek":
                if not self.params.animation_id or self.params.time_ms is None:
                    raise ValueError(
                        "animation_id and time_ms are required for seek action"
                    )
                await backend.animation_seek(
                    self.params.animation_id, self.params.time_ms
                )
                return None

            raise ValueError(f"Unknown animation action: {action}")

        finally:
            await backend.close()
