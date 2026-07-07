"""Abstract backend interface for browser automation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

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


class AbstractBackend(ABC):
    """Abstract interface for browser automation backends.

    Implementations include CDPBackend (via cdpwave) and BiDiBackend (via bidiwave).
    """

    @abstractmethod
    async def launch(self, options: BrowserOptions) -> None:
        """Launch a browser instance with the given options."""

    @abstractmethod
    async def close(self) -> None:
        """Close the browser and release all resources."""

    @abstractmethod
    async def navigate(self, url: str, wait: WaitStrategy | None = None) -> None:
        """Navigate to a URL, optionally waiting for a condition."""

    @abstractmethod
    async def screenshot(self, params: ScreenshotParams) -> bytes:
        """Take a screenshot and return the image bytes."""

    @abstractmethod
    async def screenshot_selector(
        self, selector: str, format: str = "png", quality: int = 80
    ) -> bytes:
        """Take a screenshot of an element matching a CSS selector."""

    @abstractmethod
    async def eval(self, expression: str, await_promise: bool = False) -> Any:
        """Evaluate a JavaScript expression and return the result."""

    @abstractmethod
    async def raw(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Send a raw protocol command (escape hatch)."""

    @abstractmethod
    async def go_back(self) -> None:
        """Navigate back in browser history."""

    @abstractmethod
    async def go_forward(self) -> None:
        """Navigate forward in browser history."""

    @abstractmethod
    async def reload(self, ignore_cache: bool = False) -> None:
        """Reload the current page."""

    @abstractmethod
    async def stop_loading(self) -> None:
        """Stop all pending navigations and resource loads."""

    @abstractmethod
    async def wait_for(self, strategy: WaitStrategy) -> None:
        """Wait for a specific condition (selector, load, url)."""

    @abstractmethod
    async def pdf(self, params: PDFParams) -> bytes:
        """Generate a PDF of the current page and return the bytes."""

    @abstractmethod
    async def screencast(self, params: ScreencastParams) -> list[bytes]:
        """Capture a screencast and return a list of frame bytes."""

    @abstractmethod
    async def list_tabs(self) -> list[dict[str, Any]]:
        """List all open browser tabs/targets."""

    @abstractmethod
    async def new_tab(self, url: str = "about:blank") -> str:
        """Create a new tab and return its target ID."""

    @abstractmethod
    async def close_tab(self, tab_id: str) -> None:
        """Close a tab by its target ID."""

    @abstractmethod
    async def activate_tab(self, tab_id: str) -> None:
        """Activate (focus) a tab by its target ID."""

    @abstractmethod
    async def capture_console(self, level: str = "all") -> list[dict[str, Any]]:
        """Capture console messages at or above the given level."""

    @abstractmethod
    async def capture_logs(self) -> list[dict[str, Any]]:
        """Capture browser log entries."""

    # ── DOM ────────────────────────────────────────────────

    @abstractmethod
    async def dom_get(self, selector: str, outer: bool = True) -> str:
        """Get the HTML of an element matching a CSS selector."""

    @abstractmethod
    async def dom_query(
        self, selector: str, all: bool = False
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Query elements by CSS selector.

        Returns a list when all=True, a single dict when all=False.
        """

    @abstractmethod
    async def dom_set_attr(self, selector: str, name: str, value: str) -> None:
        """Set an attribute on an element matching a CSS selector."""

    @abstractmethod
    async def dom_get_attr(self, selector: str, name: str) -> str:
        """Get an attribute value from an element matching a CSS selector."""

    @abstractmethod
    async def dom_remove_attr(self, selector: str, name: str) -> None:
        """Remove an attribute from an element matching a CSS selector."""

    @abstractmethod
    async def dom_remove(self, selector: str) -> None:
        """Remove an element matching a CSS selector from the DOM."""

    @abstractmethod
    async def dom_focus(self, selector: str) -> None:
        """Focus an element matching a CSS selector."""

    @abstractmethod
    async def dom_scroll(
        self, selector: str | None = None, x: int = 0, y: int = 0
    ) -> None:
        """Scroll to an element or by offset."""

    # ── Network ────────────────────────────────────────────

    @abstractmethod
    async def capture_har(self, params: HarParams) -> dict[str, Any]:
        """Navigate to a URL and capture network traffic as HAR 1.2 dict."""

    @abstractmethod
    async def get_cookies(self) -> list[dict[str, Any]]:
        """Get all cookies for the current page."""

    @abstractmethod
    async def set_cookie(self, params: CookieParams) -> None:
        """Set a cookie in the browser."""

    @abstractmethod
    async def delete_cookie(self, name: str, domain: str) -> None:
        """Delete cookies matching name and domain."""

    @abstractmethod
    async def clear_cookies(self) -> None:
        """Clear all browser cookies."""

    @abstractmethod
    async def set_headers(self, headers: dict[str, str]) -> None:
        """Set extra HTTP headers for all requests."""

    @abstractmethod
    async def set_user_agent(self, user_agent: str) -> None:
        """Override the browser's User-Agent string."""

    # ── Browser management ─────────────────────────────────

    @abstractmethod
    async def new_context(self) -> str:
        """Create a new browser context and return its ID."""

    @abstractmethod
    async def list_contexts(self) -> list[dict[str, Any]]:
        """List all browser contexts."""

    @abstractmethod
    async def close_context(self, context_id: str) -> None:
        """Close a browser context by ID."""

    @abstractmethod
    async def get_window_bounds(self) -> dict[str, Any]:
        """Get the current window bounds (width, height, x, y)."""

    @abstractmethod
    async def set_window_bounds(
        self, width: int, height: int, x: int = 0, y: int = 0
    ) -> None:
        """Set the window bounds."""

    @abstractmethod
    async def browser_version(self) -> str:
        """Get the browser version string."""

    # ── Emulation ─────────────────────────────────────────

    @abstractmethod
    async def emulate_device(self, device: str) -> None:
        """Emulate a device by preset name (e.g. 'iphone-15')."""

    @abstractmethod
    async def set_viewport(
        self, width: int, height: int, device_scale_factor: float = 1.0
    ) -> None:
        """Set a custom viewport with given dimensions and scale factor."""

    @abstractmethod
    async def set_geolocation(
        self, latitude: float, longitude: float, accuracy: float = 100.0
    ) -> None:
        """Override the geolocation position."""

    @abstractmethod
    async def set_timezone(self, timezone: str) -> None:
        """Override the system timezone (IANA timezone ID)."""

    @abstractmethod
    async def set_dark_mode(self, enabled: bool) -> None:
        """Enable or disable dark mode emulation."""

    # ── Input ──────────────────────────────────────────────

    @abstractmethod
    async def click(
        self,
        selector: str,
        button: str = "left",
        click_count: int = 1,
        auto_wait: bool = True,
    ) -> None:
        """Click an element matching a CSS selector."""

    @abstractmethod
    async def type_text(self, selector: str, text: str, delay: int = 0) -> None:
        """Type text into an element, optionally with delay between keystrokes."""

    @abstractmethod
    async def fill(
        self, selector: str, value: str, auto_wait: bool = True
    ) -> None:
        """Fill an input element with a value (replaces existing content)."""

    @abstractmethod
    async def select_option(self, selector: str, value: str) -> None:
        """Select an option in a <select> element by value."""

    @abstractmethod
    async def hover(self, selector: str, auto_wait: bool = True) -> None:
        """Hover over an element matching a CSS selector."""

    @abstractmethod
    async def key_press(self, key: str) -> None:
        """Press a keyboard key (e.g. 'Enter', 'Tab')."""

    @abstractmethod
    async def drag(self, source: str, target: str) -> None:
        """Drag an element from source selector to target selector."""

    @abstractmethod
    async def tap(self, selector: str) -> None:
        """Tap an element (touch emulation click)."""

    @abstractmethod
    async def set_files(self, selector: str, files: list[str]) -> None:
        """Set files on a file input element.

        Args:
            selector: CSS selector for the <input type="file"> element.
            files: List of absolute file paths to upload.
        """

    # ── iframe ─────────────────────────────────────────────

    @abstractmethod
    async def iframe_eval(
        self, iframe_selector: str, expression: str, await_promise: bool = False
    ) -> Any:
        """Evaluate a JavaScript expression inside an iframe.

        Args:
            iframe_selector: CSS selector for the <iframe> element.
            expression: JavaScript expression to evaluate in the iframe context.
            await_promise: Whether to await a returned Promise.
        """

    @abstractmethod
    async def iframe_click(
        self, iframe_selector: str, selector: str, auto_wait: bool = True
    ) -> None:
        """Click an element inside an iframe.

        Args:
            iframe_selector: CSS selector for the <iframe> element.
            selector: CSS selector inside the iframe for the target element.
            auto_wait: If True, wait for element to be visible before clicking.
        """

    @abstractmethod
    async def iframe_fill(
        self, iframe_selector: str, selector: str, value: str, auto_wait: bool = True
    ) -> None:
        """Fill an input element inside an iframe.

        Args:
            iframe_selector: CSS selector for the <iframe> element.
            selector: CSS selector inside the iframe for the target element.
            value: Value to set in the input field.
            auto_wait: If True, wait for element to be visible before filling.
        """

    # ── Network advanced ───────────────────────────────────

    @abstractmethod
    async def block_requests(self, patterns: list[str]) -> None:
        """Block requests matching URL patterns (glob-style)."""

    @abstractmethod
    async def throttle_network(self, params: ThrottleParams) -> None:
        """Throttle network conditions (latency, throughput, offline)."""

    @abstractmethod
    async def set_cache_disabled(self, disabled: bool = True) -> None:
        """Disable or enable the browser cache."""

    @abstractmethod
    async def intercept_requests(self, pattern: dict[str, Any]) -> None:
        """Intercept requests matching a pattern dict."""

    @abstractmethod
    async def mock_response(self, url: str, response: dict[str, Any]) -> None:
        """Mock a response for requests matching a URL pattern."""

    # ── Accessibility ──────────────────────────────────────

    @abstractmethod
    async def a11y_tree(self) -> dict[str, Any]:
        """Get the full accessibility tree of the current page."""

    @abstractmethod
    async def a11y_node(self, node_id: str) -> dict[str, Any]:
        """Get a specific accessibility node by its node ID."""

    @abstractmethod
    async def a11y_ancestors(self, node_id: str) -> list[dict[str, Any]]:
        """Get ancestor nodes of an accessibility node."""

    # ── Downloads ──────────────────────────────────────────

    @abstractmethod
    async def intercept_download(self, pattern: str = ".*") -> bytes:
        """Intercept a file download matching a URL pattern and return bytes."""

    # ── Dialogs ────────────────────────────────────────────

    @abstractmethod
    async def dialog_accept(self, prompt_text: str | None = None) -> None:
        """Accept a JavaScript dialog (alert, confirm, prompt)."""

    @abstractmethod
    async def dialog_dismiss(self) -> None:
        """Dismiss a JavaScript dialog."""

    # ── Permissions ────────────────────────────────────────

    @abstractmethod
    async def grant_permission(self, permission: str) -> None:
        """Grant a browser permission (e.g. 'geolocation', 'notifications')."""

    @abstractmethod
    async def reset_permissions(self) -> None:
        """Reset all granted permissions."""

    # ── Security ───────────────────────────────────────────

    @abstractmethod
    async def get_security_state(self) -> dict[str, Any]:
        """Get the current security state of the page."""

    @abstractmethod
    async def ignore_cert_errors(self, ignore: bool = True) -> None:
        """Enable or disable ignoring of certificate errors."""

    # ── Emulation advanced ─────────────────────────────────

    @abstractmethod
    async def set_locale(self, locale: str) -> None:
        """Override the browser locale (e.g. 'en-US', 'fr-FR')."""

    @abstractmethod
    async def set_cpu_throttle(self, rate: float) -> None:
        """Throttle CPU performance by a rate multiplier (e.g. 4 = 4x slower)."""

    @abstractmethod
    async def set_touch_emulation(self, enabled: bool) -> None:
        """Enable or disable touch emulation."""

    @abstractmethod
    async def set_sensors(self, sensors: SensorParams) -> None:
        """Override sensor values (geolocation, device orientation, etc.)."""

    # ── Performance ───────────────────────────────────────

    @abstractmethod
    async def perf_metrics(self) -> dict[str, Any]:
        """Get current performance metrics from the page."""

    @abstractmethod
    async def perf_trace(self, duration_ms: int = 3000) -> dict[str, Any]:
        """Capture a performance trace for the given duration.

        Args:
            duration_ms: Trace duration in milliseconds.

        Returns:
            Dict containing trace events and metadata.
        """

    @abstractmethod
    async def perf_profile(self, duration_ms: int = 3000) -> dict[str, Any]:
        """Capture a CPU profile for the given duration.

        Args:
            duration_ms: Profile duration in milliseconds.

        Returns:
            Dict containing CPU profile data.
        """

    @abstractmethod
    async def perf_heap_snapshot(self) -> dict[str, Any]:
        """Capture a heap snapshot and return it as a dict."""

    @abstractmethod
    async def perf_coverage(self) -> dict[str, Any]:
        """Get JavaScript code coverage for the current page."""

    @abstractmethod
    async def perf_css_coverage(self) -> dict[str, Any]:
        """Get CSS rule usage coverage for the current page."""

    # ── CSS ────────────────────────────────────────────────

    @abstractmethod
    async def css_get_styles(self, selector: str) -> dict[str, Any]:
        """Get inline and matched styles for an element by CSS selector.

        Args:
            selector: CSS selector for the target element.

        Returns:
            Dict containing inlineStyles and matchedStyles.
        """

    @abstractmethod
    async def css_get_stylesheets(self) -> list[dict[str, Any]]:
        """List all stylesheets in the current page.

        Returns:
            List of stylesheet header dicts (styleSheetId, origin, sourceURL, etc.).
        """

    @abstractmethod
    async def css_get_rules(self, stylesheet_id: str) -> list[dict[str, Any]]:
        """Get CSS rules from a specific stylesheet.

        Args:
            stylesheet_id: The styleSheetId from css_get_stylesheets.

        Returns:
            List of CSS rule dicts.
        """

    @abstractmethod
    async def css_get_computed(self, selector: str) -> dict[str, Any]:
        """Get computed styles for an element by CSS selector.

        Args:
            selector: CSS selector for the target element.

        Returns:
            Dict mapping CSS property names to computed values.
        """

    # ── Debugging ──────────────────────────────────────────

    @abstractmethod
    async def debug_set_breakpoint(
        self, url: str, line: int, condition: str | None = None
    ) -> str:
        """Set a breakpoint by URL and line number.

        Args:
            url: URL of the script to set the breakpoint in.
            line: Line number (0-based) for the breakpoint.
            condition: Optional condition expression.

        Returns:
            The breakpoint ID string.
        """

    @abstractmethod
    async def debug_set_breakpoint_function(self, function_name: str) -> str:
        """Set a breakpoint by function name.

        Args:
            function_name: Name of the function to break on.

        Returns:
            The breakpoint ID string.
        """

    @abstractmethod
    async def debug_remove_breakpoint(self, breakpoint_id: str) -> None:
        """Remove a breakpoint by ID.

        Args:
            breakpoint_id: The breakpoint ID returned from set_breakpoint.
        """

    @abstractmethod
    async def debug_step_over(self) -> None:
        """Step over the current statement in the debugger."""

    @abstractmethod
    async def debug_step_into(self) -> None:
        """Step into the current function call in the debugger."""

    @abstractmethod
    async def debug_step_out(self) -> None:
        """Step out of the current function in the debugger."""

    @abstractmethod
    async def debug_pause(self) -> None:
        """Pause JavaScript execution."""

    @abstractmethod
    async def debug_resume(self) -> None:
        """Resume JavaScript execution after a pause."""

    @abstractmethod
    async def debug_get_listeners(self, selector: str) -> list[dict[str, Any]]:
        """Get event listeners attached to an element by CSS selector.

        Args:
            selector: CSS selector for the target element.

        Returns:
            List of listener dicts (type, useCapture, passive, etc.).
        """

    # ── DOM Snapshot ───────────────────────────────────────

    @abstractmethod
    async def dom_snapshot(self) -> dict[str, Any]:
        """Capture a DOM snapshot of the current page.

        Returns:
            Dict containing the raw DOM snapshot (documents, strings, etc.).
        """

    # ── Overlay ────────────────────────────────────────────

    @abstractmethod
    async def overlay_highlight(
        self, selector: str, color: str = "rgba(255,0,0,0.5)"
    ) -> None:
        """Highlight an element with a colored overlay.

        Args:
            selector: CSS selector for the element to highlight.
            color: RGBA color string for the highlight overlay.
        """

    @abstractmethod
    async def overlay_clear(self) -> None:
        """Clear all highlight overlays from the page."""

    # ── Storage ────────────────────────────────────────────

    @abstractmethod
    async def storage_get(self, key: str, storage_type: str = "local") -> str:
        """Get a value from DOM storage (local or session).

        Args:
            key: The storage key to retrieve.
            storage_type: "local" or "session".

        Returns:
            The stored value as a string, or empty string if not found.
        """

    @abstractmethod
    async def storage_set(
        self, key: str, value: str, storage_type: str = "local"
    ) -> None:
        """Set a value in DOM storage (local or session).

        Args:
            key: The storage key.
            value: The value to store.
            storage_type: "local" or "session".
        """

    @abstractmethod
    async def storage_clear(self, storage_type: str = "local") -> None:
        """Clear all entries in DOM storage.

        Args:
            storage_type: "local" or "session".
        """

    @abstractmethod
    async def storage_list(self, storage_type: str = "local") -> dict[str, str]:
        """List all key-value pairs in DOM storage.

        Args:
            storage_type: "local" or "session".

        Returns:
            Dict mapping keys to values.
        """

    @abstractmethod
    async def cache_storage_list(self) -> list[str]:
        """List all Cache Storage cache names.

        Returns:
            List of cache names.
        """

    @abstractmethod
    async def cache_storage_entries(self, cache_name: str) -> list[dict[str, Any]]:
        """List entries in a Cache Storage cache.

        Args:
            cache_name: Name of the cache to inspect.

        Returns:
            List of cache entry dicts (url, status, etc.).
        """

    @abstractmethod
    async def cache_storage_delete(self, cache_name: str) -> None:
        """Delete a Cache Storage cache.

        Args:
            cache_name: Name of the cache to delete.
        """

    @abstractmethod
    async def indexeddb_list(self) -> list[dict[str, Any]]:
        """List all IndexedDB databases.

        Returns:
            List of database info dicts (name, version, etc.).
        """

    @abstractmethod
    async def indexeddb_get_data(
        self, database: str, store: str, key: str = ""
    ) -> Any:
        """Get data from an IndexedDB object store.

        Args:
            database: Database name.
            store: Object store name.
            key: Optional key to retrieve a specific entry. If empty, returns all.

        Returns:
            The stored data, or list of all entries if key is empty.
        """

    @abstractmethod
    async def indexeddb_clear(self, database: str, store: str) -> None:
        """Clear all entries in an IndexedDB object store.

        Args:
            database: Database name.
            store: Object store name.
        """

    # ── Service Workers ────────────────────────────────────

    @abstractmethod
    async def sw_list(self) -> list[dict[str, Any]]:
        """List registered service workers.

        Returns:
            List of service worker registration dicts.
        """

    @abstractmethod
    async def sw_unregister(self, registration_id: str) -> None:
        """Unregister a service worker by registration ID.

        Args:
            registration_id: The service worker registration ID.
        """

    @abstractmethod
    async def sw_update(self, registration_id: str) -> None:
        """Trigger an update for a service worker registration.

        Args:
            registration_id: The service worker registration ID.
        """

    # ── Animations ─────────────────────────────────────────

    @abstractmethod
    async def animation_list(self) -> list[dict[str, Any]]:
        """List all active animations on the page.

        Returns:
            List of animation dicts (id, name, state, etc.).
        """

    @abstractmethod
    async def animation_pause(self, animation_id: str) -> None:
        """Pause an animation by ID.

        Args:
            animation_id: The animation ID to pause.
        """

    @abstractmethod
    async def animation_play(self, animation_id: str) -> None:
        """Play/resume an animation by ID.

        Args:
            animation_id: The animation ID to play.
        """

    @abstractmethod
    async def animation_seek(self, animation_id: str, time_ms: int) -> None:
        """Seek an animation to a specific time.

        Args:
            animation_id: The animation ID to seek.
            time_ms: Target time in milliseconds.
        """

    # ── WebAuthn (experimental) ───────────────────────────

    @abstractmethod
    async def webauthn_add_virtual_authenticator(
        self, protocol: str, transport: str
    ) -> str:
        """Add a virtual authenticator for WebAuthn testing.

        Args:
            protocol: Authenticator protocol (e.g. "ctap2", "u2f").
            transport: Transport type (e.g. "usb", "nfc", "ble").

        Returns:
            The authenticator ID.
        """

    @abstractmethod
    async def webauthn_remove_authenticator(self, authenticator_id: str) -> None:
        """Remove a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID to remove.
        """

    @abstractmethod
    async def webauthn_add_credential(
        self, authenticator_id: str, credential: dict[str, Any]
    ) -> None:
        """Add a credential to a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID.
            credential: Credential dict.
        """

    @abstractmethod
    async def webauthn_get_credentials(self, authenticator_id: str) -> list[dict[str, Any]]:
        """Get credentials from a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID.

        Returns:
            List of credential dicts.
        """

    # ── WebAudio (experimental) ────────────────────────────

    @abstractmethod
    async def webaudio_get_contexts(self) -> list[dict[str, Any]]:
        """Get all WebAudio contexts.

        Returns:
            List of audio context dicts.
        """

    @abstractmethod
    async def webaudio_get_context(self, context_id: str) -> dict[str, Any]:
        """Get a specific WebAudio context by ID.

        Args:
            context_id: The audio context ID.

        Returns:
            Audio context dict.
        """

    # ── Media (experimental) ───────────────────────────────

    @abstractmethod
    async def media_get_players(self) -> list[dict[str, Any]]:
        """Get all media players.

        Returns:
            List of media player dicts.
        """

    @abstractmethod
    async def media_get_messages(self, player_id: str) -> list[dict[str, Any]]:
        """Get messages for a specific media player.

        Args:
            player_id: The media player ID.

        Returns:
            List of media message dicts.
        """

    # ── Cast (experimental) ────────────────────────────────

    @abstractmethod
    async def cast_list(self) -> list[dict[str, Any]]:
        """List available cast sinks.

        Returns:
            List of cast sink dicts.
        """

    @abstractmethod
    async def cast_start_tab(self, sink_name: str) -> None:
        """Start tab mirroring to a cast sink.

        Args:
            sink_name: The cast sink name.
        """

    @abstractmethod
    async def cast_stop(self) -> None:
        """Stop active cast mirroring."""

    # ── Bluetooth (experimental) ───────────────────────────

    @abstractmethod
    async def bluetooth_emulate(
        self, name: str, address: str = "00:00:00:00:00:01"
    ) -> None:
        """Emulate a Bluetooth Low Energy device.

        Args:
            name: Device name.
            address: Device address (MAC).
        """

    @abstractmethod
    async def bluetooth_stop(self) -> None:
        """Stop Bluetooth emulation."""
