"""Unit tests for BackendManager."""

from __future__ import annotations

from typing import Any

import pytest

from browsix.backend.base import AbstractBackend
from browsix.backend.manager import BackendManager
from browsix.exceptions import BackendNotAvailableError, BackendNotSupportedError


class DummyBackend(AbstractBackend):
    """Dummy backend for testing."""

    def __init__(self) -> None:
        pass

    async def launch(self, options: object) -> None:
        pass

    async def close(self) -> None:
        pass

    async def navigate(self, url: str, wait: object | None = None) -> None:
        pass

    async def screenshot(self, params: object) -> bytes:
        return b""

    async def screenshot_selector(
        self, selector: str, format: str = "png", quality: int = 80
    ) -> bytes:
        return b""

    async def eval(self, expression: str, await_promise: bool = False) -> object:
        return None

    async def raw(self, method: str, params: dict | None = None) -> dict:
        return {}

    async def go_back(self) -> None:
        pass

    async def go_forward(self) -> None:
        pass

    async def reload(self, ignore_cache: bool = False) -> None:
        pass

    async def stop_loading(self) -> None:
        pass

    async def wait_for(self, strategy: object) -> None:
        pass

    async def pdf(self, params: object) -> bytes:
        return b""

    async def screencast(self, params: object) -> list[bytes]:
        return []

    async def list_tabs(self) -> list[dict]:
        return []

    async def new_tab(self, url: str = "about:blank") -> str:
        return ""

    async def close_tab(self, tab_id: str) -> None:
        pass

    async def activate_tab(self, tab_id: str) -> None:
        pass

    async def capture_console(self, level: str = "all") -> list[dict]:
        return []

    async def capture_logs(self) -> list[dict]:
        return []

    async def dom_get(self, selector: str, outer: bool = True) -> str:
        return ""

    async def dom_query(self, selector: str, all: bool = False) -> list[dict] | dict:
        return {}

    async def dom_set_attr(self, selector: str, name: str, value: str) -> None:
        pass

    async def dom_get_attr(self, selector: str, name: str) -> str:
        return ""

    async def dom_remove_attr(self, selector: str, name: str) -> None:
        pass

    async def dom_remove(self, selector: str) -> None:
        pass

    async def dom_focus(self, selector: str) -> None:
        pass

    async def dom_scroll(self, selector: str | None = None, x: int = 0, y: int = 0) -> None:
        pass

    async def capture_har(self, params: object) -> dict:
        return {}

    async def get_cookies(self) -> list[dict]:
        return []

    async def set_cookie(self, params: object) -> None:
        pass

    async def delete_cookie(self, name: str, domain: str) -> None:
        pass

    async def clear_cookies(self) -> None:
        pass

    async def set_headers(self, headers: dict[str, str]) -> None:
        pass

    async def set_user_agent(self, user_agent: str) -> None:
        pass

    async def new_context(self) -> str:
        return ""

    async def list_contexts(self) -> list[dict]:
        return []

    async def close_context(self, context_id: str) -> None:
        pass

    async def get_window_bounds(self) -> dict:
        return {}

    async def set_window_bounds(self, width: int, height: int, x: int = 0, y: int = 0) -> None:
        pass

    async def browser_version(self) -> str:
        return "dummy"

    async def emulate_device(self, device: str) -> None:
        pass

    async def set_viewport(self, width: int, height: int, device_scale_factor: float = 1.0) -> None:
        pass

    async def set_geolocation(
        self, latitude: float, longitude: float, accuracy: float = 100.0
    ) -> None:
        pass

    async def set_timezone(self, timezone: str) -> None:
        pass

    async def set_dark_mode(self, enabled: bool) -> None:
        pass

    async def click(self, selector: str, button: str = "left", click_count: int = 1) -> None:
        pass

    async def type_text(self, selector: str, text: str, delay: int = 0) -> None:
        pass

    async def fill(self, selector: str, value: str) -> None:
        pass

    async def select_option(self, selector: str, value: str) -> None:
        pass

    async def hover(self, selector: str) -> None:
        pass

    async def key_press(self, key: str) -> None:
        pass

    async def drag(self, source: str, target: str) -> None:
        pass

    async def tap(self, selector: str) -> None:
        pass

    async def throttle_network(self, params: object) -> None:
        pass

    async def set_cache_disabled(self, disabled: bool) -> None:
        pass

    async def block_requests(self, patterns: list[str]) -> None:
        pass

    async def intercept_requests(self, handler: object) -> None:
        pass

    async def mock_response(self, url: str, response: dict) -> None:
        pass

    async def intercept_download(self, url: str) -> bytes:
        return b""

    async def a11y_tree(self) -> dict:
        return {}

    async def a11y_node(self, node_id: int) -> dict:
        return {}

    async def a11y_ancestors(self, node_id: int) -> list[dict]:
        return []

    async def dialog_accept(self, dialog_type: str = "alert") -> None:
        pass

    async def dialog_dismiss(self) -> None:
        pass

    async def grant_permission(self, permission: str) -> None:
        pass

    async def reset_permissions(self) -> None:
        pass

    async def get_security_state(self) -> dict:
        return {}

    async def ignore_cert_errors(self, ignore: bool) -> None:
        pass

    async def set_locale(self, locale: str) -> None:
        pass

    async def set_cpu_throttle(self, rate: float) -> None:
        pass

    async def set_touch_emulation(self, enabled: bool) -> None:
        pass

    async def set_sensors(self, sensors: dict) -> None:
        pass

    async def perf_metrics(self) -> dict:
        return {}

    async def perf_trace(self, duration_ms: int = 3000) -> dict:
        return {}

    async def perf_profile(self, duration_ms: int = 3000) -> dict:
        return {}

    async def perf_heap_snapshot(self) -> dict:
        return {}

    async def perf_coverage(self) -> dict:
        return {}

    async def perf_css_coverage(self) -> dict:
        return {}

    async def css_get_styles(self, selector: str) -> dict:
        return {}

    async def css_get_stylesheets(self) -> list[dict]:
        return []

    async def css_get_rules(self, stylesheet_id: str) -> list[dict]:
        return []

    async def css_get_computed(self, selector: str) -> dict:
        return {}

    async def debug_set_breakpoint(
        self, url: str, line: int, condition: str | None = None
    ) -> str:
        return ""

    async def debug_set_breakpoint_function(self, function_name: str) -> str:
        return ""

    async def debug_remove_breakpoint(self, breakpoint_id: str) -> None:
        pass

    async def debug_step_over(self) -> None:
        pass

    async def debug_step_into(self) -> None:
        pass

    async def debug_step_out(self) -> None:
        pass

    async def debug_pause(self) -> None:
        pass

    async def debug_resume(self) -> None:
        pass

    async def debug_get_listeners(self, selector: str) -> list[dict]:
        return []

    async def dom_snapshot(self) -> dict:
        return {}

    async def overlay_highlight(
        self, selector: str, color: str = "rgba(255,0,0,0.5)"
    ) -> None:
        pass

    async def overlay_clear(self) -> None:
        pass

    async def storage_get(self, key: str, storage_type: str = "local") -> str:
        return ""

    async def storage_set(
        self, key: str, value: str, storage_type: str = "local"
    ) -> None:
        pass

    async def storage_clear(self, storage_type: str = "local") -> None:
        pass

    async def storage_list(self, storage_type: str = "local") -> dict[str, str]:
        return {}

    async def cache_storage_list(self) -> list[str]:
        return []

    async def cache_storage_entries(self, cache_name: str) -> list[dict]:
        return []

    async def cache_storage_delete(self, cache_name: str) -> None:
        pass

    async def indexeddb_list(self) -> list[dict]:
        return []

    async def indexeddb_get_data(self, database: str, store: str, key: str = "") -> Any:
        return None

    async def indexeddb_clear(self, database: str, store: str) -> None:
        pass

    async def sw_list(self) -> list[dict]:
        return []

    async def sw_unregister(self, registration_id: str) -> None:
        pass

    async def sw_update(self, registration_id: str) -> None:
        pass

    async def animation_list(self) -> list[dict]:
        return []

    async def animation_pause(self, animation_id: str) -> None:
        pass

    async def animation_play(self, animation_id: str) -> None:
        pass

    async def animation_seek(self, animation_id: str, time_ms: int) -> None:
        pass

    async def webauthn_add_virtual_authenticator(
        self, protocol: str, transport: str
    ) -> str:
        return ""

    async def webauthn_remove_authenticator(self, authenticator_id: str) -> None:
        pass

    async def webauthn_add_credential(
        self, authenticator_id: str, credential: dict
    ) -> None:
        pass

    async def webauthn_get_credentials(self, authenticator_id: str) -> list[dict]:
        return []

    async def webaudio_get_contexts(self) -> list[dict]:
        return []

    async def webaudio_get_context(self, context_id: str) -> dict:
        return {}

    async def media_get_players(self) -> list[dict]:
        return []

    async def media_get_messages(self, player_id: str) -> list[dict]:
        return []

    async def cast_list(self) -> list[dict]:
        return []

    async def cast_start_tab(self, sink_name: str) -> None:
        pass

    async def cast_stop(self) -> None:
        pass

    async def bluetooth_emulate(
        self, name: str, address: str = "00:00:00:00:00:01"
    ) -> None:
        pass

    async def bluetooth_stop(self) -> None:
        pass


