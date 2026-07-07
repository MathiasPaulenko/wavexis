"""Unit tests for BackendManager."""

from __future__ import annotations

from wavexis.backend.base import AbstractBackend
from wavexis.backend.manager import BackendManager
from wavexis.exceptions import BackendNotAvailableError, BackendNotSupportedError


class FakeBackend(AbstractBackend):
    """Fake backend for testing."""

    async def launch(self, options):
        """Launch."""
    async def close(self):
        """Close."""
    async def navigate(self, url, wait=None):
        """Navigate."""
    async def screenshot(self, params):
        """Screenshot."""
    async def screenshot_selector(self, selector, format="png", quality=80):
        """Screenshot selector."""
    async def eval(self, expression, await_promise=False):
        """Eval."""
    async def raw(self, method, params=None):
        """Raw."""
    async def go_back(self):
        """Go back."""
    async def go_forward(self):
        """Go forward."""
    async def reload(self, ignore_cache=False):
        """Reload."""
    async def stop_loading(self):
        """Stop loading."""
    async def wait_for(self, strategy):
        """Wait for."""
    async def pdf(self, params):
        """Pdf."""
    async def screencast(self, params):
        """Screencast."""
    async def list_tabs(self):
        """List tabs."""
    async def new_tab(self, url="about:blank"):
        """New tab."""
    async def close_tab(self, tab_id):
        """Close tab."""
    async def activate_tab(self, tab_id):
        """Activate tab."""
    async def capture_console(self, level="all"):
        """Capture console."""
    async def capture_logs(self):
        """Capture logs."""
    async def dom_get(self, selector, outer=True):
        """Dom get."""
    async def dom_query(self, selector, all=False):
        """Dom query."""
    async def dom_set_attr(self, selector, name, value):
        """Dom set attr."""
    async def dom_get_attr(self, selector, name):
        """Dom get attr."""
    async def dom_remove_attr(self, selector, name):
        """Dom remove attr."""
    async def dom_remove(self, selector):
        """Dom remove."""
    async def dom_focus(self, selector):
        """Dom focus."""
    async def dom_scroll(self, selector=None, x=0, y=0):
        """Dom scroll."""
    async def suggest_locator(self, selector, all=False):
        """Suggest locator."""
        return selector
    async def find_by_text(self, query, all=False):
        """Find by text."""
        return query
    async def nl_click(self, query, auto_wait=True):
        """NL click."""
    async def nl_fill(self, query, value, auto_wait=True):
        """NL fill."""
    async def capture_har(self, params):
        """Capture har."""
    async def get_cookies(self):
        """Get cookies."""
    async def set_cookie(self, params):
        """Set cookie."""
    async def delete_cookie(self, name, domain):
        """Delete cookie."""
    async def clear_cookies(self):
        """Clear cookies."""
    async def set_headers(self, headers):
        """Set headers."""
    async def set_user_agent(self, user_agent):
        """Set user agent."""
    async def new_context(self):
        """New context."""
    async def list_contexts(self):
        """List contexts."""
    async def close_context(self, context_id):
        """Close context."""
    async def get_window_bounds(self):
        """Get window bounds."""
    async def set_window_bounds(self, width, height, x=0, y=0):
        """Set window bounds."""
    async def browser_version(self):
        """Browser version."""
    async def emulate_device(self, device):
        """Emulate device."""
    async def set_viewport(self, width, height, device_scale_factor=1.0):
        """Set viewport."""
    async def set_geolocation(self, latitude, longitude, accuracy=100.0):
        """Set geolocation."""
    async def set_timezone(self, timezone):
        """Set timezone."""
    async def set_dark_mode(self, enabled):
        """Set dark mode."""
    async def click(self, selector, button="left", click_count=1, auto_wait=True):
        """Click."""
    async def type_text(self, selector, text, delay=0):
        """Type text."""
    async def fill(self, selector, value, auto_wait=True):
        """Fill."""
    async def select_option(self, selector, value):
        """Select option."""
    async def hover(self, selector, auto_wait=True):
        """Hover."""
    async def key_press(self, key):
        """Key press."""
    async def drag(self, source, target):
        """Drag."""
    async def tap(self, selector):
        """Tap."""
    async def throttle_network(self, params):
        """Throttle network."""
    async def set_cache_disabled(self, disabled):
        """Set cache disabled."""
    async def block_requests(self, patterns):
        """Block requests."""
    async def intercept_requests(self, handler):
        """Intercept requests."""
    async def mock_response(self, url, response):
        """Mock response."""
    async def intercept_download(self, url):
        """Intercept download."""
    async def a11y_tree(self):
        """A11y tree."""
    async def a11y_node(self, node_id):
        """A11y node."""
    async def a11y_ancestors(self, node_id):
        """A11y ancestors."""
    async def dialog_accept(self, dialog_type="alert"):
        """Dialog accept."""
    async def dialog_dismiss(self):
        """Dialog dismiss."""
    async def grant_permission(self, permission):
        """Grant permission."""
    async def reset_permissions(self):
        """Reset permissions."""
    async def get_security_state(self):
        """Get security state."""
    async def ignore_cert_errors(self, ignore):
        """Ignore cert errors."""
    async def set_locale(self, locale):
        """Set locale."""
    async def set_cpu_throttle(self, rate):
        """Set cpu throttle."""
    async def set_touch_emulation(self, enabled):
        """Set touch emulation."""
    async def set_sensors(self, sensors):
        """Set sensors."""
    async def perf_metrics(self):
        """Perf metrics."""
    async def perf_trace(self, duration_ms=3000):
        """Perf trace."""
    async def perf_profile(self, duration_ms=3000):
        """Perf profile."""
    async def perf_heap_snapshot(self):
        """Perf heap snapshot."""
    async def perf_coverage(self):
        """Perf coverage."""
    async def perf_css_coverage(self):
        """Perf css coverage."""
    async def css_get_styles(self, selector):
        """Css get styles."""
    async def css_get_stylesheets(self):
        """Css get stylesheets."""
    async def css_get_rules(self, stylesheet_id):
        """Css get rules."""
    async def css_get_computed(self, selector):
        """Css get computed."""
    async def debug_set_breakpoint(self, url, line, condition=None):
        """Debug set breakpoint."""
    async def debug_set_breakpoint_function(self, function_name):
        """Debug set breakpoint function."""
    async def debug_remove_breakpoint(self, breakpoint_id):
        """Debug remove breakpoint."""
    async def debug_step_over(self):
        """Debug step over."""
    async def debug_step_into(self):
        """Debug step into."""
    async def debug_step_out(self):
        """Debug step out."""
    async def debug_pause(self):
        """Debug pause."""
    async def debug_resume(self):
        """Debug resume."""
    async def debug_get_listeners(self, selector):
        """Debug get listeners."""
    async def dom_snapshot(self):
        """Dom snapshot."""
    async def overlay_highlight(self, selector, color="rgba(255,0,0,0.5)"):
        """Overlay highlight."""
    async def overlay_clear(self):
        """Overlay clear."""
    async def storage_get(self, key, storage_type="local"):
        """Storage get."""
    async def storage_set(self, key, value, storage_type="local"):
        """Storage set."""
    async def storage_clear(self, storage_type="local"):
        """Storage clear."""
    async def storage_list(self, storage_type="local"):
        """Storage list."""
    async def cache_storage_list(self):
        """Cache storage list."""
    async def cache_storage_entries(self, cache_name):
        """Cache storage entries."""
    async def cache_storage_delete(self, cache_name):
        """Cache storage delete."""
    async def indexeddb_list(self):
        """Indexeddb list."""
    async def indexeddb_get_data(self, database, store, key=""):
        """Indexeddb get data."""
    async def indexeddb_clear(self, database, store):
        """Indexeddb clear."""
    async def sw_list(self):
        """Sw list."""
    async def sw_unregister(self, registration_id):
        """Sw unregister."""
    async def sw_update(self, registration_id):
        """Sw update."""
    async def animation_list(self):
        """Animation list."""
    async def animation_pause(self, animation_id):
        """Animation pause."""
    async def animation_play(self, animation_id):
        """Animation play."""
    async def animation_seek(self, animation_id, time_ms):
        """Animation seek."""
    async def webauthn_add_virtual_authenticator(self, protocol, transport):
        """Webauthn add virtual authenticator."""
    async def webauthn_remove_authenticator(self, authenticator_id):
        """Webauthn remove authenticator."""
    async def webauthn_add_credential(self, authenticator_id, credential):
        """Webauthn add credential."""
    async def webauthn_get_credentials(self, authenticator_id):
        """Webauthn get credentials."""
    async def webaudio_get_contexts(self):
        """Webaudio get contexts."""
    async def webaudio_get_context(self, context_id):
        """Webaudio get context."""
    async def media_get_players(self):
        """Media get players."""
    async def media_get_messages(self, player_id):
        """Media get messages."""
    async def cast_list(self):
        """Cast list."""
    async def cast_start_tab(self, sink_name):
        """Cast start tab."""
    async def cast_stop(self):
        """Cast stop."""
    async def bluetooth_emulate(self, name, address="00:00:00:00:00:01"):
        """Bluetooth emulate."""
    async def bluetooth_stop(self):
        """Bluetooth stop."""
    async def set_files(self, selector, files):
        """Set files."""
    async def iframe_eval(self, iframe_selector, expression, await_promise=False):
        """Iframe eval."""
        return None
    async def iframe_click(self, iframe_selector, selector, auto_wait=True):
        """Iframe click."""
    async def iframe_fill(self, iframe_selector, selector, value, auto_wait=True):
        """Iframe fill."""
    async def shadow_eval(self, selectors, expression, await_promise=False):
        """Shadow eval."""
        return None
    async def shadow_click(self, selectors, auto_wait=True):
        """Shadow click."""
    async def shadow_fill(self, selectors, value, auto_wait=True):
        """Shadow fill."""


