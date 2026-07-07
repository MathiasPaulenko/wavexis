"""Unit tests for concurrent tab operations (TabHandle, batch --mode tabs, multi --parallel)."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wavexis.backend.base import AbstractBackend


class FakeTabHandle:
    """Fake tab handle for testing — mimics CDPBackend.TabHandle interface."""

    def __init__(self, url: str = "about:blank") -> None:
        self._url = url
        self._closed = False
        self._navigated: list[str] = []

    async def navigate(self, url: str, wait: Any = None) -> None:
        self._navigated.append(url)

    async def eval(self, expression: str, await_promise: bool = False) -> Any:
        return f"eval:{self._url}"

    async def screenshot(self, params: Any) -> bytes:
        return f"screenshot:{self._url}".encode()

    async def close(self) -> None:
        self._closed = True


class FakeBackend:
    """Fake backend that supports new_tab_handle()."""

    def __init__(self) -> None:
        self._tabs_created = 0
        self._tabs: list[FakeTabHandle] = []
        self._launched = False

    async def launch(self, options: Any) -> None:
        self._launched = True

    async def close(self) -> None:
        self._launched = False

    async def new_tab_handle(self, url: str = "about:blank") -> FakeTabHandle:
        self._tabs_created += 1
        tab = FakeTabHandle(url)
        self._tabs.append(tab)
        return tab

    async def navigate(self, url: str, wait: Any = None) -> None:
        pass

    async def eval(self, expression: str, await_promise: bool = False) -> Any:
        return "eval:main"


class TestTabHandleCreation:
    """Tests for new_tab_handle() on backends."""

    @pytest.mark.asyncio
    async def test_abstract_backend_default_raises(self) -> None:
        """AbstractBackend.new_tab_handle() raises NotImplementedError by default."""
        with pytest.raises(NotImplementedError, match="not supported by this backend"):
            await AbstractBackend.new_tab_handle(None, "about:blank")


class TestBatchTabsMode:
    """Tests for batch --mode tabs."""

    @pytest.mark.asyncio
    async def test_batch_tabs_creates_one_backend(self) -> None:
        """batch --mode tabs should create 1 backend and N tab handles."""
        from wavexis.cli._workflow import _batch_tabs

        urls = ["https://a.com", "https://b.com", "https://c.com"]
        fake_backend = FakeBackend()

        with patch("wavexis.cli._workflow._get_backend", return_value=fake_backend), \
             patch("wavexis.cli._workflow._browser_options", return_value=MagicMock()), \
             patch("wavexis.cli._workflow._batch_single_on", new_callable=AsyncMock) as mock_single:

            mock_single.return_value = b"result"

            results = await _batch_tabs(
                urls, "screenshot", MagicMock(), "document.title", 4
            )

            assert len(results) == 3
            assert fake_backend._tabs_created == 3
            assert all(tab._closed for tab in fake_backend._tabs)

    @pytest.mark.asyncio
    async def test_batch_processes_creates_n_backends(self) -> None:
        """batch --mode processes should create N separate backends."""
        from wavexis.cli._workflow import _batch_processes

        urls = ["https://a.com", "https://b.com"]
        call_count = 0

        async def fake_single(url, action, out_dir, expression):
            nonlocal call_count
            call_count += 1
            return f"result:{url}"

        with patch("wavexis.cli._workflow._batch_single", side_effect=fake_single):
            results = await _batch_processes(
                urls, "screenshot", MagicMock(), "document.title", 2
            )

            assert len(results) == 2
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_batch_tabs_semaphore_limits_concurrency(self) -> None:
        """batch --mode tabs with semaphore should limit concurrent tabs."""
        from wavexis.cli._workflow import _batch_tabs

        urls = [f"https://example{i}.com" for i in range(6)]
        fake_backend = FakeBackend()
        concurrent = 0
        max_concurrent = 0
        lock = asyncio.Lock()

        async def track_single(url, action, out_dir, expression, backend):
            nonlocal concurrent, max_concurrent
            async with lock:
                concurrent += 1
                max_concurrent = max(max_concurrent, concurrent)
            await asyncio.sleep(0.05)
            async with lock:
                concurrent -= 1
            return b"ok"

        with patch("wavexis.cli._workflow._get_backend", return_value=fake_backend), \
             patch("wavexis.cli._workflow._browser_options", return_value=MagicMock()), \
             patch("wavexis.cli._workflow._batch_single_on", side_effect=track_single):

            await _batch_tabs(urls, "screenshot", MagicMock(), "document.title", 3)

            assert max_concurrent <= 3


class TestMultiParallel:
    """Tests for multi --parallel using tabs."""

    @pytest.mark.asyncio
    async def test_multi_parallel_uses_tabs(self) -> None:
        """multi --parallel should create a tab per action."""
        from wavexis.multi import execute_actions

        fake_backend = FakeBackend()

        actions = [
            {"screenshot": {"url": "https://a.com"}},
            {"screenshot": {"url": "https://b.com"}},
        ]

        with patch("wavexis.multi._dispatch", new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.return_value = b"result"

            results = await execute_actions(actions, fake_backend, parallel=True)

            assert len(results) == 2
            assert fake_backend._tabs_created == 2
            assert all(tab._closed for tab in fake_backend._tabs)

    @pytest.mark.asyncio
    async def test_multi_sequential_no_tabs(self) -> None:
        """multi sequential should NOT create tabs."""
        from wavexis.multi import execute_actions

        fake_backend = FakeBackend()

        actions = [
            {"screenshot": {"url": "https://a.com"}},
            {"screenshot": {"url": "https://b.com"}},
        ]

        with patch("wavexis.multi._dispatch", new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.return_value = b"result"

            results = await execute_actions(actions, fake_backend, parallel=False)

            assert len(results) == 2
            assert fake_backend._tabs_created == 0


class TestScrapeConcurrency:
    """Tests for scrape --concurrency."""

    @pytest.mark.asyncio
    async def test_scrape_concurrency_uses_tabs(self) -> None:
        """scrape --concurrency N should create N tabs."""
        from wavexis.cli._capture import _scrape

        fake_backend = FakeBackend()

        with patch("wavexis.cli._capture._get_backend", return_value=fake_backend), \
             patch("wavexis.cli._capture._browser_options", return_value=MagicMock()):

            async def fake_execute(self, backend):
                return [{"url": "test", "result": "ok"}]

            with patch("wavexis.actions.scrape.ScrapeAction.execute", fake_execute):
                results = await _scrape(
                    ["https://a.com", "https://b.com"],
                    "document.title",
                    None,
                    None,
                    concurrency=2,
                )

            assert len(results) == 2
            assert fake_backend._tabs_created == 2

    @pytest.mark.asyncio
    async def test_scrape_sequential_no_tabs(self) -> None:
        """scrape with concurrency=1 should NOT create tabs."""
        from wavexis.cli._capture import _scrape

        fake_backend = FakeBackend()

        with patch("wavexis.cli._capture._get_backend", return_value=fake_backend), \
             patch("wavexis.cli._capture._browser_options", return_value=MagicMock()):

            async def fake_execute(self, backend):
                return [{"url": "test", "result": "ok"}]

            with patch("wavexis.actions.scrape.ScrapeAction.execute", fake_execute):
                results = await _scrape(
                    ["https://a.com", "https://b.com"],
                    "document.title",
                    None,
                    None,
                    concurrency=1,
                )

            assert len(results) == 2
            assert fake_backend._tabs_created == 0
