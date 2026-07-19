"""Unit tests for BiDiBackend."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from wavexis.config import BrowserOptions, ScreenshotParams
from wavexis.exceptions import SessionNotInitializedError


@pytest.mark.unit
class TestBiDiBackend:
    """Test suite for bidibackend."""

    def test_import_error(self) -> None:
        """Test import error on launch when bidiwave not installed."""
        with patch("wavexis.backend.bidi.BiDiClient", None):
            from wavexis.backend.bidi import BiDiBackend

            backend = BiDiBackend()
            with pytest.raises(ImportError, match="bidiwave"):
                asyncio.run(backend.launch(BrowserOptions()))

    async def test_implemented_methods_raise_runtime_without_launch(self) -> None:
        """Test implemented methods raise runtime without launch."""
        with patch("wavexis.backend.bidi.BiDiClient", MagicMock()):
            from wavexis.backend.bidi import BiDiBackend

            backend = BiDiBackend()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.activate_tab("x")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.capture_console()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.capture_logs()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.get_cookies()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_cookie(MagicMock())
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.delete_cookie("x", "y")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.clear_cookies()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_headers({})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_user_agent("x")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.browser_version()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_viewport(100, 100)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_geolocation(0.0, 0.0)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_timezone("UTC")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_dark_mode(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.screenshot_selector("h1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_locale("en-US")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_touch_emulation(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.throttle_network(MagicMock())
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_cache_disabled(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.mock_response("https://example.com", {})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.pdf(MagicMock())
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.emulate_device("iphone-15")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.get_security_state()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.ignore_cert_errors(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_cpu_throttle(4.0)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_sensors(MagicMock())
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.perf_metrics()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.perf_coverage()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.performance_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.performance_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.performance_get_metrics()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.performance_set_time_domain("timeTicks")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.performance_timeline_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_get_styles("h1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_get_computed("h1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_snapshot()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.perf_css_coverage()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_get_stylesheets()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_get_rules("0")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_highlight("h1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_clear()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.cache_storage_list()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.cache_storage_entries("my-cache")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.cache_storage_delete("my-cache")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.a11y_tree()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.a11y_node("1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.a11y_ancestors("1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.intercept_download()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.perf_trace()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.perf_profile()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.perf_heap_snapshot()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_get_listeners("h1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.indexeddb_list()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.indexeddb_get_data("db", "store")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.indexeddb_clear("db", "store")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.sw_list()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.sw_unregister("scope")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.sw_update("scope")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.animation_list()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.animation_pause("0")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.animation_play("0")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.animation_seek("0", 500)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.screencast(MagicMock())
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.capture_har(MagicMock())
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_set_breakpoint("https://example.com", 10)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_set_breakpoint_function("foo")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_remove_breakpoint("bp1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_step_over()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_step_into()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_step_out()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_pause()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_resume()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.webauthn_add_virtual_authenticator("ctap2", "usb")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.webauthn_remove_authenticator("auth1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.webauthn_add_credential("auth1", {})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.webauthn_get_credentials("auth1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.webaudio_get_contexts()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.webaudio_get_context("ctx1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.media_get_players()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.media_get_messages("player1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.cast_list()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.cast_start_tab("sink1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.cast_stop()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.bluetooth_emulate("adapter1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.bluetooth_stop()

    async def test_bidi_paridad_methods_raise_runtime_without_launch(self) -> None:
        """Test bidi paridad methods raise runtime without launch."""
        with patch("wavexis.backend.bidi.BiDiClient", MagicMock()):
            from wavexis.backend.bidi import BiDiBackend

            backend = BiDiBackend()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.go_back()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.go_forward()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.reload()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.stop_loading()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.list_tabs()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.new_tab()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.close_tab("x")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get("h1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.new_context()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.list_contexts()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.close_context("x")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.get_window_bounds()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_window_bounds(100, 100)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_get_frame_tree()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_get_layout_metrics()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_get_navigation_history()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_navigate_to_history_entry(0)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_bring_to_front()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_wait_for_debugger()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_get_resource_content("frame-1", "https://example.com")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_set_download_behavior("allow", "/tmp")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_document()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_flattened_document()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_box_model("h1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_content_quads("h1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_node_for_location(10, 20)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_perform_search("hello")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_search_results("s1", 0, 10)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_scroll_into_view_if_needed("h1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_device_metrics_override(375, 812)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.clear_device_metrics_override()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_emulated_media("print")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.clear_emulated_media()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_emulated_vision_deficiency("none")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.clear_emulated_vision_deficiency()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_idle_override()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.clear_idle_override()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_script_execution_disabled(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_visible_size(800, 600)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_capture_snapshot()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_print_to_pdf()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_start_screencast()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_stop_screencast()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_set_bypass_csp(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_set_ad_blocking_enabled(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_add_script_to_evaluate_on_new_document("console.log(1)")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_remove_script_to_evaluate_on_new_document("s1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_generate_test_report("test")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_get_app_manifest()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_get_resource_tree()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_add_compilation_cache("https://example.com", "data")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_add_script_to_evaluate_on_load("console.log(1)")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_capture_screenshot()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_clear_compilation_cache()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_clear_device_orientation_override()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_clear_geolocation_override()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_crash()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_create_isolated_world("frame-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_get_ad_script_ancestry("frame-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_get_annotated_page_content()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_get_app_id()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_get_installability_errors()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_get_manifest_icons()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_get_origin_trials()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_get_permissions_policy_state("frame-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_handle_java_script_dialog(True, "ok")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_handle_javascript_dialog(False)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_produce_compilation_cache("https://example.com")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_remove_script_to_evaluate_on_load("script-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_reset_navigation_history()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_screencast_frame_ack(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_search_in_resource("frame-1", "https://example.com", "test")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_set_device_orientation_override(0.0, 0.0, 0.0)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_set_document_content("frame-1", "<html></html>")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_set_font_families({"standard": "Arial"})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_set_font_sizes({"standard": 16})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_set_geolocation_override(37.0, -122.0, 10.0)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_set_intercept_file_chooser_dialog(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_set_lifecycle_events_enabled(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_set_prerendering_allowed(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_set_rph_registration_mode("auto")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_set_spc_transaction_mode("auto")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_set_touch_emulation_enabled(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_set_web_lifecycle_state("active")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.page_stop()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_add_rule("ss-1", ".test { }")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_create_style_sheet("frame-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_get_media_queries()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_get_style_sheet_text("ss-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_set_style_sheet_text("ss-1", "body { }")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_set_rule_selector("ss-1", "0", ".new")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_set_media_text("ss-1", "0", "(max-width: 600px)")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_force_pseudo_state(1, ["hover"])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_get_background_colors(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_start_rule_usage_tracking()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_stop_rule_usage_tracking()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_take_coverage_delta()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_collect_class_names(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_force_starting_style(1, {"styleSheetId": "ss-1", "ordinal": 0})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_get_animated_styles_for_node(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_get_computed_style_for_node(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_get_environment_variables()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_get_inline_styles(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_get_inline_styles_for_node(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_get_layers_for_node(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_get_location_for_selector(".test", "ss-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_get_longhand_properties({"styleSheetId": "ss-1", "ordinal": 0})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_get_matched_styles_for_node(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_get_platform_fonts_for_node(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_get_stylesheet_text("ss-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_resolve_values([{"name": "color", "value": "red"}])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_set_container_query_condition_text(
                    "ss-1", {"styleSheetId": "ss-1", "ordinal": 0}, "(min-width: 600px)"
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_set_effective_property_value_for_node(1, "color", "red")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_set_keyframe_key(
                    "ss-1", {"styleSheetId": "ss-1", "ordinal": 0}, "0%"
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_set_local_fonts_enabled(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_set_navigation_text(
                    "ss-1", {"styleSheetId": "ss-1", "ordinal": 0}, "@media (nav)"
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_set_property_rule_property_name(
                    "ss-1", {"styleSheetId": "ss-1", "ordinal": 0}, "color"
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_set_rule_style(
                    "ss-1", {"styleSheetId": "ss-1", "ordinal": 0}, "color: red;"
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_set_scope_text(
                    "ss-1", {"styleSheetId": "ss-1", "ordinal": 0}, ".scope"
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_set_style_sheet_text("ss-1", ".test { color: red; }")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_set_style_text(
                    [{"styleSheetId": "ss-1", "ordinal": 0, "text": "color: red;"}]
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_set_style_texts(
                    [{"styleSheetId": "ss-1", "ordinal": 0, "text": "color: blue;"}]
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_set_stylesheet_text("ss-1", ".test { color: green; }")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_set_supports_text(
                    "ss-1", {"styleSheetId": "ss-1", "ordinal": 0}, "(display: flex)"
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_take_computed_style_updates()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_track_computed_style_updates(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.css_track_computed_style_updates_for_node(1, True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_evaluate_on_call_frame("cf-1", "1+1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_get_script_source("s1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_get_stack_trace()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_get_possible_breakpoints({"scriptId": "s1", "lineNumber": 0})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_search_in_content("s1", "test")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_set_pause_on_exceptions("all")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_set_breakpoints_active(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_set_skip_all_pauses(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_set_script_source("s1", "console.log(2)")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_continue_to_location("script.js", 10, 0)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_disassemble_wasm_module("script-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_get_wasm_bytecode("script-1", 0)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_next_wasm_disassembly_chunk("dis-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_pause()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_pause_on_async_call("await")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_remove_breakpoint("bp-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_restart_frame("cf-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_resume()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_set_async_call_stack_depth(32)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_set_blackbox_execution_contexts(["ctx-1"])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_set_blackbox_patterns(["*.min.js"])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_set_blackboxed_ranges("script-1", [{"lineNumber": 0}])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_set_breakpoint_raw({"scriptId": "s1", "lineNumber": 0})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_set_breakpoint_by_url("script.js", 10)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_set_breakpoint_on_function_call("obj-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_set_instrumentation_breakpoint("beforeScriptExecution")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_set_return_value({"value": 42})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.debug_set_variable_value("cf-1", 0, "x", {"value": 42})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.storage_clear_data_for_origin("https://example.com")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.storage_get_usage_and_quota("https://example.com")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.storage_get_trust_tokens()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.storage_clear_trust_tokens("https://example.com")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.storage_get_shared_storage_entries("https://example.com")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.storage_set_shared_storage_entry("https://example.com", "k", "v")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.storage_delete_shared_storage_entry("https://example.com", "k")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.storage_clear_shared_storage_entries("https://example.com")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.storage_get_interest_group_details("https://example.com", "g1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.storage_override_quota_for_origin("https://example.com")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_clear_browser_cache()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_clear_browser_cookies()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_delete_cookies("test", "example.com")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_set_blocked_urls(["https://ads.com/*"])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_set_bypass_service_worker(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_set_cookie_controls("block", "block")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_set_extra_request_headers({"X-Test": "1"})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_set_user_agent_override("TestUA", "en", "Win")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_replay_xhr("req-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_load_network_resource("frame-1", "https://example.com")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_highlight_node(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_highlight_quad([0, 0, 100, 0, 100, 100, 0, 100])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_highlight_rect(0, 0, 100, 100)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_set_inspect_mode("searchForNode")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_set_show_fps_counter(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_set_show_paint_rects(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_set_show_debug_borders(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_set_show_ad_highlights(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_get_grid_highlight_objects_for_test(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_get_highlight_object_for_test(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_get_source_order_highlight_object_for_test(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_hide_highlight()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_highlight_source_order({"nodeId": 1})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_set_paused_in_debugger_message("paused")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_set_show_container_query_overlays(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_set_show_display_cutout(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_set_show_flex_overlays(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_set_show_grid_overlays([{"nodeId": 1}])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_set_show_hinge({"rect": {}})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_set_show_inspected_element_anchor(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_set_show_isolated_elements([{"nodeId": 1}])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_set_show_layout_shift_regions(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_set_show_scroll_bottleneck_rects(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_set_show_scroll_snap_overlays(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_set_show_viewport_size_on_resize(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.overlay_set_show_window_controls_overlay(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_evaluate("1+1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_compile_script("function(){}")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_run_script("1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_call_function_on("function(){return 1;}")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_get_properties("obj-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_release_object("obj-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_release_object_group("group-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_discard_console_entries()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_get_heap_usage()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_global_lexical_scope_names()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_add_binding("test-binding")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_await_promise("obj-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_collect_garbage()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_get_exception_details("err-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_get_isolate_id()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_query_objects("proto-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_remove_binding("test-binding")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_run_if_waiting_for_debugger()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_set_async_call_stack_depth(32)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_set_custom_object_formatter_enabled(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_set_max_call_stack_size_to_capture(1000)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.runtime_terminate_execution()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.schema_get_domains()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.security_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.security_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.security_get_visible_security_state()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.security_handle_certificate_error(1, "continue")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.security_set_ignore_certificate_errors(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.security_set_override_certificate_errors(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.sensor_clear_sensor_override("accelerometer")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.sensor_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.sensor_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.sensor_set_sensor_override("accelerometer")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.target_get_targets()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.target_create_target("https://example.com")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.target_close_target("tab-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.target_activate_target("tab-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.target_attach_to_target("tab-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.target_detach_from_target("sess-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.target_set_auto_attach(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.target_set_discover_targets(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.target_get_target_info("tab-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.target_create_browser_context()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_describe_node(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_outer_html(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_remove_node(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_set_node_value(1, "test")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_set_outer_html(1, "<p>test</p>")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_request_node(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_resolve_node(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_set_attribute_value(1, "class", "test")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_remove_attribute(1, "class")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_request_child_nodes(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_collect_class_names_from_subtree(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_copy_to(1, 2)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_discard_search_results("search-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_focus_node(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_force_show_popover(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_anchor_element(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_node_attribute(1, "class")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_container_for_node(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_detached_dom_nodes()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_element_by_relation(1, "popover")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_file_info(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_frame_owner("frame-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_node_stack_traces(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_nodes_for_subtree_by_style(1, ["color"])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_querying_descendants_for_container(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_relayout_boundary(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_get_top_layer_elements()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_hide_highlight()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_highlight_node(1, {"showInfo": True})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_highlight_rect(0, 0, 100, 100, {"showInfo": True})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_mark_undoable_state()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_move_to(1, 2)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_push_node_by_path_to_frontend("body/div")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_push_nodes_by_backend_ids_to_frontend([1, 2])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_query_selector(1, ".foo")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_query_selector_all(1, ".foo")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_redo()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_remove_node_by_id(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_set_attributes_as_text(1, 'class="foo"')
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_set_file_input_files(1, ["/path/to/file"])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_set_inspected_node(1)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_set_node_name(1, "div")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_set_node_stack_traces_enabled(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_set_text_content(1, "hello")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_undo()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_debugger_get_event_listeners("obj-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_debugger_remove_dom_breakpoint(1, "subtree-modified")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_debugger_remove_event_listener_breakpoint("click")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_debugger_remove_instrumentation_breakpoint("scriptFirstStatement")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_debugger_remove_xhr_breakpoint("https://example.com")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_debugger_set_break_on_csp_violation(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_debugger_set_dom_breakpoint(1, "subtree-modified")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_debugger_set_event_listener_breakpoint("click")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_debugger_set_instrumentation_breakpoint("scriptFirstStatement")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_debugger_set_xhr_breakpoint("https://example.com")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.add_screen({"width": 1920, "height": 1080})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.can_emulate()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.clear_auto_dark_mode_override()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.clear_default_background_color_override()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.clear_device_posture_override()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.clear_display_features_override()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.clear_geolocation_override()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.clear_timezone_override()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.get_overridden_sensor_information("accelerometer")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.get_screen_infos()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.remove_screen("screen-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.reset_page_scale_factor()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_auto_dark_mode_override(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_automation_override(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_cpu_throttling_rate(4.0)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_data_saver_override(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_default_background_color_override(
                    {"r": 0, "g": 0, "b": 0, "a": 1}
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_device_posture_override("continuous")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_disabled_image_types(["avif"])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_display_features_override([{"type": "fold"}])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_document_cookie_disabled(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_emit_touch_events_for_mouse(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_emulated_media_feature(
                    [{"name": "prefers-color-scheme", "value": "dark"}]
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_emulated_os_text_scale(1.5)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_focus_emulation_enabled(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_geolocation_override(37.7749, -122.4194)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_hardware_concurrency_override(4)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_locale_override("en-US")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_navigator_overrides({"platform": "Linux"})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_page_scale_factor(2.0)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_pressure_source_override_enabled("touch", True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_pressure_state_override("touch", "known", 1.0)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_primary_screen("screen-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_safe_area_insets_override({"top": 50})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_scrollbars_hidden(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_sensor_override_enabled("accelerometer", True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_sensor_override_readings("accelerometer", [{"x": 1.0}])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_small_viewport_height_difference_override(10.0)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_timezone_override("America/New_York")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_touch_emulation_enabled(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_user_agent_override("Mozilla/5.0")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_virtual_time_policy("advance")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.update_screen("screen-1", {"width": 1920})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.device_access_cancel_prompt("prompt-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.device_access_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.device_access_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.device_access_select_prompt("prompt-1", "device-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.device_orientation_clear_override()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.device_orientation_set_override(1.0, 2.0, 3.0)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.digital_credentials_set_virtual_wallet_behavior({"mode": "test"})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_snapshot_capture_snapshot()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_snapshot_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_snapshot_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_snapshot_get_snapshot()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_storage_clear(
                    {"securityOrigin": "https://example.com", "isLocalStorage": True}
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_storage_clear_items(
                    {"securityOrigin": "https://example.com", "isLocalStorage": True}
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_storage_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_storage_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_storage_get_items(
                    {"securityOrigin": "https://example.com", "isLocalStorage": True}
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_storage_remove_item(
                    {"securityOrigin": "https://example.com", "isLocalStorage": True}, "key1"
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.dom_storage_set_item(
                    {"securityOrigin": "https://example.com", "isLocalStorage": True},
                    "key1",
                    "val1",
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.event_breakpoints_clear_instrumentation_breakpoint("Event.source")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.event_breakpoints_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.event_breakpoints_remove_instrumentation_breakpoint("Event.source")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.event_breakpoints_set_instrumentation_breakpoint("Event.source")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.extensions_clear_storage_items("ext-1", "local")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.extensions_get_storage_items("ext-1", "local")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.extensions_remove_storage_items("ext-1", "local", ["key1"])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.extensions_set_storage_items(
                    "ext-1", "local", [{"key": "k", "value": "v"}]
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.extensions_trigger_action("ext-1", "action-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.fed_cm_click_dialog_button("dialog-1", 0)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.fed_cm_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.fed_cm_dismiss_dialog("dialog-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.fed_cm_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.fed_cm_open_url("dialog-1", 0, "https://example.com")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.fed_cm_reset_cooldown()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.fed_cm_select_account("dialog-1", 0)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.fetch_continue_request("req-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.fetch_continue_request_with_auth("req-1", {"response": "Default"})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.fetch_continue_response("req-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.fetch_continue_with_auth("req-1", {"response": "Default"})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.fetch_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.fetch_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.fetch_fail_request("req-1", "Failed")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.fetch_fulfill_request("req-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.fetch_get_request_post_data("req-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.fetch_take_response_body_as_stream("req-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.file_system_get_directory("https://example.com", "local")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.headless_experimental_begin_frame()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.headless_experimental_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.headless_experimental_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.inspector_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.inspector_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.preload_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.preload_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.preload_get_preload_policy()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.preload_set_preload_policy({"key": "value"})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.profiler_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.profiler_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.profiler_get_best_effort_coverage()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.profiler_set_sampling_interval(1000)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.profiler_start()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.profiler_start_precise_coverage()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.profiler_stop()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.profiler_stop_precise_coverage()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.profiler_take_precise_coverage()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.pwa_change_app_user_settings("app-1", {"key": "value"})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.pwa_get_os_app_state("app-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.pwa_install("manifest-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.pwa_launch_files_in_app("app-1", ["/path/file.txt"])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.pwa_open_current_page_in_app("app-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.pwa_uninstall("app-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.io_read("handle-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.io_resolve_blob("obj-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.heap_profiler_add_inspected_heap_object("heap-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.heap_profiler_collect_garbage()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.heap_profiler_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.heap_profiler_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.heap_profiler_get_heap_object_id("obj-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.heap_profiler_get_object_by_heap_object_id("hoid-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.heap_profiler_get_sampling_profile()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.heap_profiler_start_sampling(1024)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.heap_profiler_start_tracking_heap_objects(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.heap_profiler_stop_sampling()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.heap_profiler_stop_tracking_heap_objects(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.heap_profiler_take_heap_snapshot(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.indexed_db_clear_object_store("https://example.com", "db1", "store1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.indexed_db_delete_database("https://example.com", "db1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.indexed_db_delete_object_store_entries(
                    "https://example.com", "db1", "store1", {"lower": 0}
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.indexed_db_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.indexed_db_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.indexed_db_get_metadata("https://example.com", "db1", "store1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.indexed_db_request_data(
                    "https://example.com", "db1", "store1", "idx1"
                )
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.indexed_db_request_database("https://example.com", "db1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.indexed_db_request_database_names("https://example.com")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.layer_tree_compositing_reasons("layer-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.layer_tree_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.layer_tree_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.layer_tree_load_snapshot([{"layers": []}])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.layer_tree_make_snapshot("layer-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.layer_tree_profile_snapshot("snap-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.layer_tree_release_snapshot("snap-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.layer_tree_replay_snapshot("snap-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.layer_tree_snapshot_command_log("snap-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.log_clear()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.log_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.log_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.log_start_violations_report([{"name": "longTask", "threshold": 100}])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.log_stop_violations_report()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.media_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.media_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.memory_forcibly_purge_javascript_memory()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.memory_get_all_time_sampling_profile()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.memory_get_browser_sampling_profile()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.memory_get_dom_counters()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.memory_get_dom_counters_for_leak_detection()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.memory_get_sampling_profile()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.memory_prepare_for_leak_detection()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.memory_set_pressure_notifications_suppressed(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.memory_simulate_pressure_notification("moderate")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.memory_start_sampling(1024)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.memory_stop_sampling()

            # Console
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.console_clear_messages()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.console_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.console_enable()

            # CrashReportContext
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.crash_report_context_get_entries()

            # Input (low-level CDP)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.input_cancel_dragging()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.input_dispatch_drag_event("dragEnter", 10, 20)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.input_dispatch_key_event("keyDown", key="a")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.input_dispatch_mouse_event("mousePressed", 10, 20)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.input_dispatch_touch_event("touchStart", [{"x": 0, "y": 0}])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.input_emulate_touch_from_mouse_event("mousePressed", 10, 20)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.input_ime_set_composition("text", 0, 4)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.input_insert_text("hello")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.input_set_ignore_input_events(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.input_set_intercept_drags(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.input_synthesize_pinch_gesture(10, 20, 2.0)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.input_synthesize_scroll_gesture(10, 20, y_distance=100)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.input_synthesize_tap_gesture(10, 20)

            # Network (additional CDP methods)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_clear_accepted_encodings_override()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_configure_durable_messages({"key": "value"})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_delete_device_bound_session("session-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_disable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_emulate_network_conditions_by_rule(offline=True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_enable()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_enable_device_bound_sessions()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_enable_reporting_api(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_fetch_schemeful_site("req-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_get_certificate("https://example.com")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_get_request_post_data("req-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_get_response_body_for_interception("int-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_get_security_isolation_status()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_override_network_state({"key": "value"})
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_search_in_response_body("req-1", "query")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_set_accepted_encodings(["gzip"])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_set_attach_debug_stack(True)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_set_cookies([{"name": "foo", "value": "bar"}])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_stream_resource_content("req-1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.network_take_response_body_for_interception_as_stream("int-1")

    async def test_navigate_without_launch(self) -> None:
        """Test navigate without launch."""
        with patch("wavexis.backend.bidi.BiDiClient", MagicMock()):
            from wavexis.backend.bidi import BiDiBackend

            backend = BiDiBackend()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.navigate("https://example.com")

    async def test_eval_without_launch(self) -> None:
        """Test eval without launch."""
        with patch("wavexis.backend.bidi.BiDiClient", MagicMock()):
            from wavexis.backend.bidi import BiDiBackend

            backend = BiDiBackend()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.eval("document.title")

    async def test_raw_without_launch(self) -> None:
        """Test raw without launch."""
        with patch("wavexis.backend.bidi.BiDiClient", MagicMock()):
            from wavexis.backend.bidi import BiDiBackend

            backend = BiDiBackend()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.raw("test.method")

    async def test_screenshot_without_launch(self) -> None:
        """Test screenshot without launch."""
        with patch("wavexis.backend.bidi.BiDiClient", MagicMock()):
            from wavexis.backend.bidi import BiDiBackend

            backend = BiDiBackend()
            params = ScreenshotParams(url="https://example.com")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.screenshot(params)

    async def test_close_without_launch(self) -> None:
        """Test close without launch."""
        with patch("wavexis.backend.bidi.BiDiClient", MagicMock()):
            from wavexis.backend.bidi import BiDiBackend

            backend = BiDiBackend()
            await backend.close()

    async def test_bidi_native_wrappers_raise_without_launch(self) -> None:
        """Test BiDi native wrapper methods raise without launch."""
        with patch("wavexis.backend.bidi.BiDiClient", MagicMock()):
            from wavexis.backend.bidi import BiDiBackend

            backend = BiDiBackend()

            # Browsing
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.get_client_windows()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.get_user_contexts()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.remove_user_context("uc1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_client_window_state("maximized")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.get_viewport()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.wait_for_function("document.title")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.wait_for_selector("h1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.locate_nodes({"type": "css", "value": "div"})

            # CDP Bridge
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.get_cdp_session()

            # Emulation
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_screen_orientation("landscapePrimary")

            # Input
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.perform_actions([])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.release_actions()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.drag_and_drop(0, 0, 100, 100)
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.input_scroll(0, 0, 0, 100)

            # Network
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.add_data_collector(["responseBody"])
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.get_network_data("req1", "responseBody")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.disown_network_data("col1", "req1", "responseBody")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.remove_data_collector("col1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.remove_intercept("int1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.remove_cache_override("cache1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.continue_response("req1")

            # Permissions
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.set_permission({"name": "geolocation"}, "granted")

            # Preload Scripts
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.add_preload_script("console.log(1)")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.remove_preload_script("script1")

            # Script
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.call_function("() => 1")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.get_realms()
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.disown_handles(["handle1"])

            # Session
            with pytest.raises(SessionNotInitializedError):
                await backend.session_status()

            # Storage
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.delete_cookies("foo", "example.com")

            # WebExtensions
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.webextension_install("base64data")
            with pytest.raises(SessionNotInitializedError, match="not launched"):
                await backend.webextension_uninstall("ext1")
