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
    mock_session.page.get_frame_tree = AsyncMock(return_value={"frameTree": {}})
    mock_session.page.get_layout_metrics = AsyncMock(return_value={"layoutViewport": {}})
    mock_session.page.bring_to_front = AsyncMock()
    mock_session.page.wait_for_debugger = AsyncMock()
    mock_session.page.get_resource_content = AsyncMock(
        return_value={"content": "body{}", "base64Encoded": False}
    )
    mock_session.page.set_download_behavior = AsyncMock()
    mock_session.page.capture_snapshot = AsyncMock(return_value={"data": "<snapshot>"})
    mock_session.page.print_to_pdf = AsyncMock(return_value={"data": "base64data"})
    mock_session.page.start_screencast = AsyncMock()
    mock_session.page.stop_screencast = AsyncMock()
    mock_session.page.set_bypass_csp = AsyncMock()
    mock_session.page.set_ad_blocking_enabled = AsyncMock()
    mock_session.page.add_script_to_evaluate_on_new_document = AsyncMock(
        return_value={"identifier": "script-1"}
    )
    mock_session.page.remove_script_to_evaluate_on_new_document = AsyncMock()
    mock_session.page.generate_test_report = AsyncMock()
    mock_session.page.get_app_manifest = AsyncMock(return_value={"data": {}})
    mock_session.page.get_resource_tree = AsyncMock(return_value={"frameTree": {}})
    mock_session.page.close = AsyncMock()

    mock_session.runtime.enable = AsyncMock()
    mock_session.runtime.evaluate = AsyncMock(return_value={"result": {"value": "result"}})
    mock_session.runtime.compile_script = AsyncMock(return_value={"scriptId": "1"})
    mock_session.runtime.run_script = AsyncMock(return_value={"result": {}})
    mock_session.runtime.call_function_on = AsyncMock(return_value={"result": {}})
    mock_session.runtime.get_properties = AsyncMock(return_value={"result": []})
    mock_session.runtime.release_object = AsyncMock()
    mock_session.runtime.release_object_group = AsyncMock()
    mock_session.runtime.discard_console_entries = AsyncMock()
    mock_session.runtime.get_heap_usage = AsyncMock(return_value={"usedSize": 0, "totalSize": 0})
    mock_session.runtime.global_lexical_scope_names = AsyncMock(return_value={"names": []})

    mock_session.dom = MagicMock()
    mock_session.dom.get_document = AsyncMock(return_value={"root": {"nodeId": 1}})
    mock_session.dom.query_selector = AsyncMock(return_value={"nodeId": 2})
    mock_session.dom.query_selector_all = AsyncMock(return_value={"nodeIds": [3, 4]})
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
    mock_session.dom.get_flattened_document = AsyncMock(return_value={"nodes": []})
    mock_session.dom.get_content_quads = AsyncMock(
        return_value={"quads": [[0, 0, 1, 0, 1, 1, 0, 1]]}
    )
    mock_session.dom.get_node_for_location = AsyncMock(return_value={"nodeId": 5})
    mock_session.dom.perform_search = AsyncMock(return_value={"searchId": "s1", "resultCount": 1})
    mock_session.dom.get_search_results = AsyncMock(return_value={"nodeIds": [6, 7]})
    mock_session.dom.scroll_into_view_if_needed = AsyncMock()
    mock_session.dom.describe_node = AsyncMock(return_value={"nodeName": "div"})
    mock_session.dom.get_outer_html = AsyncMock(return_value={"outerHTML": "<div></div>"})
    mock_session.dom.remove_node = AsyncMock()
    mock_session.dom.set_node_value = AsyncMock()
    mock_session.dom.set_outer_html = AsyncMock()
    mock_session.dom.request_node = AsyncMock(return_value={"nodeId": 10})
    mock_session.dom.resolve_node = AsyncMock(return_value={"object": {}})
    mock_session.dom.set_attribute_value = AsyncMock()
    mock_session.dom.remove_attribute = AsyncMock()
    mock_session.dom.request_child_nodes = AsyncMock()

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
    mock_session.target.attach_to_target = AsyncMock(return_value={"sessionId": "sess-1"})
    mock_session.target.detach_from_target = AsyncMock()
    mock_session.target.set_auto_attach = AsyncMock()
    mock_session.target.set_discover_targets = AsyncMock()

    mock_session.network.get_cookies = AsyncMock(return_value={"cookies": []})
    mock_session.network.set_cookie = AsyncMock()
    mock_session.network.delete_cookies = AsyncMock()
    mock_session.network.clear_browser_cookies = AsyncMock()
    mock_session.network.set_extra_request_headers = AsyncMock()
    mock_session.network.enable = AsyncMock()
    mock_session.network.disable = AsyncMock()
    mock_session.network.set_cache_disabled = AsyncMock()
    mock_session.network.set_user_agent_override = AsyncMock()
    mock_session.network.clear_browser_cache = AsyncMock()
    mock_session.network.set_blocked_urls = AsyncMock()
    mock_session.network.set_bypass_service_worker = AsyncMock()
    mock_session.network.set_cookie_controls = AsyncMock()
    mock_session.network.replay_xhr = AsyncMock()
    mock_session.network.load_network_resource = AsyncMock(return_value={"resource": {}})

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
    mock_session.emulation.clear_device_metrics_override = AsyncMock()
    mock_session.emulation.clear_emulated_media = AsyncMock()
    mock_session.emulation.set_emulated_vision_deficiency = AsyncMock()
    mock_session.emulation.clear_emulated_vision_deficiency = AsyncMock()
    mock_session.emulation.set_idle_override = AsyncMock()
    mock_session.emulation.clear_idle_override = AsyncMock()
    mock_session.emulation.set_script_execution_disabled = AsyncMock()
    mock_session.emulation.set_visible_size = AsyncMock()

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
    mock_session.overlay.disable = AsyncMock()
    mock_session.overlay.highlight_quad = AsyncMock()
    mock_session.overlay.highlight_rect = AsyncMock()
    mock_session.overlay.set_inspect_mode = AsyncMock()
    mock_session.overlay.set_show_fps_counter = AsyncMock()
    mock_session.overlay.set_show_paint_rects = AsyncMock()
    mock_session.overlay.set_show_debug_borders = AsyncMock()
    mock_session.overlay.set_show_ad_highlights = AsyncMock()

    mock_session.storage = MagicMock()
    mock_session.storage.get_cookies = AsyncMock(return_value={"cookies": []})
    mock_session.storage.set_cookie = AsyncMock()
    mock_session.storage.delete_cookie = AsyncMock()
    mock_session.storage.clear_cookies = AsyncMock()
    mock_session.storage.clear_data_for_origin = AsyncMock()
    mock_session.storage.get_data_for_origin = AsyncMock(return_value={"entries": []})
    mock_session.storage.get_usage_and_quota = AsyncMock(return_value={"usage": 0, "quota": 0})
    mock_session.storage.get_trust_tokens = AsyncMock(return_value={"tokens": []})
    mock_session.storage.clear_trust_tokens = AsyncMock()
    mock_session.storage.get_shared_storage_entries = AsyncMock(return_value={"entries": []})
    mock_session.storage.set_shared_storage_entry = AsyncMock()
    mock_session.storage.delete_shared_storage_entry = AsyncMock()
    mock_session.storage.clear_shared_storage_entries = AsyncMock()
    mock_session.storage.get_interest_group_details = AsyncMock(return_value={"details": {}})
    mock_session.storage.override_quota_for_origin = AsyncMock()

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
    mock_session.css.add_rule = AsyncMock(return_value={"ruleId": "rule-1"})
    mock_session.css.create_style_sheet = AsyncMock(return_value={"styleSheetId": "ss-1"})
    mock_session.css.get_media_queries = AsyncMock(return_value={"medias": []})
    mock_session.css.get_style_sheet_text = AsyncMock(return_value={"text": "body { }"})
    mock_session.css.set_style_sheet_text = AsyncMock()
    mock_session.css.set_rule_selector = AsyncMock()
    mock_session.css.set_media_text = AsyncMock()
    mock_session.css.force_pseudo_state = AsyncMock()
    mock_session.css.get_background_colors = AsyncMock(return_value={"backgroundColors": []})
    mock_session.css.take_coverage_delta = AsyncMock(return_value={"coverage": []})

    mock_session.debugger = MagicMock()
    mock_session.debugger.enable = AsyncMock()
    mock_session.debugger.set_breakpoint_by_url = AsyncMock(return_value={"breakpointId": "bp-1"})
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
    mock_session.debugger.evaluate_on_call_frame = AsyncMock(return_value={"result": {}})
    mock_session.debugger.get_script_source = AsyncMock(
        return_value={"scriptSource": "console.log(1)"}
    )
    mock_session.debugger.get_stack_trace = AsyncMock(return_value={"callFrames": []})
    mock_session.debugger.get_possible_breakpoints = AsyncMock(return_value={"locations": []})
    mock_session.debugger.search_in_content = AsyncMock(return_value={"result": []})
    mock_session.debugger.set_pause_on_exceptions = AsyncMock()
    mock_session.debugger.set_breakpoints_active = AsyncMock()
    mock_session.debugger.set_skip_all_pauses = AsyncMock()
    mock_session.debugger.set_script_source = AsyncMock(return_value={"result": {}})
    mock_session.debugger.continue_to_location = AsyncMock()

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

    mock_session.wait_for_selector = AsyncMock(return_value=2)
    mock_session.wait_for_load_state = AsyncMock()
    mock_session.wait_for_network_idle = AsyncMock()

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
        mock.wait_for_selector = AsyncMock(side_effect=TimeoutError())
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

    # ── Performance domain (4 new methods) ────────────────

    async def test_performance_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.performance_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Performance.disable"

    async def test_performance_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.performance_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Performance.enable"

    async def test_performance_get_metrics(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"metrics": []}
        result = await backend.performance_get_metrics()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Performance.getMetrics"
        assert isinstance(result, dict)

    async def test_performance_set_time_domain(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.performance_set_time_domain("timeTicks")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Performance.setTimeDomain"

    # ── PerformanceTimeline (1 new method) ────────────────

    async def test_performance_timeline_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.performance_timeline_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "PerformanceTimeline.enable"

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
        mock.wait_for_event = AsyncMock(side_effect=TimeoutError())
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
        backend, mock_client, mock_session = _make_mock_backend()
        with patch("wavexis.backend.cdp.CDPClient") as mock_client_cls:
            mock_client_cls.launch = AsyncMock(return_value=mock_client)
            mock_client_cls.connect = AsyncMock(return_value=mock_client)
            await backend.launch(BrowserOptions())

    async def test_context_manager(self) -> None:
        backend, _, _ = _make_mock_backend()
        async with backend as b:
            assert b is backend

    async def test_page_get_frame_tree(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.page_get_frame_tree()
        assert isinstance(result, dict)

    async def test_page_get_layout_metrics(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.page_get_layout_metrics()
        assert isinstance(result, dict)

    async def test_page_get_navigation_history(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.page_get_navigation_history()
        assert isinstance(result, dict)

    async def test_page_navigate_to_history_entry(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.page_navigate_to_history_entry(0)

    async def test_page_bring_to_front(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.page_bring_to_front()

    async def test_page_wait_for_debugger(self) -> None:
        backend, _, _ = _make_mock_backend()
        await backend.page_wait_for_debugger()

    async def test_page_get_resource_content(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.page_get_resource_content("frame-1", "https://example.com/style.css")
        assert isinstance(result, dict)

    async def test_page_set_download_behavior(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_set_download_behavior("allow", "/tmp/downloads")
        mock.page.set_download_behavior.assert_awaited_once()

    async def test_dom_get_document(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.dom_get_document()
        assert isinstance(result, dict)

    async def test_dom_get_flattened_document(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.dom_get_flattened_document()
        assert isinstance(result, dict)

    async def test_dom_get_box_model(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.dom_get_box_model("h1")
        assert isinstance(result, dict)

    async def test_dom_get_content_quads(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.dom_get_content_quads("h1")
        assert isinstance(result, list)

    async def test_dom_get_node_for_location(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.dom_get_node_for_location(10, 20)
        assert isinstance(result, dict)

    async def test_dom_perform_search(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.dom_perform_search("hello")
        assert isinstance(result, dict)

    async def test_dom_get_search_results(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.dom_get_search_results("s1", 0, 10)
        assert isinstance(result, list)

    async def test_dom_scroll_into_view_if_needed(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_scroll_into_view_if_needed("h1")
        mock.dom.scroll_into_view_if_needed.assert_awaited_once()

    async def test_set_device_metrics_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_device_metrics_override(375, 812, 3.0, True)
        mock.emulation.set_device_metrics_override.assert_awaited_once()

    async def test_clear_device_metrics_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.clear_device_metrics_override()
        mock.emulation.clear_device_metrics_override.assert_awaited_once()

    async def test_set_emulated_media(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_emulated_media("print")
        mock.emulation.set_emulated_media.assert_awaited_once()

    async def test_clear_emulated_media(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.clear_emulated_media()
        mock.emulation.clear_emulated_media.assert_awaited_once()

    async def test_set_emulated_vision_deficiency(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_emulated_vision_deficiency("achromatopsia")
        mock.emulation.set_emulated_vision_deficiency.assert_awaited_once()

    async def test_clear_emulated_vision_deficiency(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.clear_emulated_vision_deficiency()
        mock.emulation.clear_emulated_vision_deficiency.assert_awaited_once()

    async def test_set_idle_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_idle_override(True, True)
        mock.emulation.set_idle_override.assert_awaited_once()

    async def test_clear_idle_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.clear_idle_override()
        mock.emulation.clear_idle_override.assert_awaited_once()

    async def test_set_script_execution_disabled(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_script_execution_disabled(True)
        mock.emulation.set_script_execution_disabled.assert_awaited_once()

    async def test_set_visible_size(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_visible_size(800, 600)
        mock.emulation.set_visible_size.assert_awaited_once()

    async def test_page_capture_snapshot(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.page_capture_snapshot("mhtml")
        assert isinstance(result, str)

    async def test_page_print_to_pdf(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.page_print_to_pdf()
        assert isinstance(result, str)

    async def test_page_start_screencast(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_start_screencast("jpeg", 80)
        mock.page.start_screencast.assert_awaited_once()

    async def test_page_stop_screencast(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_stop_screencast()
        mock.page.stop_screencast.assert_awaited_once()

    async def test_page_set_bypass_csp(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_set_bypass_csp(True)
        mock.page.set_bypass_csp.assert_awaited_once()

    async def test_page_set_ad_blocking_enabled(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_set_ad_blocking_enabled(True)
        mock.page.set_ad_blocking_enabled.assert_awaited_once()

    async def test_page_add_script_to_evaluate_on_new_document(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.page_add_script_to_evaluate_on_new_document("console.log(1)")
        assert isinstance(result, str)

    async def test_page_remove_script_to_evaluate_on_new_document(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_remove_script_to_evaluate_on_new_document("script-1")
        mock.page.remove_script_to_evaluate_on_new_document.assert_awaited_once()

    async def test_page_generate_test_report(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_generate_test_report("test")
        mock.page.generate_test_report.assert_awaited_once()

    async def test_page_get_app_manifest(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.page_get_app_manifest()
        assert isinstance(result, dict)

    async def test_page_get_resource_tree(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.page_get_resource_tree()
        assert isinstance(result, dict)

    # ── Page (37 new methods) ─────────────────────────────

    async def test_page_add_compilation_cache(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_add_compilation_cache("https://example.com", "data")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.addCompilationCache"

    async def test_page_add_script_to_evaluate_on_load(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"identifier": "script-1"}
        result = await backend.page_add_script_to_evaluate_on_load("console.log(1)")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.addScriptToEvaluateOnLoad"
        assert isinstance(result, str)

    async def test_page_capture_screenshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"data": "base64data"}
        result = await backend.page_capture_screenshot()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.captureScreenshot"
        assert isinstance(result, str)

    async def test_page_clear_compilation_cache(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_clear_compilation_cache()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.clearCompilationCache"

    async def test_page_clear_device_orientation_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_clear_device_orientation_override()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.clearDeviceOrientationOverride"

    async def test_page_clear_geolocation_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_clear_geolocation_override()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.clearGeolocationOverride"

    async def test_page_crash(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_crash()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.crash"

    async def test_page_create_isolated_world(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"executionContextId": 42}
        result = await backend.page_create_isolated_world("frame-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.createIsolatedWorld"
        assert isinstance(result, str)

    async def test_page_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.disable"

    async def test_page_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.enable"

    async def test_page_get_ad_script_ancestry(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"ancestry": []}
        result = await backend.page_get_ad_script_ancestry("frame-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.getAdScriptAncestry"
        assert isinstance(result, dict)

    async def test_page_get_annotated_page_content(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"content": {}}
        result = await backend.page_get_annotated_page_content()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.getAnnotatedPageContent"
        assert isinstance(result, dict)

    async def test_page_get_app_id(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"appId": "com.example.app"}
        result = await backend.page_get_app_id()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.getAppId"
        assert isinstance(result, dict)

    async def test_page_get_installability_errors(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"errors": []}
        result = await backend.page_get_installability_errors()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.getInstallabilityErrors"
        assert isinstance(result, dict)

    async def test_page_get_manifest_icons(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"icons": []}
        result = await backend.page_get_manifest_icons()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.getManifestIcons"
        assert isinstance(result, dict)

    async def test_page_get_origin_trials(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"trials": []}
        result = await backend.page_get_origin_trials()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.getOriginTrials"
        assert isinstance(result, dict)

    async def test_page_get_permissions_policy_state(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"states": []}
        result = await backend.page_get_permissions_policy_state("frame-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.getPermissionsPolicyState"
        assert isinstance(result, dict)

    async def test_page_handle_java_script_dialog(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_handle_java_script_dialog(True, "ok")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.handleJavaScriptDialog"

    async def test_page_handle_javascript_dialog(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_handle_javascript_dialog(False)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.handleJavaScriptDialog"

    async def test_page_produce_compilation_cache(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"data": "cached"}
        result = await backend.page_produce_compilation_cache("https://example.com")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.produceCompilationCache"
        assert isinstance(result, dict)

    async def test_page_remove_script_to_evaluate_on_load(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_remove_script_to_evaluate_on_load("script-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.removeScriptToEvaluateOnLoad"

    async def test_page_reset_navigation_history(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_reset_navigation_history()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.resetNavigationHistory"

    async def test_page_screencast_frame_ack(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_screencast_frame_ack(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.screencastFrameAck"

    async def test_page_search_in_resource(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"results": []}
        result = await backend.page_search_in_resource("frame-1", "https://example.com", "test")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.searchInResource"
        assert isinstance(result, dict)

    async def test_page_set_device_orientation_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_set_device_orientation_override(0.0, 0.0, 0.0)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.setDeviceOrientationOverride"

    async def test_page_set_document_content(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_set_document_content("frame-1", "<html></html>")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.setDocumentContent"

    async def test_page_set_font_families(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_set_font_families({"standard": "Arial"})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.setFontFamilies"

    async def test_page_set_font_sizes(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_set_font_sizes({"standard": 16})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.setFontSizes"

    async def test_page_set_geolocation_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_set_geolocation_override(37.7749, -122.4194, 10.0)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.setGeolocationOverride"

    async def test_page_set_intercept_file_chooser_dialog(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_set_intercept_file_chooser_dialog(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.setInterceptFileChooserDialog"

    async def test_page_set_lifecycle_events_enabled(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_set_lifecycle_events_enabled(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.setLifecycleEventsEnabled"

    async def test_page_set_prerendering_allowed(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_set_prerendering_allowed(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.setPrerenderingAllowed"

    async def test_page_set_rph_registration_mode(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_set_rph_registration_mode("auto")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.setRPHRegistrationMode"

    async def test_page_set_spc_transaction_mode(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_set_spc_transaction_mode("auto")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.setSPCTransactionMode"

    async def test_page_set_touch_emulation_enabled(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_set_touch_emulation_enabled(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.setTouchEmulationEnabled"

    async def test_page_set_web_lifecycle_state(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_set_web_lifecycle_state("active")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.setWebLifecycleState"

    async def test_page_stop(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.page_stop()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Page.stop"

    async def test_css_add_rule(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.css_add_rule("ss-1", ".test { color: red; }")
        assert isinstance(result, str)

    async def test_css_create_style_sheet(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.css_create_style_sheet("frame-1")
        assert isinstance(result, str)

    async def test_css_get_media_queries(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.css_get_media_queries()
        assert isinstance(result, list)

    async def test_css_get_style_sheet_text(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.css_get_style_sheet_text("ss-1")
        assert isinstance(result, str)

    async def test_css_set_style_sheet_text(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_set_style_sheet_text("ss-1", "body { }")
        mock.css.set_style_sheet_text.assert_awaited_once()

    async def test_css_set_rule_selector(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_set_rule_selector("ss-1", "0", ".new")
        mock.css.set_rule_selector.assert_awaited_once()

    async def test_css_set_media_text(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_set_media_text("ss-1", "0", "(max-width: 600px)")
        mock.css.set_media_text.assert_awaited_once()

    async def test_css_force_pseudo_state(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_force_pseudo_state(1, ["hover"])
        mock.css.force_pseudo_state.assert_awaited_once()

    async def test_css_get_background_colors(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.css_get_background_colors(1)
        assert isinstance(result, dict)

    async def test_css_start_rule_usage_tracking(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_start_rule_usage_tracking()
        mock.css.start_rule_usage_tracking.assert_awaited_once()

    async def test_css_stop_rule_usage_tracking(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_stop_rule_usage_tracking()
        mock.css.stop_rule_usage_tracking.assert_awaited_once()

    async def test_css_take_coverage_delta(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.css_take_coverage_delta()
        assert isinstance(result, dict)

    async def test_css_collect_class_names(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"classNames": ["foo", "bar"]}
        result = await backend.css_collect_class_names(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.collectClassNames"
        assert result == ["foo", "bar"]

    async def test_css_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.disable"

    async def test_css_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.enable"

    async def test_css_force_starting_style(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_force_starting_style(1, {"styleSheetId": "ss-1", "ordinal": 0})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.forceStartingStyle"

    async def test_css_get_animated_styles_for_node(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"animationStyles": {}}
        result = await backend.css_get_animated_styles_for_node(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.getAnimatedStylesForNode"
        assert isinstance(result, dict)

    async def test_css_get_computed_style_for_node(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"computedStyle": [{"name": "color", "value": "red"}]}
        result = await backend.css_get_computed_style_for_node(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.getComputedStyleForNode"
        assert result == [{"name": "color", "value": "red"}]

    async def test_css_get_environment_variables(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"environmentVariables": [{"name": "var", "value": "val"}]}
        result = await backend.css_get_environment_variables()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.getEnvironmentVariables"
        assert result == [{"name": "var", "value": "val"}]

    async def test_css_get_inline_styles(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"inlineStyle": {}}
        result = await backend.css_get_inline_styles(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.getInlineStyles"
        assert isinstance(result, dict)

    async def test_css_get_inline_styles_for_node(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"inlineStyles": {}}
        result = await backend.css_get_inline_styles_for_node(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.getInlineStylesForNode"
        assert isinstance(result, dict)

    async def test_css_get_layers_for_node(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"layers": [{"name": "base"}]}
        result = await backend.css_get_layers_for_node(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.getLayersForNode"
        assert result == [{"name": "base"}]

    async def test_css_get_location_for_selector(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"startLine": 0, "startColumn": 0}
        result = await backend.css_get_location_for_selector(".test", "ss-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.getLocationForSelector"
        assert isinstance(result, dict)

    async def test_css_get_longhand_properties(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"longhandProperties": [{"name": "prop"}]}
        result = await backend.css_get_longhand_properties({"styleSheetId": "ss-1", "ordinal": 0})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.getLonghandProperties"
        assert result == [{"name": "prop"}]

    async def test_css_get_matched_styles_for_node(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"matchedCSSRules": []}
        result = await backend.css_get_matched_styles_for_node(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.getMatchedStylesForNode"
        assert isinstance(result, dict)

    async def test_css_get_platform_fonts_for_node(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"fonts": [{"familyName": "Arial"}]}
        result = await backend.css_get_platform_fonts_for_node(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.getPlatformFontsForNode"
        assert result == [{"familyName": "Arial"}]

    async def test_css_get_stylesheet_text(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"text": ".test { color: red; }"}
        result = await backend.css_get_stylesheet_text("ss-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.getStyleSheetText"
        assert result == ".test { color: red; }"

    async def test_css_resolve_values(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"resolvedValues": [{"name": "color", "value": "red"}]}
        result = await backend.css_resolve_values([{"name": "color", "value": "red"}])
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.resolveValues"
        assert result == [{"name": "color", "value": "red"}]

    async def test_css_set_container_query_condition_text(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_set_container_query_condition_text(
            "ss-1", {"styleSheetId": "ss-1", "ordinal": 0}, "(min-width: 600px)"
        )
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.setContainerQueryConditionText"

    async def test_css_set_effective_property_value_for_node(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_set_effective_property_value_for_node(1, "color", "red")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.setEffectivePropertyValueForNode"

    async def test_css_set_keyframe_key(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_set_keyframe_key("ss-1", {"styleSheetId": "ss-1", "ordinal": 0}, "0%")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.setKeyframeKey"

    async def test_css_set_local_fonts_enabled(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_set_local_fonts_enabled(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.setLocalFontsEnabled"

    async def test_css_set_navigation_text(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_set_navigation_text(
            "ss-1", {"styleSheetId": "ss-1", "ordinal": 0}, "@media (nav)"
        )
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.setNavigationText"

    async def test_css_set_property_rule_property_name(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_set_property_rule_property_name(
            "ss-1", {"styleSheetId": "ss-1", "ordinal": 0}, "color"
        )
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.setPropertyRulePropertyName"

    async def test_css_set_rule_style(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_set_rule_style(
            "ss-1", {"styleSheetId": "ss-1", "ordinal": 0}, "color: red;"
        )
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.setRuleStyle"

    async def test_css_set_scope_text(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_set_scope_text("ss-1", {"styleSheetId": "ss-1", "ordinal": 0}, ".scope")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.setScopeText"

    async def test_css_set_style_sheet_text(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_set_style_sheet_text("ss-1", ".test { color: red; }")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.setStyleSheetText"

    async def test_css_set_style_text(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"styles": [{"styleId": {"styleSheetId": "ss-1", "ordinal": 0}}]}
        result = await backend.css_set_style_text(
            [{"styleSheetId": "ss-1", "ordinal": 0, "text": "color: red;"}]
        )
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.setStyleTexts"
        assert isinstance(result, list)

    async def test_css_set_style_texts(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"styles": [{"styleId": {"styleSheetId": "ss-1", "ordinal": 0}}]}
        result = await backend.css_set_style_texts(
            [{"styleSheetId": "ss-1", "ordinal": 0, "text": "color: blue;"}]
        )
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.setStyleTexts"
        assert isinstance(result, list)

    async def test_css_set_stylesheet_text(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_set_stylesheet_text("ss-1", ".test { color: green; }")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.setStyleSheetText"

    async def test_css_set_supports_text(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_set_supports_text(
            "ss-1", {"styleSheetId": "ss-1", "ordinal": 0}, "(display: flex)"
        )
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.setSupportsText"

    async def test_css_take_computed_style_updates(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"computedStyleUpdates": [{"nodeId": 1}]}
        result = await backend.css_take_computed_style_updates()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.takeComputedStyleUpdates"
        assert result == [{"nodeId": 1}]

    async def test_css_track_computed_style_updates(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_track_computed_style_updates(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.trackComputedStyleUpdates"

    async def test_css_track_computed_style_updates_for_node(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.css_track_computed_style_updates_for_node(1, True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CSS.trackComputedStyleUpdatesForNode"

    async def test_debug_evaluate_on_call_frame(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.debug_evaluate_on_call_frame("cf-1", "1+1")
        assert isinstance(result, dict)

    async def test_debug_get_script_source(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.debug_get_script_source("script-1")
        assert isinstance(result, str)

    async def test_debug_get_stack_trace(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.debug_get_stack_trace()
        assert isinstance(result, dict)

    async def test_debug_get_possible_breakpoints(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.debug_get_possible_breakpoints({"scriptId": "s1", "lineNumber": 0})
        assert isinstance(result, list)

    async def test_debug_search_in_content(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.debug_search_in_content("script-1", "test")
        assert isinstance(result, list)

    async def test_debug_set_pause_on_exceptions(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debug_set_pause_on_exceptions("all")
        mock.debugger.set_pause_on_exceptions.assert_awaited_once()

    async def test_debug_set_breakpoints_active(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debug_set_breakpoints_active(True)
        mock.debugger.set_breakpoints_active.assert_awaited_once()

    async def test_debug_set_skip_all_pauses(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debug_set_skip_all_pauses(True)
        mock.debugger.set_skip_all_pauses.assert_awaited_once()

    async def test_debug_set_script_source(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.debug_set_script_source("script-1", "console.log(2)")
        assert isinstance(result, dict)

    async def test_debug_continue_to_location(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debug_continue_to_location("script.js", 10, 0)
        mock.debugger.continue_to_location.assert_awaited_once()

    async def test_debug_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debug_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.disable"

    async def test_debug_disassemble_wasm_module(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"disassembly": {}}
        result = await backend.debug_disassemble_wasm_module("script-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.disassembleWasmModule"
        assert isinstance(result, dict)

    async def test_debug_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debug_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.enable"

    async def test_debug_get_wasm_bytecode(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"bytecode": {}}
        result = await backend.debug_get_wasm_bytecode("script-1", 0)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.getWasmBytecode"
        assert isinstance(result, dict)

    async def test_debug_next_wasm_disassembly_chunk(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"chunk": {}}
        result = await backend.debug_next_wasm_disassembly_chunk("dis-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.nextWasmDisassemblyChunk"
        assert isinstance(result, dict)

    async def test_debug_pause(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debug_pause()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.pause"

    async def test_debug_pause_on_async_call(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debug_pause_on_async_call("await")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.pauseOnAsyncCall"

    async def test_debug_remove_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debug_remove_breakpoint("bp-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.removeBreakpoint"

    async def test_debug_restart_frame(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debug_restart_frame("cf-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.restartFrame"

    async def test_debug_resume(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debug_resume()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.resume"

    async def test_debug_set_async_call_stack_depth(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debug_set_async_call_stack_depth(32)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.setAsyncCallStackDepth"

    async def test_debug_set_blackbox_execution_contexts(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debug_set_blackbox_execution_contexts(["ctx-1"])
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.setBlackboxExecutionContexts"

    async def test_debug_set_blackbox_patterns(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debug_set_blackbox_patterns(["*.min.js"])
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.setBlackboxPatterns"

    async def test_debug_set_blackboxed_ranges(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debug_set_blackboxed_ranges(
            "script-1", [{"lineNumber": 0, "columnNumber": 0}]
        )
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.setBlackboxedRanges"

    async def test_debug_set_breakpoint_raw(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"breakpointId": "bp-1", "actualLocation": {}}
        result = await backend.debug_set_breakpoint_raw({"scriptId": "s1", "lineNumber": 0})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.setBreakpoint"
        assert isinstance(result, dict)

    async def test_debug_set_breakpoint_by_url(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"breakpointId": "bp-2", "actualLocation": {}}
        result = await backend.debug_set_breakpoint_by_url("script.js", 10)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.setBreakpointByUrl"
        assert isinstance(result, dict)

    async def test_debug_set_breakpoint_on_function_call(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"breakpointId": "bp-3"}
        result = await backend.debug_set_breakpoint_on_function_call("obj-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.setBreakpointOnFunctionCall"
        assert isinstance(result, dict)

    async def test_debug_set_instrumentation_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"breakpointId": "bp-4"}
        result = await backend.debug_set_instrumentation_breakpoint("beforeScriptExecution")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.setInstrumentationBreakpoint"
        assert isinstance(result, dict)

    async def test_debug_set_return_value(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debug_set_return_value({"value": 42})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.setReturnValue"

    async def test_debug_set_variable_value(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debug_set_variable_value("cf-1", 0, "x", {"value": 42})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Debugger.setVariableValue"

    async def test_storage_clear_data_for_origin(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.storage_clear_data_for_origin("https://example.com")
        mock.storage.clear_data_for_origin.assert_awaited_once()

    async def test_storage_get_usage_and_quota(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.storage_get_usage_and_quota("https://example.com")
        assert isinstance(result, dict)

    async def test_storage_get_trust_tokens(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.storage_get_trust_tokens()
        assert isinstance(result, list)

    async def test_storage_clear_trust_tokens(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.storage_clear_trust_tokens("https://example.com")
        mock.storage.clear_trust_tokens.assert_awaited_once()

    async def test_storage_get_shared_storage_entries(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.storage_get_shared_storage_entries("https://example.com")
        assert isinstance(result, list)

    async def test_storage_set_shared_storage_entry(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.storage_set_shared_storage_entry("https://example.com", "k", "v")
        mock.storage.set_shared_storage_entry.assert_awaited_once()

    async def test_storage_delete_shared_storage_entry(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.storage_delete_shared_storage_entry("https://example.com", "k")
        mock.storage.delete_shared_storage_entry.assert_awaited_once()

    async def test_storage_clear_shared_storage_entries(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.storage_clear_shared_storage_entries("https://example.com")
        mock.storage.clear_shared_storage_entries.assert_awaited_once()

    async def test_storage_get_interest_group_details(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.storage_get_interest_group_details("https://example.com", "group1")
        assert isinstance(result, dict)

    async def test_storage_override_quota_for_origin(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.storage_override_quota_for_origin("https://example.com", 1024)
        mock.storage.override_quota_for_origin.assert_awaited_once()

    async def test_network_clear_browser_cache(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_clear_browser_cache()
        mock.network.clear_browser_cache.assert_awaited_once()

    async def test_network_clear_browser_cookies(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_clear_browser_cookies()
        mock.network.clear_browser_cookies.assert_awaited_once()

    async def test_network_delete_cookies(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_delete_cookies("test", "example.com")
        mock.network.delete_cookies.assert_awaited_once()

    async def test_network_set_blocked_urls(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_set_blocked_urls(["https://ads.com/*"])
        mock.network.set_blocked_urls.assert_awaited_once()

    async def test_network_set_bypass_service_worker(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_set_bypass_service_worker(True)
        mock.network.set_bypass_service_worker.assert_awaited_once()

    async def test_network_set_cookie_controls(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_set_cookie_controls("block", "block")
        mock.network.set_cookie_controls.assert_awaited_once()

    async def test_network_set_extra_request_headers(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_set_extra_request_headers({"X-Test": "1"})
        mock.network.set_extra_request_headers.assert_awaited_once()

    async def test_network_set_user_agent_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_set_user_agent_override("TestUA", "en", "Win")
        mock.network.set_user_agent_override.assert_awaited_once()

    async def test_network_replay_xhr(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_replay_xhr("req-1")
        mock.network.replay_xhr.assert_awaited_once()

    async def test_network_load_network_resource(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.network_load_network_resource("frame-1", "https://example.com")
        assert isinstance(result, dict)

    async def test_overlay_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_enable()
        mock.overlay.enable.assert_awaited_once()

    async def test_overlay_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_disable()
        mock.overlay.disable.assert_awaited_once()

    async def test_overlay_highlight_node(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_highlight_node(1)
        mock.overlay.highlight_node.assert_awaited_once()

    async def test_overlay_highlight_quad(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_highlight_quad([0, 0, 100, 0, 100, 100, 0, 100])
        mock.overlay.highlight_quad.assert_awaited_once()

    async def test_overlay_highlight_rect(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_highlight_rect(0, 0, 100, 100)
        mock.overlay.highlight_rect.assert_awaited_once()

    async def test_overlay_set_inspect_mode(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_set_inspect_mode("searchForNode")
        mock.overlay.set_inspect_mode.assert_awaited_once()

    async def test_overlay_set_show_fps_counter(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_set_show_fps_counter(True)
        mock.overlay.set_show_fps_counter.assert_awaited_once()

    async def test_overlay_set_show_paint_rects(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_set_show_paint_rects(True)
        mock.overlay.set_show_paint_rects.assert_awaited_once()

    async def test_overlay_set_show_debug_borders(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_set_show_debug_borders(True)
        mock.overlay.set_show_debug_borders.assert_awaited_once()

    async def test_overlay_set_show_ad_highlights(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_set_show_ad_highlights(True)
        mock.overlay.set_show_ad_highlights.assert_awaited_once()

    async def test_runtime_evaluate(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.runtime_evaluate("1+1")
        assert isinstance(result, dict)

    async def test_runtime_compile_script(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.runtime_compile_script("function(){}")
        assert isinstance(result, dict)

    async def test_runtime_run_script(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.runtime_run_script("1")
        assert isinstance(result, dict)

    async def test_runtime_call_function_on(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.runtime_call_function_on("function(){return 1;}")
        assert isinstance(result, dict)

    async def test_runtime_get_properties(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.runtime_get_properties("obj-1")
        assert isinstance(result, dict)

    async def test_runtime_release_object(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.runtime_release_object("obj-1")
        mock.runtime.release_object.assert_awaited_once()

    async def test_runtime_release_object_group(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.runtime_release_object_group("group-1")
        mock.runtime.release_object_group.assert_awaited_once()

    async def test_runtime_discard_console_entries(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.runtime_discard_console_entries()
        mock.runtime.discard_console_entries.assert_awaited_once()

    async def test_runtime_get_heap_usage(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.runtime_get_heap_usage()
        assert isinstance(result, dict)

    async def test_runtime_global_lexical_scope_names(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.runtime_global_lexical_scope_names()
        assert isinstance(result, dict)

    async def test_runtime_add_binding(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.runtime_add_binding("test-binding")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Runtime.addBinding"

    async def test_runtime_await_promise(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"result": {}}
        result = await backend.runtime_await_promise("obj-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Runtime.awaitPromise"
        assert isinstance(result, dict)

    async def test_runtime_collect_garbage(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.runtime_collect_garbage()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Runtime.collectGarbage"

    async def test_runtime_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.runtime_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Runtime.disable"

    async def test_runtime_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.runtime_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Runtime.enable"

    async def test_runtime_get_exception_details(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"exceptionDetails": {}}
        result = await backend.runtime_get_exception_details("err-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Runtime.getExceptionDetails"
        assert isinstance(result, dict)

    async def test_runtime_get_isolate_id(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"isolateId": "iso-1"}
        result = await backend.runtime_get_isolate_id()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Runtime.getIsolateId"
        assert isinstance(result, dict)

    async def test_runtime_query_objects(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"objects": []}
        result = await backend.runtime_query_objects("proto-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Runtime.queryObjects"
        assert isinstance(result, dict)

    async def test_runtime_remove_binding(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.runtime_remove_binding("test-binding")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Runtime.removeBinding"

    async def test_runtime_run_if_waiting_for_debugger(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.runtime_run_if_waiting_for_debugger()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Runtime.runIfWaitingForDebugger"

    async def test_runtime_set_async_call_stack_depth(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.runtime_set_async_call_stack_depth(32)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Runtime.setAsyncCallStackDepth"

    async def test_runtime_set_custom_object_formatter_enabled(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.runtime_set_custom_object_formatter_enabled(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Runtime.setCustomObjectFormatterEnabled"

    async def test_runtime_set_max_call_stack_size_to_capture(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.runtime_set_max_call_stack_size_to_capture(1000)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Runtime.setMaxCallStackSizeToCapture"

    async def test_runtime_terminate_execution(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.runtime_terminate_execution()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Runtime.terminateExecution"

    # ── Schema ───────────────────────────────────────────────

    async def test_schema_get_domains(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"domains": []}
        result = await backend.schema_get_domains()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Schema.getDomains"
        assert isinstance(result, dict)

    # ── Security ────────────────────────────────────────────

    async def test_security_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.security_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Security.disable"

    async def test_security_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.security_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Security.enable"

    async def test_security_get_visible_security_state(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"securityState": "secure"}
        result = await backend.security_get_visible_security_state()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Security.getVisibleSecurityState"
        assert isinstance(result, dict)

    async def test_security_handle_certificate_error(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.security_handle_certificate_error(1, "continue")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Security.handleCertificateError"

    async def test_security_set_ignore_certificate_errors(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.security_set_ignore_certificate_errors(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Security.setIgnoreCertificateErrors"

    async def test_security_set_override_certificate_errors(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.security_set_override_certificate_errors(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Security.setOverrideCertificateErrors"

    # ── Sensor ───────────────────────────────────────────────

    async def test_sensor_clear_sensor_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.sensor_clear_sensor_override("accelerometer")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Sensor.clearSensorOverride"

    async def test_sensor_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.sensor_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Sensor.disable"

    async def test_sensor_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.sensor_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Sensor.enable"

    async def test_sensor_set_sensor_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.sensor_set_sensor_override("accelerometer")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Sensor.setSensorOverride"

    async def test_target_get_targets(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.target_get_targets()
        assert isinstance(result, list)

    async def test_target_create_target(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.target_create_target("https://example.com")
        assert isinstance(result, str)

    async def test_target_close_target(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.target_close_target("tab-1")
        mock.target.close_target.assert_awaited_once()

    async def test_target_activate_target(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.target_activate_target("tab-1")
        mock.target.activate_target.assert_awaited_once()

    async def test_target_attach_to_target(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.target_attach_to_target("tab-1")
        assert isinstance(result, str)

    async def test_target_detach_from_target(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.target_detach_from_target("sess-1")
        mock.target.detach_from_target.assert_awaited_once()

    async def test_target_set_auto_attach(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.target_set_auto_attach(True)
        mock.target.set_auto_attach.assert_awaited_once()

    async def test_target_set_discover_targets(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.target_set_discover_targets(True)
        mock.target.set_discover_targets.assert_awaited_once()

    async def test_target_get_target_info(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.target_get_target_info("tab-1")
        assert isinstance(result, dict)

    async def test_target_create_browser_context(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.target_create_browser_context()
        assert isinstance(result, str)

    async def test_dom_describe_node(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.dom_describe_node(1)
        assert isinstance(result, dict)

    async def test_dom_get_outer_html(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.dom_get_outer_html(1)
        assert isinstance(result, str)

    async def test_dom_remove_node(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_remove_node(1)
        mock.dom.remove_node.assert_awaited_once()

    async def test_dom_set_node_value(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_set_node_value(1, "test")
        mock.dom.set_node_value.assert_awaited_once()

    async def test_dom_set_outer_html(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_set_outer_html(1, "<p>test</p>")
        mock.dom.set_outer_html.assert_awaited_once()

    async def test_dom_request_node(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.dom_request_node(1)
        assert isinstance(result, int)

    async def test_dom_resolve_node(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.dom_resolve_node(1)
        assert isinstance(result, dict)

    async def test_dom_set_attribute_value(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_set_attribute_value(1, "class", "test")
        mock.dom.set_attribute_value.assert_awaited_once()

    async def test_dom_remove_attribute(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_remove_attribute(1, "class")
        mock.dom.remove_attribute.assert_awaited_once()

    async def test_dom_request_child_nodes(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_request_child_nodes(1)
        mock.dom.request_child_nodes.assert_awaited_once()

    # ── DOM batch 3 ───────────────────────────────────────

    async def test_dom_collect_class_names_from_subtree(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"classNames": ["foo", "bar"]}
        result = await backend.dom_collect_class_names_from_subtree(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.collectClassNamesFromSubtree"
        assert result == ["foo", "bar"]

    async def test_dom_copy_to(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_copy_to(1, 2)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.copyTo"

    async def test_dom_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.disable"

    async def test_dom_discard_search_results(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_discard_search_results("search-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.discardSearchResults"

    async def test_dom_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.enable"

    async def test_dom_focus_node(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_focus_node(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.focus"

    async def test_dom_force_show_popover(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_force_show_popover(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.forceShowPopover"

    async def test_dom_get_anchor_element(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"nodeId": 5}
        result = await backend.dom_get_anchor_element(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.getAnchorElement"
        assert result == {"nodeId": 5}

    async def test_dom_get_node_attribute(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"value": "test"}
        result = await backend.dom_get_node_attribute(1, "class")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.getAttribute"
        assert result == "test"

    async def test_dom_get_container_for_node(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"nodeId": 3}
        result = await backend.dom_get_container_for_node(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.getContainerForNode"
        assert result == {"nodeId": 3}

    # ── DOM batch 4 ───────────────────────────────────────

    async def test_dom_get_detached_dom_nodes(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"detachedNodes": [{"nodeId": 1}]}
        result = await backend.dom_get_detached_dom_nodes()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.getDetachedDomNodes"
        assert result == [{"nodeId": 1}]

    async def test_dom_get_element_by_relation(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"nodeId": 5}
        result = await backend.dom_get_element_by_relation(1, "popover")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.getElementByRelation"
        assert result == {"nodeId": 5}

    async def test_dom_get_file_info(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"name": "test.txt"}
        result = await backend.dom_get_file_info(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.getFileInfo"
        assert result == {"name": "test.txt"}

    async def test_dom_get_frame_owner(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"nodeId": 3}
        result = await backend.dom_get_frame_owner("frame-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.getFrameOwner"
        assert result == {"nodeId": 3}

    async def test_dom_get_node_stack_traces(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"creation": {}}
        result = await backend.dom_get_node_stack_traces(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.getNodeStackTraces"
        assert result == {"creation": {}}

    async def test_dom_get_nodes_for_subtree_by_style(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"nodeIds": [1, 2]}
        result = await backend.dom_get_nodes_for_subtree_by_style(1, ["color"])
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.getNodesForSubtreeByStyle"
        assert result == [1, 2]

    async def test_dom_get_querying_descendants_for_container(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"nodeIds": [1, 2]}
        result = await backend.dom_get_querying_descendants_for_container(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.getQueryingDescendantsForContainer"
        assert result == [1, 2]

    async def test_dom_get_relayout_boundary(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"nodeId": 7}
        result = await backend.dom_get_relayout_boundary(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.getRelayoutBoundary"
        assert result == {"nodeId": 7}

    async def test_dom_get_top_layer_elements(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"nodes": [{"nodeId": 1}]}
        result = await backend.dom_get_top_layer_elements()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.getTopLayerElements"
        assert result == [{"nodeId": 1}]

    async def test_dom_hide_highlight(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_hide_highlight()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.hideHighlight"

    # ── DOM batch 5 ───────────────────────────────────────

    async def test_dom_highlight_node(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_highlight_node(1, {"showInfo": True})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.highlightNode"

    async def test_dom_highlight_rect(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_highlight_rect(0, 0, 100, 100, {"showInfo": True})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.highlightRect"

    async def test_dom_mark_undoable_state(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_mark_undoable_state()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.markUndoableState"

    async def test_dom_move_to(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_move_to(1, 2)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.moveTo"

    async def test_dom_push_node_by_path_to_frontend(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"nodeId": 5}
        result = await backend.dom_push_node_by_path_to_frontend("body/div")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.pushNodeByPathToFrontend"
        assert result == {"nodeId": 5}

    async def test_dom_push_nodes_by_backend_ids_to_frontend(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"nodes": [{"nodeId": 1}]}
        result = await backend.dom_push_nodes_by_backend_ids_to_frontend([1, 2])
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.pushNodesByBackendIdsToFrontend"
        assert result == {"nodes": [{"nodeId": 1}]}

    async def test_dom_query_selector(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"nodeId": 3}
        result = await backend.dom_query_selector(1, ".foo")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.querySelector"
        assert result == {"nodeId": 3}

    async def test_dom_query_selector_all(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"nodes": [{"nodeId": 1}, {"nodeId": 2}]}
        result = await backend.dom_query_selector_all(1, ".foo")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.querySelectorAll"
        assert result == [{"nodeId": 1}, {"nodeId": 2}]

    async def test_dom_redo(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_redo()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.redo"

    async def test_dom_remove_node_by_id(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_remove_node_by_id(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.removeNode"

    # ── DOM batch 6 (final) ───────────────────────────────

    async def test_dom_set_attributes_as_text(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_set_attributes_as_text(1, 'class="foo"')
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.setAttributesAsText"

    async def test_dom_set_file_input_files(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_set_file_input_files(1, ["/path/to/file"])
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.setFileInputFiles"

    async def test_dom_set_inspected_node(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_set_inspected_node(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.setInspectedNode"

    async def test_dom_set_node_name(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"nodeId": 2}
        result = await backend.dom_set_node_name(1, "div")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.setNodeName"
        assert result == {"nodeId": 2}

    async def test_dom_set_node_stack_traces_enabled(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_set_node_stack_traces_enabled(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.setNodeStackTracesEnabled"

    async def test_dom_set_text_content(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_set_text_content(1, "hello")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.setTextContent"

    async def test_dom_undo(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_undo()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOM.undo"

    # ── DOMDebugger ────────────────────────────────────────

    async def test_dom_debugger_get_event_listeners(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"listeners": [{"type": "click"}]}
        result = await backend.dom_debugger_get_event_listeners("obj-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMDebugger.getEventListeners"
        assert result == [{"type": "click"}]

    async def test_dom_debugger_remove_dom_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_remove_dom_breakpoint(1, "subtree-modified")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMDebugger.removeDOMBreakpoint"

    async def test_dom_debugger_remove_event_listener_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_remove_event_listener_breakpoint("click")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMDebugger.removeEventListenerBreakpoint"

    async def test_dom_debugger_remove_instrumentation_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_remove_instrumentation_breakpoint("scriptFirstStatement")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMDebugger.removeInstrumentationBreakpoint"

    async def test_dom_debugger_remove_xhr_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_remove_xhr_breakpoint("https://example.com")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMDebugger.removeXHRBreakpoint"

    async def test_dom_debugger_set_break_on_csp_violation(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_set_break_on_csp_violation(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMDebugger.setBreakOnCSPViolation"

    async def test_dom_debugger_set_dom_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_set_dom_breakpoint(1, "subtree-modified")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMDebugger.setDOMBreakpoint"

    async def test_dom_debugger_set_event_listener_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_set_event_listener_breakpoint("click")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMDebugger.setEventListenerBreakpoint"

    async def test_dom_debugger_set_instrumentation_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_set_instrumentation_breakpoint("scriptFirstStatement")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMDebugger.setInstrumentationBreakpoint"

    async def test_dom_debugger_set_xhr_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_set_xhr_breakpoint("https://example.com")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMDebugger.setXHRBreakpoint"

    # ── Emulation batch 2 ─────────────────────────────────

    async def test_add_screen(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.add_screen({"width": 1920, "height": 1080})
        mock.send.assert_awaited_once()
        call_args = mock.send.call_args
        assert call_args.args[0] == "Emulation.addScreen"

    async def test_can_emulate(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"result": True})
        result = await backend.can_emulate()
        assert isinstance(result, bool)
        assert result is True

    async def test_clear_auto_dark_mode_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.clear_auto_dark_mode_override()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.clearAutoDarkModeOverride"

    async def test_clear_default_background_color_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.clear_default_background_color_override()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.clearDefaultBackgroundColorOverride"

    async def test_clear_device_posture_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.clear_device_posture_override()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.clearDevicePostureOverride"

    async def test_clear_display_features_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.clear_display_features_override()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.clearDisplayFeaturesOverride"

    async def test_clear_geolocation_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.clear_geolocation_override()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.clearGeolocationOverride"

    async def test_clear_timezone_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.clear_timezone_override()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.clearTimezoneOverride"

    async def test_get_overridden_sensor_information(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.get_overridden_sensor_information("accelerometer")
        assert isinstance(result, dict)

    async def test_get_screen_infos(self) -> None:
        backend, _, _ = _make_mock_backend()
        result = await backend.get_screen_infos()
        assert isinstance(result, dict)

    # ── Emulation batch 3 ─────────────────────────────────

    async def test_remove_screen(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.remove_screen("screen-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.removeScreen"

    async def test_reset_page_scale_factor(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.reset_page_scale_factor()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.resetPageScaleFactor"

    async def test_set_auto_dark_mode_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_auto_dark_mode_override(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setAutoDarkModeOverride"

    async def test_set_automation_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_automation_override(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setAutomationOverride"

    async def test_set_cpu_throttling_rate(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_cpu_throttling_rate(4.0)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setCPUThrottlingRate"

    async def test_set_data_saver_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_data_saver_override(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setDataSaverOverride"

    async def test_set_default_background_color_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_default_background_color_override({"r": 0, "g": 0, "b": 0, "a": 1})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setDefaultBackgroundColorOverride"

    async def test_set_device_posture_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_device_posture_override("continuous")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setDevicePostureOverride"

    async def test_set_disabled_image_types(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_disabled_image_types(["avif", "webp"])
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setDisabledImageTypes"

    async def test_set_display_features_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_display_features_override([{"type": "fold"}])
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setDisplayFeaturesOverride"

    # ── Emulation batch 4 ─────────────────────────────────

    async def test_set_document_cookie_disabled(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_document_cookie_disabled(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setDocumentCookieDisabled"

    async def test_set_emit_touch_events_for_mouse(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_emit_touch_events_for_mouse(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setEmitTouchEventsForMouse"

    async def test_set_emulated_media_feature(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_emulated_media_feature(
            [{"name": "prefers-color-scheme", "value": "dark"}]
        )
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setEmulatedMediaFeature"

    async def test_set_emulated_os_text_scale(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_emulated_os_text_scale(1.5)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setEmulatedOSTextScale"

    async def test_set_focus_emulation_enabled(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_focus_emulation_enabled(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setFocusEmulationEnabled"

    async def test_set_geolocation_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_geolocation_override(37.7749, -122.4194)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setGeolocationOverride"

    async def test_set_hardware_concurrency_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_hardware_concurrency_override(4)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setHardwareConcurrencyOverride"

    async def test_set_locale_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_locale_override("en-US")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setLocaleOverride"

    async def test_set_navigator_overrides(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_navigator_overrides({"platform": "Linux"})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setNavigatorOverrides"

    async def test_set_page_scale_factor(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_page_scale_factor(2.0)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setPageScaleFactor"

    # ── Emulation batch 5 (final) ────────────────────────

    async def test_set_pressure_source_override_enabled(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_pressure_source_override_enabled("touch", True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setPressureSourceOverrideEnabled"

    async def test_set_pressure_state_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_pressure_state_override("touch", "known", 1.0)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setPressureStateOverride"

    async def test_set_primary_screen(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_primary_screen("screen-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setPrimaryScreen"

    async def test_set_safe_area_insets_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_safe_area_insets_override({"top": 50, "bottom": 0})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setSafeAreaInsetsOverride"

    async def test_set_scrollbars_hidden(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_scrollbars_hidden(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setScrollbarsHidden"

    async def test_set_sensor_override_enabled(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_sensor_override_enabled("accelerometer", True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setSensorOverrideEnabled"

    async def test_set_sensor_override_readings(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_sensor_override_readings(
            "accelerometer", [{"x": 1.0, "y": 0.0, "z": 0.0}]
        )
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setSensorOverrideReadings"

    async def test_set_small_viewport_height_difference_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_small_viewport_height_difference_override(10.0)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setSmallViewportHeightDifferenceOverride"

    async def test_set_timezone_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_timezone_override("America/New_York")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setTimezoneOverride"

    async def test_set_touch_emulation_enabled(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_touch_emulation_enabled(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setTouchEmulationEnabled"

    async def test_set_user_agent_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_user_agent_override("Mozilla/5.0")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setUserAgentOverride"

    async def test_set_virtual_time_policy(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.set_virtual_time_policy("advance")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.setVirtualTimePolicy"

    async def test_update_screen(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.update_screen("screen-1", {"width": 1920, "height": 1080})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Emulation.updateScreen"

    # ── DeviceAccess ────────────────────────────────────────

    async def test_device_access_cancel_prompt(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.device_access_cancel_prompt("prompt-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DeviceAccess.cancelPrompt"

    async def test_device_access_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.device_access_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DeviceAccess.disable"

    async def test_device_access_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.device_access_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DeviceAccess.enable"

    async def test_device_access_select_prompt(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.device_access_select_prompt("prompt-1", "device-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DeviceAccess.selectPrompt"

    # ── DeviceOrientation ───────────────────────────────────

    async def test_device_orientation_clear_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.device_orientation_clear_override()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DeviceOrientation.clearDeviceOrientationOverride"

    async def test_device_orientation_set_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.device_orientation_set_override(1.0, 2.0, 3.0)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DeviceOrientation.setDeviceOrientationOverride"

    # ── DigitalCredentials ──────────────────────────────────

    async def test_digital_credentials_set_virtual_wallet_behavior(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.digital_credentials_set_virtual_wallet_behavior({"mode": "test"})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DigitalCredentials.setVirtualWalletBehavior"

    # ── DOMSnapshot ─────────────────────────────────────────

    async def test_dom_snapshot_capture_snapshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"doc": {}}
        result = await backend.dom_snapshot_capture_snapshot()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMSnapshot.captureSnapshot"
        assert isinstance(result, dict)

    async def test_dom_snapshot_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_snapshot_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMSnapshot.disable"

    async def test_dom_snapshot_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_snapshot_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMSnapshot.enable"

    async def test_dom_snapshot_get_snapshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"doc": {}}
        result = await backend.dom_snapshot_get_snapshot()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMSnapshot.getSnapshot"
        assert isinstance(result, dict)

    # ── DOMStorage ──────────────────────────────────────────

    async def test_dom_storage_clear(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_storage_clear(
            {"securityOrigin": "https://example.com", "isLocalStorage": True}
        )
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMStorage.clear"

    async def test_dom_storage_clear_items(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_storage_clear_items(
            {"securityOrigin": "https://example.com", "isLocalStorage": True}
        )
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMStorage.clear"

    async def test_dom_storage_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_storage_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMStorage.disable"

    async def test_dom_storage_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_storage_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMStorage.enable"

    async def test_dom_storage_get_items(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"items": [{"key": "k", "value": "v"}]}
        result = await backend.dom_storage_get_items(
            {"securityOrigin": "https://example.com", "isLocalStorage": True}
        )
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMStorage.getDOMStorageItems"
        assert isinstance(result, list)

    async def test_dom_storage_remove_item(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_storage_remove_item(
            {"securityOrigin": "https://example.com", "isLocalStorage": True}, "key1"
        )
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMStorage.removeDOMStorageItem"

    async def test_dom_storage_set_item(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_storage_set_item(
            {"securityOrigin": "https://example.com", "isLocalStorage": True}, "key1", "val1"
        )
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "DOMStorage.setDOMStorageItem"

    # ── EventBreakpoints ────────────────────────────────────

    async def test_event_breakpoints_clear_instrumentation_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.event_breakpoints_clear_instrumentation_breakpoint("Event.source")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "EventBreakpoints.clearInstrumentationBreakpoint"

    async def test_event_breakpoints_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.event_breakpoints_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "EventBreakpoints.disable"

    async def test_event_breakpoints_remove_instrumentation_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.event_breakpoints_remove_instrumentation_breakpoint("Event.source")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "EventBreakpoints.removeInstrumentationBreakpoint"

    async def test_event_breakpoints_set_instrumentation_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.event_breakpoints_set_instrumentation_breakpoint("Event.source")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "EventBreakpoints.setInstrumentationBreakpoint"

    # ── Extensions ──────────────────────────────────────────

    async def test_extensions_clear_storage_items(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.extensions_clear_storage_items("ext-1", "local")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Extensions.clearStorageItems"

    async def test_extensions_get_storage_items(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"items": []}
        result = await backend.extensions_get_storage_items("ext-1", "local")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Extensions.getStorageItems"
        assert isinstance(result, dict)

    async def test_extensions_remove_storage_items(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.extensions_remove_storage_items("ext-1", "local", ["key1"])
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Extensions.removeStorageItems"

    async def test_extensions_set_storage_items(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.extensions_set_storage_items("ext-1", "local", [{"key": "k", "value": "v"}])
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Extensions.setStorageItems"

    async def test_extensions_trigger_action(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.extensions_trigger_action("ext-1", "action-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Extensions.triggerAction"

    # ── FedCm ───────────────────────────────────────────────

    async def test_fed_cm_click_dialog_button(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fed_cm_click_dialog_button("dialog-1", 0)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "FedCm.clickDialogButton"

    async def test_fed_cm_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fed_cm_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "FedCm.disable"

    async def test_fed_cm_dismiss_dialog(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fed_cm_dismiss_dialog("dialog-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "FedCm.dismissDialog"

    async def test_fed_cm_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fed_cm_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "FedCm.enable"

    async def test_fed_cm_open_url(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fed_cm_open_url("dialog-1", 0, "https://example.com")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "FedCm.openUrl"

    async def test_fed_cm_reset_cooldown(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fed_cm_reset_cooldown()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "FedCm.resetCooldown"

    async def test_fed_cm_select_account(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fed_cm_select_account("dialog-1", 0)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "FedCm.selectAccount"

    # ── Fetch ───────────────────────────────────────────────

    async def test_fetch_continue_request(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fetch_continue_request("req-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Fetch.continueRequest"

    async def test_fetch_continue_request_with_auth(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fetch_continue_request_with_auth("req-1", {"response": "Default"})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Fetch.continueWithAuth"

    async def test_fetch_continue_response(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fetch_continue_response("req-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Fetch.continueResponse"

    async def test_fetch_continue_with_auth(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fetch_continue_with_auth("req-1", {"response": "Default"})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Fetch.continueWithAuth"

    async def test_fetch_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fetch_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Fetch.disable"

    async def test_fetch_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fetch_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Fetch.enable"

    async def test_fetch_fail_request(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fetch_fail_request("req-1", "Failed")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Fetch.failRequest"

    async def test_fetch_fulfill_request(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fetch_fulfill_request("req-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Fetch.fulfillRequest"

    async def test_fetch_get_request_post_data(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"postData": "data"}
        result = await backend.fetch_get_request_post_data("req-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Fetch.getRequestPostData"
        assert isinstance(result, str)

    async def test_fetch_take_response_body_as_stream(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"stream": "s-1"}
        result = await backend.fetch_take_response_body_as_stream("req-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Fetch.takeResponseBodyAsStream"
        assert isinstance(result, dict)

    # ── FileSystem ──────────────────────────────────────────

    async def test_file_system_get_directory(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"directory": {}}
        result = await backend.file_system_get_directory("https://example.com", "local")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "FileSystem.getDirectory"
        assert isinstance(result, dict)

    # ── HeadlessExperimental ────────────────────────────────

    async def test_headless_experimental_begin_frame(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"frameData": {}}
        result = await backend.headless_experimental_begin_frame()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "HeadlessExperimental.beginFrame"
        assert isinstance(result, dict)

    async def test_headless_experimental_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.headless_experimental_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "HeadlessExperimental.disable"

    async def test_headless_experimental_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.headless_experimental_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "HeadlessExperimental.enable"

    # ── Inspector ───────────────────────────────────────────

    async def test_inspector_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.inspector_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Inspector.disable"

    async def test_inspector_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.inspector_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Inspector.enable"

    # ── Preload ──────────────────────────────────────────────

    async def test_preload_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.preload_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Preload.disable"

    async def test_preload_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.preload_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Preload.enable"

    async def test_preload_get_preload_policy(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"policy": {}}
        result = await backend.preload_get_preload_policy()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Preload.getPreloadPolicy"
        assert isinstance(result, dict)

    async def test_preload_set_preload_policy(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.preload_set_preload_policy({"key": "value"})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Preload.setPreloadPolicy"

    # ── Profiler ─────────────────────────────────────────────

    async def test_profiler_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.profiler_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Profiler.disable"

    async def test_profiler_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.profiler_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Profiler.enable"

    async def test_profiler_get_best_effort_coverage(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"result": []}
        result = await backend.profiler_get_best_effort_coverage()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Profiler.getBestEffortCoverage"
        assert isinstance(result, dict)

    async def test_profiler_set_sampling_interval(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.profiler_set_sampling_interval(1000)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Profiler.setSamplingInterval"

    async def test_profiler_start(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.profiler_start()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Profiler.start"

    async def test_profiler_start_precise_coverage(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"timestamp": 0}
        result = await backend.profiler_start_precise_coverage(call_count=True, detailed=True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Profiler.startPreciseCoverage"
        assert isinstance(result, dict)

    async def test_profiler_stop(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"profile": {}}
        result = await backend.profiler_stop()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Profiler.stop"
        assert isinstance(result, dict)

    async def test_profiler_stop_precise_coverage(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.profiler_stop_precise_coverage()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Profiler.stopPreciseCoverage"

    async def test_profiler_take_precise_coverage(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"result": []}
        result = await backend.profiler_take_precise_coverage()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Profiler.takePreciseCoverage"
        assert isinstance(result, dict)

    # ── PWA ──────────────────────────────────────────────────

    async def test_pwa_change_app_user_settings(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.pwa_change_app_user_settings("app-1", {"key": "value"})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "PWA.changeAppUserSettings"

    async def test_pwa_get_os_app_state(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"state": {}}
        result = await backend.pwa_get_os_app_state("app-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "PWA.getOsAppState"
        assert isinstance(result, dict)

    async def test_pwa_install(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.pwa_install("manifest-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "PWA.install"

    async def test_pwa_launch_files_in_app(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"targetId": "target-1"}
        result = await backend.pwa_launch_files_in_app("app-1", ["/path/file.txt"])
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "PWA.launchFilesInApp"
        assert isinstance(result, dict)

    async def test_pwa_open_current_page_in_app(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"targetId": "target-1"}
        result = await backend.pwa_open_current_page_in_app("app-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "PWA.openCurrentPageInApp"
        assert isinstance(result, dict)

    async def test_pwa_uninstall(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.pwa_uninstall("app-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "PWA.uninstall"

    # ── IO ──────────────────────────────────────────────────

    async def test_io_read(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"data": "abc", "eof": True}
        result = await backend.io_read("handle-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "IO.read"
        assert isinstance(result, dict)

    async def test_io_resolve_blob(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"uuid": "uuid-1"}
        result = await backend.io_resolve_blob("obj-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "IO.resolveBlob"
        assert isinstance(result, str)

    # ── HeapProfiler ────────────────────────────────────────

    async def test_heap_profiler_add_inspected_heap_object(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_add_inspected_heap_object("heap-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "HeapProfiler.addInspectedHeapObject"

    async def test_heap_profiler_collect_garbage(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_collect_garbage()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "HeapProfiler.collectGarbage"

    async def test_heap_profiler_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "HeapProfiler.disable"

    async def test_heap_profiler_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "HeapProfiler.enable"

    async def test_heap_profiler_get_heap_object_id(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"heapSnapshotObjectId": "hsoid-1"}
        result = await backend.heap_profiler_get_heap_object_id("obj-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "HeapProfiler.getHeapObjectId"
        assert isinstance(result, str)

    async def test_heap_profiler_get_object_by_heap_object_id(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"result": {}}
        result = await backend.heap_profiler_get_object_by_heap_object_id("hoid-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "HeapProfiler.getObjectByHeapObjectId"
        assert isinstance(result, dict)

    async def test_heap_profiler_get_sampling_profile(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"profile": {}}
        result = await backend.heap_profiler_get_sampling_profile()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "HeapProfiler.getSamplingProfile"
        assert isinstance(result, dict)

    async def test_heap_profiler_start_sampling(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_start_sampling(1024)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "HeapProfiler.startSampling"

    async def test_heap_profiler_start_tracking_heap_objects(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_start_tracking_heap_objects(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "HeapProfiler.startTrackingHeapObjects"

    async def test_heap_profiler_stop_sampling(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"profile": {}}
        result = await backend.heap_profiler_stop_sampling()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "HeapProfiler.stopSampling"
        assert isinstance(result, dict)

    async def test_heap_profiler_stop_tracking_heap_objects(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_stop_tracking_heap_objects(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "HeapProfiler.stopTrackingHeapObjects"

    async def test_heap_profiler_take_heap_snapshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_take_heap_snapshot(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "HeapProfiler.takeHeapSnapshot"

    # ── IndexedDB ───────────────────────────────────────────

    async def test_indexed_db_clear_object_store(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.indexed_db_clear_object_store("https://example.com", "db1", "store1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "IndexedDB.clearObjectStore"

    async def test_indexed_db_delete_database(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.indexed_db_delete_database("https://example.com", "db1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "IndexedDB.deleteDatabase"

    async def test_indexed_db_delete_object_store_entries(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.indexed_db_delete_object_store_entries(
            "https://example.com", "db1", "store1", {"lower": 0}
        )
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "IndexedDB.deleteObjectStoreEntries"

    async def test_indexed_db_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.indexed_db_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "IndexedDB.disable"

    async def test_indexed_db_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.indexed_db_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "IndexedDB.enable"

    async def test_indexed_db_get_metadata(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"entriesCount": 10}
        result = await backend.indexed_db_get_metadata("https://example.com", "db1", "store1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "IndexedDB.getMetadata"
        assert isinstance(result, dict)

    async def test_indexed_db_request_data(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"data": []}
        result = await backend.indexed_db_request_data(
            "https://example.com", "db1", "store1", "idx1"
        )
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "IndexedDB.requestData"
        assert isinstance(result, dict)

    async def test_indexed_db_request_database(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"objectStores": []}
        result = await backend.indexed_db_request_database("https://example.com", "db1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "IndexedDB.requestDatabase"
        assert isinstance(result, dict)

    async def test_indexed_db_request_database_names(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"databaseNames": ["db1"]}
        result = await backend.indexed_db_request_database_names("https://example.com")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "IndexedDB.requestDatabaseNames"
        assert isinstance(result, dict)

    # ── LayerTree ───────────────────────────────────────────

    async def test_layer_tree_compositing_reasons(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"reasons": []}
        result = await backend.layer_tree_compositing_reasons("layer-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "LayerTree.compositingReasons"
        assert isinstance(result, dict)

    async def test_layer_tree_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.layer_tree_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "LayerTree.disable"

    async def test_layer_tree_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.layer_tree_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "LayerTree.enable"

    async def test_layer_tree_load_snapshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"snapshotId": "snap-1"}
        result = await backend.layer_tree_load_snapshot([{"layers": []}])
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "LayerTree.loadSnapshot"
        assert isinstance(result, dict)

    async def test_layer_tree_make_snapshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"snapshotId": "snap-1"}
        result = await backend.layer_tree_make_snapshot("layer-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "LayerTree.makeSnapshot"
        assert isinstance(result, dict)

    async def test_layer_tree_profile_snapshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"timings": []}
        result = await backend.layer_tree_profile_snapshot("snap-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "LayerTree.profileSnapshot"
        assert isinstance(result, dict)

    async def test_layer_tree_release_snapshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.layer_tree_release_snapshot("snap-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "LayerTree.releaseSnapshot"

    async def test_layer_tree_replay_snapshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"result": {}}
        result = await backend.layer_tree_replay_snapshot("snap-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "LayerTree.replaySnapshot"
        assert isinstance(result, dict)

    async def test_layer_tree_snapshot_command_log(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"commands": []}
        result = await backend.layer_tree_snapshot_command_log("snap-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "LayerTree.snapshotCommandLog"
        assert isinstance(result, dict)

    # ── Log ─────────────────────────────────────────────────

    async def test_log_clear(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.log_clear()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Log.clear"

    async def test_log_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.log_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Log.disable"

    async def test_log_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.log_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Log.enable"

    async def test_log_start_violations_report(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.log_start_violations_report([{"name": "longTask", "threshold": 100}])
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Log.startViolationsReport"

    async def test_log_stop_violations_report(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.log_stop_violations_report()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Log.stopViolationsReport"

    # ── Media ───────────────────────────────────────────────

    async def test_media_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.media_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Media.disable"

    async def test_media_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.media_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Media.enable"

    # ── Memory ──────────────────────────────────────────────

    async def test_memory_forcibly_purge_javascript_memory(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.memory_forcibly_purge_javascript_memory()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Memory.forciblyPurgeJavaScriptMemory"

    async def test_memory_get_all_time_sampling_profile(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"profile": {}}
        result = await backend.memory_get_all_time_sampling_profile()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Memory.getAllTimeSamplingProfile"
        assert isinstance(result, dict)

    async def test_memory_get_browser_sampling_profile(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"profile": {}}
        result = await backend.memory_get_browser_sampling_profile()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Memory.getBrowserSamplingProfile"
        assert isinstance(result, dict)

    async def test_memory_get_dom_counters(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"documents": 1, "nodes": 10}
        result = await backend.memory_get_dom_counters()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Memory.getDOMCounters"
        assert isinstance(result, dict)

    async def test_memory_get_dom_counters_for_leak_detection(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"documents": 1, "nodes": 10}
        result = await backend.memory_get_dom_counters_for_leak_detection()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Memory.getDOMCountersForLeakDetection"
        assert isinstance(result, dict)

    async def test_memory_get_sampling_profile(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"profile": {}}
        result = await backend.memory_get_sampling_profile()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Memory.getSamplingProfile"
        assert isinstance(result, dict)

    async def test_memory_prepare_for_leak_detection(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.memory_prepare_for_leak_detection()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Memory.prepareForLeakDetection"

    async def test_memory_set_pressure_notifications_suppressed(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.memory_set_pressure_notifications_suppressed(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Memory.setPressureNotificationsSuppressed"

    async def test_memory_simulate_pressure_notification(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.memory_simulate_pressure_notification("moderate")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Memory.simulatePressureNotification"

    async def test_memory_start_sampling(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.memory_start_sampling(1024)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Memory.startSampling"

    async def test_memory_stop_sampling(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.memory_stop_sampling()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Memory.stopSampling"

    # ── Console ─────────────────────────────────────────────

    async def test_console_clear_messages(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.console_clear_messages()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Console.clearMessages"

    async def test_console_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.console_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Console.disable"

    async def test_console_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.console_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Console.enable"

    # ── CrashReportContext ──────────────────────────────────

    async def test_crash_report_context_get_entries(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = []
        result = await backend.crash_report_context_get_entries()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "CrashReportContext.getEntries"
        assert isinstance(result, list)

    # ── Input (low-level CDP) ───────────────────────────────

    async def test_input_cancel_dragging(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.input_cancel_dragging()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Input.cancelDragging"

    async def test_input_dispatch_drag_event(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.input_dispatch_drag_event("dragEnter", 10, 20)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Input.dispatchDragEvent"

    async def test_input_dispatch_key_event(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.input_dispatch_key_event("keyDown", key="a")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Input.dispatchKeyEvent"

    async def test_input_dispatch_mouse_event(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.input_dispatch_mouse_event("mousePressed", 10, 20)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Input.dispatchMouseEvent"

    async def test_input_dispatch_touch_event(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.input_dispatch_touch_event("touchStart", [{"x": 0, "y": 0}])
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Input.dispatchTouchEvent"

    async def test_input_emulate_touch_from_mouse_event(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.input_emulate_touch_from_mouse_event("mousePressed", 10, 20)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Input.emulateTouchFromMouseEvent"

    async def test_input_ime_set_composition(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.input_ime_set_composition("text", 0, 4)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Input.imeSetComposition"

    async def test_input_insert_text(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.input_insert_text("hello")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Input.insertText"

    async def test_input_set_ignore_input_events(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.input_set_ignore_input_events(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Input.setIgnoreInputEvents"

    async def test_input_set_intercept_drags(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.input_set_intercept_drags(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Input.setInterceptDrags"

    async def test_input_synthesize_pinch_gesture(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.input_synthesize_pinch_gesture(10, 20, 2.0)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Input.synthesizePinchGesture"

    async def test_input_synthesize_scroll_gesture(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.input_synthesize_scroll_gesture(10, 20, y_distance=100)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Input.synthesizeScrollGesture"

    async def test_input_synthesize_tap_gesture(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.input_synthesize_tap_gesture(10, 20)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Input.synthesizeTapGesture"

    # ── Network (additional CDP methods) ────────────────────

    async def test_network_clear_accepted_encodings_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_clear_accepted_encodings_override()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.clearAcceptedEncodingsOverride"

    async def test_network_configure_durable_messages(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_configure_durable_messages({"key": "value"})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.configureDurableMessages"

    async def test_network_delete_device_bound_session(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_delete_device_bound_session("session-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.deleteDeviceBoundSession"

    async def test_network_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.disable"

    async def test_network_emulate_network_conditions_by_rule(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_emulate_network_conditions_by_rule(offline=True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.emulateNetworkConditionsByRule"

    async def test_network_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.enable"

    async def test_network_enable_device_bound_sessions(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_enable_device_bound_sessions()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.enableDeviceBoundSessions"

    async def test_network_enable_reporting_api(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_enable_reporting_api(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.enableReportingApi"

    async def test_network_fetch_schemeful_site(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {}
        result = await backend.network_fetch_schemeful_site("req-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.fetchSchemefulSite"
        assert isinstance(result, dict)

    async def test_network_get_certificate(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {}
        result = await backend.network_get_certificate("https://example.com")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.getCertificate"
        assert isinstance(result, dict)

    async def test_network_get_request_post_data(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"postData": "data"}
        result = await backend.network_get_request_post_data("req-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.getRequestPostData"
        assert isinstance(result, str)

    async def test_network_get_response_body_for_interception(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"body": "data"}
        result = await backend.network_get_response_body_for_interception("int-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.getResponseBodyForInterception"
        assert isinstance(result, str)

    async def test_network_get_security_isolation_status(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {}
        result = await backend.network_get_security_isolation_status()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.getSecurityIsolationStatus"
        assert isinstance(result, dict)

    async def test_network_override_network_state(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_override_network_state({"key": "value"})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.overrideNetworkState"

    async def test_network_search_in_response_body(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {}
        result = await backend.network_search_in_response_body("req-1", "query")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.searchInResponseBody"
        assert isinstance(result, dict)

    async def test_network_set_accepted_encodings(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_set_accepted_encodings(["gzip"])
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.setAcceptedEncodings"

    async def test_network_set_attach_debug_stack(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_set_attach_debug_stack(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.setAttachDebugStack"

    async def test_network_set_cookies(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.network_set_cookies([{"name": "foo", "value": "bar"}])
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.setCookies"

    async def test_network_stream_resource_content(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {}
        result = await backend.network_stream_resource_content("req-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.streamResourceContent"
        assert isinstance(result, dict)

    async def test_network_take_response_body_for_interception_as_stream(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {}
        result = await backend.network_take_response_body_for_interception_as_stream("int-1")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Network.takeResponseBodyForInterceptionAsStream"
        assert isinstance(result, dict)

    # ── Overlay (18 new methods) ──────────────────────────

    async def test_overlay_get_grid_highlight_objects_for_test(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"highlights": {}}
        result = await backend.overlay_get_grid_highlight_objects_for_test(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Overlay.getGridHighlightObjectsForTest"
        assert isinstance(result, dict)

    async def test_overlay_get_highlight_object_for_test(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"highlight": {}}
        result = await backend.overlay_get_highlight_object_for_test(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Overlay.getHighlightObjectForTest"
        assert isinstance(result, dict)

    async def test_overlay_get_source_order_highlight_object_for_test(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"highlight": {}}
        result = await backend.overlay_get_source_order_highlight_object_for_test(1)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Overlay.getSourceOrderHighlightObjectForTest"
        assert isinstance(result, dict)

    async def test_overlay_hide_highlight(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_hide_highlight()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Overlay.hideHighlight"

    async def test_overlay_highlight_source_order(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_highlight_source_order({"nodeId": 1})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Overlay.highlightSourceOrder"

    async def test_overlay_set_paused_in_debugger_message(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_set_paused_in_debugger_message("paused")
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Overlay.setPausedInDebuggerMessage"

    async def test_overlay_set_show_container_query_overlays(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_set_show_container_query_overlays(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Overlay.setShowContainerQueryOverlays"

    async def test_overlay_set_show_display_cutout(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_set_show_display_cutout(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Overlay.setShowDisplayCutout"

    async def test_overlay_set_show_flex_overlays(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_set_show_flex_overlays(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Overlay.setShowFlexOverlays"

    async def test_overlay_set_show_grid_overlays(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_set_show_grid_overlays([{"nodeId": 1}])
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Overlay.setShowGridOverlays"

    async def test_overlay_set_show_hinge(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_set_show_hinge({"rect": {}})
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Overlay.setShowHinge"

    async def test_overlay_set_show_inspected_element_anchor(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_set_show_inspected_element_anchor(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Overlay.setShowInspectedElementAnchor"

    async def test_overlay_set_show_isolated_elements(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_set_show_isolated_elements([{"nodeId": 1}])
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Overlay.setShowIsolatedElements"

    async def test_overlay_set_show_layout_shift_regions(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_set_show_layout_shift_regions(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Overlay.setShowLayoutShiftRegions"

    async def test_overlay_set_show_scroll_bottleneck_rects(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_set_show_scroll_bottleneck_rects(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Overlay.setShowScrollBottleneckRects"

    async def test_overlay_set_show_scroll_snap_overlays(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_set_show_scroll_snap_overlays(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Overlay.setShowScrollSnapOverlays"

    async def test_overlay_set_show_viewport_size_on_resize(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_set_show_viewport_size_on_resize(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Overlay.setShowViewportSizeOnResize"

    async def test_overlay_set_show_window_controls_overlay(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.overlay_set_show_window_controls_overlay(True)
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Overlay.setShowWindowControlsOverlay"

    # ── Accessibility (extended) ──────────────────────────

    async def test_a11y_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.a11y_disable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Accessibility.disable"

    async def test_a11y_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.a11y_enable()
        mock.send.assert_awaited_once()
        assert mock.send.call_args.args[0] == "Accessibility.enable"

    async def test_a11y_get_ax_node_and_ancestors(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"nodes": []}
        await backend.a11y_get_ax_node_and_ancestors(node_id=1)
        assert mock.send.call_args.args[0] == "Accessibility.getAXNodeAndAncestors"

    async def test_a11y_get_child_ax_nodes(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"nodes": []}
        await backend.a11y_get_child_ax_nodes("node1")
        assert mock.send.call_args.args[0] == "Accessibility.getChildAXNodes"

    async def test_a11y_get_full_ax_tree(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"nodes": []}
        await backend.a11y_get_full_ax_tree()
        assert mock.send.call_args.args[0] == "Accessibility.getFullAXTree"

    async def test_a11y_get_partial_ax_tree(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"nodes": []}
        await backend.a11y_get_partial_ax_tree(node_id=1)
        assert mock.send.call_args.args[0] == "Accessibility.getPartialAXTree"

    async def test_a11y_get_root_ax_node(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"node": {}}
        await backend.a11y_get_root_ax_node()
        assert mock.send.call_args.args[0] == "Accessibility.getRootAXNode"

    async def test_a11y_query_ax_tree(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"nodes": []}
        await backend.a11y_query_ax_tree(node_id=1, role="button")
        assert mock.send.call_args.args[0] == "Accessibility.queryAXTree"

    # ── Ads ────────────────────────────────────────────────

    async def test_ads_get_ad_metrics(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {}
        await backend.ads_get_ad_metrics()
        assert mock.send.call_args.args[0] == "Ads.getAdMetrics"

    # ── Animation (extended) ──────────────────────────────

    async def test_animation_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.animation_disable()
        assert mock.send.call_args.args[0] == "Animation.disable"

    async def test_animation_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.animation_enable()
        assert mock.send.call_args.args[0] == "Animation.enable"

    async def test_animation_get_current_time(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"currentTime": 5000}
        result = await backend.animation_get_current_time("anim1")
        assert result == 5000.0
        assert mock.send.call_args.args[0] == "Animation.getCurrentTime"

    async def test_animation_get_playback_rate(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"playbackRate": 2.0}
        result = await backend.animation_get_playback_rate()
        assert result == 2.0

    async def test_animation_release_animations(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.animation_release_animations(["a1", "a2"])
        assert mock.send.call_args.args[0] == "Animation.releaseAnimations"

    async def test_animation_replay(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.animation_replay(["a1"])
        assert mock.send.call_args.args[0] == "Animation.replay"

    async def test_animation_resolve_animation(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {}
        await backend.animation_resolve_animation("a1")
        assert mock.send.call_args.args[0] == "Animation.resolveAnimation"

    async def test_animation_seek_animations(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.animation_seek_animations(["a1"], 1000)
        assert mock.send.call_args.args[0] == "Animation.seekAnimations"

    async def test_animation_seek_to(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.animation_seek_to(["a1"], 1000)
        assert mock.send.call_args.args[0] == "Animation.seekTo"

    async def test_animation_set_paused(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.animation_set_paused(["a1"], True)
        assert mock.send.call_args.args[0] == "Animation.setPaused"

    async def test_animation_set_playback_rate(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.animation_set_playback_rate(2.0)
        assert mock.send.call_args.args[0] == "Animation.setPlaybackRate"

    async def test_animation_set_timing(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.animation_set_timing("a1", 500, 100)
        assert mock.send.call_args.args[0] == "Animation.setTiming"

    # ── Audits ─────────────────────────────────────────────

    async def test_audits_check_contrast(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {}
        await backend.audits_check_contrast()
        assert mock.send.call_args.args[0] == "Audits.checkContrast"

    async def test_audits_check_forms_issues(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {}
        await backend.audits_check_forms_issues()
        assert mock.send.call_args.args[0] == "Audits.checkFormsIssues"

    async def test_audits_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.audits_disable()
        assert mock.send.call_args.args[0] == "Audits.disable"

    async def test_audits_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.audits_enable()
        assert mock.send.call_args.args[0] == "Audits.enable"

    async def test_audits_get_encoded_response(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {}
        await backend.audits_get_encoded_response("req1", "webp")
        assert mock.send.call_args.args[0] == "Audits.getEncodedResponse"

    # ── Autofill ───────────────────────────────────────────

    async def test_autofill_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.autofill_disable()
        assert mock.send.call_args.args[0] == "Autofill.disable"

    async def test_autofill_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.autofill_enable()
        assert mock.send.call_args.args[0] == "Autofill.enable"

    async def test_autofill_set_addresses(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.autofill_set_addresses([{"city": "NYC"}])
        assert mock.send.call_args.args[0] == "Autofill.setAddresses"

    async def test_autofill_trigger(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.autofill_trigger(1)
        assert mock.send.call_args.args[0] == "Autofill.trigger"

    async def test_autofill_trigger_fill(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.autofill_trigger_fill(1)
        assert mock.send.call_args.args[0] == "Autofill.triggerFill"

    async def test_autofill_trigger_fill_after_save(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.autofill_trigger_fill_after_save(1)
        assert mock.send.call_args.args[0] == "Autofill.triggerFillAfterSave"

    # ── Background Service ─────────────────────────────────

    async def test_background_service_clear_events(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.background_service_clear_events("pushMessaging")
        assert mock.send.call_args.args[0] == "BackgroundService.clearEvents"

    async def test_background_service_set_recording(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.background_service_set_recording(True, "pushMessaging")
        assert mock.send.call_args.args[0] == "BackgroundService.setRecording"

    async def test_background_service_start_observing(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.background_service_start_observing("pushMessaging")
        assert mock.send.call_args.args[0] == "BackgroundService.startObserving"

    async def test_background_service_stop_observing(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.background_service_stop_observing("pushMessaging")
        assert mock.send.call_args.args[0] == "BackgroundService.stopObserving"

    # ── Bluetooth Emulation ────────────────────────────────

    async def test_bluetooth_emulation_add_characteristic(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"characteristicId": "c1"}
        result = await backend.bluetooth_emulation_add_characteristic("s1", "uuid", {})
        assert result == "c1"
        assert mock.send.call_args.args[0] == "BluetoothEmulation.addCharacteristic"

    async def test_bluetooth_emulation_add_descriptor(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"descriptorId": "d1"}
        await backend.bluetooth_emulation_add_descriptor("c1", "uuid")
        assert mock.send.call_args.args[0] == "BluetoothEmulation.addDescriptor"

    async def test_bluetooth_emulation_add_service(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"serviceId": "s1"}
        await backend.bluetooth_emulation_add_service("addr", "uuid")
        assert mock.send.call_args.args[0] == "BluetoothEmulation.addService"

    async def test_bluetooth_emulation_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.bluetooth_emulation_disable()
        assert mock.send.call_args.args[0] == "BluetoothEmulation.disable"

    async def test_bluetooth_emulation_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.bluetooth_emulation_enable("powered-on", True)
        assert mock.send.call_args.args[0] == "BluetoothEmulation.enable"

    async def test_bluetooth_emulation_remove_characteristic(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.bluetooth_emulation_remove_characteristic("c1")
        assert mock.send.call_args.args[0] == "BluetoothEmulation.removeCharacteristic"

    async def test_bluetooth_emulation_remove_descriptor(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.bluetooth_emulation_remove_descriptor("d1")
        assert mock.send.call_args.args[0] == "BluetoothEmulation.removeDescriptor"

    async def test_bluetooth_emulation_remove_service(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.bluetooth_emulation_remove_service("s1")
        assert mock.send.call_args.args[0] == "BluetoothEmulation.removeService"

    async def test_bluetooth_emulation_set_simulated_central_state(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.bluetooth_emulation_set_simulated_central_state("powered-on")
        assert mock.send.call_args.args[0] == "BluetoothEmulation.setSimulatedCentralState"

    async def test_bluetooth_emulation_simulate_advertisement(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.bluetooth_emulation_simulate_advertisement({})
        assert mock.send.call_args.args[0] == "BluetoothEmulation.simulateAdvertisement"

    async def test_bluetooth_emulation_simulate_characteristic_operation_response(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.bluetooth_emulation_simulate_characteristic_operation_response(
            "c1", "read", 0
        )
        assert (
            mock.send.call_args.args[0]
            == "BluetoothEmulation.simulateCharacteristicOperationResponse"
        )

    async def test_bluetooth_emulation_simulate_descriptor_operation_response(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.bluetooth_emulation_simulate_descriptor_operation_response("d1", "read", 0)
        assert (
            mock.send.call_args.args[0] == "BluetoothEmulation.simulateDescriptorOperationResponse"
        )

    async def test_bluetooth_emulation_simulate_gatt_disconnection(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.bluetooth_emulation_simulate_gatt_disconnection("addr")
        assert mock.send.call_args.args[0] == "BluetoothEmulation.simulateGATTDisconnection"

    async def test_bluetooth_emulation_simulate_gatt_operation_response(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.bluetooth_emulation_simulate_gatt_operation_response("addr", "read", 0)
        assert mock.send.call_args.args[0] == "BluetoothEmulation.simulateGATTOperationResponse"

    async def test_bluetooth_emulation_simulate_preconnected_peripheral(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.bluetooth_emulation_simulate_preconnected_peripheral("addr", "name", [], [])
        assert mock.send.call_args.args[0] == "BluetoothEmulation.simulatePreconnectedPeripheral"

    # ── Browser (extended) ─────────────────────────────────

    async def test_browser_crash(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.browser_crash()
        assert mock.send.call_args.args[0] == "Browser.crash"

    async def test_browser_crash_gpu_process(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.browser_crash_gpu_process()
        assert mock.send.call_args.args[0] == "Browser.crashGpuProcess"

    async def test_browser_get_version(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"product": "Chrome/120"}
        result = await backend.browser_get_version()
        assert result["product"] == "Chrome/120"

    async def test_browser_get_histogram(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {}
        await backend.browser_get_histogram("Histogram.Name")
        assert mock.send.call_args.args[0] == "Browser.getHistogram"

    async def test_browser_get_histograms(self) -> None:
        backend, _, mock = _make_mock_backend()
        mock.send.return_value = {"histograms": []}
        await backend.browser_get_histograms()
        assert mock.send.call_args.args[0] == "Browser.getHistograms"

    async def test_browser_grant_permissions(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.browser_grant_permissions("https://example.com", ["geolocation"])
        assert mock.send.call_args.args[0] == "Browser.grantPermissions"

    async def test_browser_set_permission(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.browser_set_permission({"name": "geolocation"}, "grant")
        assert mock.send.call_args.args[0] == "Browser.setPermission"

    async def test_browser_cancel_download(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.browser_cancel_download("guid-1")
        assert mock.send.call_args.args[0] == "Browser.cancelDownload"

    async def test_browser_set_download_behavior(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.browser_set_download_behavior("allow", download_path="/tmp")
        assert mock.send.call_args.args[0] == "Browser.setDownloadBehavior"

    # ── Debugger ──────────────────────────────────────────

    async def test_debugger_continue_to_location(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_continue_to_location({"scriptId": "1", "lineNumber": 0})
        assert mock.send.call_args.args[0] == "Debugger.continueToLocation"

    async def test_debugger_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_disable()
        assert mock.send.call_args.args[0] == "Debugger.disable"

    async def test_debugger_disassemble_wasm_module(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_disassemble_wasm_module("script-1")
        assert mock.send.call_args.args[0] == "Debugger.disassembleWasmModule"

    async def test_debugger_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_enable()
        assert mock.send.call_args.args[0] == "Debugger.enable"

    async def test_debugger_evaluate_on_call_frame(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_evaluate_on_call_frame("frame-1", "1+1")
        assert mock.send.call_args.args[0] == "Debugger.evaluateOnCallFrame"

    async def test_debugger_get_possible_breakpoints(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_get_possible_breakpoints({"scriptId": "1", "lineNumber": 0})
        assert mock.send.call_args.args[0] == "Debugger.getPossibleBreakpoints"

    async def test_debugger_get_script_source(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_get_script_source("script-1")
        assert mock.send.call_args.args[0] == "Debugger.getScriptSource"

    async def test_debugger_get_stack_trace(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_get_stack_trace({"id": "trace-1"})
        assert mock.send.call_args.args[0] == "Debugger.getStackTrace"

    async def test_debugger_get_wasm_bytecode(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_get_wasm_bytecode("script-1")
        assert mock.send.call_args.args[0] == "Debugger.getWasmBytecode"

    async def test_debugger_next_wasm_disassembly_chunk(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_next_wasm_disassembly_chunk("stream-1")
        assert mock.send.call_args.args[0] == "Debugger.nextWasmDisassemblyChunk"

    async def test_debugger_pause(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_pause()
        assert mock.send.call_args.args[0] == "Debugger.pause"

    async def test_debugger_pause_on_async_call(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_pause_on_async_call({"id": "trace-1"})
        assert mock.send.call_args.args[0] == "Debugger.pauseOnAsyncCall"

    async def test_debugger_remove_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_remove_breakpoint("bp-1")
        assert mock.send.call_args.args[0] == "Debugger.removeBreakpoint"

    async def test_debugger_restart_frame(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_restart_frame("frame-1", "into")
        assert mock.send.call_args.args[0] == "Debugger.restartFrame"

    async def test_debugger_resume(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_resume()
        assert mock.send.call_args.args[0] == "Debugger.resume"

    async def test_debugger_search_in_content(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_search_in_content("script-1", "query")
        assert mock.send.call_args.args[0] == "Debugger.searchInContent"

    async def test_debugger_set_async_call_stack_depth(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_set_async_call_stack_depth(32)
        assert mock.send.call_args.args[0] == "Debugger.setAsyncCallStackDepth"

    async def test_debugger_set_blackbox_execution_contexts(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_set_blackbox_execution_contexts([1, 2])
        assert mock.send.call_args.args[0] == "Debugger.setBlackboxExecutionContexts"

    async def test_debugger_set_blackbox_patterns(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_set_blackbox_patterns(["*.min.js"])
        assert mock.send.call_args.args[0] == "Debugger.setBlackboxPatterns"

    async def test_debugger_set_blackboxed_ranges(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_set_blackboxed_ranges(
            "script-1", [{"lineNumber": 0, "columnNumber": 0}]
        )
        assert mock.send.call_args.args[0] == "Debugger.setBlackboxedRanges"

    async def test_debugger_set_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_set_breakpoint({"scriptId": "1", "lineNumber": 0})
        assert mock.send.call_args.args[0] == "Debugger.setBreakpoint"

    async def test_debugger_set_breakpoint_by_url(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_set_breakpoint_by_url(10)
        assert mock.send.call_args.args[0] == "Debugger.setBreakpointByUrl"

    async def test_debugger_set_breakpoint_on_function_call(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_set_breakpoint_on_function_call("obj-1")
        assert mock.send.call_args.args[0] == "Debugger.setBreakpointOnFunctionCall"

    async def test_debugger_set_breakpoints_active(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_set_breakpoints_active(True)
        assert mock.send.call_args.args[0] == "Debugger.setBreakpointsActive"

    async def test_debugger_set_instrumentation_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_set_instrumentation_breakpoint("beforeScriptExecution")
        assert mock.send.call_args.args[0] == "Debugger.setInstrumentationBreakpoint"

    async def test_debugger_set_pause_on_exceptions(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_set_pause_on_exceptions("all")
        assert mock.send.call_args.args[0] == "Debugger.setPauseOnExceptions"

    async def test_debugger_set_return_value(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_set_return_value({"type": "number", "value": 42})
        assert mock.send.call_args.args[0] == "Debugger.setReturnValue"

    async def test_debugger_set_script_source(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_set_script_source("script-1", "console.log(1)")
        assert mock.send.call_args.args[0] == "Debugger.setScriptSource"

    async def test_debugger_set_skip_all_pauses(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_set_skip_all_pauses(True)
        assert mock.send.call_args.args[0] == "Debugger.setSkipAllPauses"

    async def test_debugger_set_variable_value(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_set_variable_value("frame-1", 0, "x", {"type": "number", "value": 1})
        assert mock.send.call_args.args[0] == "Debugger.setVariableValue"

    async def test_debugger_step_into(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_step_into()
        assert mock.send.call_args.args[0] == "Debugger.stepInto"

    async def test_debugger_step_out(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_step_out()
        assert mock.send.call_args.args[0] == "Debugger.stepOut"

    async def test_debugger_step_over(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.debugger_step_over()
        assert mock.send.call_args.args[0] == "Debugger.stepOver"

    # ── HeapProfiler ──────────────────────────────────────

    async def test_heap_profiler_add_inspected_heap_object(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_add_inspected_heap_object("heap-1")
        assert mock.send.call_args.args[0] == "HeapProfiler.addInspectedHeapObject"

    async def test_heap_profiler_collect_garbage(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_collect_garbage()
        assert mock.send.call_args.args[0] == "HeapProfiler.collectGarbage"

    async def test_heap_profiler_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_disable()
        assert mock.send.call_args.args[0] == "HeapProfiler.disable"

    async def test_heap_profiler_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_enable()
        assert mock.send.call_args.args[0] == "HeapProfiler.enable"

    async def test_heap_profiler_get_heap_object_id(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_get_heap_object_id("obj-1")
        assert mock.send.call_args.args[0] == "HeapProfiler.getHeapObjectId"

    async def test_heap_profiler_get_object_by_heap_object_id(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_get_object_by_heap_object_id("heap-1")
        assert mock.send.call_args.args[0] == "HeapProfiler.getObjectByHeapObjectId"

    async def test_heap_profiler_get_sampling_profile(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_get_sampling_profile()
        assert mock.send.call_args.args[0] == "HeapProfiler.getSamplingProfile"

    async def test_heap_profiler_start_sampling(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_start_sampling()
        assert mock.send.call_args.args[0] == "HeapProfiler.startSampling"

    async def test_heap_profiler_start_tracking_heap_objects(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_start_tracking_heap_objects()
        assert mock.send.call_args.args[0] == "HeapProfiler.startTrackingHeapObjects"

    async def test_heap_profiler_stop_sampling(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_stop_sampling()
        assert mock.send.call_args.args[0] == "HeapProfiler.stopSampling"

    async def test_heap_profiler_stop_tracking_heap_objects(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_stop_tracking_heap_objects()
        assert mock.send.call_args.args[0] == "HeapProfiler.stopTrackingHeapObjects"

    async def test_heap_profiler_take_heap_snapshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.heap_profiler_take_heap_snapshot()
        assert mock.send.call_args.args[0] == "HeapProfiler.takeHeapSnapshot"

    # ── SmartCardEmulation ────────────────────────────────

    async def test_smart_card_emulation_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.smart_card_emulation_disable()
        assert mock.send.call_args.args[0] == "SmartCardEmulation.disable"

    async def test_smart_card_emulation_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.smart_card_emulation_enable()
        assert mock.send.call_args.args[0] == "SmartCardEmulation.enable"

    async def test_smart_card_emulation_report_begin_transaction_result(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.smart_card_emulation_report_begin_transaction_result("req-1", 1)
        assert mock.send.call_args.args[0] == "SmartCardEmulation.reportBeginTransactionResult"

    async def test_smart_card_emulation_report_connect_result(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.smart_card_emulation_report_connect_result("req-1", 1)
        assert mock.send.call_args.args[0] == "SmartCardEmulation.reportConnectResult"

    async def test_smart_card_emulation_report_data_result(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.smart_card_emulation_report_data_result("req-1", "data")
        assert mock.send.call_args.args[0] == "SmartCardEmulation.reportDataResult"

    async def test_smart_card_emulation_report_error(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.smart_card_emulation_report_error("req-1", "failed")
        assert mock.send.call_args.args[0] == "SmartCardEmulation.reportError"

    async def test_smart_card_emulation_report_establish_context_result(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.smart_card_emulation_report_establish_context_result("req-1", 1)
        assert mock.send.call_args.args[0] == "SmartCardEmulation.reportEstablishContextResult"

    async def test_smart_card_emulation_report_get_status_change_result(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.smart_card_emulation_report_get_status_change_result("req-1", [])
        assert mock.send.call_args.args[0] == "SmartCardEmulation.reportGetStatusChangeResult"

    async def test_smart_card_emulation_report_list_readers_result(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.smart_card_emulation_report_list_readers_result("req-1", ["reader1"])
        assert mock.send.call_args.args[0] == "SmartCardEmulation.reportListReadersResult"

    async def test_smart_card_emulation_report_plain_result(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.smart_card_emulation_report_plain_result("req-1")
        assert mock.send.call_args.args[0] == "SmartCardEmulation.reportPlainResult"

    async def test_smart_card_emulation_report_release_context_result(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.smart_card_emulation_report_release_context_result("req-1")
        assert mock.send.call_args.args[0] == "SmartCardEmulation.reportReleaseContextResult"

    async def test_smart_card_emulation_report_status_result(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.smart_card_emulation_report_status_result("req-1", "reader1", "active", "atr")
        assert mock.send.call_args.args[0] == "SmartCardEmulation.reportStatusResult"

    # ── IndexedDB ─────────────────────────────────────────

    async def test_indexed_db_clear_object_store(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.indexed_db_clear_object_store("db", "store")
        assert mock.send.call_args.args[0] == "IndexedDB.clearObjectStore"

    async def test_indexed_db_delete_database(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.indexed_db_delete_database("db")
        assert mock.send.call_args.args[0] == "IndexedDB.deleteDatabase"

    async def test_indexed_db_delete_object_store_entries(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.indexed_db_delete_object_store_entries("db", "store", {"lowerOpen": True})
        assert mock.send.call_args.args[0] == "IndexedDB.deleteObjectStoreEntries"

    async def test_indexed_db_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.indexed_db_disable()
        assert mock.send.call_args.args[0] == "IndexedDB.disable"

    async def test_indexed_db_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.indexed_db_enable()
        assert mock.send.call_args.args[0] == "IndexedDB.enable"

    async def test_indexed_db_get_metadata(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.indexed_db_get_metadata("db", "store")
        assert mock.send.call_args.args[0] == "IndexedDB.getMetadata"

    async def test_indexed_db_request_data(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.indexed_db_request_data("db", "store")
        assert mock.send.call_args.args[0] == "IndexedDB.requestData"

    async def test_indexed_db_request_database(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.indexed_db_request_database("db")
        assert mock.send.call_args.args[0] == "IndexedDB.requestDatabase"

    async def test_indexed_db_request_database_names(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.indexed_db_request_database_names()
        assert mock.send.call_args.args[0] == "IndexedDB.requestDatabaseNames"

    # ── LayerTree ─────────────────────────────────────────

    async def test_layer_tree_compositing_reasons(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.layer_tree_compositing_reasons("layer-1")
        assert mock.send.call_args.args[0] == "LayerTree.compositingReasons"

    async def test_layer_tree_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.layer_tree_disable()
        assert mock.send.call_args.args[0] == "LayerTree.disable"

    async def test_layer_tree_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.layer_tree_enable()
        assert mock.send.call_args.args[0] == "LayerTree.enable"

    async def test_layer_tree_load_snapshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.layer_tree_load_snapshot([])
        assert mock.send.call_args.args[0] == "LayerTree.loadSnapshot"

    async def test_layer_tree_make_snapshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.layer_tree_make_snapshot("layer-1")
        assert mock.send.call_args.args[0] == "LayerTree.makeSnapshot"

    async def test_layer_tree_profile_snapshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.layer_tree_profile_snapshot("snap-1")
        assert mock.send.call_args.args[0] == "LayerTree.profileSnapshot"

    async def test_layer_tree_release_snapshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.layer_tree_release_snapshot("snap-1")
        assert mock.send.call_args.args[0] == "LayerTree.releaseSnapshot"

    async def test_layer_tree_replay_snapshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.layer_tree_replay_snapshot("snap-1")
        assert mock.send.call_args.args[0] == "LayerTree.replaySnapshot"

    async def test_layer_tree_snapshot_command_log(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.layer_tree_snapshot_command_log("snap-1")
        assert mock.send.call_args.args[0] == "LayerTree.snapshotCommandLog"

    # ── FedCM ─────────────────────────────────────────────

    async def test_fed_cm_click_dialog_button(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fed_cm_click_dialog_button("dialog-1", "ConfirmIdPLogin")
        assert mock.send.call_args.args[0] == "FedCM.clickDialogButton"

    async def test_fed_cm_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fed_cm_disable()
        assert mock.send.call_args.args[0] == "FedCM.disable"

    async def test_fed_cm_dismiss_dialog(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fed_cm_dismiss_dialog("dialog-1")
        assert mock.send.call_args.args[0] == "FedCM.dismissDialog"

    async def test_fed_cm_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fed_cm_enable()
        assert mock.send.call_args.args[0] == "FedCM.enable"

    async def test_fed_cm_open_url(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fed_cm_open_url("dialog-1", 0, "TermsOfService")
        assert mock.send.call_args.args[0] == "FedCM.openURL"

    async def test_fed_cm_reset_cooldown(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fed_cm_reset_cooldown()
        assert mock.send.call_args.args[0] == "FedCM.resetCooldown"

    async def test_fed_cm_select_account(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.fed_cm_select_account("dialog-1", 0)
        assert mock.send.call_args.args[0] == "FedCM.selectAccount"

    # ── CacheStorage ──────────────────────────────────────

    async def test_cache_storage_delete_cache(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.cache_storage_delete_cache("cache-1")
        assert mock.send.call_args.args[0] == "CacheStorage.deleteCache"

    async def test_cache_storage_delete_entry(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.cache_storage_delete_entry("cache-1", "request-1")
        assert mock.send.call_args.args[0] == "CacheStorage.deleteEntry"

    async def test_cache_storage_request_cache_names(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.cache_storage_request_cache_names()
        assert mock.send.call_args.args[0] == "CacheStorage.requestCacheNames"

    async def test_cache_storage_request_cached_response(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.cache_storage_request_cached_response("cache-1", "http://example.com", [])
        assert mock.send.call_args.args[0] == "CacheStorage.requestCachedResponse"

    async def test_cache_storage_request_entries(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.cache_storage_request_entries("cache-1")
        assert mock.send.call_args.args[0] == "CacheStorage.requestEntries"

    # ── DOMStorage ────────────────────────────────────────

    async def test_dom_storage_clear(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_storage_clear(
            {"securityOrigin": "http://example.com", "isLocalStorage": True}
        )
        assert mock.send.call_args.args[0] == "DOMStorage.clear"

    async def test_dom_storage_clear_dom_storage_items(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_storage_clear_dom_storage_items(
            {"securityOrigin": "http://example.com", "isLocalStorage": True}
        )
        assert mock.send.call_args.args[0] == "DOMStorage.clear"

    async def test_dom_storage_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_storage_disable()
        assert mock.send.call_args.args[0] == "DOMStorage.disable"

    async def test_dom_storage_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_storage_enable()
        assert mock.send.call_args.args[0] == "DOMStorage.enable"

    async def test_dom_storage_get_dom_storage_items(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_storage_get_dom_storage_items(
            {"securityOrigin": "http://example.com", "isLocalStorage": True}
        )
        assert mock.send.call_args.args[0] == "DOMStorage.getDOMStorageItems"

    async def test_dom_storage_remove_dom_storage_item(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_storage_remove_dom_storage_item(
            {"securityOrigin": "http://example.com", "isLocalStorage": True}, "key"
        )
        assert mock.send.call_args.args[0] == "DOMStorage.removeDOMStorageItem"

    async def test_dom_storage_set_dom_storage_item(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_storage_set_dom_storage_item(
            {"securityOrigin": "http://example.com", "isLocalStorage": True}, "key", "val"
        )
        assert mock.send.call_args.args[0] == "DOMStorage.setDOMStorageItem"

    # ── EventBreakpoints ──────────────────────────────────

    async def test_event_breakpoints_clear_instrumentation_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.event_breakpoints_clear_instrumentation_breakpoint("DOMContentLoaded")
        assert mock.send.call_args.args[0] == "EventBreakpoints.clearInstrumentationBreakpoint"

    async def test_event_breakpoints_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.event_breakpoints_disable()
        assert mock.send.call_args.args[0] == "EventBreakpoints.disable"

    async def test_event_breakpoints_remove_instrumentation_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.event_breakpoints_remove_instrumentation_breakpoint("DOMContentLoaded")
        assert mock.send.call_args.args[0] == "EventBreakpoints.removeInstrumentationBreakpoint"

    async def test_event_breakpoints_set_instrumentation_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.event_breakpoints_set_instrumentation_breakpoint("DOMContentLoaded")
        assert mock.send.call_args.args[0] == "EventBreakpoints.setInstrumentationBreakpoint"

    # ── Extensions ────────────────────────────────────────

    async def test_extensions_get_extensions(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.extensions_get_extensions()
        assert mock.send.call_args.args[0] == "Extensions.getExtensions"

    async def test_extensions_load_unpacked(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.extensions_load_unpacked("/path/to/ext")
        assert mock.send.call_args.args[0] == "Extensions.loadUnpacked"

    async def test_extensions_uninstall(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.extensions_uninstall("ext-1")
        assert mock.send.call_args.args[0] == "Extensions.uninstall"

    # ── HeadlessExperimental ──────────────────────────────

    async def test_headless_experimental_begin_frame(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.headless_experimental_begin_frame()
        assert mock.send.call_args.args[0] == "HeadlessExperimental.beginFrame"

    async def test_headless_experimental_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.headless_experimental_disable()
        assert mock.send.call_args.args[0] == "HeadlessExperimental.disable"

    async def test_headless_experimental_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.headless_experimental_enable()
        assert mock.send.call_args.args[0] == "HeadlessExperimental.enable"

    # ── SystemInfo ────────────────────────────────────────

    async def test_system_info_get_feature_state(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.system_info_get_feature_state("feature")
        assert mock.send.call_args.args[0] == "SystemInfo.getFeatureState"

    async def test_system_info_get_info(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.system_info_get_info()
        assert mock.send.call_args.args[0] == "SystemInfo.getInfo"

    async def test_system_info_get_process_info(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.system_info_get_process_info()
        assert mock.send.call_args.args[0] == "SystemInfo.getProcessInfo"

    # ── DeviceOrientation ─────────────────────────────────

    async def test_device_orientation_clear_device_orientation_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.device_orientation_clear_device_orientation_override()
        assert mock.send.call_args.args[0] == "DeviceOrientation.clearDeviceOrientationOverride"

    async def test_device_orientation_set_device_orientation_override(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.device_orientation_set_device_orientation_override(0.0, 0.0, 0.0)
        assert mock.send.call_args.args[0] == "DeviceOrientation.setDeviceOrientationOverride"

    # ── DOMDebugger ───────────────────────────────────────

    async def test_dom_debugger_get_event_listeners(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_get_event_listeners("obj-1")
        assert mock.send.call_args.args[0] == "DOMDebugger.getEventListeners"

    async def test_dom_debugger_remove_dom_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_remove_dom_breakpoint(1, "subtree")
        assert mock.send.call_args.args[0] == "DOMDebugger.removeDOMBreakpoint"

    async def test_dom_debugger_remove_event_listener_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_remove_event_listener_breakpoint("click")
        assert mock.send.call_args.args[0] == "DOMDebugger.removeEventListenerBreakpoint"

    async def test_dom_debugger_remove_instrumentation_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_remove_instrumentation_breakpoint("setInterval")
        assert mock.send.call_args.args[0] == "DOMDebugger.removeInstrumentationBreakpoint"

    async def test_dom_debugger_remove_xhr_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_remove_xhr_breakpoint("http://example.com")
        assert mock.send.call_args.args[0] == "DOMDebugger.removeXHRBreakpoint"

    async def test_dom_debugger_set_break_on_csp_violation(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_set_break_on_csp_violation(["trusted-types-sink"])
        assert mock.send.call_args.args[0] == "DOMDebugger.setBreakOnCSPViolation"

    async def test_dom_debugger_set_dom_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_set_dom_breakpoint(1, "subtree")
        assert mock.send.call_args.args[0] == "DOMDebugger.setDOMBreakpoint"

    async def test_dom_debugger_set_event_listener_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_set_event_listener_breakpoint("click")
        assert mock.send.call_args.args[0] == "DOMDebugger.setEventListenerBreakpoint"

    async def test_dom_debugger_set_instrumentation_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_set_instrumentation_breakpoint("setInterval")
        assert mock.send.call_args.args[0] == "DOMDebugger.setInstrumentationBreakpoint"

    async def test_dom_debugger_set_xhr_breakpoint(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_debugger_set_xhr_breakpoint("http://example.com")
        assert mock.send.call_args.args[0] == "DOMDebugger.setXHRBreakpoint"

    # ── DOMSnapshot ───────────────────────────────────────

    async def test_dom_snapshot_capture_snapshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_snapshot_capture_snapshot(["color"])
        assert mock.send.call_args.args[0] == "DOMSnapshot.captureSnapshot"

    async def test_dom_snapshot_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_snapshot_disable()
        assert mock.send.call_args.args[0] == "DOMSnapshot.disable"

    async def test_dom_snapshot_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_snapshot_enable()
        assert mock.send.call_args.args[0] == "DOMSnapshot.enable"

    async def test_dom_snapshot_get_snapshot(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_snapshot_get_snapshot(["color"])
        assert mock.send.call_args.args[0] == "DOMSnapshot.getSnapshot"

    # ── DeviceAccess ──────────────────────────────────────

    async def test_device_access_cancel_prompt(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.device_access_cancel_prompt("req-1")
        assert mock.send.call_args.args[0] == "DeviceAccess.cancelPrompt"

    async def test_device_access_disable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.device_access_disable()
        assert mock.send.call_args.args[0] == "DeviceAccess.disable"

    async def test_device_access_enable(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.device_access_enable()
        assert mock.send.call_args.args[0] == "DeviceAccess.enable"

    async def test_device_access_select_prompt(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.device_access_select_prompt("req-1", "dev-1")
        assert mock.send.call_args.args[0] == "DeviceAccess.selectPrompt"

    # ── Remaining single methods ──────────────────────────

    async def test_dom_get_attribute(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.dom_get_attribute(1)
        assert mock.send.call_args.args[0] == "DOM.getAttributes"

    async def test_webauthn_remove_virtual_authenticator(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.webauthn_remove_virtual_authenticator("auth-1")
        assert mock.send.call_args.args[0] == "WebAuthn.removeVirtualAuthenticator"

    async def test_crash_report_context_get_entries(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.crash_report_context_get_entries()
        assert mock.send.call_args.args[0] == "CrashReportContext.getEntries"

    async def test_digital_credentials_set_virtual_wallet_behavior(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.digital_credentials_set_virtual_wallet_behavior("cancel")
        assert mock.send.call_args.args[0] == "DigitalCredentials.setVirtualWalletBehavior"

    async def test_file_system_get_directory(self) -> None:
        backend, _, mock = _make_mock_backend()
        await backend.file_system_get_directory("key", [])
        assert mock.send.call_args.args[0] == "FileSystem.getDirectory"
