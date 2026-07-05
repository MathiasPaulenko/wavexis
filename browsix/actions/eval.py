"""Eval action for executing JavaScript expressions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from browsix.actions.base import BaseAction
from browsix.backend.base import AbstractBackend
from browsix.config import EvalParams


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
            expression = Path(params.file).read_text(encoding="utf-8")  # noqa: ASYNC240

        return await backend.eval(expression, await_promise=params.await_promise)
