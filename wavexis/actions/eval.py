"""Eval action for executing JavaScript expressions."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import EvalParams


class EvalAction(BaseAction[EvalParams, Any]):
    """Action for evaluating a JavaScript expression on a web page.

    Navigates to the URL in params, then evaluates the expression.
    Supports @file syntax to read expression from a file.
    """

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the eval action.

        Args:
            backend: The browser backend to use.

        Returns:
            The JavaScript evaluation result.
        """
        params = self.params
        await backend.navigate(params.url, params.wait)

        expression = params.expression
        if params.file:
            file_path = params.file
            expression = await asyncio.to_thread(
                lambda: Path(file_path).read_text(encoding="utf-8")
            )

        return await backend.eval(expression, await_promise=params.await_promise)
