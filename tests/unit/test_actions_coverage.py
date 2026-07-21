"""Unit tests for FormAction, HARAction, and ScrapeAction.

These three actions previously had no dedicated test coverage.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from tests.conftest import MockBackend
from wavexis.actions.form import FormAction, FormParams
from wavexis.actions.har import HARAction
from wavexis.actions.scrape import ScrapeAction
from wavexis.config import HarParams, ScrapeParams
from wavexis.exceptions import WavexisError


@pytest.mark.unit
class TestFormAction:
    """Tests for FormAction.execute."""

    async def test_fill_all_fields_and_submit(self) -> None:
        backend = MockBackend()
        action = FormAction(
            FormParams(
                url="https://example.com/login",
                fields={"#user": "alice", "#pass": "secret"},
                submit="#submit",
            )
        )
        result = await action.execute(backend)

        assert result["fields_filled"] == 2
        assert result["fields_total"] == 2
        assert result["submitted"] is True
        assert result["url"] == "https://example.com/login"
        backend.navigate.assert_awaited_once()
        backend.fill.assert_any_call("#user", "alice")
        backend.fill.assert_any_call("#pass", "secret")
        backend.click.assert_awaited_once_with("#submit")

    async def test_fill_without_submit(self) -> None:
        backend = MockBackend()
        action = FormAction(FormParams(url="https://example.com", fields={"#x": "1"}))
        result = await action.execute(backend)

        assert result["submitted"] is False
        assert result["fields_filled"] == 1
        backend.click.assert_not_awaited()

    async def test_partial_fill_when_field_fails(self) -> None:
        backend = MockBackend()
        backend.fill = AsyncMock(side_effect=[WavexisError("no element"), None])
        action = FormAction(
            FormParams(
                url="https://example.com",
                fields={"#missing": "a", "#present": "b"},
            )
        )
        result = await action.execute(backend)

        assert result["fields_filled"] == 1
        assert result["fields_total"] == 2

    async def test_submit_failure_does_not_raise(self) -> None:
        backend = MockBackend()
        backend.click = AsyncMock(side_effect=WavexisError("no submit button"))
        action = FormAction(
            FormParams(url="https://example.com", fields={"#x": "1"}, submit="#go")
        )
        result = await action.execute(backend)

        assert result["submitted"] is False
        assert result["fields_filled"] == 1

    async def test_empty_fields_dict(self) -> None:
        backend = MockBackend()
        action = FormAction(FormParams(url="https://example.com"))
        result = await action.execute(backend)

        assert result["fields_filled"] == 0
        assert result["fields_total"] == 0
        assert result["submitted"] is False

    async def test_no_url_skips_navigation(self) -> None:
        backend = MockBackend()
        action = FormAction(FormParams(fields={"#x": "1"}))
        await action.execute(backend)
        backend.navigate.assert_not_awaited()


@pytest.mark.unit
class TestHARAction:
    """Tests for HARAction.execute."""

    async def test_basic_har_capture(self) -> None:
        backend = MockBackend()
        backend.capture_har = AsyncMock(
            return_value={"log": {"version": "1.2", "entries": [{"request": {}}]}}
        )
        action = HARAction(HarParams(url="https://example.com"))
        result = await action.execute(backend)

        assert result["log"]["version"] == "1.2"
        assert len(result["log"]["entries"]) == 1
        backend.capture_har.assert_awaited_once()

    async def test_har_with_filter_and_timeout(self) -> None:
        backend = MockBackend()
        backend.capture_har = AsyncMock(return_value={"log": {"entries": []}})
        action = HARAction(
            HarParams(url="https://example.com", filter="*.js", timeout=5000)
        )
        result = await action.execute(backend)

        assert result == {"log": {"entries": []}}
        # Verify the params were passed through
        passed_params = backend.capture_har.await_args.args[0]
        assert passed_params.filter == "*.js"
        assert passed_params.timeout == 5000

    async def test_har_backend_failure_propagates(self) -> None:
        backend = MockBackend()
        backend.capture_har = AsyncMock(side_effect=WavexisError("network error"))
        action = HARAction(HarParams(url="https://example.com"))
        with pytest.raises(WavexisError, match="network error"):
            await action.execute(backend)

    async def test_har_empty_result(self) -> None:
        backend = MockBackend()
        backend.capture_har = AsyncMock(return_value={})
        action = HARAction(HarParams(url="https://example.com"))
        result = await action.execute(backend)
        assert result == {}


@pytest.mark.unit
class TestScrapeAction:
    """Tests for ScrapeAction.execute."""

    async def test_basic_scrape_multiple_urls(self) -> None:
        backend = MockBackend()
        backend.eval = AsyncMock(side_effect=["Title 1", "Title 2"])
        action = ScrapeAction(
            ScrapeParams(
                urls=["https://a.com", "https://b.com"],
                expression="document.title",
            )
        )
        results = await action.execute(backend)

        assert len(results) == 2
        assert results[0] == {"url": "https://a.com", "result": "Title 1"}
        assert results[1] == {"url": "https://b.com", "result": "Title 2"}
        assert backend.navigate.await_count == 2

    async def test_default_expression_when_empty(self) -> None:
        backend = MockBackend()
        backend.eval = AsyncMock(return_value="Default Title")
        action = ScrapeAction(
            ScrapeParams(urls=["https://example.com"], expression="")
        )
        results = await action.execute(backend)

        assert results[0]["result"] == "Default Title"
        # Verify default expression was used
        backend.eval.assert_awaited_with("document.title", await_promise=True)

    async def test_expression_from_file(self, tmp_path: Path) -> None:
        backend = MockBackend()
        backend.eval = AsyncMock(return_value="from-file")
        expr_file = tmp_path / "expr.js"
        expr_file.write_text("document.querySelector('h1').textContent", encoding="utf-8")

        action = ScrapeAction(
            ScrapeParams(urls=["https://example.com"], file=str(expr_file))
        )
        results = await action.execute(backend)

        assert results[0]["result"] == "from-file"
        backend.eval.assert_awaited_with(
            "document.querySelector('h1').textContent", await_promise=True
        )

    async def test_expression_file_unreadable_raises(self, tmp_path: Path) -> None:
        backend = MockBackend()
        missing = tmp_path / "no-such-file.js"
        action = ScrapeAction(
            ScrapeParams(urls=["https://example.com"], file=str(missing))
        )
        with pytest.raises(WavexisError, match="Failed to read scrape expression file"):
            await action.execute(backend)

    async def test_empty_urls_returns_empty_list(self) -> None:
        backend = MockBackend()
        action = ScrapeAction(ScrapeParams(urls=[], expression="document.title"))
        results = await action.execute(backend)
        assert results == []
        backend.navigate.assert_not_awaited()

    async def test_blank_urls_are_skipped(self) -> None:
        backend = MockBackend()
        backend.eval = AsyncMock(return_value="ok")
        action = ScrapeAction(
            ScrapeParams(
                urls=["", "https://example.com", ""],
                expression="document.title",
            )
        )
        results = await action.execute(backend)

        assert len(results) == 1
        assert results[0]["url"] == "https://example.com"
        assert backend.navigate.await_count == 1

    async def test_selector_overrides_wait_strategy(self) -> None:
        backend = MockBackend()
        backend.eval = AsyncMock(return_value="ok")
        action = ScrapeAction(
            ScrapeParams(
                urls=["https://example.com"],
                expression="document.title",
                selector="#loaded",
            )
        )
        await action.execute(backend)

        # Verify navigate was called with a selector wait strategy
        wait_arg = backend.navigate.await_args.args[1]
        assert wait_arg.strategy == "selector"
        assert wait_arg.selector == "#loaded"
