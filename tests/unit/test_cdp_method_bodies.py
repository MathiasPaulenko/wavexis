"""Unit tests for CDPBackend method bodies with mocked CDPSession."""

from __future__ import annotations

import base64
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wavexis.config import (
    BrowserOptions,
    CookieParams,
    HarParams,
    PDFParams,
    ScreencastParams,
    ScreenshotParams,
    SensorParams,
    ThrottleParams,
    WaitStrategy,
)


def _make_mock_backend() -> tuple[Any, Any, Any]:
    """Create a CDPBackend with a fully mocked CDPClient and CDPSession."""
    from wavexis.backend.cdp import CDPBackend

    backend = CDPBackend()
    mock_session = MagicMock()

    mock_session.page = MagicMock()
    mock_session.page.enable = AsyncMock()
    mock_session.page.navigate = AsyncMock()
    mock_session.page.capture_screenshot = AsyncMock(
        return_value={"data": base64.b64encode(b"img").decode()}
    )
    mock_session.page.reload = AsyncMock()
    mock_session.page.stop = AsyncMock()
    mock_session.page.get_navigation_history = AsyncMock(
        return_value={"entries": [{"id": 0, "url": "https://example.com"}], "currentIndex": 0}
    )
    mock_session.page.navigate_to_history_entry = AsyncMock()
    mock_session.page.close = AsyncMock()

    mock_session.runtime.enable = AsyncMock()
    mock_session.runtime.evaluate = AsyncMock(
        return_value={"result": {"value": "result"}}
    )

    mock_session.dom = MagicMock()
    mock_session.dom.get_document = AsyncMock(
        return_value={"root": {"nodeId": 1}}
    )
    mock_session.dom.query_selector = AsyncMock(
        return_value={"nodeId": 2}
    )
    mock_session.dom.query_selector_all = AsyncMock(
        return_value={"nodeIds": [3, 4]}
    )
    mock_session.dom.get_box_model = AsyncMock(
        return_value={"model": {"border": [0, 0, 100, 0, 100, 50, 0, 50]}}
    )
    mock_session.dom.set_attribute_value = AsyncMock()
    mock_session.dom.get_attribute = AsyncMock(return_value={"attributes": ["class", "active"]})
    mock_session.dom.remove_attribute = AsyncMock()
    mock_session.dom.remove_node = AsyncMock()
    mock_session.dom.focus = AsyncMock()
    mock_session.dom.scroll_into_view = AsyncMock()
    mock_session.dom.describe_node = AsyncMock(return_value={"node": {}})
    mock_session.dom.get_outer_html = AsyncMock(return_value={"outerHTML": "<h1>Test</h1>"})

    mock_session.target = MagicMock()
    mock_session.target.create_target = AsyncMock(return_value={"targetId": "tab-1"})
    mock_session.target.close_target = AsyncMock()
    mock_session.target.activate_target = AsyncMock()
    mock_session.target.get_targets = AsyncMock(return_value={"targetInfos": []})
    mock_session.target.create_browser_context = AsyncMock(
        return_value={"browserContextId": "ctx-2"}
    )
    mock_session.target.dispose_browser_context = AsyncMock()
    mock_session.target.get_browser_contexts = AsyncMock(return_value={"browserContextIds": []})
    mock_session.target.get_target_info = AsyncMock(
        return_value={"bounds": {"left": 0, "top": 0, "width": 800, "height": 600}}
    )

    mock_session.network.get_cookies = AsyncMock(return_value={"cookies": []})
    mock_session.network.set_cookie = AsyncMock()
    mock_session.network.delete_cookies = AsyncMock()
    mock_session.network.clear_browser_cookies = AsyncMock()
    mock_session.network.set_extra_request_headers = AsyncMock()
    mock_session.network.enable = AsyncMock()
    mock_session.network.disable = AsyncMock()
    mock_session.network.set_cache_disabled = AsyncMock()
    mock_session.network.set_user_agent_override = AsyncMock()

    mock_session.emulation = MagicMock()
    mock_session.emulation.set_user_agent_override = AsyncMock()
    mock_session.emulation.set_device_metrics_override = AsyncMock()
    mock_session.emulation.set_touch_emulation_enabled = AsyncMock()
    mock_session.emulation.set_geolocation_override = AsyncMock()
    mock_session.emulation.set_timezone_override = AsyncMock()
    mock_session.emulation.set_emulated_media = AsyncMock()
    mock_session.emulation.set_network_conditions = AsyncMock()
    mock_session.emulation.set_locale_override = AsyncMock()
    mock_session.emulation.set_cpu_throttling_rate = AsyncMock()
    mock_session.emulation.set_sensors_override = AsyncMock()

    mock_session.security = MagicMock()
    mock_session.security.set_ignore_certificate_errors = AsyncMock()

    mock_session.browser = MagicMock()
    mock_session.browser.get_version = AsyncMock(return_value={"product": "Chrome/120"})
    mock_session.browser.get_window_bounds = AsyncMock(
        return_value={"bounds": {"left": 0, "top": 0, "width": 800, "height": 600}}
    )
    mock_session.browser.set_window_bounds = AsyncMock()
    mock_session.browser.get_window_for_target = AsyncMock(return_value={"windowId": 1})

    mock_session.input = MagicMock()
    mock_session.input.dispatch_mouse_event = AsyncMock()
    mock_session.input.dispatch_key_event = AsyncMock()
    mock_session.input.dispatch_touch_event = AsyncMock()

    mock_session.dom.enable = AsyncMock()
    mock_session.dom.focus = AsyncMock()

    mock_session.overlay = MagicMock()
    mock_session.overlay.enable = AsyncMock()
    mock_session.overlay.highlight_node = AsyncMock()
    mock_session.overlay.hide_highlight = AsyncMock()

    mock_session.storage = MagicMock()
    mock_session.storage.get_cookies = AsyncMock(return_value={"cookies": []})
    mock_session.storage.set_cookie = AsyncMock()
    mock_session.storage.delete_cookie = AsyncMock()
    mock_session.storage.clear_cookies = AsyncMock()
    mock_session.storage.clear_data_for_origin = AsyncMock()
    mock_session.storage.get_data_for_origin = AsyncMock(return_value={"entries": []})

    mock_session.performance = MagicMock()
    mock_session.performance.enable = AsyncMock()
    mock_session.performance.get_metrics = AsyncMock(return_value={"metrics": []})

    mock_session.profiler = MagicMock()
    mock_session.profiler.enable = AsyncMock()
    mock_session.profiler.start = AsyncMock()
    mock_session.profiler.stop = AsyncMock(return_value={"profile": {}})
    mock_session.profiler.start_precise_coverage = AsyncMock()
    mock_session.profiler.take_precise_coverage = AsyncMock(return_value={"result": {}})
    mock_session.profiler.disable = AsyncMock()

    mock_session.heapprofiler = MagicMock()
    mock_session.heapprofiler.enable = AsyncMock()
    mock_session.heapprofiler.take_heap_snapshot = AsyncMock(return_value={"snapshot": {}})

    mock_session.css = MagicMock()
    mock_session.css.enable = AsyncMock()
    mock_session.css.start_rule_usage_tracking = AsyncMock()
    mock_session.css.stop_rule_usage_tracking = AsyncMock(return_value={"result": {}})
    mock_session.css.get_stylesheets = AsyncMock(return_value={"headers": []})
    mock_session.css.get_rules = AsyncMock(return_value={"rules": []})

    mock_session.debugger = MagicMock()
    mock_session.debugger.enable = AsyncMock()
    mock_session.debugger.set_breakpoint_by_url = AsyncMock(
        return_value={"breakpointId": "bp-1"}
    )
    mock_session.debugger.set_breakpoint_on_function = AsyncMock(
        return_value={"breakpointId": "bp-2"}
    )
    mock_session.debugger.remove_breakpoint = AsyncMock()
    mock_session.debugger.step_over = AsyncMock()
    mock_session.debugger.step_into = AsyncMock()
    mock_session.debugger.step_out = AsyncMock()
    mock_session.debugger.pause = AsyncMock()
    mock_session.debugger.resume = AsyncMock()
    mock_session.debugger.get_event_listeners = AsyncMock(return_value={"listeners": []})

    mock_session.tracing = MagicMock()
    mock_session.tracing.start = AsyncMock()
    mock_session.tracing.end = AsyncMock(return_value={})

    mock_session.serviceworker = MagicMock()
    mock_session.serviceworker.enable = AsyncMock()

    mock_session.animation = MagicMock()
    mock_session.animation.enable = AsyncMock()
    mock_session.animation.get_current_time = AsyncMock(return_value={"currentTime": 0})

    mock_session.web_authn = MagicMock()
    mock_session.web_authn.enable = AsyncMock()
    mock_session.web_authn.add_virtual_authenticator = AsyncMock(
        return_value={"authenticatorId": "auth-1"}
    )
    mock_session.web_authn.remove_virtual_authenticator = AsyncMock()
    mock_session.web_authn.add_credential = AsyncMock()
    mock_session.web_authn.get_credentials = AsyncMock(return_value={"credentials": []})
    mock_session.webaudio = MagicMock()
    mock_session.webaudio.enable = AsyncMock()
    mock_session.webaudio.get_realtime_context_data = AsyncMock(return_value={"context": {}})

    mock_session.media = MagicMock()
    mock_session.media.enable = AsyncMock()
    mock_session.media.get_players = AsyncMock(return_value={"players": []})
    mock_session.media.get_player_properties = AsyncMock(return_value={"messages": []})

    mock_session.cast = MagicMock()
    mock_session.cast.enable = AsyncMock()

    mock_session.bluetooth = MagicMock()

    mock_session.fetch = MagicMock()
    mock_session.fetch.enable = AsyncMock()
    mock_session.fetch.disable = AsyncMock()
    mock_session.fetch.get_request_post_data = AsyncMock(return_value={"postData": "data"})
    mock_session.fetch.get_response_body = AsyncMock(return_value={"body": "data"})

    mock_session.on = MagicMock()
    mock_session.log = MagicMock()
    mock_session.log.enable = AsyncMock()
    mock_session.send_command = AsyncMock(return_value={})
    mock_session.send = AsyncMock(return_value={})
    mock_session.close = AsyncMock()
    mock_session.wait_for_event = AsyncMock()

    mock_client = MagicMock()
    mock_client.new_page = AsyncMock(return_value=mock_session)
    mock_client.close = AsyncMock()
    mock_client.send = AsyncMock(return_value={"browserContextId": "ctx-2"})
    mock_client.browser = MagicMock()
    mock_client.browser.get_window_for_target = AsyncMock(
        return_value={"windowId": 1, "bounds": {"left": 0, "top": 0, "width": 800, "height": 600}}
    )
    mock_client.browser.set_window_bounds = AsyncMock()
    mock_client.browser.get_version = AsyncMock(return_value={"product": "Chrome/120"})

    backend._client = mock_client
    backend._session = mock_session

    return backend, mock_client, mock_session