@pytest.mark.unit
class TestBackendManager:
    def test_list_available(self) -> None:
        manager = BackendManager()
        available = manager.list_available()
        assert isinstance(available, list)
        assert "cdp" in available

    def test_select_default(self) -> None:
        manager = BackendManager()
        backend = manager.select()
        assert backend is not None

    def test_select_preferred_cdp(self) -> None:
        manager = BackendManager()
        backend = manager.select("cdp")
        assert backend is not None

    def test_select_preferred_unavailable(self) -> None:
        manager = BackendManager()
        with pytest.raises(BackendNotAvailableError):
            manager.select("nonexistent")

    def test_select_no_backends(self) -> None:
        manager = BackendManager()
        manager._registry.clear()
        with pytest.raises(BackendNotAvailableError):
            manager.select()

    def test_create_unknown(self) -> None:
        manager = BackendManager()
        with pytest.raises(BackendNotSupportedError):
            manager.create("nonexistent")

    def test_register_custom(self) -> None:
        manager = BackendManager()
        manager.register("dummy", DummyBackend)
        assert "dummy" in manager.list_available()
        backend = manager.select("dummy")
        assert isinstance(backend, DummyBackend)

    def test_install_check(self) -> None:
        manager = BackendManager()
        result = manager.install_check()
        assert "cdp" in result
        assert "bidi" in result
        assert isinstance(result["cdp"], str)
        assert isinstance(result["bidi"], str)
