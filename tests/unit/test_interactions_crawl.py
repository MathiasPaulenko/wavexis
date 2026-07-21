"""Unit tests for input scroll, upload, and crawl action."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.actions.crawl import CrawlAction, CrawlParams
from wavexis.actions.input import InputAction
from wavexis.config import InputParams, WaitStrategy
from wavexis.exceptions import WavexisError

pytestmark = pytest.mark.unit


class TestScrollAction:
    """Tests for input scroll action dispatch."""

    def test_scroll_params_defaults(self) -> None:
        params = InputParams(action="scroll")
        assert params.scroll_x == 0
        assert params.scroll_y == 0

    def test_scroll_params_with_offset(self) -> None:
        params = InputParams(action="scroll", scroll_x=100, scroll_y=500)
        assert params.scroll_x == 100
        assert params.scroll_y == 500

    async def test_scroll_by_offset(self) -> None:
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.close = AsyncMock()
        backend.dom_scroll = AsyncMock()

        params = InputParams(
            url="https://example.com",
            action="scroll",
            scroll_x=0,
            scroll_y=500,
            wait=WaitStrategy(strategy="load"),
        )
        await InputAction(params).execute(backend)

        backend.dom_scroll.assert_called_once_with(selector=None, x=0, y=500)

    async def test_scroll_to_selector(self) -> None:
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.close = AsyncMock()
        backend.dom_scroll = AsyncMock()

        params = InputParams(
            url="https://example.com",
            action="scroll",
            selector="#footer",
            wait=WaitStrategy(strategy="load"),
        )
        await InputAction(params).execute(backend)

        backend.dom_scroll.assert_called_once_with(selector="#footer", x=0, y=0)


class TestUploadAction:
    """Tests for input upload action dispatch."""

    def test_upload_params_defaults(self) -> None:
        params = InputParams(action="upload")
        assert params.files is None

    def test_upload_params_with_files(self) -> None:
        params = InputParams(
            action="upload",
            files=["/path/to/file1.pdf", "/path/to/file2.pdf"],
        )
        assert params.files == ["/path/to/file1.pdf", "/path/to/file2.pdf"]

    async def test_upload_executes_set_files(self) -> None:
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.close = AsyncMock()
        backend.set_files = AsyncMock()

        params = InputParams(
            url="https://example.com/upload",
            action="upload",
            selector="#file-input",
            files=["/abs/path/file.pdf"],
            wait=WaitStrategy(strategy="load"),
        )
        await InputAction(params).execute(backend)

        backend.set_files.assert_called_once_with("#file-input", ["/abs/path/file.pdf"])


class TestCrawlParams:
    """Tests for CrawlParams dataclass."""

    def test_defaults(self) -> None:
        params = CrawlParams()
        assert params.start_url == ""
        assert params.max_depth == 2
        assert params.max_pages == 50
        assert params.same_origin is True
        assert params.url_pattern == ""

    def test_custom_params(self) -> None:
        params = CrawlParams(
            start_url="https://example.com",
            max_depth=5,
            max_pages=200,
            same_origin=False,
            url_pattern=".*blog.*",
        )
        assert params.start_url == "https://example.com"
        assert params.max_depth == 5
        assert params.max_pages == 200
        assert params.same_origin is False
        assert params.url_pattern == ".*blog.*"


class TestCrawlAction:
    """Tests for CrawlAction execution."""

    async def test_crawl_single_page(self) -> None:
        backend = MagicMock()
        backend.navigate = AsyncMock()
        backend.eval = AsyncMock(
            side_effect=[
                "Example Page",
                ["https://example.com/about", "https://other.com/"],
            ]
        )

        params = CrawlParams(
            start_url="https://example.com",
            max_depth=0,
            max_pages=10,
            same_origin=True,
        )
        action = CrawlAction(params)
        results = await action.execute(backend)

        assert len(results) == 1
        assert results[0]["url"] == "https://example.com"
        assert results[0]["title"] == "Example Page"
        assert results[0]["depth"] == 0
        assert results[0]["links_found"] == 2

    async def test_crawl_respects_max_depth(self) -> None:
        backend = MagicMock()
        backend.navigate = AsyncMock()
        backend.eval = AsyncMock(
            side_effect=[
                "Page 1",
                ["https://example.com/page2"],
                "Page 2",
                ["https://example.com/page3"],
            ]
        )

        params = CrawlParams(
            start_url="https://example.com",
            max_depth=0,
            max_pages=10,
            same_origin=True,
        )
        action = CrawlAction(params)
        results = await action.execute(backend)

        assert len(results) == 1
        assert results[0]["url"] == "https://example.com"

    async def test_crawl_same_origin_filter(self) -> None:
        backend = MagicMock()
        backend.navigate = AsyncMock()
        backend.eval = AsyncMock(
            side_effect=[
                "Page 1",
                ["https://example.com/about", "https://other.com/page"],
                "About",
                [],
            ]
        )

        params = CrawlParams(
            start_url="https://example.com",
            max_depth=2,
            max_pages=10,
            same_origin=True,
        )
        action = CrawlAction(params)
        results = await action.execute(backend)

        assert len(results) >= 1
        for page in results:
            assert "other.com" not in page["url"]

    async def test_crawl_url_pattern_filter(self) -> None:
        backend = MagicMock()
        backend.navigate = AsyncMock()
        backend.eval = AsyncMock(
            side_effect=[
                "Blog",
                ["https://example.com/blog/post1", "https://example.com/about"],
                "Blog Post 1",
                [],
            ]
        )

        params = CrawlParams(
            start_url="https://example.com",
            max_depth=2,
            max_pages=10,
            same_origin=True,
            url_pattern=".*blog.*",
        )
        action = CrawlAction(params)
        results = await action.execute(backend)

        assert len(results) >= 1
        for page in results:
            assert "blog" in page["url"] or page["url"] == "https://example.com"

    async def test_crawl_max_pages_limit(self) -> None:
        backend = MagicMock()
        backend.navigate = AsyncMock()
        backend.eval = AsyncMock(side_effect=["Page", []])

        params = CrawlParams(
            start_url="https://example.com",
            max_depth=5,
            max_pages=1,
            same_origin=True,
        )
        action = CrawlAction(params)
        results = await action.execute(backend)

        assert len(results) <= 1

    async def test_crawl_handles_navigation_error(self) -> None:
        backend = MagicMock()
        backend.navigate = AsyncMock(side_effect=WavexisError("Network error"))
        backend.eval = AsyncMock()

        params = CrawlParams(
            start_url="https://example.com",
            max_depth=1,
            max_pages=10,
        )
        action = CrawlAction(params)
        results = await action.execute(backend)

        assert len(results) == 0

    async def test_crawl_invalid_regex_pattern(self) -> None:
        """Test that invalid url_pattern regex raises WavexisError."""
        backend = MagicMock()
        backend.navigate = AsyncMock()
        backend.eval = AsyncMock(return_value=None)

        params = CrawlParams(
            start_url="https://example.com",
            url_pattern="[unclosed",
            max_depth=1,
            max_pages=10,
        )
        action = CrawlAction(params)
        with pytest.raises(WavexisError, match="Invalid url_pattern regex"):
            await action.execute(backend)

    async def test_crawl_uses_deque_for_bfs_queue(self) -> None:
        """Regression: crawl must use collections.deque for O(1) popleft.

        Previously used list.pop(0) which is O(n) per iteration — slow for
        large crawls. This test verifies the queue is a deque and that a
        breadth-first traversal order is preserved.
        """
        from collections import deque

        backend = MagicMock()
        backend.navigate = AsyncMock()
        # Page 1 links to page2 and page3; page2 links to page4.
        backend.eval = AsyncMock(
            side_effect=[
                "Page 1",
                ["https://example.com/page2", "https://example.com/page3"],
                "Page 2",
                ["https://example.com/page4"],
                "Page 3",
                [],
                "Page 4",
                [],
            ]
        )

        params = CrawlParams(
            start_url="https://example.com",
            max_depth=2,
            max_pages=10,
            same_origin=True,
        )
        action = CrawlAction(params)
        results = await action.execute(backend)

        urls = [r["url"] for r in results]
        # BFS order: root, then page2, page3 (depth 1), then page4 (depth 2).
        assert urls == [
            "https://example.com",
            "https://example.com/page2",
            "https://example.com/page3",
            "https://example.com/page4",
        ]
        # Sanity check: the action imports deque (regression guard for the
        # list.pop(0) -> deque.popleft fix).
        import wavexis.actions.crawl as crawl_mod

        assert hasattr(crawl_mod, "deque")
        assert crawl_mod.deque is deque