@pytest.mark.unit
class TestCDPMethodBodies:
    """Test CDPBackend method bodies with mocked session."""

    async def test_navigate(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.navigate("https://example.com")

    async def test_navigate_with_wait_load(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.navigate("https://example.com", WaitStrategy(strategy="load", timeout=1000))

    async def test_navigate_with_wait_selector(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.runtime.evaluate = AsyncMock(return_value={"result": {"value": True}})
        await backend.navigate(
            "https://example.com",
            WaitStrategy(strategy="selector", selector="h1", timeout=100),
        )

    async def test_navigate_with_wait_domcontentloaded(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.navigate(
            "https://example.com",
            WaitStrategy(strategy="domcontentloaded", timeout=1000),
        )

    async def test_screenshot(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.screenshot(ScreenshotParams(url="https://example.com"))
        assert isinstance(result, bytes)

    async def test_screenshot_with_device(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.screenshot(
            ScreenshotParams(url="https://example.com", device="iphone-15")
        )
        assert isinstance(result, bytes)

    async def test_screenshot_selector(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.screenshot_selector("h1")
        assert isinstance(result, bytes)

    async def test_annotated_screenshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.runtime.evaluate = AsyncMock(return_value={"result": {"value": "{}"}})
        result = await backend.annotated_screenshot(["h1", "p"])
        assert isinstance(result, tuple)

    async def test_eval(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.eval("document.title")
        assert result == "result"

    async def test_raw(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"ok": True})
        result = await backend.raw("Test.method", {"key": "val"})
        assert result == {"ok": True}

    async def test_go_back(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.go_back()

    async def test_go_forward(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.go_forward()

    async def test_reload(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.reload()

    async def test_stop_loading(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.stop_loading()

    async def test_wait_for_load(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.wait_for(WaitStrategy(strategy="load"))

    async def test_wait_for_selector_found(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.runtime.evaluate = AsyncMock(return_value={"result": {"value": True}})
        await backend.wait_for(WaitStrategy(strategy="selector", selector="h1", timeout=100))

    async def test_wait_for_selector_timeout(self) -> None:
        from wavexis.exceptions import WaitTimeoutError
        backend, _, mock = _make_mock_backend()
        mock.runtime.evaluate = AsyncMock(return_value={"result": {"value": False}})
        with pytest.raises(WaitTimeoutError):
            await backend.wait_for(WaitStrategy(strategy="selector", selector="h1", timeout=50))

    async def test_pdf(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.page.print_to_pdf = AsyncMock(return_value={"data": base64.b64encode(b"pdf").decode()})
        result = await backend.pdf(PDFParams(url="https://example.com"))
        assert isinstance(result, bytes)

    async def test_screencast(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.screencast(ScreencastParams(url="https://example.com", duration=0.1))
        assert isinstance(result, list)

    async def test_list_tabs(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.target.get_targets = AsyncMock(return_value={"targetInfos": [{"type": "page"}]})
        result = await backend.list_tabs()
        assert isinstance(result, list)

    async def test_new_tab(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.target.create_target = AsyncMock(return_value={"targetId": "tab-1"})
        result = await backend.new_tab("https://example.com")
        assert result == "tab-1"

    async def test_close_tab(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.close_tab("tab-1")

    async def test_activate_tab(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.activate_tab("tab-1")

    async def test_capture_console(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.capture_console()
        assert isinstance(result, list)

    async def test_capture_logs(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.capture_logs()
        assert isinstance(result, list)

    async def test_dom_get(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.dom_get("h1")
        assert isinstance(result, str)

    async def test_dom_query(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.runtime.evaluate = AsyncMock(return_value={"result": {"value": {"tagName": "div"}}})
        result = await backend.dom_query("div")
        assert isinstance(result, dict)

    async def test_dom_query_all(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.dom.describe_node = AsyncMock(
            return_value={"node": {"children": [{"nodeId": 3}, {"nodeId": 4}]}}
        )
        result = await backend.dom_query("div", all=True)
        assert isinstance(result, list)

    async def test_dom_set_attr(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.dom_set_attr("h1", "class", "active")

    async def test_dom_get_attr(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.dom_get_attr("h1", "class")
        assert result == "active"

    async def test_dom_remove_attr(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.dom_remove_attr("h1", "class")

    async def test_dom_remove(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.dom_remove("h1")

    async def test_dom_focus(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.dom_focus("h1")

    async def test_dom_scroll(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.dom_scroll("h1")

    async def test_get_cookies(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.get_cookies()
        assert isinstance(result, list)

    async def test_set_cookie(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.set_cookie(CookieParams(name="test", value="val", domain="example.com"))

    async def test_delete_cookie(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.delete_cookie("test", "example.com")

    async def test_clear_cookies(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.clear_cookies()

    async def test_set_headers(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.set_headers({"X-Test": "val"})

    async def test_set_user_agent(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.set_user_agent("TestAgent")

    async def test_new_context(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.new_context()
        assert result == "ctx-2"

    async def test_list_contexts(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"browserContextIds": []})
        result = await backend.list_contexts()
        assert isinstance(result, list)

    async def test_close_context(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.close_context("ctx-2")

    async def test_get_window_bounds(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.get_window_bounds()
        assert "width" in result

    async def test_set_window_bounds(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.set_window_bounds(1024, 768)

    async def test_browser_version(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.browser_version()
        assert "Chrome" in result

    async def test_emulate_device(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.emulate_device("iphone-15")

    async def test_set_viewport(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.set_viewport(1280, 720)

    async def test_set_geolocation(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.set_geolocation(37.7749, -122.4194)

    async def test_set_timezone(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.set_timezone("America/Los_Angeles")

    async def test_set_dark_mode(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.set_dark_mode(True)

    async def test_click(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.runtime.evaluate = AsyncMock(return_value={"result": {"value": True}})
        await backend.click("h1")

    async def test_type_text(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.type_text("input", "hello")

    async def test_fill(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.runtime.evaluate = AsyncMock(return_value={"result": {"value": True}})
        await backend.fill("input", "hello", auto_wait=False)

    async def test_select_option(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.select_option("select", "option1")

    async def test_hover(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.runtime.evaluate = AsyncMock(return_value={"result": {"value": True}})
        await backend.hover("h1", auto_wait=False)

    async def test_key_press(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.key_press("Enter")

    async def test_drag(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.drag("#source", "#target")

    async def test_tap(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.runtime.evaluate = AsyncMock(return_value={"result": {"value": True}})
        await backend.tap("h1")

    async def test_set_files(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.set_files("input[type=file]", ["/path/to/file"])

    async def test_block_requests(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.block_requests(["*://ads.example.com/*"])

    async def test_throttle_network(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.throttle_network(ThrottleParams())

    async def test_set_cache_disabled(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.set_cache_disabled(True)

    async def test_intercept_requests(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.intercept_requests({"urlPattern": "*"})

    async def test_mock_response(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.mock_response("https://example.com", {"status": 200, "body": "ok"})

    async def test_get_request_body(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"postData": "data"})
        result = await backend.get_request_body("req-1")
        assert result == "data"

    async def test_get_response_body(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"body": "data"})
        result = await backend.get_response_body("req-1")
        assert result == "data"

    async def test_modify_request(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.modify_request({"urlPattern": "*"}, {"method": "POST"})

    async def test_modify_response(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.modify_response({"urlPattern": "*"}, {"status": 200, "body": "ok"})

    async def test_replay_har(self, tmp_path: Any) -> None:
        backend, _, _ = _make_mock_backend()
        har_file = tmp_path / "test.har"
        har_file.write_text('{"log":{"entries":[]}}')
        await backend.replay_har(str(har_file))

    async def test_intercept_download(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.intercept_download()

    async def test_dialog_accept(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.dialog_accept()

    async def test_dialog_dismiss(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.dialog_dismiss()

    async def test_grant_permission(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.grant_permission("geolocation")

    async def test_reset_permissions(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.reset_permissions()

    async def test_get_security_state(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"security": "secure"})
        result = await backend.get_security_state()
        assert isinstance(result, dict)

    async def test_ignore_cert_errors(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.ignore_cert_errors(True)

    async def test_set_locale(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.set_locale("en-US")

    async def test_set_cpu_throttle(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.set_cpu_throttle(4.0)

    async def test_set_touch_emulation(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.set_touch_emulation(True)

    async def test_set_sensors(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.set_sensors(SensorParams())

    async def test_perf_metrics(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.perf_metrics()
        assert isinstance(result, dict)

    async def test_perf_trace(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.perf_trace(duration_ms=1)

    async def test_perf_profile(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.perf_profile(duration_ms=1)
        assert isinstance(result, dict)

    async def test_perf_heap_snapshot(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.perf_heap_snapshot()
        assert isinstance(result, dict)

    async def test_perf_coverage(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.perf_coverage()
        assert isinstance(result, dict)

    async def test_perf_css_coverage(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"result": {}})
        result = await backend.perf_css_coverage()
        assert isinstance(result, dict)

    async def test_css_get_styles(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"inlineStyles": {}, "computedStyles": {}})
        result = await backend.css_get_styles("h1")
        assert isinstance(result, dict)

    async def test_css_get_stylesheets(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"stylesheets": []})
        result = await backend.css_get_stylesheets()
        assert isinstance(result, list)

    async def test_css_get_rules(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"text": "h1 { color: red; }"})
        result = await backend.css_get_rules("0")
        assert isinstance(result, list)

    async def test_css_get_computed(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"object": {"objectId": "obj-1"}, "computedStyle": []})
        result = await backend.css_get_computed("h1")
        assert isinstance(result, dict)

    async def test_debug_set_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"breakpointId": "bp-1"})
        result = await backend.debug_set_breakpoint("https://example.com", 10)
        assert result == "bp-1"

    async def test_debug_set_breakpoint_function(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"breakpointId": "bp-2"})
        result = await backend.debug_set_breakpoint_function("foo")
        assert result == "bp-2"

    async def test_debug_remove_breakpoint(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.debug_remove_breakpoint("bp-1")

    async def test_debug_step_over(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.debug_step_over()

    async def test_debug_step_into(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.debug_step_into()

    async def test_debug_step_out(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.debug_step_out()

    async def test_debug_pause(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.debug_pause()

    async def test_debug_resume(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.debug_resume()

    async def test_debug_get_listeners(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"object": {"objectId": "obj-1"}, "listeners": []})
        result = await backend.debug_get_listeners("h1")
        assert isinstance(result, list)

    async def test_dom_snapshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"dom": {}})
        result = await backend.dom_snapshot()
        assert isinstance(result, dict)

    async def test_overlay_highlight(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.overlay_highlight("h1")

    async def test_overlay_clear(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.overlay_clear()

    async def test_storage_get(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"value": "data"})
        result = await backend.storage_get("key")
        assert isinstance(result, str)

    async def test_storage_set(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.storage_set("key", "value")

    async def test_storage_clear(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.storage_clear()

    async def test_storage_list(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"entries": [["k", "v"]]})
        result = await backend.storage_list()
        assert isinstance(result, dict)

    async def test_cache_storage_list(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.runtime.evaluate = AsyncMock(return_value={"result": {"value": "[]"}})
        result = await backend.cache_storage_list()
        assert isinstance(result, list)

    async def test_cache_storage_entries(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.runtime.evaluate = AsyncMock(return_value={"result": {"value": "[]"}})
        result = await backend.cache_storage_entries("my-cache")
        assert isinstance(result, list)

    async def test_cache_storage_delete(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.cache_storage_delete("my-cache")

    async def test_indexeddb_list(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"databasesWithOrigins": []})
        result = await backend.indexeddb_list()
        assert isinstance(result, list)

    async def test_indexeddb_get_data(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"objectStoreDataEntries": []})
        result = await backend.indexeddb_get_data("db", "store")
        assert isinstance(result, list)

    async def test_indexeddb_clear(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.indexeddb_clear("db", "store")

    async def test_sw_list(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"registrations": []})
        result = await backend.sw_list()
        assert isinstance(result, list)

    async def test_sw_unregister(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.sw_unregister("reg-1")

    async def test_sw_update(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.sw_update("reg-1")

    async def test_animation_list(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"animations": []})
        result = await backend.animation_list()
        assert isinstance(result, list)

    async def test_animation_pause(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.animation_pause("anim-1")

    async def test_animation_play(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.animation_play("anim-1")

    async def test_animation_seek(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.animation_seek("anim-1", 500)

    async def test_webauthn_add_virtual_authenticator(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.webauthn_add_virtual_authenticator("ctap2", "usb")
        assert result == "auth-1"

    async def test_webauthn_remove_authenticator(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.webauthn_remove_authenticator("auth-1")

    async def test_webauthn_add_credential(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.webauthn_add_credential("auth-1", {})

    async def test_webauthn_get_credentials(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.webauthn_get_credentials("auth-1")
        assert isinstance(result, list)

    async def test_webaudio_get_contexts(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.wait_for_event = AsyncMock(side_effect=TimeoutError())
        result = await backend.webaudio_get_contexts()
        assert isinstance(result, list)

    async def test_webaudio_get_context(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"data": {}})
        result = await backend.webaudio_get_context("ctx-1")
        assert isinstance(result, dict)

    async def test_media_get_players(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"players": []})
        result = await backend.media_get_players()
        assert isinstance(result, list)

    async def test_media_get_messages(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.media_get_messages("player-1")
        assert isinstance(result, list)

    async def test_cast_list(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"sinks": []})
        result = await backend.cast_list()
        assert isinstance(result, list)

    async def test_cast_start_tab(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.cast_start_tab("sink-1")

    async def test_cast_stop(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.cast_stop()

    async def test_bluetooth_emulate(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.bluetooth_emulate("adapter-1", "00:00:00:00:00:00")

    async def test_bluetooth_stop(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.bluetooth_stop()

    async def test_extension_install(self, tmp_path: Any) -> None:
        backend, _, mock = _make_mock_backend()
        ext_dir = tmp_path / "myext"
        ext_dir.mkdir()
        mock.send = AsyncMock(return_value={"id": "ext-123"})
        result = await backend.extension_install(str(ext_dir))
        assert len(result) == 32

    async def test_extension_uninstall(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.extension_uninstall("ext-123")

    async def test_extension_list(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"extensions": []})
        result = await backend.extension_list()
        assert isinstance(result, list)

    async def test_get_pref(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"value": True})
        result = await backend.get_pref("safebrowsing.enabled")
        assert result is True

    async def test_set_pref(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.set_pref("safebrowsing.enabled", False)

    async def test_capture_har(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.capture_har(HarParams(url="https://example.com"))
        assert isinstance(result, dict)

    async def test_subscribe_events(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.subscribe_events(["console"], callback=lambda e: None)
        assert isinstance(result, str)

    async def test_unsubscribe_events(self) -> None:
        backend, _, _ = _make_mock_backend()
        backend._subscriptions = {"sub-1": {"event": lambda: None}}
        await backend.unsubscribe_events("sub-1")

    async def test_a11y_tree(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"tree": {}})
        result = await backend.a11y_tree()
        assert isinstance(result, dict)

    async def test_a11y_node(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"node": {}})
        result = await backend.a11y_node("1")
        assert isinstance(result, dict)

    async def test_a11y_ancestors(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"ancestors": []})
        result = await backend.a11y_ancestors("1")
        assert isinstance(result, list)

    async def test_start_combined_trace(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.start_combined_trace(
            capture_screenshots=False, capture_network=False, capture_console=False
        )
        assert isinstance(result, str)

    async def test_stop_combined_trace(self) -> None:
        backend, _, _ = _make_mock_backend()
        trace_id = await backend.start_combined_trace(
            capture_screenshots=False, capture_network=False, capture_console=False
        )
        result = await backend.stop_combined_trace(trace_id)
        assert isinstance(result, dict)

    async def test_axe_audit(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.runtime.evaluate = AsyncMock(return_value={"result": {"value": '{"passes":[]}'}})
        result = await backend.axe_audit()
        assert isinstance(result, dict)

    async def test_close_with_client(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.close()
        assert backend._client is None

    async def test_close_without_client(self) -> None:
        from wavexis.backend.cdp import CDPBackend
        backend = CDPBackend()
        await backend.close()

    async def test_new_tab_handle(self) -> None:
        backend, _, _ = _make_mock_backend()
        handle = await backend.new_tab_handle("https://example.com")
        assert handle is not None

    async def test_launch_with_browser_url(self) -> None:
        from wavexis.backend.cdp import CDPBackend
        backend = CDPBackend()
        mock_session = MagicMock()
        mock_session.emulation.set_user_agent_override = AsyncMock()
        mock_session.network.set_extra_http_headers = AsyncMock()
        mock_session.runtime.evaluate = AsyncMock()
        mock_session.page.enable = AsyncMock()
        mock_session.close = AsyncMock()
        mock_client = MagicMock()
        mock_client.new_page = AsyncMock(return_value=mock_session)
        mock_client.close = AsyncMock()
        with patch("wavexis.backend.cdp.CDPClient") as mock_client_cls:
            mock_client_cls.connect = AsyncMock(return_value=mock_client)
            opts = BrowserOptions(browser_url="http://localhost:9222", stealth=True)
            await backend.launch(opts)

    async def test_launch_with_remote_url(self) -> None:
        from wavexis.backend.cdp import CDPBackend
        backend = CDPBackend()
        mock_session = MagicMock()
        mock_session.emulation.set_user_agent_override = AsyncMock()
        mock_session.network.set_extra_http_headers = AsyncMock()
        mock_session.runtime.evaluate = AsyncMock()
        mock_session.page.enable = AsyncMock()
        mock_session.close = AsyncMock()
        mock_client = MagicMock()
        mock_client.new_page = AsyncMock(return_value=mock_session)
        mock_client.close = AsyncMock()
        with patch("wavexis.backend.cdp.CDPClient") as mock_client_cls:
            mock_client_cls.connect = AsyncMock(return_value=mock_client)
            opts = BrowserOptions(
                remote_url="ws://localhost:9222/session",
                user_agent="TestAgent",
                extra_headers={"X-Test": "val"},
            )
            await backend.launch(opts)

    async def test_launch_already_launched(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.launch(BrowserOptions())

    async def test_context_manager(self) -> None:
        backend, _, _ = _make_mock_backend()
        async with backend as b:
            assert b is backend
