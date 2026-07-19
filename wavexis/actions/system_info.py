"""System info action for querying browser system information."""

from __future__ import annotations

from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import SystemInfoParams


class SystemInfoAction(BaseAction[SystemInfoParams, Any]):
    """Action for system info operations."""

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the system info action on the backend.

        Args:
            backend: An AbstractBackend instance.

        Returns:
            Result of the system info operation.
        """
        if self.params.url:
            await backend.navigate(self.params.url, self.params.wait)

        action = self.params.action

        if action == "get-info":
            return await backend.system_info_get_info()

        if action == "get-process-info":
            return await backend.system_info_get_process_info()

        if action == "get-feature-state":
            if not self.params.feature_name:
                raise ValueError("feature_name is required for get-feature-state action")
            return await backend.system_info_get_feature_state(self.params.feature_name)

        raise ValueError(f"Unknown SystemInfo action: {action}")
