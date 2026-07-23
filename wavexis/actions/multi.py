"""Multi-action: parse YAML and execute multiple actions on a single backend."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.multi import execute_actions, parse_yaml


class MultiAction(BaseAction[Path, list[Any]]):
    """Action that parses a YAML config and executes multiple actions.

    Reuses a single backend instance for all actions. Supports both
    sequential (default) and parallel execution modes.
    """

    def __init__(self, params: Path, parallel: bool = False) -> None:
        """Initialize the multi-action.

        Args:
            params: Path to the YAML config file.
            parallel: If True, execute actions concurrently.
        """
        super().__init__(params)
        self._parallel = parallel

    async def execute(self, backend: AbstractBackend) -> list[Any]:
        """Parse the YAML config and execute all actions on the backend.

        Args:
            backend: An already-launched AbstractBackend instance.

        Returns:
            List of results from each action.
        """
        actions = await asyncio.to_thread(parse_yaml, self.params)
        return await execute_actions(actions, backend, parallel=self._parallel)