class TestBackendManager:
    """Tests for BackendManager."""

    def test_register_and_list(self):
        """Test register and list."""
        manager = BackendManager()
        manager.register("fake", FakeBackend)
        assert "fake" in manager.list_available()

    def test_create_registered(self):
        """Test create registered."""
        manager = BackendManager()
        manager.register("fake", FakeBackend)
        backend = manager.create("fake")
        assert isinstance(backend, FakeBackend)

    def test_create_unregistered_raises(self):
        """Test create unregistered raises."""
        manager = BackendManager()
        try:
            manager.create("nonexistent")
        except BackendNotSupportedError:
            pass
        else:
            raise AssertionError("Should have raised BackendNotSupportedError")

    def test_select_preferred(self):
        """Test select preferred."""
        manager = BackendManager()
        manager.register("fake", FakeBackend)
        backend = manager.select("fake")
        assert isinstance(backend, FakeBackend)

    def test_select_fallback(self):
        """Test select fallback."""
        manager = BackendManager()
        manager._registry.clear()
        manager.register("fake", FakeBackend)
        backend = manager.select(None)
        assert isinstance(backend, FakeBackend)

    def test_select_unavailable_preferred_raises(self):
        """Test select unavailable preferred raises."""
        manager = BackendManager()
        manager.register("fake", FakeBackend)
        try:
            manager.select("nonexistent")
        except BackendNotAvailableError:
            pass
        else:
            raise AssertionError("Should have raised BackendNotAvailableError")
