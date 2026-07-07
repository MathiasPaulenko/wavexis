"""Unit tests for BackendManager."""

from __future__ import annotations

from typing import Any

import pytest

from wavexis.backend.base import AbstractBackend
from wavexis.backend.manager import BackendManager
from wavexis.exceptions import BackendNotAvailableError, BackendNotSupportedError


class DummyBackend(AbstractBackend):
    """Dummy backend for testing."""

    def __init__(self) -> None:
        """  init  ."""
        pass

    async def launch(self, options: object) -> None:
        """Launch."""
        pass

    async def close(self) -> None:
        """Close."""
        pass

    async def navigate(self, url: str, wait: object | None = None) -> None:
        """Navigate."""
        pass

    async def screenshot(self, params: object) -> bytes:
        """Screenshot."""
        return b""

    async def screenshot_selector(
        self, selector: str, format: str = "png", quality: int = 80
    ) -> bytes:
        """Screenshot selector."""
        return b""

    async def annotated_screenshot(
        self, selectors: list[str], format: str = "png"
    ) -> tuple[bytes, dict[str, str]]:
        """Annotated screenshot."""
        return b"", {}

    async def eval(self, expression: str, await_promise: bool = False) -> object:
        """Eval."""
        return None

    async def raw(self, method: str, params: dict | None = None) -> dict:
        """Raw."""
        return {}

    async def go_back(self) -> None:
        """Go back."""
        pass

    async def go_forward(self) -> None:
        """Go forward."""
        pass

    async def reload(self, ignore_cache: bool = False) -> None:
        """Reload."""
        pass

    async def stop_loading(self) -> None:
        """Stop loading."""
        pass

    async def wait_for(self, strategy: object) -> None:
        """Wait for."""
        pass

    async def pdf(self, params: object) -> bytes:
        """Pdf."""
        return b""

    async def screencast(self, params: object) -> list[bytes]:
        """Screencast."""
        return []

    async def list_tabs(self) -> list[dict]:
        """List tabs."""
        return []

    async def new_tab(self, url: str = "about:blank") -> str:
        """New tab."""
        return ""

    async def close_tab(self, tab_id: str) -> None:
        """Close tab."""
        pass

    async def activate_tab(self, tab_id: str) -> None:
        """Activate tab."""
        pass

    async def capture_console(self, level: str = "all") -> list[dict]:
        """Capture console."""
        return []

    async def capture_logs(self) -> list[dict]:
        """Capture logs."""
        return []

    async def dom_get(self, selector: str, outer: bool = True) -> str:
        """Dom get."""
        return ""

    async def dom_query(self, selector: str, all: bool = False) -> list[dict] | dict:
        """Dom query."""
        return {}

    async def dom_set_attr(self, selector: str, name: str, value: str) -> None:
        """Dom set attr."""
        pass

    async def dom_get_attr(self, selector: str, name: str) -> str:
        """Dom get attr."""
        return ""

    async def dom_remove_attr(self, selector: str, name: str) -> None:
        """Dom remove attr."""
        pass

    async def dom_remove(self, selector: str) -> None:
        """Dom remove."""
        pass

    async def dom_focus(self, selector: str) -> None:
        """Dom focus."""
        pass

    async def dom_scroll(self, selector: str | None = None, x: int = 0, y: int = 0) -> None:
        """Dom scroll."""
        pass

    async def suggest_locator(
        self, selector: str, all: bool = False
    ) -> list[str] | str:
        """Suggest locator."""
        return selector

    async def find_by_text(
        self, query: str, all: bool = False
    ) -> list[str] | str:
        """Find by text."""
        return query

    async def nl_click(self, query: str, auto_wait: bool = True) -> None:
        """NL click."""
        pass

    async def nl_fill(
        self, query: str, value: str, auto_wait: bool = True
    ) -> None:
        """NL fill."""
        pass

    async def capture_har(self, params: object) -> dict:
        """Capture har."""
        return {}

    async def get_cookies(self) -> list[dict]:
        """Get cookies."""
        return []

    async def set_cookie(self, params: object) -> None:
        """Set cookie."""
        pass

    async def delete_cookie(self, name: str, domain: str) -> None:
        """Delete cookie."""
        pass

    async def clear_cookies(self) -> None:
        """Clear cookies."""
        pass

    async def set_headers(self, headers: dict[str, str]) -> None:
        """Set headers."""
        pass

    async def set_user_agent(self, user_agent: str) -> None:
        """Set user agent."""
        pass

    async def new_context(self) -> str:
        """New context."""
        return ""

    async def list_contexts(self) -> list[dict]:
        """List contexts."""
        return []

    async def close_context(self, context_id: str) -> None:
        """Close context."""
        pass

    async def get_window_bounds(self) -> dict:
        """Get window bounds."""
        return {}

    async def set_window_bounds(self, width: int, height: int, x: int = 0, y: int = 0) -> None:
        """Set window bounds."""
        pass

    async def browser_version(self) -> str:
        """Browser version."""
        return "dummy"

    async def emulate_device(self, device: str) -> None:
        """Emulate device."""
        pass

    async def set_viewport(self, width: int, height: int, device_scale_factor: float = 1.0) -> None:
        """Set viewport."""
        pass

    async def set_geolocation(
        self, latitude: float, longitude: float, accuracy: float = 100.0
    ) -> None:
        """Set geolocation."""
        pass

    async def set_timezone(self, timezone: str) -> None:
        """Set timezone."""
        pass

    async def set_dark_mode(self, enabled: bool) -> None:
        """Set dark mode."""
        pass

    async def click(
        self,
        selector: str,
        button: str = "left",
        click_count: int = 1,
        auto_wait: bool = True,
    ) -> None:
        """Click."""
        pass

    async def type_text(self, selector: str, text: str, delay: int = 0) -> None:
        """Type text."""
        pass

    async def fill(
        self, selector: str, value: str, auto_wait: bool = True
    ) -> None:
        """Fill."""
        pass

    async def select_option(self, selector: str, value: str) -> None:
        """Select option."""
        pass

    async def hover(self, selector: str, auto_wait: bool = True) -> None:
        """Hover."""
        pass

    async def key_press(self, key: str) -> None:
        """Key press."""
        pass

    async def drag(self, source: str, target: str) -> None:
        """Drag."""
        pass

    async def tap(self, selector: str) -> None:
        """Tap."""
        pass

    async def set_files(self, selector: str, files: list[str]) -> None:
        """Set files."""
        pass

    async def iframe_eval(
        self, iframe_selector: str, expression: str, await_promise: bool = False
    ) -> object:
        """Iframe eval."""
        return None

    async def iframe_click(
        self, iframe_selector: str, selector: str, auto_wait: bool = True
    ) -> None:
        """Iframe click."""
        pass

    async def iframe_fill(
        self, iframe_selector: str, selector: str, value: str, auto_wait: bool = True
    ) -> None:
        """Iframe fill."""
        pass

    async def shadow_eval(
        self, selectors: list[str], expression: str, await_promise: bool = False
    ) -> object:
        """Shadow eval."""
        return None

    async def shadow_click(
        self, selectors: list[str], auto_wait: bool = True
    ) -> None:
        """Shadow click."""
        pass

    async def shadow_fill(
        self, selectors: list[str], value: str, auto_wait: bool = True
    ) -> None:
        """Shadow fill."""
        pass

    async def throttle_network(self, params: object) -> None:
        """Throttle network."""
        pass

    async def set_cache_disabled(self, disabled: bool) -> None:
        """Set cache disabled."""
        pass

    async def block_requests(self, patterns: list[str]) -> None:
        """Block requests."""
        pass

    async def intercept_requests(self, handler: object) -> None:
        """Intercept requests."""
        pass

    async def mock_response(self, url: str, response: dict) -> None:
        """Mock response."""
        pass

    async def intercept_download(self, url: str) -> bytes:
        """Intercept download."""
        return b""

    async def a11y_tree(self) -> dict:
        """A11y tree."""
        return {}

    async def a11y_node(self, node_id: int) -> dict:
        """A11y node."""
        return {}

    async def a11y_ancestors(self, node_id: int) -> list[dict]:
        """A11y ancestors."""
        return []

    async def dialog_accept(self, dialog_type: str = "alert") -> None:
        """Dialog accept."""
        pass

    async def dialog_dismiss(self) -> None:
        """Dialog dismiss."""
        pass

    async def grant_permission(self, permission: str) -> None:
        """Grant permission."""
        pass

    async def reset_permissions(self) -> None:
        """Reset permissions."""
        pass

    async def get_security_state(self) -> dict:
        """Get security state."""
        return {}

    async def ignore_cert_errors(self, ignore: bool) -> None:
        """Ignore cert errors."""
        pass

    async def set_locale(self, locale: str) -> None:
        """Set locale."""
        pass

    async def set_cpu_throttle(self, rate: float) -> None:
        """Set cpu throttle."""
        pass

    async def set_touch_emulation(self, enabled: bool) -> None:
        """Set touch emulation."""
        pass

    async def set_sensors(self, sensors: dict) -> None:
        """Set sensors."""
        pass

    async def perf_metrics(self) -> dict:
        """Perf metrics."""
        return {}

    async def perf_trace(self, duration_ms: int = 3000) -> dict:
        """Perf trace."""
        return {}

    async def perf_profile(self, duration_ms: int = 3000) -> dict:
        """Perf profile."""
        return {}

    async def perf_heap_snapshot(self) -> dict:
        """Perf heap snapshot."""
        return {}

    async def perf_coverage(self) -> dict:
        """Perf coverage."""
        return {}

    async def perf_css_coverage(self) -> dict:
        """Perf css coverage."""
        return {}

    async def css_get_styles(self, selector: str) -> dict:
        """Css get styles."""
        return {}

    async def css_get_stylesheets(self) -> list[dict]:
        """Css get stylesheets."""
        return []

    async def css_get_rules(self, stylesheet_id: str) -> list[dict]:
        """Css get rules."""
        return []

    async def css_get_computed(self, selector: str) -> dict:
        """Css get computed."""
        return {}

    async def debug_set_breakpoint(
        self, url: str, line: int, condition: str | None = None
    ) -> str:
        """Debug set breakpoint."""
        return ""

    async def debug_set_breakpoint_function(self, function_name: str) -> str:
        """Debug set breakpoint function."""
        return ""

    async def debug_remove_breakpoint(self, breakpoint_id: str) -> None:
        """Debug remove breakpoint."""
        pass

    async def debug_step_over(self) -> None:
        """Debug step over."""
        pass

    async def debug_step_into(self) -> None:
        """Debug step into."""
        pass

    async def debug_step_out(self) -> None:
        """Debug step out."""
        pass

    async def debug_pause(self) -> None:
        """Debug pause."""
        pass

    async def debug_resume(self) -> None:
        """Debug resume."""
        pass

    async def debug_get_listeners(self, selector: str) -> list[dict]:
        """Debug get listeners."""
        return []

    async def dom_snapshot(self) -> dict:
        """Dom snapshot."""
        return {}

    async def overlay_highlight(
        self, selector: str, color: str = "rgba(255,0,0,0.5)"
    ) -> None:
        """Overlay highlight."""
        pass

    async def overlay_clear(self) -> None:
        """Overlay clear."""
        pass

    async def storage_get(self, key: str, storage_type: str = "local") -> str:
        """Storage get."""
        return ""

    async def storage_set(
        self, key: str, value: str, storage_type: str = "local"
    ) -> None:
        """Storage set."""
        pass

    async def storage_clear(self, storage_type: str = "local") -> None:
        """Storage clear."""
        pass

    async def storage_list(self, storage_type: str = "local") -> dict[str, str]:
        """Storage list."""
        return {}

    async def cache_storage_list(self) -> list[str]:
        """Cache storage list."""
        return []

    async def cache_storage_entries(self, cache_name: str) -> list[dict]:
        """Cache storage entries."""
        return []

    async def cache_storage_delete(self, cache_name: str) -> None:
        """Cache storage delete."""
        pass

    async def indexeddb_list(self) -> list[dict]:
        """Indexeddb list."""
        return []

    async def indexeddb_get_data(self, database: str, store: str, key: str = "") -> Any:
        """Indexeddb get data."""
        return None

    async def indexeddb_clear(self, database: str, store: str) -> None:
        """Indexeddb clear."""
        pass

    async def sw_list(self) -> list[dict]:
        """Sw list."""
        return []

    async def sw_unregister(self, registration_id: str) -> None:
        """Sw unregister."""
        pass

    async def sw_update(self, registration_id: str) -> None:
        """Sw update."""
        pass

    async def animation_list(self) -> list[dict]:
        """Animation list."""
        return []

    async def animation_pause(self, animation_id: str) -> None:
        """Animation pause."""
        pass

    async def animation_play(self, animation_id: str) -> None:
        """Animation play."""
        pass

    async def animation_seek(self, animation_id: str, time_ms: int) -> None:
        """Animation seek."""
        pass

    async def webauthn_add_virtual_authenticator(
        self, protocol: str, transport: str
    ) -> str:
        """Webauthn add virtual authenticator."""
        return ""

    async def webauthn_remove_authenticator(self, authenticator_id: str) -> None:
        """Webauthn remove authenticator."""
        pass

    async def webauthn_add_credential(
        self, authenticator_id: str, credential: dict
    ) -> None:
        """Webauthn add credential."""
        pass

    async def webauthn_get_credentials(self, authenticator_id: str) -> list[dict]:
        """Webauthn get credentials."""
        return []

    async def webaudio_get_contexts(self) -> list[dict]:
        """Webaudio get contexts."""
        return []

    async def webaudio_get_context(self, context_id: str) -> dict:
        """Webaudio get context."""
        return {}

    async def media_get_players(self) -> list[dict]:
        """Media get players."""
        return []

    async def media_get_messages(self, player_id: str) -> list[dict]:
        """Media get messages."""
        return []

    async def cast_list(self) -> list[dict]:
        """Cast list."""
        return []

    async def cast_start_tab(self, sink_name: str) -> None:
        """Cast start tab."""
        pass

    async def cast_stop(self) -> None:
        """Cast stop."""
        pass

    async def bluetooth_emulate(
        self, name: str, address: str = "00:00:00:00:00:01"
    ) -> None:
        """Bluetooth emulate."""
        pass

    async def bluetooth_stop(self) -> None:
        """Bluetooth stop."""
        pass

    async def get_request_body(self, request_id: str) -> str | None:
        """Get request body."""
        return None

    async def get_response_body(self, request_id: str) -> str | None:
        """Get response body."""
        return None

    async def modify_request(
        self, pattern: dict[str, Any], modifications: dict[str, Any]
    ) -> None:
        """Modify request."""
        pass

    async def replay_har(self, har_path: str, url_filter: str = "") -> None:
        """Replay har."""
        pass

    async def start_combined_trace(
        self,
        capture_screenshots: bool = True,
        capture_network: bool = True,
        capture_console: bool = True,
    ) -> str:
        """Start combined trace."""
        return "trace-dummy"

    async def stop_combined_trace(self, trace_id: str) -> dict[str, Any]:
        """Stop combined trace."""
        return {}

    async def axe_audit(self) -> dict[str, Any]:
        """Axe audit."""
        return {}

    async def subscribe_events(
        self, event_types: list[str], callback: Any
    ) -> str:
        """Subscribe events."""
        return "sub-dummy"

    async def unsubscribe_events(self, subscription_id: str) -> None:
        """Unsubscribe events."""
        pass

    async def extension_install(self, path: str) -> str:
        """Install extension."""
        return "ext-dummy"

    async def extension_uninstall(self, extension_id: str) -> None:
        """Uninstall extension."""
        pass

    async def extension_list(self) -> list[dict[str, Any]]:
        """List extensions."""
        return []

    async def get_pref(self, key: str) -> Any:
        """Get preference."""
        return None

    async def set_pref(self, key: str, value: Any) -> None:
        """Set preference."""
        pass


