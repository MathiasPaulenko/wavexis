"""Unit tests for actions with mock backend."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from browsix.actions.console import ConsoleAction, ConsoleParams
from browsix.actions.eval import EvalAction
from browsix.actions.navigate import (
    BackAction,
    ForwardAction,
    NavigateAction,
    NavigateParams,
    ReloadAction,
    StopAction,
)
from browsix.actions.pdf import PDFAction
from browsix.actions.screenshot import ScreenshotAction
from browsix.actions.tabs import TabsAction, TabsParams
from browsix.config import (
    EvalParams,
    PDFParams,
    ScreenshotParams,
)


class FakeBackend:
    """Mock backend for unit testing actions."""

    def __init__(self) -> None:
        self.navigate = AsyncMock()
        self.screenshot = AsyncMock(return_value=b"png-bytes")
        self.screenshot_selector = AsyncMock(return_value=b"selector-bytes")
        self.eval = AsyncMock(return_value="eval-result")
        self.close = AsyncMock()
        self.launch = AsyncMock()
        self.raw = AsyncMock(return_value={})
        self.go_back = AsyncMock()
        self.go_forward = AsyncMock()
        self.reload = AsyncMock()
        self.stop_loading = AsyncMock()
        self.wait_for = AsyncMock()
        self.pdf = AsyncMock(return_value=b"pdf-bytes")
        self.screencast = AsyncMock(return_value=[b"frame1"])
        self.list_tabs = AsyncMock(return_value=[{"targetId": "tab1"}])
        self.new_tab = AsyncMock(return_value="new-tab-id")
        self.close_tab = AsyncMock()
        self.activate_tab = AsyncMock()
        self.capture_console = AsyncMock(return_value=[{"type": "log"}])
        self.capture_logs = AsyncMock(return_value=[{"level": "info"}])
        self.dom_get = AsyncMock(return_value="<div>html</div>")
        self.dom_query = AsyncMock(return_value={"nodeId": 1})
        self.dom_set_attr = AsyncMock()
        self.dom_get_attr = AsyncMock(return_value="class-value")
        self.dom_remove_attr = AsyncMock()
        self.dom_remove = AsyncMock()
        self.dom_focus = AsyncMock()
        self.dom_scroll = AsyncMock()
        self.capture_har = AsyncMock(return_value={"log": {"entries": []}})
        self.get_cookies = AsyncMock(return_value=[{"name": "session"}])
        self.set_cookie = AsyncMock()
        self.delete_cookie = AsyncMock()
        self.clear_cookies = AsyncMock()
        self.set_headers = AsyncMock()
        self.set_user_agent = AsyncMock()
        self.new_context = AsyncMock(return_value="ctx-1")
        self.list_contexts = AsyncMock(return_value=[{"contextId": "ctx-1"}])
        self.close_context = AsyncMock()
        self.get_window_bounds = AsyncMock(
            return_value={"width": 1280, "height": 800, "x": 0, "y": 0}
        )
        self.set_window_bounds = AsyncMock()
        self.browser_version = AsyncMock(return_value="Chrome/120.0")


@pytest.fixture
def backend() -> FakeBackend:
    return FakeBackend()


class TestScreenshotAction:
    """Tests for ScreenshotAction."""

    @pytest.mark.unit
    async def test_execute_basic(self, backend: FakeBackend):
        params = ScreenshotParams(url="https://example.com")
        action = ScreenshotAction(params)
        result = await action.execute(backend)
        assert result == b"png-bytes"
        backend.navigate.assert_called_once_with(params.url, params.wait)

    @pytest.mark.unit
    async def test_execute_with_js(self, backend: FakeBackend):
        params = ScreenshotParams(url="https://example.com", js="document.title='test'")
        action = ScreenshotAction(params)
        await action.execute(backend)
        backend.eval.assert_called_once_with("document.title='test'", await_promise=True)

    @pytest.mark.unit
    async def test_execute_with_selector(self, backend: FakeBackend):
        params = ScreenshotParams(url="https://example.com", selector="#hero")
        action = ScreenshotAction(params)
        result = await action.execute(backend)
        assert result == b"selector-bytes"
        backend.screenshot_selector.assert_called_once()


class TestPDFAction:
    """Tests for PDFAction."""

    @pytest.mark.unit
    async def test_execute(self, backend: FakeBackend):
        params = PDFParams(url="https://example.com", paper="a4")
        action = PDFAction(params)
        result = await action.execute(backend)
        assert result == b"pdf-bytes"
        backend.navigate.assert_called_once()
        backend.pdf.assert_called_once_with(params)

    @pytest.mark.unit
    async def test_execute_with_js(self, backend: FakeBackend):
        params = PDFParams(url="https://example.com", js="document.title='test'")
        action = PDFAction(params)
        await action.execute(backend)
        backend.eval.assert_called_once_with("document.title='test'", await_promise=True)


class TestEvalAction:
    """Tests for EvalAction."""

    @pytest.mark.unit
    async def test_execute(self, backend: FakeBackend):
        params = EvalParams(url="https://example.com", expression="document.title")
        action = EvalAction(params)
        result = await action.execute(backend)
        assert result == "eval-result"
        backend.eval.assert_called_once_with("document.title", await_promise=False)

    @pytest.mark.unit
    async def test_execute_with_file(self, backend: FakeBackend, tmp_path):
        js_file = tmp_path / "script.js"
        js_file.write_text("document.title", encoding="utf-8")
        params = EvalParams(url="https://example.com", file=str(js_file))
        action = EvalAction(params)
        result = await action.execute(backend)
        assert result == "eval-result"
        backend.eval.assert_called_once_with("document.title", await_promise=False)


class TestNavigateActions:
    """Tests for navigation actions."""

    @pytest.mark.unit
    async def test_navigate(self, backend: FakeBackend):
        params = NavigateParams(url="https://example.com")
        action = NavigateAction(params)
        await action.execute(backend)
        backend.navigate.assert_called_once_with("https://example.com", None)

    @pytest.mark.unit
    async def test_back(self, backend: FakeBackend):
        action = BackAction(None)
        await action.execute(backend)
        backend.go_back.assert_called_once()

    @pytest.mark.unit
    async def test_forward(self, backend: FakeBackend):
        action = ForwardAction(None)
        await action.execute(backend)
        backend.go_forward.assert_called_once()

    @pytest.mark.unit
    async def test_reload(self, backend: FakeBackend):
        action = ReloadAction(True)
        await action.execute(backend)
        backend.reload.assert_called_once()

    @pytest.mark.unit
    async def test_stop(self, backend: FakeBackend):
        action = StopAction(None)
        await action.execute(backend)
        backend.stop_loading.assert_called_once()


class TestTabsAction:
    """Tests for TabsAction."""

    @pytest.mark.unit
    async def test_list(self, backend: FakeBackend):
        params = TabsParams(action="list")
        action = TabsAction(params)
        result = await action.execute(backend)
        assert result == [{"targetId": "tab1"}]
        backend.list_tabs.assert_called_once()

    @pytest.mark.unit
    async def test_new(self, backend: FakeBackend):
        params = TabsParams(action="new", url="https://example.com")
        action = TabsAction(params)
        result = await action.execute(backend)
        assert result == "new-tab-id"
        backend.new_tab.assert_called_once_with("https://example.com")

    @pytest.mark.unit
    async def test_close(self, backend: FakeBackend):
        params = TabsParams(action="close", tab_id="tab1")
        action = TabsAction(params)
        await action.execute(backend)
        backend.close_tab.assert_called_once_with("tab1")

    @pytest.mark.unit
    async def test_activate(self, backend: FakeBackend):
        params = TabsParams(action="activate", tab_id="tab1")
        action = TabsAction(params)
        await action.execute(backend)
        backend.activate_tab.assert_called_once_with("tab1")


class TestConsoleAction:
    """Tests for ConsoleAction."""

    @pytest.mark.unit
    async def test_console_capture(self, backend: FakeBackend):
        params = ConsoleParams(url="https://example.com", capture="console")
        action = ConsoleAction(params)
        result = await action.execute(backend)
        assert "console" in result
        assert result["console"] == [{"type": "log"}]
        backend.capture_console.assert_called_once()

    @pytest.mark.unit
    async def test_logs_capture(self, backend: FakeBackend):
        params = ConsoleParams(url="https://example.com", capture="logs")
        action = ConsoleAction(params)
        result = await action.execute(backend)
        assert "logs" in result
        assert result["logs"] == [{"level": "info"}]
        backend.capture_logs.assert_called_once()

    @pytest.mark.unit
    async def test_both_capture(self, backend: FakeBackend):
        params = ConsoleParams(url="https://example.com", capture="both")
        action = ConsoleAction(params)
        result = await action.execute(backend)
        assert "console" in result
        assert "logs" in result


class TestDOMAction:
    """Tests for DOMAction."""

    @pytest.mark.unit
    async def test_dom_get(self, backend: FakeBackend):
        from browsix.actions.dom import DOMAction
        from browsix.config import DOMParams

        params = DOMParams(url="https://example.com", action="get", selector="#main")
        action = DOMAction(params)
        result = await action.execute(backend)
        assert result == "<div>html</div>"
        backend.dom_get.assert_called_once_with("#main", outer=True)

    @pytest.mark.unit
    async def test_dom_get_inner(self, backend: FakeBackend):
        from browsix.actions.dom import DOMAction
        from browsix.config import DOMParams

        params = DOMParams(
            url="https://example.com", action="get", selector="#main", outer=False
        )
        action = DOMAction(params)
        result = await action.execute(backend)
        assert result == "<div>html</div>"
        backend.dom_get.assert_called_once_with("#main", outer=False)

    @pytest.mark.unit
    async def test_dom_query_single(self, backend: FakeBackend):
        from browsix.actions.dom import DOMAction
        from browsix.config import DOMParams

        params = DOMParams(
            url="https://example.com", action="query", selector=".item", all=False
        )
        action = DOMAction(params)
        result = await action.execute(backend)
        assert result == {"nodeId": 1}
        backend.dom_query.assert_called_once_with(".item", all=False)

    @pytest.mark.unit
    async def test_dom_query_all(self, backend: FakeBackend):
        from browsix.actions.dom import DOMAction
        from browsix.config import DOMParams

        params = DOMParams(
            url="https://example.com", action="query", selector=".item", all=True
        )
        action = DOMAction(params)
        await action.execute(backend)
        backend.dom_query.assert_called_once_with(".item", all=True)

    @pytest.mark.unit
    async def test_dom_set_attr(self, backend: FakeBackend):
        from browsix.actions.dom import DOMAction
        from browsix.config import DOMParams

        params = DOMParams(
            url="https://example.com",
            action="attr",
            selector="#main",
            attribute="class",
            value="highlighted",
        )
        action = DOMAction(params)
        await action.execute(backend)
        backend.dom_set_attr.assert_called_once_with("#main", "class", "highlighted")

    @pytest.mark.unit
    async def test_dom_get_attr(self, backend: FakeBackend):
        from browsix.actions.dom import DOMAction
        from browsix.config import DOMParams

        params = DOMParams(
            url="https://example.com",
            action="attr",
            selector="#main",
            attribute="class",
        )
        action = DOMAction(params)
        result = await action.execute(backend)
        assert result == "class-value"
        backend.dom_get_attr.assert_called_once_with("#main", "class")

    @pytest.mark.unit
    async def test_dom_remove(self, backend: FakeBackend):
        from browsix.actions.dom import DOMAction
        from browsix.config import DOMParams

        params = DOMParams(
            url="https://example.com", action="remove", selector="#ad-banner"
        )
        action = DOMAction(params)
        await action.execute(backend)
        backend.dom_remove.assert_called_once_with("#ad-banner")

    @pytest.mark.unit
    async def test_dom_focus(self, backend: FakeBackend):
        from browsix.actions.dom import DOMAction
        from browsix.config import DOMParams

        params = DOMParams(
            url="https://example.com", action="focus", selector="#input"
        )
        action = DOMAction(params)
        await action.execute(backend)
        backend.dom_focus.assert_called_once_with("#input")

    @pytest.mark.unit
    async def test_dom_scroll(self, backend: FakeBackend):
        from browsix.actions.dom import DOMAction
        from browsix.config import DOMParams

        params = DOMParams(
            url="https://example.com", action="scroll", selector="#section"
        )
        action = DOMAction(params)
        await action.execute(backend)
        backend.dom_scroll.assert_called_once()


class TestScrapeAction:
    """Tests for ScrapeAction."""

    @pytest.mark.unit
    async def test_scrape_basic(self, backend: FakeBackend):
        from browsix.actions.scrape import ScrapeAction
        from browsix.config import ScrapeParams

        params = ScrapeParams(
            urls=["https://example.com", "https://test.com"],
            expression="document.title",
        )
        action = ScrapeAction(params)
        results = await action.execute(backend)
        assert len(results) == 2
        assert results[0]["url"] == "https://example.com"
        assert results[0]["result"] == "eval-result"
        assert results[1]["url"] == "https://test.com"

    @pytest.mark.unit
    async def test_scrape_with_file(self, backend: FakeBackend, tmp_path):
        from browsix.actions.scrape import ScrapeAction
        from browsix.config import ScrapeParams

        js_file = tmp_path / "scraper.js"
        js_file.write_text("document.title", encoding="utf-8")
        params = ScrapeParams(
            urls=["https://example.com"],
            file=str(js_file),
        )
        action = ScrapeAction(params)
        results = await action.execute(backend)
        assert len(results) == 1
        backend.eval.assert_called_with("document.title", await_promise=True)


class TestHARAction:
    """Tests for HARAction."""

    @pytest.mark.unit
    async def test_har_capture(self, backend: FakeBackend):
        from browsix.actions.har import HARAction
        from browsix.config import HarParams

        params = HarParams(url="https://example.com", wait=100)
        action = HARAction(params)
        result = await action.execute(backend)
        assert "log" in result
        assert result["log"]["entries"] == []
        backend.capture_har.assert_called_once_with(params)


class TestNetworkAction:
    """Tests for NetworkAction."""

    @pytest.mark.unit
    async def test_cookies_get(self, backend: FakeBackend):
        from browsix.actions.network import NetworkAction
        from browsix.config import NetworkParams

        params = NetworkParams(action="cookies_get")
        action = NetworkAction(params)
        result = await action.execute(backend)
        assert result == [{"name": "session"}]
        backend.get_cookies.assert_called_once()

    @pytest.mark.unit
    async def test_cookies_set(self, backend: FakeBackend):
        from browsix.actions.network import NetworkAction
        from browsix.config import CookieParams, NetworkParams

        cookie = CookieParams(name="test", value="val", domain="example.com")
        params = NetworkParams(action="cookies_set", cookie=cookie)
        action = NetworkAction(params)
        await action.execute(backend)
        backend.set_cookie.assert_called_once_with(cookie)

    @pytest.mark.unit
    async def test_cookies_clear(self, backend: FakeBackend):
        from browsix.actions.network import NetworkAction
        from browsix.config import NetworkParams

        params = NetworkParams(action="cookies_clear")
        action = NetworkAction(params)
        await action.execute(backend)
        backend.clear_cookies.assert_called_once()

    @pytest.mark.unit
    async def test_headers(self, backend: FakeBackend):
        from browsix.actions.network import NetworkAction
        from browsix.config import NetworkParams

        params = NetworkParams(
            action="headers", headers={"X-Custom": "value"}
        )
        action = NetworkAction(params)
        await action.execute(backend)
        backend.set_headers.assert_called_once_with({"X-Custom": "value"})

    @pytest.mark.unit
    async def test_user_agent(self, backend: FakeBackend):
        from browsix.actions.network import NetworkAction
        from browsix.config import NetworkParams

        params = NetworkParams(action="user_agent", user_agent="TestBot/1.0")
        action = NetworkAction(params)
        await action.execute(backend)
        backend.set_user_agent.assert_called_once_with("TestBot/1.0")


class TestBrowserAction:
    """Tests for BrowserAction."""

    @pytest.mark.unit
    async def test_version(self, backend: FakeBackend):
        from browsix.actions.browser import BrowserAction

        action = BrowserAction("version")
        result = await action.execute(backend)
        assert result == "Chrome/120.0"
        backend.browser_version.assert_called_once()

    @pytest.mark.unit
    async def test_new_context(self, backend: FakeBackend):
        from browsix.actions.browser import BrowserAction

        action = BrowserAction("new_context")
        result = await action.execute(backend)
        assert result == "ctx-1"
        backend.new_context.assert_called_once()

    @pytest.mark.unit
    async def test_list_contexts(self, backend: FakeBackend):
        from browsix.actions.browser import BrowserAction

        action = BrowserAction("list_contexts")
        result = await action.execute(backend)
        assert result == [{"contextId": "ctx-1"}]
        backend.list_contexts.assert_called_once()
