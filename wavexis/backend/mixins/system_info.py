"""SystemInfo mixin — browser system information."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SystemInfoBackend(ABC):
    """System information operations."""

    @abstractmethod
    async def system_info_get_info(self) -> dict[str, Any]:
        """Get system info (OS, GPU, model, etc.).

        Returns:
            Dict with system information fields.
        """

    @abstractmethod
    async def system_info_get_process_info(self) -> dict[str, Any]:
        """Get process info for the browser.

        Returns:
            The command result with a ``processInfo`` list.
        """

    @abstractmethod
    async def system_info_get_feature_state(self, feature_name: str) -> dict[str, Any]:
        """Get the state of a specific feature.

        Args:
            feature_name: The feature name to query.

        Returns:
            Dict with feature state information.
        """