@pytest.mark.unit
class TestBackendManager:
    """Test suite for backendmanager."""
    def test_list_available(self) -> None:
        """Test list available."""
        manager = BackendManager()
        available = manager.list_available()
        assert isinstance(available, list)
        assert "cdp" in available

    def test_select_default(self) -> None:
        """Test select default."""
        manager = BackendManager()
        backend = manager.select()
        assert backend is not None

    def test_select_preferred_cdp(self) -> None:
        """Test select preferred cdp."""
        manager = BackendManager()
        backend = manager.select("cdp")
        assert backend is not None

    def test_select_preferred_unavailable(self) -> None:
        """Test select preferred unavailable."""
        manager = BackendManager()
        with pytest.raises(BackendNotAvailableError):
            manager.select("nonexistent")

    def test_select_no_backends(self) -> None:
        """Test select no backends."""
        manager = BackendManager()
        manager._registry.clear()
        with pytest.raises(BackendNotAvailableError):
            manager.select()

    def test_create_unknown(self) -> None:
        """Test create unknown."""
        manager = BackendManager()
        with pytest.raises(BackendNotSupportedError):
            manager.create("nonexistent")

    def test_register_custom(self) -> None:
        """Test register custom."""
        manager = BackendManager()
        manager.register("dummy", DummyBackend)
        assert "dummy" in manager.list_available()
        backend = manager.select("dummy")
        assert isinstance(backend, DummyBackend)

    def test_install_check(self) -> None:
        """Test install check."""
        manager = BackendManager()
        result = manager.install_check()
        assert "cdp" in result
        assert "bidi" in result
        assert isinstance(result["cdp"], str)
        assert isinstance(result["bidi"], str)
