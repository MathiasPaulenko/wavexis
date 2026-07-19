"""Crawl action for spidering a website with depth limit."""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import WaitStrategy
from wavexis.exceptions import WavexisError


@dataclass
class CrawlParams:
    """Parameters for crawling a website.

    Attributes:
        start_url: Starting URL for the crawl.
        max_depth: Maximum crawl depth (1 = start page only, 2 = start + links).
        max_pages: Maximum number of pages to visit.
        same_origin: If True, only crawl links on the same origin.
        url_pattern: Regex pattern to filter URLs (empty = all).
        wait: Wait strategy after each navigation.
    """

    start_url: str = ""
    max_depth: int = 2
    max_pages: int = 50
    same_origin: bool = True
    url_pattern: str = ""
    wait: WaitStrategy = field(default_factory=WaitStrategy)


class CrawlAction(BaseAction[CrawlParams, list[dict[str, Any]]]):
    """Action for crawling a website and collecting page data."""

    async def execute(self, backend: AbstractBackend) -> list[dict[str, Any]]:
        """Execute the crawl on the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            List of page dicts with url, title, links, and depth.
        """
        results: list[dict[str, Any]] = []
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(self.params.start_url, 0)]
        origin = urlparse(self.params.start_url).netloc
        pattern = None
        if self.params.url_pattern:
            try:
                pattern = re.compile(self.params.url_pattern)
            except re.error as e:
                raise WavexisError(f"Invalid url_pattern regex: {e}") from e

        while queue and len(results) < self.params.max_pages:
            url, depth = queue.pop(0)
            normalized = url.rstrip("/")
            if normalized in visited or depth > self.params.max_depth:
                continue
            visited.add(normalized)

            try:
                await backend.navigate(url, self.params.wait)
            except WavexisError:
                continue

            title = ""
            links: list[str] = []
            with contextlib.suppress(WavexisError):
                title = await backend.eval("document.title", await_promise=False)
            with contextlib.suppress(WavexisError):
                raw_links = await backend.eval(
                    "Array.from(document.querySelectorAll('a[href]')).map(a => a.href)",
                    await_promise=False,
                )
                if isinstance(raw_links, list):
                    links = [str(link) for link in raw_links if isinstance(link, str)]

            page_data: dict[str, Any] = {
                "url": url,
                "title": title,
                "depth": depth,
                "links_found": len(links),
            }
            results.append(page_data)

            if depth < self.params.max_depth:
                for link in links:
                    absolute = urljoin(url, link)
                    parsed = urlparse(absolute)
                    if parsed.scheme not in ("http", "https"):
                        continue
                    if self.params.same_origin and parsed.netloc != origin:
                        continue
                    if pattern and not pattern.search(absolute):
                        continue
                    norm = absolute.rstrip("/")
                    if norm not in visited:
                        queue.append((absolute, depth + 1))

        return results
