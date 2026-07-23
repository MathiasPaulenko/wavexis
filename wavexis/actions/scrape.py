"""Scrape action for evaluating JS across multiple URLs."""

from __future__ import annotations

import asyncio
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import ScrapeParams, WaitStrategy
from wavexis.exceptions import WavexisError
from wavexis.output import validate_path

MAX_EXPRESSION_LENGTH = 100_000


class ScrapeAction(BaseAction[ScrapeParams, list[dict[str, Any]]]):
    """Action for scraping multiple URLs.

    Iterates over URLs, navigates to each, evaluates an expression,
    and collects results. Supports reading expression from a file via @file syntax.
    """

    async def execute(self, backend: AbstractBackend) -> list[dict[str, Any]]:
        """Execute the scrape action.

        Args:
            backend: The browser backend to use.

        Returns:
            List of result dicts with "url" and "result" keys.
        """
        params = self.params
        expression = params.expression

        if params.file:
            file_path = params.file
            try:
                path = validate_path(file_path)
                if not await asyncio.to_thread(path.is_file):
                    raise WavexisError(
                        f"Failed to read scrape expression file: not a regular file: {file_path}"
                    )
                expression = await asyncio.to_thread(
                    path.read_text, encoding="utf-8"
                )
            except OSError as e:
                raise WavexisError(f"Failed to read scrape expression file: {e}") from e

        if not expression:
            expression = "document.title"
        if len(expression) > MAX_EXPRESSION_LENGTH:
            raise WavexisError(
                f"expression exceeds maximum length of {MAX_EXPRESSION_LENGTH} characters"
            )

        wait = params.wait
        if params.selector:
            wait = WaitStrategy(strategy="selector", selector=params.selector)

        results: list[dict[str, Any]] = []
        for url in params.urls:
            if not url:
                continue
            await backend.navigate(url, wait)
            value = await backend.eval(expression, await_promise=True)
            results.append({"url": url, "result": value})

        return results
