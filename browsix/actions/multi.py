"""Multi-action: parse YAML and execute multiple actions on a single backend."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from browsix.actions.base import BaseAction
from browsix.backend.base import AbstractBackend
from browsix.multi import execute_actions, parse_yaml


class MultiAction(BaseAction[Path, list[Any]]):
    """Action that parses a YAML config and executes multiple actions sequentially.

    Reuses a single backend instance for all actions.
    """

    async def execute(self, backend: AbstractBackend) -> list[Any]:
        """Parse the YAML config and execute all actions on the backend.

        Args:
            backend: An already-launched AbstractBackend instance.

        Returns:
            List of results from each action.
        """
        actions = parse_yaml(self.params)
        return await execute_actions(actions, backend)
