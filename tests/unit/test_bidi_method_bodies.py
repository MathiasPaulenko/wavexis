"""Unit tests for BiDiBackend method bodies with mocked BiDiClient."""

from __future__ import annotations

import base64
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wavexis.config import (
    BrowserOptions,
    PDFParams,
    ScreencastParams,
    ScreenshotParams,
    WaitStrategy,
)
from wavexis.exceptions import ElementNotFoundError


def _make_mock_backend() -> tuple[Any, Any]:
    """Create a BiDiBackend with a fully mocked BiDiClient."""
    from wavexis.backend.bidi import BiDiBackend

    backend = BiDiBackend()
    mock_client = MagicMock()

    mock_client.session = MagicMock()
    mock_client.session.new = AsyncMock()
    mock_client.browsing = MagicMock()
    mock_client.browsing.navigate = AsyncMock()
    mock_client.browsing.screenshot = AsyncMock(
        return_value=MagicMock(data=base64.b64encode(b"img").decode())
    )
    mock_ctx = MagicMock()
    mock_ctx.id = "ctx-123"
    mock_client.browsing.create_context = AsyncMock(return_value=mock_ctx)
    mock_client.browsing.close = AsyncMock()
    mock_client.browsing.activate = AsyncMock()
    mock_client.browsing.set_viewport = AsyncMock()
    mock_client.browsing.get_tree = AsyncMock(return_value=MagicMock(contexts=[]))
    mock_client.browsing.locate_nodes = AsyncMock(return_value=[])
    mock_client.browsing.print = AsyncMock(
        return_value=MagicMock(data=base64.b64encode(b"pdf").decode())
    )
    mock_client.browsing.capture_screenshot = AsyncMock(
        return_value=MagicMock(data=base64.b64encode(b"img").decode())
    )
    mock_client.script = MagicMock()
    mock_client.script.evaluate = AsyncMock(return_value=MagicMock(value="result"))
    mock_client.storage = MagicMock()
    mock_client.storage.get_cookies = AsyncMock(return_value=[])
    mock_client.storage.set_cookie = AsyncMock()
    mock_client.storage.delete_cookie = AsyncMock()
    mock_client.storage.delete_cookies = AsyncMock()
    mock_client.emulation = MagicMock()
    mock_client.emulation.set_user_agent = AsyncMock()
    mock_client.emulation.set_geolocation = AsyncMock()
    mock_client.emulation.set_timezone = AsyncMock()
    mock_client.emulation.set_network_conditions = AsyncMock()
    mock_client.network = MagicMock()
    mock_client.network.add_cache_override = AsyncMock()
    mock_client.network.add_intercept = AsyncMock()
    mock_client.network.set_cache_behavior = AsyncMock()
    mock_client.network.response_body = AsyncMock(return_value=MagicMock(body="data"))
    mock_client.network.fail_request = AsyncMock()
    mock_client.network.continue_request = AsyncMock()
    mock_client.network.continue_response = AsyncMock()
    mock_client.network.add_data_collector = AsyncMock(return_value="collector-1")
    mock_client.network.get_data = AsyncMock(return_value=[])
    mock_client.network.remove_intercept = AsyncMock()
    mock_client.network.remove_data_collector = AsyncMock()
    mock_client.network.remove_cache_override = AsyncMock()
    mock_client.cdp = MagicMock()
    mock_client.cdp.send_command = AsyncMock(return_value={})
    mock_client.cdp.on = MagicMock()
    mock_client.cdp.off = MagicMock()
    mock_client.on_log_entry = AsyncMock(return_value="sub-1")
    mock_client.off = MagicMock()
    mock_client.close = AsyncMock()
    mock_client._connection = MagicMock()
    mock_client._connection.send_command = AsyncMock(return_value={})
    mock_client.send = AsyncMock(return_value={})

    backend._client = mock_client
    backend._context = "ctx-123"

    return backend, mock_client


