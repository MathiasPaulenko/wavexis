"""Scrape action for evaluating JS across multiple URLs."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import ScrapeParams, WaitStrategy


class ScrapeAction(BaseAction[ScrapeParams, list[dict[str, Any]]]):
    """Action for scraping multiple URLs.

    Iterates over URLs, navigates to each, evaluates an expression,
    and collects results. Supports reading expression from a file via @file syntax.
    """

    async def execute(
        self, backend: AbstractBackend
    ) -> list[dict[str, Any]]:
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
            expression = await asyncio.to_thread(
                lambda: Path(file_path).read_text(encoding="utf-8")
            )

        if not expression:
            expression = "document.title"

        wait = params.wait
        if params.selector:
            wait = WaitStrategy(strategy="selector", selector=params.selector)

        results: list[dict[str, Any]] = []
        for url in params.urls:
            await backend.navigate(url, wait)
            value = await backend.eval(expression, await_promise=True)
            results.append({"url": url, "result": value})

        return results
