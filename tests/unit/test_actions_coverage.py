"""Unit tests for actions that previously lacked coverage."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from wavexis.actions.axe_audit import AxeAuditAction, AxeAuditParams
from wavexis.actions.bluetooth import BluetoothAction, BluetoothParams
from wavexis.actions.cast import CastAction, CastParams
from wavexis.actions.crawl import CrawlAction, CrawlParams
from wavexis.actions.download import DownloadAction
from wavexis.actions.extract import ExtractAction, ExtractParams
from wavexis.actions.form import FormAction, FormParams
from wavexis.actions.har_replay import HARReplayAction, HARReplayParams
from wavexis.actions.lighthouse import LighthouseAction, LighthouseParams
from wavexis.actions.session import SessionData, SessionLoadAction, SessionSaveAction
from wavexis.actions.tabs import TabsAction, TabsParams
from wavexis.actions.visual_diff import VisualDiffAction, VisualDiffParams
from wavexis.config import WaitStrategy
from wavexis.exceptions import ActionError


@pytest.fixture
def backend() -> AsyncMock:
    """Return a mock backend with all async methods stubbed."""
    mock = AsyncMock()
    mock.navigate = AsyncMock()
    mock.axe_audit = AsyncMock(return_value={"violations": []})
    mock.bluetooth_emulate = AsyncMock()
    mock.bluetooth_stop = AsyncMock()
    mock.cast_list = AsyncMock(return_value=[])
    mock.cast_start_tab = AsyncMock()
    mock.cast_stop = AsyncMock()
    mock.cast_enable = AsyncMock()
    mock.cast_disable = AsyncMock()
    mock.cast_set_sink_to_use = AsyncMock()
    mock.cast_start_desktop_mirroring = AsyncMock()
    mock.cast_start_tab_mirroring = AsyncMock()
    mock.cast_stop_casting = AsyncMock()
    mock.eval = AsyncMock(return_value="")
    mock.fill = AsyncMock()
    mock.click = AsyncMock()
    mock.get_cookies = AsyncMock(return_value=[])
    mock.storage_list = AsyncMock(return_value={})
    mock.storage_set = AsyncMock()
    mock.list_tabs = AsyncMock(return_value=[])
    mock.new_tab = AsyncMock(return_value="tab-1")
    mock.close_tab = AsyncMock()
    mock.activate_tab = AsyncMock()
    mock.perf_metrics = AsyncMock(return_value={})
    mock.capture_console = AsyncMock(return_value=[])
    mock.screenshot = AsyncMock(return_value=b"png")
    mock.screenshot_selector = AsyncMock(return_value=b"png")
    mock.intercept_download = AsyncMock(return_value=b"data")
    mock.replay_har = AsyncMock()
    mock.set_cookie = AsyncMock()
    return mock


@pytest.mark.unit
class TestAxeAuditAction:
    """Tests for AxeAuditAction."""

    async def test_executes_axe_audit(self, backend: AsyncMock) -> None:
        action = AxeAuditAction(AxeAuditParams(url="https://example.com"))
        result = await action.execute(backend)
        backend.navigate.assert_awaited_once()
        backend.axe_audit.assert_awaited_once()
        assert result == {"violations": []}

    async def test_no_navigate_when_url_empty(self, backend: AsyncMock) -> None:
        action = AxeAuditAction(AxeAuditParams(url=""))
        await action.execute(backend)
        backend.navigate.assert_not_called()


@pytest.mark.unit
class TestBluetoothAction:
    """Tests for BluetoothAction."""

    async def test_emulate(self, backend: AsyncMock) -> None:
        action = BluetoothAction(
            BluetoothParams(action="emulate", name="Device", url="https://example.com")
        )
        result = await action.execute(backend)
        assert result is None
        backend.navigate.assert_awaited_once()
        backend.bluetooth_emulate.assert_awaited_once_with("Device", "00:00:00:00:00:01")

    async def test_stop(self, backend: AsyncMock) -> None:
        action = BluetoothAction(BluetoothParams(action="stop"))
        result = await action.execute(backend)
        assert result is None
        backend.bluetooth_stop.assert_awaited_once()

    async def test_emulate_requires_name(self, backend: AsyncMock) -> None:
        action = BluetoothAction(BluetoothParams(action="emulate"))
        with pytest.raises(ActionError, match="name is required"):
            await action.execute(backend)

    async def test_unknown_action(self, backend: AsyncMock) -> None:
        action = BluetoothAction(BluetoothParams(action="unknown"))
        with pytest.raises(ActionError, match="Unknown Bluetooth action"):
            await action.execute(backend)


@pytest.mark.unit
class TestCastAction:
    """Tests for CastAction."""

    async def test_list(self, backend: AsyncMock) -> None:
        action = CastAction(CastParams(action="list"))
        result = await action.execute(backend)
        assert result == []
        backend.cast_list.assert_awaited_once()

    async def test_start_tab_requires_sink(self, backend: AsyncMock) -> None:
        action = CastAction(CastParams(action="start-tab"))
        with pytest.raises(ActionError, match="sink_name is required"):
            await action.execute(backend)

    async def test_set_sink(self, backend: AsyncMock) -> None:
        action = CastAction(CastParams(action="set-sink", sink_name="Living Room"))
        await action.execute(backend)
        backend.cast_set_sink_to_use.assert_awaited_once_with("Living Room")

    async def test_unknown_action(self, backend: AsyncMock) -> None:
        action = CastAction(CastParams(action="unknown"))
        with pytest.raises(ActionError, match="Unknown Cast action"):
            await action.execute(backend)


@pytest.mark.unit
class TestCrawlAction:
    """Tests for CrawlAction."""

    async def test_crawls_single_page(self, backend: AsyncMock) -> None:
        async def _eval(script: str, *, await_promise: bool = False) -> str | list[str]:
            if "document.title" in script:
                return "Test Page"
            return ["https://example.com/page2"]

        backend.eval.side_effect = _eval
        action = CrawlAction(
            CrawlParams(start_url="https://example.com", max_depth=1, max_pages=10)
        )
        results = await action.execute(backend)
        assert len(results) == 2
        assert results[0]["url"] == "https://example.com"
        assert results[0]["title"] == "Test Page"

    async def test_crawl_same_origin_filter(self, backend: AsyncMock) -> None:
        async def _eval(script: str, *, await_promise: bool = False) -> str | list[str]:
            if "document.title" in script:
                return "Home"
            return ["https://other.com/page", "https://example.com/internal"]

        backend.eval.side_effect = _eval
        action = CrawlAction(
            CrawlParams(start_url="https://example.com/", max_depth=2, max_pages=10)
        )
        results = await action.execute(backend)
        assert all(r["url"].startswith("https://example.com") for r in results)

    async def test_invalid_max_depth(self) -> None:
        with pytest.raises(ActionError):
            CrawlAction(CrawlParams(start_url="https://example.com", max_depth=-1))


@pytest.mark.unit
class TestDownloadAction:
    """Tests for DownloadAction."""

    async def test_intercepts_download(self, backend: AsyncMock) -> None:
        action = DownloadAction(".*", url="https://example.com", wait=WaitStrategy(strategy="load"))
        result = await action.execute(backend)
        backend.navigate.assert_awaited_once()
        backend.intercept_download.assert_awaited_once_with(".*")
        assert result == b"data"

    async def test_no_url(self, backend: AsyncMock) -> None:
        action = DownloadAction(".*")
        await action.execute(backend)
        backend.navigate.assert_not_called()


@pytest.mark.unit
class TestExtractAction:
    """Tests for ExtractAction."""

    async def test_extract_with_schema(self, backend: AsyncMock) -> None:
        backend.eval.return_value = [{"title": "Hello"}]
        action = ExtractAction(ExtractParams(url="https://example.com", schema={"title": "h1"}))
        result = await action.execute(backend)
        assert result == [{"title": "Hello"}]
        backend.navigate.assert_awaited_once()

    async def test_invalid_schema(self) -> None:
        with pytest.raises(ActionError, match="schema must be a dict"):
            ExtractAction(ExtractParams(url="https://example.com", schema=["bad"]))


@pytest.mark.unit
class TestFormAction:
    """Tests for FormAction."""

    async def test_fill_and_submit(self, backend: AsyncMock) -> None:
        action = FormAction(
            FormParams(url="https://example.com", fields={"#name": "Dev"}, submit="#submit")
        )
        result = await action.execute(backend)
        backend.navigate.assert_awaited_once()
        backend.fill.assert_awaited_once_with("#name", "Dev")
        backend.click.assert_awaited_once_with("#submit")
        assert result["fields_filled"] == 1
        assert result["submitted"] is True

    async def test_fill_suppresses_errors(self, backend: AsyncMock) -> None:
        backend.fill.side_effect = ActionError("not found")
        action = FormAction(FormParams(url="https://example.com", fields={"#missing": "x"}))
        result = await action.execute(backend)
        assert result["fields_filled"] == 0


@pytest.mark.unit
class TestHARReplayAction:
    """Tests for HARReplayAction."""

    async def test_replays_har_file(self, backend: AsyncMock, tmp_path: Path) -> None:
        har = tmp_path / "test.har"
        har.write_text('{"log": {"entries": []}}', encoding="utf-8")
        action = HARReplayAction(HARReplayParams(har_path=str(har), url="https://example.com"))
        result = await action.execute(backend)
        backend.navigate.assert_awaited_once()
        backend.replay_har.assert_awaited_once_with(str(har), "")
        assert result["status"] == "ok"

    async def test_missing_har_path(self) -> None:
        with pytest.raises(ActionError, match="har_path is required"):
            await HARReplayAction(HARReplayParams()).execute(AsyncMock())


@pytest.mark.unit
class TestLighthouseAction:
    """Tests for LighthouseAction."""

    async def test_runs_all_categories(self, backend: AsyncMock) -> None:
        async def _eval(script: str, *, await_promise: bool = False) -> dict[str, Any]:
            if "domContentLoaded" in script:
                return {
                    "ttfb": 100,
                    "fcp": 200,
                    "loadComplete": 300,
                    "domSize": 50,
                    "transferSize": 0,
                    "encodedBodySize": 0,
                }
            if "largest-contentful-paint" in script:
                return {"lcp": 250, "cls": 0, "inp": 50, "tbt": 0}
            if "issues" in script and "has_viewport" in script:
                return {"issues": [], "issue_count": 0, "has_lang": True, "has_viewport": True}
            if "title_length" in script:
                return {
                    "title": "T",
                    "title_length": 1,
                    "description": "D",
                    "description_length": 1,
                    "h1_count": 1,
                    "canonical": "c",
                    "og_title": "o",
                    "twitter_card": "t",
                }
            if "is_https" in script:
                return {"issues": [], "is_https": True, "console_errors": []}
            return {}

        backend.eval.side_effect = _eval
        backend.perf_metrics.return_value = {}
        action = LighthouseAction(LighthouseParams(url="https://example.com"))
        result = await action.execute(backend)
        assert "categories" in result
        for cat in ("performance", "accessibility", "seo", "best-practices"):
            assert cat in result["categories"]
            assert "score" in result["categories"][cat]

    async def test_budgets(self, backend: AsyncMock) -> None:
        async def _eval(script: str, *, await_promise: bool = False) -> dict[str, Any]:
            if "domContentLoaded" in script:
                return {
                    "ttfb": 1000,
                    "fcp": 2000,
                    "loadComplete": 3000,
                    "domSize": 50,
                    "transferSize": 0,
                    "encodedBodySize": 0,
                }
            if "largest-contentful-paint" in script:
                return {"lcp": 250, "cls": 0, "inp": 50, "tbt": 0}
            if "has_viewport" in script:
                return {"issues": [], "issue_count": 0, "has_lang": True, "has_viewport": True}
            if "title_length" in script:
                return {
                    "title": "T",
                    "title_length": 1,
                    "description": "D",
                    "description_length": 1,
                    "h1_count": 1,
                    "canonical": "c",
                    "og_title": "o",
                    "twitter_card": "t",
                }
            if "is_https" in script:
                return {"issues": [], "is_https": True, "console_errors": []}
            return {}

        backend.eval.side_effect = _eval
        backend.perf_metrics.return_value = {}
        action = LighthouseAction(
            LighthouseParams(url="https://example.com", budgets={"ttfb_ms": 800})
        )
        result = await action.execute(backend)
        perf = result["categories"]["performance"]
        assert "budgets" in perf
        assert perf["budgets"]["pass"] is False


@pytest.mark.unit
class TestSessionActions:
    """Tests for SessionSaveAction and SessionLoadAction."""

    async def test_save_session(self, backend: AsyncMock, tmp_path: Path) -> None:
        backend.get_cookies.return_value = [{"name": "s", "value": "v"}]
        backend.storage_list.return_value = {"key": "val"}
        backend.eval.return_value = "https://example.com"
        out = tmp_path / "session.json"
        action = SessionSaveAction(out)
        json_str = await action.execute(backend)
        data = json.loads(json_str)
        assert data["url"] == "https://example.com"
        assert out.exists()

    async def test_load_session(self, backend: AsyncMock, tmp_path: Path) -> None:
        session = {
            "cookies": [{"name": "c", "value": "v", "domain": "example.com"}],
            "local_storage": {"a": "1"},
            "session_storage": {"b": "2"},
            "url": "",
        }
        path = tmp_path / "session.json"
        path.write_text(json.dumps(session), encoding="utf-8")
        action = SessionLoadAction(path)
        await action.execute(backend)
        backend.set_cookie.assert_awaited_once()
        backend.storage_set.assert_awaited()

    async def test_session_data_roundtrip(self) -> None:
        data = SessionData(cookies=[], local_storage={}, session_storage={}, url="u")
        parsed = SessionData.from_json(data.to_json())
        assert parsed.url == "u"


@pytest.mark.unit
class TestTabsAction:
    """Tests for TabsAction."""

    async def test_list(self, backend: AsyncMock) -> None:
        action = TabsAction(TabsParams(action="list"))
        await action.execute(backend)
        backend.list_tabs.assert_awaited_once()

    async def test_new(self, backend: AsyncMock) -> None:
        action = TabsAction(TabsParams(action="new", url="https://example.com"))
        result = await action.execute(backend)
        assert result == "tab-1"

    async def test_close_requires_tab_id(self) -> None:
        with pytest.raises(ActionError, match="tab_id is required"):
            TabsAction(TabsParams(action="close"))

    async def test_unknown(self) -> None:
        with pytest.raises(ActionError, match="Invalid tabs action"):
            await TabsAction(TabsParams(action="bad")).execute(AsyncMock())


@pytest.mark.unit
class TestVisualDiffAction:
    """Tests for VisualDiffAction."""

    def _make_png(self, tmp_path: Path, name: str = "baseline.png") -> str:
        from PIL import Image

        path = tmp_path / name
        img = Image.new("RGB", (10, 10), color="white")
        img.save(path, "PNG")
        return str(path)

    async def test_identical_images(self, backend: AsyncMock, tmp_path: Path) -> None:
        pytest.importorskip("PIL")
        baseline = self._make_png(tmp_path)
        backend.screenshot.return_value = await asyncio.to_thread(Path(baseline).read_bytes)
        action = VisualDiffAction(
            VisualDiffParams(url="https://example.com", baseline_path=baseline)
        )
        result = await action.execute(backend)
        assert result["diff_count"] == 0
        assert result["diff_percentage"] == 0.0

    async def test_missing_baseline_path(self, backend: AsyncMock) -> None:
        with pytest.raises(ActionError, match="baseline_path is required"):
            await VisualDiffAction(VisualDiffParams()).execute(backend)

    async def test_invalid_threshold(self, backend: AsyncMock) -> None:
        with pytest.raises(ActionError, match="threshold must be between"):
            await VisualDiffAction(VisualDiffParams(baseline_path="x", threshold=300)).execute(
                backend
            )