@pytest.mark.unit
class TestBiDiMethodBodies:
    """Test BiDiBackend method bodies with mocked client."""

    async def test_navigate(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.navigate("https://example.com")
        mock.browsing.navigate.assert_called_once_with(
            "ctx-123", "https://example.com", wait="complete"
        )

    async def test_screenshot(self) -> None:
        backend, _ = _make_mock_backend()
        result = await backend.screenshot(ScreenshotParams(url="https://example.com"))
        assert isinstance(result, bytes)

    async def test_screenshot_selector(self) -> None:
        backend, mock = _make_mock_backend()
        mock.browsing.locate_nodes = AsyncMock(return_value=[MagicMock()])
        mock.script.evaluate = AsyncMock(
            return_value=MagicMock(value='{"x":0,"y":0,"width":1,"height":1}')
        )
        _png_1x1 = (
            b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
            b"AAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        )
        mock.browsing.screenshot = AsyncMock(return_value=MagicMock(data=_png_1x1.decode()))
        result = await backend.screenshot_selector("h1")
        assert isinstance(result, bytes)

    async def test_screenshot_selector_not_found(self) -> None:
        backend, mock = _make_mock_backend()
        mock.browsing.locate_nodes = AsyncMock(return_value=[])
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value=None))
        with pytest.raises(ElementNotFoundError):
            await backend.screenshot_selector("h1")

    async def test_eval(self) -> None:
        backend, _ = _make_mock_backend()
        result = await backend.eval("document.title")
        assert result == "result"

    async def test_raw(self) -> None:
        backend, mock = _make_mock_backend()
        mock._connection.send_command = AsyncMock(return_value={"ok": True})
        result = await backend.raw("test.method", {"key": "val"})
        assert result == {"ok": True}

    async def test_go_back(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.go_back()

    async def test_go_forward(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.go_forward()

    async def test_reload(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.reload()

    async def test_stop_loading(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.stop_loading()

    async def test_wait_for_load(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.wait_for(WaitStrategy(strategy="load"))

    async def test_wait_for_selector_found(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value=True))
        await backend.wait_for(WaitStrategy(strategy="selector", selector="h1", timeout=100))

    async def test_wait_for_selector_timeout(self) -> None:
        from wavexis.exceptions import WaitTimeoutError

        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value=False))
        with pytest.raises(WaitTimeoutError):
            await backend.wait_for(WaitStrategy(strategy="selector", selector="h1", timeout=50))

    async def test_pdf(self) -> None:
        backend, _ = _make_mock_backend()
        result = await backend.pdf(PDFParams(url="https://example.com"))
        assert isinstance(result, bytes)

    async def test_screencast(self) -> None:
        backend, mock = _make_mock_backend()
        mock.cdp.send_command = AsyncMock(
            return_value={"data": base64.b64encode(b"frame").decode()}
        )
        result = await backend.screencast(ScreencastParams(url="https://example.com", duration=0.6))
        assert len(result) >= 1

    async def test_list_tabs(self) -> None:
        backend, mock = _make_mock_backend()
        mock._connection.send_command = AsyncMock(return_value={"contexts": [{"url": "a"}]})
        result = await backend.list_tabs()
        assert result == [{"url": "a"}]

    async def test_new_tab(self) -> None:
        backend, mock = _make_mock_backend()
        mock._connection.send_command = AsyncMock(return_value={"context": "tab-1"})
        result = await backend.new_tab("https://example.com")
        assert result == "tab-1"

    async def test_close_tab(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.close_tab("tab-1")

    async def test_activate_tab(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.activate_tab("tab-1")

    async def test_capture_console(self) -> None:
        backend, mock = _make_mock_backend()
        mock.on_log_entry = AsyncMock(return_value="sub-1")
        result = await backend.capture_console()
        assert isinstance(result, list)

    async def test_capture_logs(self) -> None:
        backend, mock = _make_mock_backend()
        mock.on_log_entry = AsyncMock(return_value="sub-1")
        result = await backend.capture_logs()
        assert isinstance(result, list)

    async def test_dom_get(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value="<html>"))
        result = await backend.dom_get("h1")
        assert result == "<html>"

    async def test_dom_query(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value={"tagName": "div"}))
        result = await backend.dom_query("div")
        assert isinstance(result, dict)

    async def test_dom_set_attr(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.dom_set_attr("h1", "class", "active")

    async def test_dom_get_attr(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value="active"))
        result = await backend.dom_get_attr("h1", "class")
        assert result == "active"

    async def test_dom_remove_attr(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.dom_remove_attr("h1", "class")

    async def test_dom_remove(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.dom_remove("h1")

    async def test_dom_focus(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.dom_focus("h1")

    async def test_dom_scroll(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.dom_scroll("h1")

    async def test_get_cookies(self) -> None:
        backend, mock = _make_mock_backend()
        mock.storage.get_cookies = AsyncMock(return_value=[])
        result = await backend.get_cookies()
        assert isinstance(result, list)

    async def test_set_cookie(self) -> None:
        backend, _ = _make_mock_backend()
        from wavexis.config import CookieParams

        with patch("bidiwave.Cookie", MagicMock()):
            await backend.set_cookie(CookieParams(name="test", value="val", domain="example.com"))

    async def test_delete_cookie(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.delete_cookie("test", "example.com")

    async def test_clear_cookies(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.clear_cookies()

    async def test_set_headers(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.set_headers({"X-Test": "val"})

    async def test_set_user_agent(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.set_user_agent("TestAgent")

    async def test_new_context(self) -> None:
        backend, mock = _make_mock_backend()
        mock_ctx = MagicMock()
        mock_ctx.id = "ctx-2"
        mock.browsing.create_context = AsyncMock(return_value=mock_ctx)
        result = await backend.new_context()
        assert result == "ctx-2"

    async def test_list_contexts(self) -> None:
        backend, mock = _make_mock_backend()
        mock.browsing.get_tree = AsyncMock(return_value=MagicMock(contexts=[]))
        result = await backend.list_contexts()
        assert isinstance(result, list)

    async def test_close_context(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.close_context("ctx-2")

    async def test_get_window_bounds(self) -> None:
        backend, mock = _make_mock_backend()
        mock._connection.send_command = AsyncMock(
            return_value={"contexts": [{"bounds": {"width": 800}}]}
        )
        result = await backend.get_window_bounds()
        assert "width" in result

    async def test_set_window_bounds(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.set_window_bounds(1024, 768)

    async def test_browser_version(self) -> None:
        backend, mock = _make_mock_backend()
        mock.cdp.send_command = AsyncMock(return_value={"product": "Chrome/120"})
        result = await backend.browser_version()
        assert result == "Chrome/120"

    async def test_emulate_device(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.emulate_device("iphone-15")

    async def test_set_viewport(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.set_viewport(1280, 720)

    async def test_set_geolocation(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.set_geolocation(37.7749, -122.4194)

    async def test_set_timezone(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.set_timezone("America/Los_Angeles")

    async def test_set_dark_mode(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.set_dark_mode(True)

    async def test_click(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value=True))
        await backend.click("h1")

    async def test_type_text(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.type_text("input", "hello")

    async def test_fill(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value=True))
        await backend.fill("input", "hello", auto_wait=False)

    async def test_select_option(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.select_option("select", "option1")

    async def test_hover(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value=True))
        await backend.hover("h1")

    async def test_key_press(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.key_press("Enter")

    async def test_drag(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.drag("#source", "#target")

    async def test_tap(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value=True))
        await backend.tap("h1")

    async def test_set_files(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.set_files("input[type=file]", ["/path/to/file"])

    async def test_block_requests(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.block_requests(["*://ads.example.com/*"])

    async def test_throttle_network(self) -> None:
        backend, _ = _make_mock_backend()
        from wavexis.config import ThrottleParams

        await backend.throttle_network(ThrottleParams())

    async def test_set_cache_disabled(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.set_cache_disabled(True)

    async def test_intercept_requests(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.intercept_requests({"urlPattern": "*"})

    async def test_mock_response(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.mock_response("https://example.com", {"status": 200, "body": "ok"})

    async def test_get_request_body(self) -> None:
        backend, mock = _make_mock_backend()
        mock.cdp.send_command = AsyncMock(return_value={"postData": "data"})
        result = await backend.get_request_body("req-1")
        assert result == "data"

    async def test_get_response_body(self) -> None:
        backend, mock = _make_mock_backend()
        mock.network.response_body = AsyncMock(return_value=MagicMock(body="data"))
        result = await backend.get_response_body("req-1")
        assert result == "data"

    async def test_modify_request(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.modify_request({"urlPattern": "*"}, {"method": "POST"})

    async def test_modify_response(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.modify_response({"urlPattern": "*"}, {"status": 200, "body": "ok"})

    async def test_replay_har(self, tmp_path: Any) -> None:
        backend, _ = _make_mock_backend()
        har_file = tmp_path / "test.har"
        har_file.write_text('{"log":{"entries":[]}}')
        await backend.replay_har(str(har_file))

    async def test_intercept_download(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.intercept_download()

    async def test_dialog_accept(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.dialog_accept()

    async def test_dialog_dismiss(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.dialog_dismiss()

    async def test_grant_permission(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.grant_permission("geolocation")

    async def test_reset_permissions(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.reset_permissions()

    async def test_get_security_state(self) -> None:
        backend, mock = _make_mock_backend()
        mock.cdp.send_command = AsyncMock(return_value={"security": "secure"})
        result = await backend.get_security_state()
        assert isinstance(result, dict)

    async def test_ignore_cert_errors(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.ignore_cert_errors(True)

    async def test_set_locale(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.set_locale("en-US")

    async def test_set_cpu_throttle(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.set_cpu_throttle(4.0)

    async def test_set_touch_emulation(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.set_touch_emulation(True)

    async def test_set_sensors(self) -> None:
        backend, _ = _make_mock_backend()
        from wavexis.config import SensorParams

        await backend.set_sensors(SensorParams())

    async def test_perf_metrics(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value='{"loadEventEnd":100}'))
        result = await backend.perf_metrics()
        assert isinstance(result, dict)

    async def test_perf_trace(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.perf_trace(duration_ms=1)

    async def test_perf_profile(self) -> None:
        backend, mock = _make_mock_backend()
        mock.cdp.send_command = AsyncMock(return_value={"profile": "data"})
        result = await backend.perf_profile(duration_ms=1)
        assert isinstance(result, dict)

    async def test_perf_heap_snapshot(self) -> None:
        backend, mock = _make_mock_backend()
        mock.cdp.send_command = AsyncMock(return_value={"snapshot": "data"})
        result = await backend.perf_heap_snapshot()
        assert isinstance(result, dict)

    async def test_perf_coverage(self) -> None:
        backend, mock = _make_mock_backend()
        mock.cdp.send_command = AsyncMock(return_value={"result": {"script": []}})
        result = await backend.perf_coverage()
        assert isinstance(result, dict)

    async def test_perf_css_coverage(self) -> None:
        backend, mock = _make_mock_backend()
        mock.cdp.send_command = AsyncMock(return_value={"result": {"css": []}})
        result = await backend.perf_css_coverage()
        assert isinstance(result, dict)

    async def test_css_get_styles(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value="[]"))
        result = await backend.css_get_styles("h1")
        assert isinstance(result, list)

    async def test_css_get_stylesheets(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value="[]"))
        result = await backend.css_get_stylesheets()
        assert isinstance(result, list)

    async def test_css_get_rules(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value="[]"))
        result = await backend.css_get_rules("0")
        assert isinstance(result, list)

    async def test_css_get_computed(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value='{"color":"red"}'))
        result = await backend.css_get_computed("h1")
        assert isinstance(result, dict)

    async def test_debug_set_breakpoint(self) -> None:
        backend, mock = _make_mock_backend()
        mock.cdp.send_command = AsyncMock(return_value={"breakpointId": "bp-1"})
        result = await backend.debug_set_breakpoint("https://example.com", 10)
        assert result == "bp-1"

    async def test_debug_set_breakpoint_function(self) -> None:
        backend, mock = _make_mock_backend()
        mock.cdp.send_command = AsyncMock(return_value={"breakpointId": "bp-2"})
        result = await backend.debug_set_breakpoint_function("foo")
        assert result == "bp-2"

    async def test_debug_remove_breakpoint(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.debug_remove_breakpoint("bp-1")

    async def test_debug_step_over(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.debug_step_over()

    async def test_debug_step_into(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.debug_step_into()

    async def test_debug_step_out(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.debug_step_out()

    async def test_debug_pause(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.debug_pause()

    async def test_debug_resume(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.debug_resume()

    async def test_debug_get_listeners(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value="[]"))
        result = await backend.debug_get_listeners("h1")
        assert isinstance(result, list)

    async def test_dom_snapshot(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value='{"html":"<html>"}'))
        result = await backend.dom_snapshot()
        assert isinstance(result, dict)

    async def test_overlay_highlight(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.overlay_highlight("h1")

    async def test_overlay_clear(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.overlay_clear()

    async def test_storage_get(self) -> None:
        backend, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"value": "data"})
        result = await backend.storage_get("key")
        assert result == "data"

    async def test_storage_set(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.storage_set("key", "value")

    async def test_storage_clear(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.storage_clear()

    async def test_storage_list(self) -> None:
        backend, mock = _make_mock_backend()
        mock.send = AsyncMock(return_value={"entries": [["k", "v"]]})
        result = await backend.storage_list()
        assert isinstance(result, dict)

    async def test_cache_storage_list(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value="[]"))
        result = await backend.cache_storage_list()
        assert isinstance(result, list)

    async def test_cache_storage_entries(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value="[]"))
        result = await backend.cache_storage_entries("my-cache")
        assert isinstance(result, list)

    async def test_cache_storage_delete(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.cache_storage_delete("my-cache")

    async def test_indexeddb_list(self) -> None:
        backend, mock = _make_mock_backend()
        mock._connection.send_command = AsyncMock(return_value={"databases": []})
        result = await backend.indexeddb_list()
        assert isinstance(result, list)

    async def test_indexeddb_get_data(self) -> None:
        backend, mock = _make_mock_backend()
        mock._connection.send_command = AsyncMock(return_value={"rows": []})
        result = await backend.indexeddb_get_data("db", "store")
        assert isinstance(result, list)

    async def test_indexeddb_clear(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.indexeddb_clear("db", "store")

    async def test_sw_list(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value="[]"))
        result = await backend.sw_list()
        assert isinstance(result, list)

    async def test_sw_unregister(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.sw_unregister("scope")

    async def test_sw_update(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.sw_update("scope")

    async def test_animation_list(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value="[]"))
        result = await backend.animation_list()
        assert isinstance(result, list)

    async def test_animation_pause(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.animation_pause("anim-1")

    async def test_animation_play(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.animation_play("anim-1")

    async def test_animation_seek(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.animation_seek("anim-1", 500)

    async def test_webauthn_add_virtual_authenticator(self) -> None:
        backend, mock = _make_mock_backend()
        mock.cdp.send_command = AsyncMock(return_value={"authenticatorId": "auth-1"})
        result = await backend.webauthn_add_virtual_authenticator("ctap2", "usb")
        assert result == "auth-1"

    async def test_webauthn_remove_authenticator(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.webauthn_remove_authenticator("auth-1")

    async def test_webauthn_add_credential(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.webauthn_add_credential("auth-1", {})

    async def test_webauthn_get_credentials(self) -> None:
        backend, mock = _make_mock_backend()
        mock._connection.send_command = AsyncMock(return_value={"credentials": []})
        result = await backend.webauthn_get_credentials("auth-1")
        assert isinstance(result, list)

    async def test_webaudio_get_contexts(self) -> None:
        backend, mock = _make_mock_backend()
        mock.cdp.send_command = AsyncMock(return_value={})
        mock.cdp.wait_for_event = AsyncMock(side_effect=TimeoutError())
        result = await backend.webaudio_get_contexts()
        assert isinstance(result, list)

    async def test_webaudio_get_context(self) -> None:
        backend, mock = _make_mock_backend()
        mock.cdp.send_command = AsyncMock(return_value={})
        mock.cdp.wait_for_event = AsyncMock(side_effect=TimeoutError())
        result = await backend.webaudio_get_context("ctx-1")
        assert isinstance(result, dict)

    async def test_media_get_players(self) -> None:
        backend, mock = _make_mock_backend()
        mock._connection.send_command = AsyncMock(return_value={"players": []})
        result = await backend.media_get_players()
        assert isinstance(result, list)

    async def test_media_get_messages(self) -> None:
        backend, mock = _make_mock_backend()
        mock._connection.send_command = AsyncMock(return_value={"messages": []})
        result = await backend.media_get_messages("player-1")
        assert isinstance(result, list)

    async def test_cast_list(self) -> None:
        backend, mock = _make_mock_backend()
        mock._connection.send_command = AsyncMock(return_value={"sinks": []})
        result = await backend.cast_list()
        assert isinstance(result, list)

    async def test_cast_start_tab(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.cast_start_tab("sink-1")

    async def test_cast_stop(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.cast_stop()

    async def test_bluetooth_emulate(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.bluetooth_emulate("adapter-1")

    async def test_bluetooth_stop(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.bluetooth_stop()

    async def test_extension_install(self, tmp_path: Any) -> None:
        backend, mock = _make_mock_backend()
        ext_dir = tmp_path / "myext"
        ext_dir.mkdir()
        mock.cdp.send_command = AsyncMock(return_value={"id": "ext-123"})
        result = await backend.extension_install(str(ext_dir))
        assert len(result) == 32

    async def test_extension_uninstall(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.extension_uninstall("ext-123")

    async def test_extension_list(self) -> None:
        backend, mock = _make_mock_backend()
        mock._connection.send_command = AsyncMock(return_value={"extensions": []})
        result = await backend.extension_list()
        assert isinstance(result, list)

    async def test_get_pref(self) -> None:
        backend, mock = _make_mock_backend()
        mock.cdp.send_command = AsyncMock(return_value={"value": True})
        result = await backend.get_pref("safebrowsing.enabled")
        assert result is True

    async def test_set_pref(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.set_pref("safebrowsing.enabled", False)

    async def test_annotated_screenshot(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value="{}"))
        mock.browsing.screenshot = AsyncMock(
            return_value=MagicMock(data=base64.b64encode(b"img").decode())
        )
        result = await backend.annotated_screenshot(["h1", "p"])
        assert isinstance(result, tuple)

    async def test_find_by_text(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value='["h1"]'))
        result = await backend.find_by_text("Hello")
        assert result == "h1"

    async def test_nl_click(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value='["h1"]'))
        await backend.nl_click("click the button", auto_wait=False)

    async def test_nl_fill(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value='["input"]'))
        await backend.nl_fill("fill the input", "hello", auto_wait=False)

    async def test_suggest_locator(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value='["h1"]'))
        result = await backend.suggest_locator("the heading")
        assert isinstance(result, (list, str))

    async def test_iframe_eval(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value="result"))
        result = await backend.iframe_eval("iframe", "document.title")
        assert result == "result"

    async def test_iframe_click(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value=True))
        await backend.iframe_click("iframe", "button")

    async def test_iframe_fill(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value=True))
        await backend.iframe_fill("iframe", "input", "hello")

    async def test_shadow_eval(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value="result"))
        result = await backend.shadow_eval("host", "element")
        assert result == "result"

    async def test_shadow_click(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value=True))
        await backend.shadow_click("host", "button")

    async def test_shadow_fill(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value=True))
        await backend.shadow_fill("host", "input", "hello")

    async def test_capture_har(self) -> None:
        backend, mock = _make_mock_backend()
        mock._connection.send_command = AsyncMock(return_value={})
        from wavexis.config import HarParams

        result = await backend.capture_har(HarParams(url="https://example.com"))
        assert isinstance(result, dict)

    async def test_subscribe_events(self) -> None:
        backend, mock = _make_mock_backend()
        mock.cdp.on = MagicMock()
        result = await backend.subscribe_events(["console"], callback=lambda e: None)
        assert isinstance(result, str)

    async def test_unsubscribe_events(self) -> None:
        backend, mock = _make_mock_backend()
        mock.cdp.off = MagicMock()
        backend._subscriptions = {"sub-1": {"event": lambda: None}}
        await backend.unsubscribe_events("sub-1")

    async def test_a11y_tree(self) -> None:
        backend, mock = _make_mock_backend()
        mock._connection.send_command = AsyncMock(return_value={"tree": {}})
        result = await backend.a11y_tree()
        assert isinstance(result, dict)

    async def test_a11y_node(self) -> None:
        backend, mock = _make_mock_backend()
        mock._connection.send_command = AsyncMock(return_value={"node": {}})
        result = await backend.a11y_node("1")
        assert isinstance(result, dict)

    async def test_a11y_ancestors(self) -> None:
        backend, mock = _make_mock_backend()
        mock._connection.send_command = AsyncMock(return_value={"ancestors": []})
        result = await backend.a11y_ancestors("1")
        assert isinstance(result, list)

    async def test_start_combined_trace(self) -> None:
        backend, _ = _make_mock_backend()
        result = await backend.start_combined_trace(
            capture_screenshots=False,
            capture_network=True,
            capture_console=True,
        )
        assert isinstance(result, str)

    async def test_stop_combined_trace(self) -> None:
        backend, _ = _make_mock_backend()
        trace_id = await backend.start_combined_trace()
        result = await backend.stop_combined_trace(trace_id)
        assert isinstance(result, dict)

    async def test_axe_audit(self) -> None:
        backend, mock = _make_mock_backend()
        mock.script.evaluate = AsyncMock(return_value=MagicMock(value='{"passes":[]}'))
        result = await backend.axe_audit()
        assert isinstance(result, dict)

    async def test_launch_with_browser_url(self) -> None:
        backend = _make_mock_backend()[0]
        backend._client = None
        backend._context = None
        mock_client = MagicMock(
            session=MagicMock(new=AsyncMock()),
            browsing=MagicMock(
                create_context=AsyncMock(return_value="ctx-1"),
                set_viewport=AsyncMock(),
            ),
            script=MagicMock(evaluate=AsyncMock()),
            cdp=MagicMock(send_command=AsyncMock()),
            emulation=MagicMock(set_user_agent=AsyncMock()),
            close=AsyncMock(),
        )
        with patch("wavexis.backend.bidi.BiDiClient") as mock_client_cls:
            mock_client_cls.connect = AsyncMock(return_value=mock_client)
            opts = BrowserOptions(browser_url="http://localhost:9222", stealth=True)
            await backend.launch(opts)

    async def test_launch_with_remote_url(self) -> None:
        backend = _make_mock_backend()[0]
        backend._client = None
        backend._context = None
        mock_client = MagicMock(
            session=MagicMock(new=AsyncMock()),
            browsing=MagicMock(
                create_context=AsyncMock(return_value="ctx-1"),
                set_viewport=AsyncMock(),
            ),
            script=MagicMock(evaluate=AsyncMock()),
            cdp=MagicMock(send_command=AsyncMock()),
            emulation=MagicMock(set_user_agent=AsyncMock()),
            close=AsyncMock(),
        )
        with patch("wavexis.backend.bidi.BiDiClient") as mock_client_cls:
            mock_client_cls.connect = AsyncMock(return_value=mock_client)
            opts = BrowserOptions(
                remote_url="ws://localhost:9222/session",
                user_agent="TestAgent",
                extra_headers={"X-Test": "val"},
                proxy="http://proxy:8080",
            )
            await backend.launch(opts)

    async def test_launch_already_launched(self) -> None:
        backend, _ = _make_mock_backend()
        await backend.launch(BrowserOptions())

    async def test_close_with_client(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.close()
        mock.browsing.close.assert_called_once()
        mock.close.assert_called_once()
        assert backend._client is None

    async def test_close_without_client(self) -> None:
        from wavexis.backend.bidi import BiDiBackend

        backend = BiDiBackend()
        await backend.close()

    async def test_new_tab_handle(self) -> None:
        backend, mock = _make_mock_backend()
        mock.browsing.create_context = AsyncMock(return_value="ctx-2")
        handle = await backend.new_tab_handle("https://example.com")
        assert handle is not None
