"""Eval action for executing JavaScript expressions."""

from __future__ import annotations

import asyncio
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import EvalParams
from wavexis.exceptions import WavexisError
from wavexis.output import validate_path

MAX_EXPRESSION_LENGTH = 100_000


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
        if params.url:
            await backend.navigate(params.url, params.wait)

        expression = params.expression
        if params.file:
            file_path = params.file
            try:
                expression = await asyncio.to_thread(
                    lambda: validate_path(file_path).read_text(encoding="utf-8")
                )
            except OSError as e:
                raise WavexisError(f"Failed to read expression file: {e}") from e

        if not expression:
            raise WavexisError("expression or file is required for eval action")
        if len(expression) > MAX_EXPRESSION_LENGTH:
            raise WavexisError(
                f"expression exceeds maximum length of {MAX_EXPRESSION_LENGTH} characters"
            )

        return await backend.eval(expression, await_promise=params.await_promise)
