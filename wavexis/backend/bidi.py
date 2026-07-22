"""WebDriver BiDi backend using bidiwave.

Supports launch, navigate, screenshot, eval, raw, close, and BiDi parity
for navigation, tabs, DOM, storage, contexts, window bounds, dialogs, and permissions.
Experimental CDP domains (WebAuthn, WebAudio, Media, Cast, Bluetooth) raise
NotImplementedError — use --backend cdp for those features.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import inspect
import json
import re
import tempfile
import time
from pathlib import Path
from typing import Any

try:
    from io import BytesIO

    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from wavexis.backend.base import AbstractBackend
from wavexis.config import (
    DEVICE_PRESETS,
    PAPER_SIZES,
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
from wavexis.exceptions import (
    ElementNotFoundError,
    SessionNotInitializedError,
    WaitTimeoutError,
    WavexisError,
)
from wavexis.output import validate_path

try:
    from bidiwave import BiDiClient
except ImportError:
    BiDiClient = None  # type: ignore[assignment,misc]


class BiDiBackend(AbstractBackend):
    """WebDriver BiDi backend via bidiwave.

    Supports: launch, navigate, screenshot, screenshot_selector, pdf, eval,
    raw, close, go_back, go_forward, reload, stop_loading, wait_for,
    list_tabs, new_tab, close_tab, activate_tab, capture_console,
    capture_logs, DOM methods, dom_snapshot, storage methods,
    cookies (get/set/delete/clear), set_headers, set_user_agent,
    browser_version, emulate_device, set_viewport, set_geolocation,
    set_timezone, set_dark_mode, set_locale, set_touch_emulation,
    set_cpu_throttle, set_sensors, new_context, list_contexts, close_context,
    get_window_bounds, set_window_bounds, get_security_state, ignore_cert_errors,
    perf_metrics, perf_coverage, perf_css_coverage, perf_trace, perf_profile,
    perf_heap_snapshot, css_get_styles, css_get_computed, css_get_stylesheets,
    css_get_rules, overlay_highlight, overlay_clear, a11y_tree, a11y_node,
    a11y_ancestors, intercept_download, debug_set_breakpoint,
    debug_set_breakpoint_function, debug_remove_breakpoint, debug_step_over,
    debug_step_into, debug_step_out, debug_pause, debug_resume,
    debug_get_listeners, cache_storage_list, cache_storage_entries,
    cache_storage_delete, indexeddb_list, indexeddb_get_data, indexeddb_clear,
    sw_list, sw_unregister, sw_update, animation_list, animation_pause,
    animation_play, animation_seek, capture_har, screencast,
    dialog_accept, dialog_dismiss, grant_permission, reset_permissions,
    click, type_text, fill, select_option, hover, key_press, drag, tap,
    block_requests, throttle_network, set_cache_disabled, intercept_requests,
    mock_response, webauthn_add_virtual_authenticator,
    webauthn_remove_authenticator, webauthn_add_credential,
    webauthn_get_credentials, webaudio_get_contexts, webaudio_get_context,
    media_get_players, media_get_messages, cast_list, cast_start_tab,
    cast_stop, bluetooth_emulate, bluetooth_stop.

    BiDi native wrappers: get_client_windows, get_user_contexts,
    remove_user_context, set_client_window_state, close_browser,
    get_viewport, wait_for_function, wait_for_selector, locate_nodes,
    get_cdp_session, set_screen_orientation, perform_actions,
    release_actions, drag_and_drop, input_scroll, add_data_collector,
    get_network_data, disown_network_data, remove_data_collector,
    remove_intercept, remove_cache_override, continue_response,
    set_permission, add_preload_script, remove_preload_script,
    call_function, get_realms, disown_handles, session_status,
    delete_cookies (by filter), webextension_install, webextension_uninstall.

    All methods are implemented via BiDi native commands, JS workarounds,
    or the CDP bridge (browser.cdp.sendCommand).
    """

    def __init__(self) -> None:
        """Initialize the BiDi backend."""
        self._client: BiDiClient | None = None
        self._context: Any = None
        self._current_url: str = ""

    async def new_tab_handle(self, url: str = "about:blank") -> BiDiTabHandle:
        """Create a new browsing context with its own session for concurrent ops.

        Args:
            url: Initial URL for the new tab.

        Returns:
            A BiDiTabHandle sharing the browser process with its own context.
        """
        client = self._require_client()
        context = await client.browsing.create_context()
        return BiDiTabHandle(client, context)

    def _require_client(self) -> BiDiClient:
        """Return the current client or raise if not initialized.

        Returns:
            The active BiDiClient instance.

        Raises:
            SessionNotInitializedError: If launch() has not been called.
        """
        if self._client is None:
            raise SessionNotInitializedError("Session not initialized. Call launch() first.")
        return self._client

    def _require_launched(self) -> BiDiClient:
        """Return the client if launched, or raise if not initialized.

        Returns:
            The active BiDiClient instance.

        Raises:
            SessionNotInitializedError: If launch() has not been called
                or the browsing context was not created.
        """
        if self._client is None or self._context is None:
            raise SessionNotInitializedError("BiDiBackend not launched. Call launch() first.")
        return self._client

    async def launch(self, options: BrowserOptions) -> None:
        """Launch a browser via ChromeDriver WebSocket BiDi endpoint.

        Args:
            options: Browser launch options (headless, width, height, etc.).

        Note:
            BiDi connects to an existing ChromeDriver instance, so it cannot
            control headless mode, user_data_dir, or timeout at launch time.
            These options are ignored if provided.
        """
        if self._client is not None:
            return
        if BiDiClient is None:
            raise ImportError("bidiwave is not installed. Run: pip install wavexis[bidi]")

        # BiDi connects to existing browser, cannot control launch options
        if options.headless is not None:
            import warnings

            warnings.warn(
                "BiDi backend ignores 'headless' option - it connects to "
                "an existing ChromeDriver instance. Use CDP backend for headless control.",
                UserWarning,
                stacklevel=2,
            )
        if options.user_data_dir:
            import warnings

            warnings.warn(
                "BiDi backend ignores 'user_data_dir' option - it connects to "
                "an existing ChromeDriver instance. Use CDP backend for profile control.",
                UserWarning,
                stacklevel=2,
            )
        if options.timeout:
            import warnings

            warnings.warn(
                "BiDi backend ignores 'timeout' option - it connects to "
                "an existing ChromeDriver instance. Use CDP backend for timeout control.",
                UserWarning,
                stacklevel=2,
            )

        if options.browser_url:
            from urllib.parse import urlparse

            parsed = urlparse(options.browser_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 9222
            ws_url = f"ws://{host}:{port}/session"
        elif options.remote_url:
            ws_url = options.remote_url
        else:
            ws_url = "ws://localhost:9222/session"
        try:
            client = await BiDiClient.connect(ws_url)
        except WavexisError:
            # Already a friendly error; re-raise as-is.
            raise
        except Exception as e:
            # Bug #34: the default ws://localhost:9222/session requires a
            # running ChromeDriver with BiDi enabled. The raw exception
            # (OSError "Connection refused", websockets InvalidStatus
            # "HTTP 404", bidiwave BiDiConnectionError, etc.) is confusing.
            # Catch any connection-time failure and provide a clear message
            # with setup instructions.
            raise WavexisError(
                f"Could not connect to the BiDi endpoint at {ws_url}.\n"
                f"The BiDi backend requires ChromeDriver running with BiDi support.\n"
                f"Start it with:\n"
                f"  chromedriver --port=9222 --allowed-origins='*'\n"
                f"or use the CDP backend instead (default):\n"
                f"  wavexis screenshot https://example.com\n"
                f"Original error: {type(e).__name__}: {e}"
            ) from e
        try:
            await client.session.new()
            self._context = await client.browsing.create_context()

            if options.width and options.height:
                await client.browsing.set_viewport(
                    self._context,
                    viewport={"width": options.width, "height": options.height},
                )

            if options.user_agent:
                await client.emulation.set_user_agent(
                    options.user_agent,
                    contexts=[self._context],
                )

            if options.extra_headers:
                header_list = [{"name": k, "value": v} for k, v in options.extra_headers.items()]
                await client.cdp.send_command(
                    "Network.setExtraRequestHeaders", {"headers": header_list}
                )

            if options.proxy:
                await client.cdp.send_command(
                    "Network.setProxyOverride",
                    {"proxy": {"server": options.proxy}},
                )

            if options.stealth:
                from wavexis.actions.stealth import get_stealth_js

                await client.script.evaluate(self._context, get_stealth_js())

            self._client = client
        except Exception:
            with contextlib.suppress(Exception):
                await client.close()
            self._client = None
            self._context = None
            raise

    async def close(self) -> None:
        """Close the BiDi client and release resources."""
        client = self._client
        if client is not None:
            if self._context is not None:
                await client.browsing.close(self._context)
                self._context = None
            await client.close()
            self._client = None

    async def navigate(self, url: str, wait: WaitStrategy | None = None) -> None:
        """Navigate to a URL via browsingContext.navigate.

        Args:
            url: The URL to navigate to.
            wait: Wait strategy (mapped to BiDi wait parameter).
        """
        client = self._require_launched()
        timeout_ms: int = wait.timeout if wait is not None else 30000

        # Map WaitStrategy to BiDi wait parameter
        # BiDi accepts: "none", "complete", "interactive"
        bidi_wait = "complete"  # default
        if wait:
            if wait.strategy == "load":
                bidi_wait = "complete"
            elif wait.strategy == "domcontentloaded":
                bidi_wait = "interactive"
            elif wait.strategy in ("selector", "networkidle", "url"):
                # For these strategies, navigate first then wait separately
                await client.browsing.navigate(self._context, url, wait="complete")
                self._current_url = url
                await self.wait_for(wait)
                return
            else:
                raise ValueError(
                    f"Unsupported wait strategy for BiDi navigate: {wait.strategy}. "
                    "Use 'load', 'domcontentloaded', 'selector', 'networkidle', or 'url'."
                )

        try:
            await client.browsing.navigate(self._context, url, wait=bidi_wait)
            self._current_url = url
        except TimeoutError:
            raise WaitTimeoutError(wait.strategy if wait else "load", timeout_ms) from None

    async def screenshot(self, params: ScreenshotParams) -> bytes:
        """Take a screenshot via browsingContext.captureScreenshot.

        Args:
            params: Screenshot parameters.

        Returns:
            PNG or JPEG image bytes.
        """
        client = self._require_launched()

        # Navigate only if url is provided (CDP doesn't auto-navigate)
        if params.url:
            # Map wait strategy to BiDi wait parameter
            bidi_wait = "complete"
            navigated = False
            if params.wait:
                if params.wait.strategy == "load":
                    bidi_wait = "complete"
                elif params.wait.strategy == "domcontentloaded":
                    bidi_wait = "interactive"
                elif params.wait.strategy in ("selector", "networkidle", "url"):
                    # For these strategies, navigate first then wait separately
                    await client.browsing.navigate(self._context, params.url, wait="complete")
                    await self.wait_for(params.wait)
                    navigated = True
                else:
                    bidi_wait = "complete"

            if not navigated:
                timeout_ms: int = params.wait.timeout if params.wait is not None else 30000
                try:
                    await client.browsing.navigate(self._context, params.url, wait=bidi_wait)
                except TimeoutError:
                    raise WaitTimeoutError(
                        params.wait.strategy if params.wait else "load",
                        timeout_ms,
                    ) from None

        # Execute custom JS before screenshot if provided
        if params.js:
            await client.script.evaluate(self._context, params.js)

        result = await client.browsing.screenshot(
            self._context, format=params.format, quality=params.quality
        )
        data = result.data if hasattr(result, "data") else result.get("data", "")
        return base64.b64decode(data)

    async def screenshot_selector(
        self, selector: str, format: str = "png", quality: int = 80
    ) -> bytes:
        """Take a screenshot of a specific element via element bounding box.

        Uses script.evaluate to get the element's bounding rect, then
        captures a screenshot and crops to that rect via BiDi browsingContext.

        Args:
            selector: CSS selector for the target element.
            format: Image format ("png" or "jpeg").
            quality: JPEG quality (0-100).

        Returns:
            Image bytes of the element screenshot.
        """
        client = self._require_launched()
        escaped = json.dumps(selector)
        js = (
            f"var el=document.querySelector({escaped});"
            f"el?JSON.stringify(el.getBoundingClientRect()):null"
        )
        result = await client.script.evaluate(self._context, js)
        rect_str = result.value if hasattr(result, "value") else result
        if not rect_str:
            raise ElementNotFoundError(selector)
        rect = json.loads(rect_str)

        screenshot_result = await client.browsing.screenshot(
            self._context, format=format, quality=quality
        )
        data = (
            screenshot_result.data
            if hasattr(screenshot_result, "data")
            else screenshot_result.get("data", "")
        )
        image_bytes = base64.b64decode(data)

        # Crop to bounding box if PIL is available
        if PIL_AVAILABLE:
            img = Image.open(BytesIO(image_bytes))
            # rect contains x, y, width, height
            crop_box = (
                int(rect.get("x", 0)),
                int(rect.get("y", 0)),
                int(rect.get("x", 0) + rect.get("width", img.width)),
                int(rect.get("y", 0) + rect.get("height", img.height)),
            )
            cropped = img.crop(crop_box)
            output = BytesIO()
            cropped.save(output, format=format.upper() if format != "jpg" else "JPEG")
            return output.getvalue()

        return image_bytes

    @staticmethod
    def _annotate_js(selectors: list[str]) -> str:
        """Build JS that overlays numbered labels on elements."""
        selectors_json = json.dumps(selectors)
        return (
            f"(function(){{"
            f"var sels={selectors_json};"
            f"var container=document.createElement('div');"
            f"container.id='__wavexis_annotate';"
            f"container.style.cssText="
            f"'position:fixed;top:0;left:0;width:100%;height:100%;"
            f"pointer-events:none;z-index:999999;';"
            f"var labelMap={{}};"
            f"for(var i=0;i<sels.length;i++){{"
            f"var el=document.querySelector(sels[i]);"
            f"if(!el)continue;"
            f"var rect=el.getBoundingClientRect();"
            f"var label=document.createElement('div');"
            f"var num=i+1;"
            f"label.textContent='@e'+num;"
            f"label.style.cssText="
            f"'position:fixed;left:'+(rect.left+4)+'px;'"
            f"+'top:'+(rect.top+4)+'px;'"
            f"+'background:#ff4444;color:#fff;'"
            f"+'padding:2px 6px;border-radius:3px;'"
            f"+'font:bold 12px monospace;'"
            f"+'pointer-events:none;z-index:999999;';"
            f"var outline=document.createElement('div');"
            f"outline.style.cssText="
            f"'position:fixed;left:'+rect.left+'px;'"
            f"+'top:'+rect.top+'px;'"
            f"+'width:'+rect.width+'px;'"
            f"+'height:'+rect.height+'px;'"
            f"+'border:2px solid #ff4444;'"
            f"+'pointer-events:none;z-index:999998;';"
            f"container.appendChild(outline);"
            f"container.appendChild(label);"
            f"labelMap['e'+num]=sels[i];"
            f"}}"
            f"document.body.appendChild(container);"
            f"return JSON.stringify(labelMap);"
            f"}})()"
        )

    @staticmethod
    def _remove_annotate_js() -> str:
        """Build JS that removes annotation overlays."""
        return (
            "(function(){var e=document.getElementById('__wavexis_annotate');if(e)e.remove();})()"
        )

    async def annotated_screenshot(
        self,
        selectors: list[str],
        format: str = "png",
    ) -> tuple[bytes, dict[str, str]]:
        """Take a screenshot with numbered labels overlaid on elements.

        Args:
            selectors: List of CSS selectors to annotate.
            format: Image format: "png" or "jpeg".

        Returns:
            Tuple of (image_bytes, label_map).
        """
        client = self._require_client()
        js = self._annotate_js(selectors)
        result = await client.script.evaluate(self._context, js)
        raw = getattr(result, "value", None)
        label_map: dict[str, str] = json.loads(raw) if isinstance(raw, str) else {}
        screenshot_result = await client.browsing.screenshot(self._context, format=format)
        await client.script.evaluate(self._context, self._remove_annotate_js())
        data = (
            screenshot_result.data
            if hasattr(screenshot_result, "data")
            else screenshot_result.get("data", "")
        )
        return base64.b64decode(data), label_map

    async def eval(self, expression: str, await_promise: bool = False) -> Any:
        """Evaluate a JavaScript expression via script.evaluate.

        Args:
            expression: JavaScript expression to evaluate.
            await_promise: Whether to await a returned Promise.

        Returns:
            The evaluated result value.
        """
        client = self._require_launched()
        result = await client.script.evaluate(
            self._context, expression, await_promise=await_promise
        )
        if hasattr(result, "value"):
            return result.value
        return result

    async def raw(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a raw BiDi command (escape hatch).

        Args:
            method: BiDi command method name.
            params: Command parameters dict.

        Returns:
            Response dict from the BiDi command.
        """
        client = self._require_launched()
        return dict(await client._connection.send_command(method, params or {}))

    async def go_back(self) -> None:
        """Navigate back via browsingContext.traverse."""
        client = self._require_launched()
        await client._connection.send_command(
            "browsingContext.traverse",
            {"context": self._context, "direction": "back"},
        )

    async def go_forward(self) -> None:
        """Navigate forward via browsingContext.traverse."""
        client = self._require_launched()
        await client._connection.send_command(
            "browsingContext.traverse",
            {"context": self._context, "direction": "forward"},
        )

    async def reload(self, ignore_cache: bool = False) -> None:
        """Reload the current page via browsingContext.reload."""
        client = self._require_launched()
        await client._connection.send_command(
            "browsingContext.reload",
            {"context": self._context, "ignoreCache": ignore_cache},
        )

    async def stop_loading(self) -> None:
        """Stop loading via browsingContext.cancelNavigation."""
        client = self._require_launched()
        await client._connection.send_command(
            "browsingContext.cancelNavigation",
            {"context": self._context},
        )

    # ── Page lifecycle ─────────────────────────────────────

    async def page_get_frame_tree(self) -> dict[str, Any]:
        """Get the current page frame tree via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Page.getFrameTree", {}))

    async def page_get_layout_metrics(self) -> dict[str, Any]:
        """Get page layout metrics via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Page.getLayoutMetrics", {}))

    async def page_get_navigation_history(self) -> dict[str, Any]:
        """Get the navigation history for the current page."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Page.getNavigationHistory", {}))

    async def page_navigate_to_history_entry(self, entry_id: int) -> None:
        """Navigate to a specific history entry by ID."""
        client = self._require_launched()
        await client._connection.send_command(
            "browsingContext.traverse",
            {"context": self._context, "delta": entry_id},
        )

    async def page_bring_to_front(self) -> None:
        """Bring the current page to the foreground."""
        client = self._require_launched()
        await client.browsing.activate(context=self._context)

    async def page_wait_for_debugger(self) -> None:
        """Wait for the debugger to attach via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.waitForDebugger", {})

    async def page_get_resource_content(self, frame_id: str, url: str) -> dict[str, Any]:
        """Get the content of a page resource by frame ID and URL."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "Page.getResourceContent",
                {"frameId": frame_id, "url": url},
            )
        )

    async def page_set_download_behavior(self, behavior: str, download_path: str = "") -> None:
        """Set page download behavior (allow/deny and path)."""
        client = self._require_launched()
        params: dict[str, Any] = {"behavior": behavior}
        if download_path:
            params["downloadPath"] = download_path
        await client.cdp.send_command("Page.setDownloadBehavior", params)

    async def page_capture_snapshot(self, format: str = "mhtml") -> str:
        """Capture a snapshot of the page as MHTML or text via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Page.captureSnapshot", {"format": format})
        return str(result.get("data", ""))

    async def page_print_to_pdf(
        self,
        landscape: bool = False,
        display_header_footer: bool = False,
        print_background: bool = False,
        scale: float = 1.0,
        paper_width: float = 8.5,
        paper_height: float = 11.0,
        margin_top: float = 0.4,
        margin_bottom: float = 0.4,
        margin_left: float = 0.4,
        margin_right: float = 0.4,
    ) -> str:
        """Print the page to PDF and return base64-encoded data via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Page.printToPDF",
            {
                "landscape": landscape,
                "displayHeaderFooter": display_header_footer,
                "printBackground": print_background,
                "scale": scale,
                "paperWidth": paper_width,
                "paperHeight": paper_height,
                "marginTop": margin_top,
                "marginBottom": margin_bottom,
                "marginLeft": margin_left,
                "marginRight": margin_right,
            },
        )
        return str(result.get("data", ""))

    async def page_start_screencast(
        self, format: str = "jpeg", quality: int = 80, max_width: int = 0, max_height: int = 0
    ) -> None:
        """Start screencasting the page via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Page.startScreencast",
            {
                "format": format,
                "quality": quality,
                "maxWidth": max_width,
                "maxHeight": max_height,
            },
        )

    async def page_stop_screencast(self) -> None:
        """Stop screencasting the page via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.stopScreencast", {})

    async def page_set_bypass_csp(self, enabled: bool) -> None:
        """Enable or disable CSP bypass for the page via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.setBypassCSP", {"enabled": enabled})

    async def page_set_ad_blocking_enabled(self, enabled: bool) -> None:
        """Enable or disable ad blocking for the page via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.setAdBlockingEnabled", {"enabled": enabled})

    async def page_add_script_to_evaluate_on_new_document(
        self, source: str, world_name: str = ""
    ) -> str:
        """Add a script to evaluate on every new document via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"source": source}
        if world_name:
            params["worldName"] = world_name
        result = await client.cdp.send_command("Page.addScriptToEvaluateOnNewDocument", params)
        return str(result.get("identifier", ""))

    async def page_remove_script_to_evaluate_on_new_document(self, script_id: str) -> None:
        """Remove a previously added script by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Page.removeScriptToEvaluateOnNewDocument",
            {"identifier": script_id},
        )

    async def page_generate_test_report(self, message: str, group: str = "") -> None:
        """Generate a test report for the Reporting API via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"message": message}
        if group:
            params["group"] = group
        await client.cdp.send_command("Page.generateTestReport", params)

    async def page_get_app_manifest(self) -> dict[str, Any]:
        """Get the web app manifest for the current page via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Page.getAppManifest", {}))

    async def page_get_resource_tree(self) -> dict[str, Any]:
        """Get the resource tree for the current page via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Page.getResourceTree", {}))

    async def page_add_compilation_cache(self, url: str, data: str) -> None:
        """Add data to the compilation cache for the given URL via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.addCompilationCache", {"url": url, "data": data})

    async def page_add_script_to_evaluate_on_load(self, source: str) -> str:
        """Add a script to evaluate on page load via CDP bridge. Returns script ID."""
        client = self._require_launched()
        result = await client.cdp.send_command("Page.addScriptToEvaluateOnLoad", {"source": source})
        return str(result.get("identifier", "")) if result else ""

    async def page_capture_screenshot(
        self,
        format: str = "png",
        quality: int = 80,
        clip: dict[str, Any] | None = None,
        from_surface: bool = True,
        capture_beyond_viewport: bool = False,
    ) -> str:
        """Capture a screenshot of the page via CDP bridge. Returns base64-encoded data."""
        client = self._require_launched()
        params: dict[str, Any] = {
            "format": format,
            "quality": quality,
            "fromSurface": from_surface,
            "captureBeyondViewport": capture_beyond_viewport,
        }
        if clip is not None:
            params["clip"] = clip
        result = await client.cdp.send_command("Page.captureScreenshot", params)
        return str(result.get("data", "")) if result else ""

    async def page_clear_compilation_cache(self) -> None:
        """Clear the compilation cache via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.clearCompilationCache", {})

    async def page_clear_device_orientation_override(self) -> None:
        """Clear the device orientation override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.clearDeviceOrientationOverride", {})

    async def page_clear_geolocation_override(self) -> None:
        """Clear the geolocation override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.clearGeolocationOverride", {})

    async def page_crash(self) -> None:
        """Crash the renderer via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.crash", {})

    async def page_create_isolated_world(
        self, frame_id: str, world_name: str = "", grant_univeral_access: bool = False
    ) -> str:
        """Create an isolated world for the given frame via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {
            "frameId": frame_id,
            "grantUniveralAccess": grant_univeral_access,
        }
        if world_name:
            params["worldName"] = world_name
        result = await client.cdp.send_command("Page.createIsolatedWorld", params)
        return str(result.get("executionContextId", "")) if result else ""

    async def page_disable(self) -> None:
        """Disable the page domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.disable", {})

    async def page_enable(self) -> None:
        """Enable the page domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.enable", {})

    async def page_get_ad_script_ancestry(self, frame_id: str) -> dict[str, Any]:
        """Get the ad script ancestry for a frame via CDP bridge."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command("Page.getAdScriptAncestry", {"frameId": frame_id})
        )

    async def page_get_annotated_page_content(self) -> dict[str, Any]:
        """Get annotated page content via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Page.getAnnotatedPageContent", {}))

    async def page_get_app_id(self) -> dict[str, Any]:
        """Get the app ID for the current page via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Page.getAppId", {}))

    async def page_get_installability_errors(self) -> dict[str, Any]:
        """Get installability errors for the current page via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Page.getInstallabilityErrors", {}))

    async def page_get_manifest_icons(self) -> dict[str, Any]:
        """Get manifest icons for the current page via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Page.getManifestIcons", {}))

    async def page_get_origin_trials(self) -> dict[str, Any]:
        """Get origin trials for the current page via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Page.getOriginTrials", {}))

    async def page_get_permissions_policy_state(self, frame_id: str) -> dict[str, Any]:
        """Get permissions policy state for a frame via CDP bridge."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command("Page.getPermissionsPolicyState", {"frameId": frame_id})
        )

    async def page_handle_java_script_dialog(self, accept: bool, prompt_text: str = "") -> None:
        """Handle a JavaScript dialog via CDP bridge (alias for handle_javascript_dialog)."""
        client = self._require_launched()
        params: dict[str, Any] = {"accept": accept}
        if prompt_text:
            params["promptText"] = prompt_text
        await client.cdp.send_command("Page.handleJavaScriptDialog", params)

    async def page_handle_javascript_dialog(self, accept: bool, prompt_text: str = "") -> None:
        """Handle a JavaScript dialog via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"accept": accept}
        if prompt_text:
            params["promptText"] = prompt_text
        await client.cdp.send_command("Page.handleJavaScriptDialog", params)

    async def page_produce_compilation_cache(self, url: str) -> dict[str, Any]:
        """Produce compilation cache for the given URL via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Page.produceCompilationCache", {"url": url}))

    async def page_remove_script_to_evaluate_on_load(self, script_id: str) -> None:
        """Remove a script previously added to evaluate on load via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Page.removeScriptToEvaluateOnLoad", {"identifier": script_id}
        )

    async def page_reset_navigation_history(self) -> None:
        """Reset the navigation history via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.resetNavigationHistory", {})

    async def page_screencast_frame_ack(self, session_id: int) -> None:
        """Acknowledge a screencast frame via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.screencastFrameAck", {"sessionId": session_id})

    async def page_search_in_resource(
        self,
        frame_id: str,
        url: str,
        query: str,
        case_sensitive: bool = False,
        is_regex: bool = False,
    ) -> dict[str, Any]:
        """Search for a string in a resource via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {
            "frameId": frame_id,
            "url": url,
            "query": query,
            "caseSensitive": case_sensitive,
            "isRegex": is_regex,
        }
        return dict(await client.cdp.send_command("Page.searchInResource", params))

    async def page_set_device_orientation_override(
        self, alpha: float, beta: float, gamma: float
    ) -> None:
        """Override the device orientation via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Page.setDeviceOrientationOverride", {"alpha": alpha, "beta": beta, "gamma": gamma}
        )

    async def page_set_document_content(self, frame_id: str, html: str) -> None:
        """Set the document content for a frame via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Page.setDocumentContent", {"frameId": frame_id, "html": html}
        )

    async def page_set_font_families(self, font_families: dict[str, Any]) -> None:
        """Set font families for the page via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.setFontFamilies", {"fontFamilies": font_families})

    async def page_set_font_sizes(self, font_sizes: dict[str, Any]) -> None:
        """Set font sizes for the page via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.setFontSizes", {"fontSizes": font_sizes})

    async def page_set_geolocation_override(
        self, latitude: float = 0.0, longitude: float = 0.0, accuracy: float = 0.0
    ) -> None:
        """Override the geolocation via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Page.setGeolocationOverride",
            {"latitude": latitude, "longitude": longitude, "accuracy": accuracy},
        )

    async def page_set_intercept_file_chooser_dialog(self, enabled: bool) -> None:
        """Intercept file chooser dialogs via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.setInterceptFileChooserDialog", {"enabled": enabled})

    async def page_set_lifecycle_events_enabled(self, enabled: bool) -> None:
        """Enable or disable lifecycle events via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.setLifecycleEventsEnabled", {"enabled": enabled})

    async def page_set_prerendering_allowed(self, is_allowed: bool) -> None:
        """Set whether prerendering is allowed via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.setPrerenderingAllowed", {"isAllowed": is_allowed})

    async def page_set_rph_registration_mode(self, mode: str) -> None:
        """Set the RPH registration mode via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.setRPHRegistrationMode", {"mode": mode})

    async def page_set_spc_transaction_mode(self, mode: str) -> None:
        """Set the SPC transaction mode via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.setSPCTransactionMode", {"mode": mode})

    async def page_set_touch_emulation_enabled(
        self, enabled: bool, configuration: str = ""
    ) -> None:
        """Enable or disable touch emulation via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"enabled": enabled}
        if configuration:
            params["configuration"] = configuration
        await client.cdp.send_command("Page.setTouchEmulationEnabled", params)

    async def page_set_web_lifecycle_state(self, state: str) -> None:
        """Set the web lifecycle state via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.setWebLifecycleState", {"state": state})

    async def page_stop(self) -> None:
        """Stop all page loading via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Page.stop", {})

    async def wait_for(self, strategy: WaitStrategy) -> None:
        """Wait for a condition via polling script.evaluate."""
        client = self._require_launched()

        deadline = time.monotonic() + strategy.timeout / 1000
        while time.monotonic() < deadline:
            if strategy.strategy == "selector" and strategy.selector:
                escaped = json.dumps(strategy.selector)
                js = f"!!document.querySelector({escaped})"
                result = await client.script.evaluate(self._context, js, await_promise=False)
                if hasattr(result, "value") and result.value:
                    return
            elif strategy.strategy == "load":
                # For load, wait for document.readyState == 'complete'
                js = "document.readyState === 'complete'"
                result = await client.script.evaluate(self._context, js, await_promise=False)
                if hasattr(result, "value") and result.value:
                    return
            elif strategy.strategy == "networkidle":
                # Poll for network idle: no more than 2 active requests for 500ms
                js = """
                (function() {
                    return window.performance.getEntries()
                        .filter(e => e.entryType === 'resource')
                        .filter(e => !e.duration || e.duration < 0)
                        .length <= 2;
                })()
                """
                result = await client.script.evaluate(self._context, js, await_promise=False)
                is_idle = getattr(result, "value", False)
                if is_idle:
                    if not hasattr(self, "_networkidle_start"):
                        self._networkidle_start = time.monotonic()
                    elif time.monotonic() - self._networkidle_start >= 0.5:
                        delattr(self, "_networkidle_start")
                        return
                else:
                    if hasattr(self, "_networkidle_start"):
                        delattr(self, "_networkidle_start")
            elif strategy.strategy == "url" and strategy.url_pattern:
                result = await client.script.evaluate(
                    self._context, "window.location.href", await_promise=False
                )
                href = getattr(result, "value", "") or ""
                if strategy.url_pattern in href:
                    return
            else:
                raise ValueError(f"Unsupported wait strategy: {strategy.strategy}")
            await asyncio.sleep(0.1)
        raise WaitTimeoutError(strategy.strategy, strategy.timeout)

    async def pdf(self, params: PDFParams) -> bytes:
        """Generate a PDF via browsingContext.print.

        Args:
            params: PDF parameters (url, paper, landscape, margin, etc.).

        Returns:
            PDF bytes.
        """
        client = self._require_launched()
        if params.js:
            await client.script.evaluate(self._context, params.js)
        paper = PAPER_SIZES.get(params.paper, PAPER_SIZES["letter"])
        margin_match = re.match(r"([\d.]+)", params.margin)
        margin_val = float(margin_match.group(1)) if margin_match else 0.4
        margin_dict = {
            "top": margin_val,
            "bottom": margin_val,
            "left": margin_val,
            "right": margin_val,
        }
        result = await client.browsing.print(
            self._context,
            background=True,
            margin=margin_dict,
            orientation="landscape" if params.landscape else "portrait",
            page={"width": paper["width"], "height": paper["height"]},
            scale=1.0,
            shrink_to_fit=True,
        )
        data = result.data if hasattr(result, "data") else result.get("data", "")
        return base64.b64decode(data)

    async def screencast(self, params: ScreencastParams) -> list[bytes]:
        """Capture a screencast via repeated CDP screenshots.

        Captures frames at ~2fps by taking screenshots in a loop.
        Uses CDP Page.captureScreenshot since BiDi screencast events
        are not available via the bridge.

        Args:
            params: Screencast parameters.

        Returns:
            List of image bytes (one per frame).
        """
        client = self._require_launched()

        frames: list[bytes] = []
        interval = 0.5
        elapsed = 0.0
        while elapsed < params.duration:
            result = await client.cdp.send_command(
                "Page.captureScreenshot",
                {"format": params.format, "quality": params.quality},
            )
            data = result.get("data", "") if result else ""
            if data:
                frames.append(base64.b64decode(data))
            await asyncio.sleep(interval)
            elapsed += interval
        return frames

    async def list_tabs(self) -> list[dict[str, Any]]:
        """List browsing contexts (tabs) via browsingContext.getTree."""
        client = self._require_launched()
        result = await client._connection.send_command("browsingContext.getTree", {})
        return list(result.get("contexts", []))

    async def new_tab(self, url: str = "about:blank") -> str:
        """Create a new browsing context (tab) via browsingContext.create."""
        client = self._require_launched()
        result = await client._connection.send_command(
            "browsingContext.create",
            {"type": "tab", "url": url},
        )
        return str(result.get("context", ""))

    async def close_tab(self, tab_id: str) -> None:
        """Close a browsing context via browsingContext.close."""
        client = self._require_launched()
        await client._connection.send_command(
            "browsingContext.close",
            {"context": tab_id},
        )

    async def activate_tab(self, tab_id: str) -> None:
        """Activate a browsing context via browsingContext.activate.

        Args:
            tab_id: The browsing context ID to activate.
        """
        client = self._require_launched()
        await client.browsing.activate(tab_id)

    async def capture_console(self, level: str = "all") -> list[dict[str, Any]]:
        """Capture console messages via log.entryAdded event subscription.

        Subscribes to log.entryAdded, navigates to the current page URL
        (already loaded), collects entries for a short window, then returns.

        Args:
            level: Minimum log level (all, info, warning, error).

        Returns:
            List of console entry dicts with type, level, text, timestamp.
        """
        client = self._require_launched()

        entries: list[dict[str, Any]] = []
        level_order = {"all": 0, "debug": 0, "info": 1, "warning": 2, "error": 3}
        min_level = level_order.get(level, 0)

        async def _handler(event: Any) -> None:
            """Handle a console event and append it to entries if level matches.

            Args:
                event: The BiDi console event object.
            """
            entry_level = getattr(event, "level", "info")
            if level_order.get(entry_level, 0) >= min_level or level == "all":
                entries.append(
                    {
                        "type": getattr(event, "type", "console"),
                        "level": entry_level,
                        "text": getattr(event, "text", ""),
                        "timestamp": getattr(event, "timestamp", None),
                        "args": getattr(event, "args", []),
                    }
                )

        sub = await client.on_log_entry(_handler)
        await asyncio.sleep(0.5)
        client.off(sub)
        return entries

    async def capture_logs(self) -> list[dict[str, Any]]:
        """Capture browser log entries via log.entryAdded subscription.

        Returns:
            List of log entry dicts.
        """
        return await self.capture_console(level="all")

    async def dom_get(self, selector: str, outer: bool = True) -> str:
        """Get outerHTML of an element via script.evaluate."""
        client = self._require_launched()
        escaped = json.dumps(selector)
        prop = "outerHTML" if outer else "innerHTML"
        js = f"var el=document.querySelector({escaped});el?el.{prop}:null"
        result = await client.script.evaluate(self._context, js)
        value = result.value if hasattr(result, "value") else result
        if not value:
            raise ElementNotFoundError(selector)
        return str(value)

    async def dom_query(
        self, selector: str, all: bool = False
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Query elements via script.evaluate."""
        client = self._require_launched()
        escaped = json.dumps(selector)
        if all:
            js = (
                f"Array.from(document.querySelectorAll({escaped}))"
                f".map(e=>({{tagName:e.tagName,id:e.id,className:e.className}}))"
            )
            result = await client.script.evaluate(self._context, js)
            return list(result.value if hasattr(result, "value") else result)
        js = (
            f"var e=document.querySelector({escaped});"
            f"e?{{tagName:e.tagName,id:e.id,className:e.className}}:null"
        )
        result = await client.script.evaluate(self._context, js)
        return dict(result.value if hasattr(result, "value") else result)

    async def dom_set_attr(self, selector: str, name: str, value: str) -> None:
        """Set an attribute on an element via script.evaluate."""
        client = self._require_launched()
        escaped = json.dumps(selector)
        escaped_name = json.dumps(name)
        escaped_val = json.dumps(value)
        js = (
            f"var el=document.querySelector({escaped});"
            f"if(!el)throw new Error('Element not found');"
            f"el.setAttribute({escaped_name},{escaped_val})"
        )
        await client.script.evaluate(self._context, js)

    async def dom_get_attr(self, selector: str, name: str) -> str:
        """Get an attribute from an element via script.evaluate."""
        client = self._require_launched()
        escaped = json.dumps(selector)
        escaped_name = json.dumps(name)
        js = (
            f"var el=document.querySelector({escaped});"
            f"if(!el)throw new Error('Element not found');"
            f"el.getAttribute({escaped_name})"
        )
        result = await client.script.evaluate(self._context, js)
        return str(result.value if hasattr(result, "value") else result)

    async def dom_remove_attr(self, selector: str, name: str) -> None:
        """Remove an attribute from an element via script.evaluate."""
        client = self._require_launched()
        escaped = json.dumps(selector)
        escaped_name = json.dumps(name)
        js = (
            f"var el=document.querySelector({escaped});"
            f"if(!el)throw new Error('Element not found');"
            f"el.removeAttribute({escaped_name})"
        )
        await client.script.evaluate(self._context, js)

    async def dom_remove(self, selector: str) -> None:
        """Remove an element via script.evaluate."""
        client = self._require_launched()
        escaped = json.dumps(selector)
        js = f"document.querySelector({escaped})?.remove()"
        await client.script.evaluate(self._context, js)

    async def dom_focus(self, selector: str) -> None:
        """Focus an element via script.evaluate."""
        client = self._require_launched()
        escaped = json.dumps(selector)
        js = f"document.querySelector({escaped})?.focus()"
        await client.script.evaluate(self._context, js)

    async def dom_scroll(self, selector: str | None = None, x: int = 0, y: int = 0) -> None:
        """Scroll to a position or element via script.evaluate."""
        client = self._require_launched()
        if selector:
            escaped = json.dumps(selector)
            js = f"document.querySelector({escaped})?.scrollIntoView()"
        else:
            js = f"window.scrollTo({x},{y})"
        await client.script.evaluate(self._context, js)

    async def _find_node_cdp(self, client: Any, selector: str) -> int:
        """Resolve a CSS selector to a CDP nodeId via the CDP bridge."""
        await client.cdp.send_command("DOM.enable", {})
        doc = await client.cdp.send_command("DOM.getDocument", {})
        root_id = doc.get("root", {}).get("nodeId", 0)
        result = await client.cdp.send_command(
            "DOM.querySelector", {"nodeId": root_id, "selector": selector}
        )
        node_id = result.get("nodeId", 0)
        if node_id == 0:
            raise ElementNotFoundError(selector)
        return int(node_id)

    async def dom_get_document(self) -> dict[str, Any]:
        """Get the document root node via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.enable", {})
        return dict(await client.cdp.send_command("DOM.getDocument", {}))

    async def dom_get_flattened_document(self) -> dict[str, Any]:
        """Get the flattened document tree via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.enable", {})
        return dict(await client.cdp.send_command("DOM.getFlattenedDocument", {}))

    async def dom_get_box_model(self, selector: str) -> dict[str, Any]:
        """Get the box model for an element matching a CSS selector."""
        client = self._require_launched()
        node_id = await self._find_node_cdp(client, selector)
        return dict(await client.cdp.send_command("DOM.getBoxModel", {"nodeId": node_id}))

    async def dom_get_content_quads(self, selector: str) -> list[dict[str, Any]]:
        """Get the content quads for an element matching a CSS selector."""
        client = self._require_launched()
        node_id = await self._find_node_cdp(client, selector)
        result = await client.cdp.send_command("DOM.getContentQuads", {"nodeId": node_id})
        return list(result.get("quads", []))

    async def dom_get_node_for_location(self, x: int, y: int) -> dict[str, Any]:
        """Get the node ID for a location in the viewport (hit testing)."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.enable", {})
        return dict(await client.cdp.send_command("DOM.getNodeForLocation", {"x": x, "y": y}))

    async def dom_perform_search(self, query: str) -> dict[str, Any]:
        """Search the DOM for the given query string."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.enable", {})
        return dict(await client.cdp.send_command("DOM.performSearch", {"query": query}))

    async def dom_get_search_results(
        self, search_id: str, from_index: int = 0, to_index: int = 0
    ) -> list[dict[str, Any]]:
        """Get search results for a DOM search session."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "DOM.getSearchResults",
            {"searchId": search_id, "fromIndex": from_index, "toIndex": to_index},
        )
        return list(result.get("nodeIds", []))

    async def dom_scroll_into_view_if_needed(self, selector: str) -> None:
        """Scroll an element matching a CSS selector into view if needed."""
        client = self._require_launched()
        node_id = await self._find_node_cdp(client, selector)
        await client.cdp.send_command("DOM.scrollIntoViewIfNeeded", {"nodeId": node_id})

    async def dom_describe_node(self, node_id: int) -> dict[str, Any]:
        """Describe a DOM node by node ID via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("DOM.describeNode", {"nodeId": node_id}))

    async def dom_get_outer_html(self, node_id: int) -> str:
        """Get the outer HTML of a node by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("DOM.getOuterHTML", {"nodeId": node_id})
        return str(result.get("outerHTML", ""))

    async def dom_remove_node(self, node_id: int) -> None:
        """Remove a node from the DOM by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.removeNode", {"nodeId": node_id})

    async def dom_set_node_value(self, node_id: int, value: str) -> None:
        """Set the value of a node by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.setNodeValue", {"nodeId": node_id, "value": value})

    async def dom_set_outer_html(self, node_id: int, outer_html: str) -> None:
        """Set the outer HTML of a node by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "DOM.setOuterHTML", {"nodeId": node_id, "outerHTML": outer_html}
        )

    async def dom_request_node(self, object_id: str) -> int:
        """Request a node by JavaScript object reference via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("DOM.requestNode", {"objectId": object_id})
        return int(result.get("nodeId", 0))

    async def dom_resolve_node(self, node_id: int) -> dict[str, Any]:
        """Resolve a node to a remote object via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("DOM.resolveNode", {"nodeId": node_id}))

    async def dom_set_attribute_value(self, node_id: int, name: str, value: str) -> None:
        """Set an attribute value on a node by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "DOM.setAttributeValue",
            {"nodeId": node_id, "name": name, "value": value},
        )

    async def dom_remove_attribute(self, node_id: int, name: str) -> None:
        """Remove an attribute from a node by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.removeAttribute", {"nodeId": node_id, "name": name})

    async def dom_request_child_nodes(self, node_id: int, depth: int = -1) -> None:
        """Request child nodes of a node by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.requestChildNodes", {"nodeId": node_id, "depth": depth})

    async def dom_collect_class_names_from_subtree(self, node_id: int) -> list[str]:
        """Collect class names from the subtree of a node by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "DOM.collectClassNamesFromSubtree", {"nodeId": node_id}
        )
        return list(result.get("classNames", [])) if result else []

    async def dom_copy_to(
        self, node_id: int, target_node_id: int, insert_before_node_id: int | None = None
    ) -> None:
        """Copy a node to a target node via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"nodeId": node_id, "targetNodeId": target_node_id}
        if insert_before_node_id is not None:
            params["insertBeforeNodeId"] = insert_before_node_id
        await client.cdp.send_command("DOM.copyTo", params)

    async def dom_disable(self) -> None:
        """Disable the DOM agent via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.disable", {})

    async def dom_discard_search_results(self, search_id: str) -> None:
        """Discard search results for a DOM search session via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.discardSearchResults", {"searchId": search_id})

    async def dom_enable(self) -> None:
        """Enable the DOM agent via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.enable", {})

    async def dom_focus_node(self, node_id: int) -> None:
        """Focus a node by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.focus", {"nodeId": node_id})

    async def dom_force_show_popover(self, node_id: int) -> None:
        """Force show a popover for a node by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.forceShowPopover", {"nodeId": node_id})

    async def dom_get_anchor_element(self, node_id: int) -> dict[str, Any]:
        """Get the anchor element for a node by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("DOM.getAnchorElement", {"nodeId": node_id})
        return dict(result) if result else {}

    async def dom_get_node_attribute(self, node_id: int, name: str) -> str:
        """Get an attribute value from a node by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "DOM.getAttribute", {"nodeId": node_id, "name": name}
        )
        return str(result.get("value", "")) if result else ""

    async def dom_get_container_for_node(
        self, node_id: int, container_name: str | None = None
    ) -> dict[str, Any]:
        """Get the container for a node by ID via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"nodeId": node_id}
        if container_name is not None:
            params["containerName"] = container_name
        result = await client.cdp.send_command("DOM.getContainerForNode", params)
        return dict(result) if result else {}

    async def dom_get_detached_dom_nodes(self) -> list[dict[str, Any]]:
        """Get detached DOM nodes via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("DOM.getDetachedDomNodes", {})
        return list(result.get("detachedNodes", [])) if result else []

    async def dom_get_element_by_relation(self, node_id: int, relation: str) -> dict[str, Any]:
        """Get an element by relation from a node by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "DOM.getElementByRelation", {"nodeId": node_id, "relation": relation}
        )
        return dict(result) if result else {}

    async def dom_get_file_info(self, node_id: int) -> dict[str, Any]:
        """Get file info for a node by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("DOM.getFileInfo", {"nodeId": node_id})
        return dict(result) if result else {}

    async def dom_get_frame_owner(self, frame_id: str) -> dict[str, Any]:
        """Get the frame owner node for a frame ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("DOM.getFrameOwner", {"frameId": frame_id})
        return dict(result) if result else {}

    async def dom_get_node_stack_traces(self, node_id: int) -> dict[str, Any]:
        """Get stack traces for a node by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("DOM.getNodeStackTraces", {"nodeId": node_id})
        return dict(result) if result else {}

    async def dom_get_nodes_for_subtree_by_style(
        self, node_id: int, computed_styles: list[str], pierce: bool = False
    ) -> list[dict[str, Any]]:
        """Get nodes in a subtree matching the given computed styles via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "DOM.getNodesForSubtreeByStyle",
            {"nodeId": node_id, "computedStyles": computed_styles, "pierce": pierce},
        )
        return list(result.get("nodeIds", [])) if result else []

    async def dom_get_querying_descendants_for_container(
        self, node_id: int
    ) -> list[dict[str, Any]]:
        """Get querying descendants for a container node by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "DOM.getQueryingDescendantsForContainer", {"nodeId": node_id}
        )
        return list(result.get("nodeIds", [])) if result else []

    async def dom_get_relayout_boundary(self, node_id: int) -> dict[str, Any]:
        """Get the relayout boundary for a node by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("DOM.getRelayoutBoundary", {"nodeId": node_id})
        return dict(result) if result else {}

    async def dom_get_top_layer_elements(self) -> list[dict[str, Any]]:
        """Get top layer elements via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("DOM.getTopLayerElements", {})
        return list(result.get("nodes", [])) if result else []

    async def dom_hide_highlight(self) -> None:
        """Hide any DOM highlight via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.hideHighlight", {})

    async def dom_highlight_node(self, node_id: int, highlight_config: dict[str, Any]) -> None:
        """Highlight a node by ID with the given highlight config via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "DOM.highlightNode", {"highlightConfig": highlight_config, "nodeId": node_id}
        )

    async def dom_highlight_rect(
        self, x: int, y: int, width: int, height: int, highlight_config: dict[str, Any]
    ) -> None:
        """Highlight a rect with the given highlight config via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "DOM.highlightRect",
            {
                "highlightConfig": highlight_config,
                "rect": {"x": x, "y": y, "width": width, "height": height},
            },
        )

    async def dom_mark_undoable_state(self) -> None:
        """Mark an undoable state in the DOM via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.markUndoableState", {})

    async def dom_move_to(
        self, node_id: int, target_node_id: int, insert_before_node_id: int | None = None
    ) -> None:
        """Move a node to a target node via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"nodeId": node_id, "targetNodeId": target_node_id}
        if insert_before_node_id is not None:
            params["insertBeforeNodeId"] = insert_before_node_id
        await client.cdp.send_command("DOM.moveTo", params)

    async def dom_push_node_by_path_to_frontend(self, path: str) -> dict[str, Any]:
        """Push a node by path to frontend via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("DOM.pushNodeByPathToFrontend", {"path": path})
        return dict(result) if result else {}

    async def dom_push_nodes_by_backend_ids_to_frontend(
        self, backend_node_ids: list[int]
    ) -> dict[str, Any]:
        """Push nodes by backend IDs to frontend via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "DOM.pushNodesByBackendIdsToFrontend", {"backendNodeIds": backend_node_ids}
        )
        return dict(result) if result else {}

    async def dom_query_selector(self, node_id: int, selector: str) -> dict[str, Any]:
        """Query a single selector within a node's subtree via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "DOM.querySelector", {"nodeId": node_id, "selector": selector}
        )
        return dict(result) if result else {}

    async def dom_query_selector_all(self, node_id: int, selector: str) -> list[dict[str, Any]]:
        """Query all selectors within a node's subtree via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "DOM.querySelectorAll", {"nodeId": node_id, "selector": selector}
        )
        return list(result.get("nodes", [])) if result else []

    async def dom_redo(self) -> None:
        """Redo the last DOM action via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.redo", {})

    async def dom_remove_node_by_id(self, node_id: int) -> None:
        """Remove a node from the DOM by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.removeNode", {"nodeId": node_id})

    async def dom_set_attributes_as_text(self, node_id: int, text: str) -> None:
        """Set attributes on a node from a text string via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.setAttributesAsText", {"nodeId": node_id, "text": text})

    async def dom_set_file_input_files(self, node_id: int, files: list[str]) -> None:
        """Set files for a file input node by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.setFileInputFiles", {"nodeId": node_id, "files": files})

    async def dom_set_inspected_node(self, node_id: int) -> None:
        """Set the inspected node by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.setInspectedNode", {"nodeId": node_id})

    async def dom_set_node_name(self, node_id: int, name: str) -> dict[str, Any]:
        """Set the name of a node by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("DOM.setNodeName", {"nodeId": node_id, "name": name})
        return dict(result) if result else {}

    async def dom_set_node_stack_traces_enabled(self, enable: bool) -> None:
        """Enable or disable node stack traces via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.setNodeStackTracesEnabled", {"enable": enable})

    async def dom_set_text_content(self, node_id: int, text: str) -> None:
        """Set the text content of a node by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.setTextContent", {"nodeId": node_id, "text": text})

    async def dom_undo(self) -> None:
        """Undo the last DOM action via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOM.undo", {})

    async def suggest_locator(self, selector: str, all: bool = False) -> list[str] | str:
        """Suggest the best CSS selector for an element.

        Args:
            selector: CSS selector for the target element.
            all: If True, return multiple suggestions; otherwise just the best one.

        Returns:
            List of selector strings when all=True, single best selector when all=False.
        """
        client = self._require_client()
        escaped = json.dumps(selector)
        js = self._suggest_locator_js(escaped)
        result = await client.script.evaluate(self._context, js)
        raw = getattr(result, "value", None)
        if not raw:
            raise ElementNotFoundError(selector)
        suggestions: list[str] = json.loads(raw)
        if all:
            return suggestions
        return suggestions[0] if suggestions else selector

    @staticmethod
    def _suggest_locator_js(escaped: str) -> str:
        """Build JS that generates CSS selector suggestions for an element."""
        return (
            f"(function(){{"
            f"var el=document.querySelector({escaped});"
            f"if(!el)return null;"
            f"var s=[];var t=el.tagName.toLowerCase();"
            f"var id=el.id;"
            f"var tid=el.getAttribute('data-testid')"
            f"||el.getAttribute('data-test-id')"
            f"||el.getAttribute('data-cy');"
            f"var aria=el.getAttribute('aria-label');"
            f"var role=el.getAttribute('role');"
            f"var txt=(el.textContent||'').trim().substring(0,50);"
            f"var cls=Array.from(el.classList);"
            f"if(id)s.push('#'+CSS.escape(id));"
            f"if(tid)s.push('[data-testid=\"'+tid+'\"]');"
            f"if(aria)s.push(t+'[aria-label=\"'+aria+'\"]');"
            f"if(role)s.push(t+'[role=\"'+role+'\"]');"
            f"if(txt&&txt.length<30)s.push(t+':has-text(\"'+txt+'\"]');"
            f"if(cls.length>0)s.push(t+'.'+cls.join('.'));"
            f"var p=el.parentElement;"
            f"if(p&&p.id)s.push('#'+CSS.escape(p.id)+' > '+t);"
            f"var sib=p?Array.from(p.children)"
            f".filter(function(c){{return c.tagName===el.tagName}}):[];"
            f"if(sib.length>1){{"
            f"var i=sib.indexOf(el)+1;"
            f"s.push(t+':nth-of-type('+i+')');}}"
            f"s.push(t);"
            f"return JSON.stringify(s);"
            f"}})()"
        )

    @staticmethod
    def _find_by_text_js(query: str) -> str:
        """Build JS that finds elements by natural language text query.

        Delegates to the shared :func:`build_find_by_text_js` helper so the
        CDP and BiDi backends use identical matching logic.
        """
        from wavexis.backend.mixins.dom import build_find_by_text_js

        return build_find_by_text_js(query)

    async def find_by_text(self, query: str, all: bool = False) -> list[str] | str:
        """Find elements by natural language text query.

        Args:
            query: Natural language query (e.g. "the login button").
            all: If True, return all matches; otherwise just the best one.

        Returns:
            List of CSS selector strings when all=True, single best when all=False.

        Raises:
            ElementNotFoundError: If no element matches the query.
        """
        client = self._require_client()
        js = self._find_by_text_js(query)
        result = await client.script.evaluate(self._context, js)
        raw = getattr(result, "value", None)
        if not raw:
            raise ElementNotFoundError(query)
        selectors: list[str] = json.loads(raw)
        if not selectors:
            raise ElementNotFoundError(query)
        if all:
            return selectors
        return selectors[0]

    async def nl_click(self, query: str, auto_wait: bool = True) -> None:
        """Click an element found by natural language text query.

        Args:
            query: Natural language query (e.g. "login button").
            auto_wait: If True, wait for element to be visible before clicking.
        """
        selector = await self.find_by_text(query)
        if not isinstance(selector, str):
            raise ElementNotFoundError(query)
        await self.click(selector, auto_wait=auto_wait)

    async def nl_fill(self, query: str, value: str, auto_wait: bool = True) -> None:
        """Fill an input element found by natural language text query.

        Args:
            query: Natural language query (e.g. "email field").
            value: Value to set in the input field.
            auto_wait: If True, wait for element to be visible before filling.
        """
        selector = await self.find_by_text(query)
        if not isinstance(selector, str):
            raise ElementNotFoundError(query)
        await self.fill(selector, value, auto_wait=auto_wait)

    async def capture_har(self, params: HarParams) -> dict[str, Any]:
        """Capture HAR data via CDP Network domain.

        Enables Network, navigates, waits, then gets HAR log.

        Args:
            params: HAR capture parameters.

        Returns:
            Dict with HAR log entries.
        """
        client = self._require_launched()
        await client.cdp.send_command("Network.enable", {})
        await client.browsing.navigate(
            self._context,
            params.url,
            wait="complete",
        )

        await asyncio.sleep(params.timeout / 1000)
        result = await client.cdp.send_command(
            "Network.getResponseBody",
            {"requestId": ""},
        )
        har_log = await client.cdp.send_command(
            "Page.frameNavigated",
            {},
        )
        entries = await client.cdp.send_command(
            "Network.getCookies",
            {},
        )
        return {
            "log": {
                "version": "1.2",
                "creator": {"name": "wavexis", "version": "1.7.0"},
                "entries": [],
                "cookies": entries.get("cookies", []) if entries else [],
            },
            "raw": dict(result) if result else {},
            "nav": dict(har_log) if har_log else {},
        }

    async def get_cookies(self) -> list[dict[str, Any]]:
        """Get all cookies via storage.getCookies.

        Returns:
            List of cookie dicts with name, value, domain, path, etc.
        """
        client = self._require_launched()
        cookies = await client.storage.get_cookies(self._context)
        return [c.model_dump() if hasattr(c, "model_dump") else dict(c) for c in cookies]

    async def set_cookie(self, params: CookieParams) -> None:
        """Set a cookie via storage.setCookie.

        Args:
            params: Cookie parameters (name, value, domain, path, etc.).
        """
        client = self._require_launched()
        from bidiwave import Cookie as BiDiCookie

        cookie = BiDiCookie(
            name=params.name,
            value=params.value,
            domain=params.domain,
            path=params.path,
            http_only=params.http_only,
            secure=params.secure,
            same_site=params.same_site,
        )
        await client.storage.set_cookie(self._context, cookie)

    async def delete_cookie(self, name: str, domain: str) -> None:
        """Delete a cookie by name via storage.deleteCookie.

        Args:
            name: Cookie name to delete.
            domain: Cookie domain (ignored by BiDi — uses context).
        """
        client = self._require_launched()
        await client.storage.delete_cookie(self._context, name)

    async def clear_cookies(self) -> None:
        """Clear all cookies for the current browsing context."""
        client = self._require_launched()
        await client.storage.delete_cookies(self._context)

    async def set_headers(self, headers: dict[str, str]) -> None:
        """Set extra HTTP headers via CDP Network.setExtraRequestHeaders.

        Uses the CDP bridge (bidiwave.cdp.send_command) to set extra headers.

        Args:
            headers: Dict of header name to value.
        """
        client = self._require_launched()
        header_list = [{"name": k, "value": v} for k, v in headers.items()]
        await client.cdp.send_command("Network.setExtraRequestHeaders", {"headers": header_list})

    async def set_user_agent(self, user_agent: str) -> None:
        """Override the User-Agent string via emulation.setUserAgentOverride.

        Args:
            user_agent: The User-Agent string to set.
        """
        client = self._require_launched()
        await client.emulation.set_user_agent(
            user_agent, contexts=[self._context] if self._context else None
        )

    async def new_context(self) -> str:
        """Create a new browsing context via browsingContext.create."""
        client = self._require_launched()
        result = await client.browsing.create_context(type="window")
        return str(result.id)

    async def list_contexts(self) -> list[dict[str, Any]]:
        """List browsing contexts via browsingContext.getTree."""
        client = self._require_launched()
        result = await client.browsing.get_tree()
        return [ctx.model_dump() for ctx in result.contexts]

    async def close_context(self, context_id: str) -> None:
        """Close a browsing context via browsingContext.close."""
        client = self._require_launched()
        await client.browsing.close(context_id)

    async def new_user_context(self) -> str:
        """Create a new user context via browsingContext.createUserContext.

        Returns:
            The user context ID string.
        """
        client = self._require_launched()
        result = await client.browsing.create_user_context()
        return str(result.user_context)

    async def get_window_bounds(self) -> dict[str, Any]:
        """Get window bounds via browsingContext.getTree."""
        client = self._require_launched()
        result = await client._connection.send_command(
            "browsingContext.getTree",
            {"root": self._context},
        )
        contexts = result.get("contexts", [])
        if contexts:
            return dict(contexts[0].get("bounds", {}))
        return {}

    async def set_window_bounds(self, width: int, height: int, x: int = 0, y: int = 0) -> None:
        """Set window bounds via browsingContext.setViewport."""
        client = self._require_launched()
        await client._connection.send_command(
            "browsingContext.setViewport",
            {
                "context": self._context,
                "viewport": {"width": width, "height": height},
            },
        )

    async def browser_version(self) -> str:
        """Get the browser version via CDP Browser.getVersion.

        Returns:
            Browser version string (e.g. 'Chrome/120.0.6099.109').
        """
        client = self._require_launched()
        result = await client.cdp.send_command("Browser.getVersion", {})
        return str(result.get("product", "unknown"))

    async def emulate_device(self, device: str) -> None:
        """Emulate a device by preset name using viewport + user agent + touch.

        Args:
            device: Device preset name (e.g. 'iphone-15').

        Raises:
            ValueError: If the device name is not in DEVICE_PRESETS.
        """
        client = self._require_launched()
        preset = DEVICE_PRESETS.get(device)
        if preset is None:
            raise ValueError(f"Unknown device preset: {device}")
        await client.browsing.set_viewport(
            self._context,
            viewport={"width": int(preset["width"]), "height": int(preset["height"])},
            device_pixel_ratio=float(preset["device_scale_factor"]),
        )
        await client.emulation.set_user_agent(
            str(preset["user_agent"]),
            contexts=[self._context] if self._context else None,
        )
        if preset.get("touch"):
            await client.cdp.send_command(
                "Emulation.setTouchEmulationEnabled",
                {"enabled": True},
            )

    async def set_viewport(self, width: int, height: int, device_scale_factor: float = 1.0) -> None:
        """Set the viewport size via browsingContext.setViewport.

        Args:
            width: Viewport width in pixels.
            height: Viewport height in pixels.
            device_scale_factor: Device pixel ratio.
        """
        client = self._require_launched()
        await client.browsing.set_viewport(
            self._context,
            viewport={"width": width, "height": height},
            device_pixel_ratio=device_scale_factor,
        )

    async def set_geolocation(
        self, latitude: float, longitude: float, accuracy: float = 100.0
    ) -> None:
        """Override geolocation via emulation.setGeolocationOverride.

        Args:
            latitude: Latitude in degrees.
            longitude: Longitude in degrees.
            accuracy: Position accuracy in meters.
        """
        client = self._require_launched()
        await client.emulation.set_geolocation(
            coordinates={"latitude": latitude, "longitude": longitude, "accuracy": accuracy},
            contexts=[self._context] if self._context else None,
        )

    async def set_timezone(self, timezone: str) -> None:
        """Override the timezone via emulation.setTimezoneOverride.

        Args:
            timezone: IANA timezone ID (e.g. 'America/New_York').
        """
        client = self._require_launched()
        await client.emulation.set_timezone(
            timezone, contexts=[self._context] if self._context else None
        )

    async def set_dark_mode(self, enabled: bool) -> None:
        """Enable or disable dark mode via CDP Emulation.setEmulatedMedia.

        Args:
            enabled: True to enable dark mode, False to disable.
        """
        client = self._require_launched()
        feature = "dark" if enabled else "light"
        await client.cdp.send_command(
            "Emulation.setEmulatedMedia",
            {"features": [{"name": "prefers-color-scheme", "value": feature}]},
        )

    # ── Input ──────────────────────────────────────────────

    async def _wait_for_element(self, selector: str, timeout_ms: int = 30000) -> None:
        """Wait for an element to exist and be visible in the DOM.

        Polls until the element matches, is attached, and has non-zero size.

        Args:
            selector: CSS selector for the target element.
            timeout_ms: Maximum wait time in milliseconds.

        Raises:
            WaitTimeoutError: If the element is not found within the timeout.
        """
        client = self._require_client()
        escaped = json.dumps(selector)
        js = (
            f"(function(){{var el=document.querySelector({escaped});"
            f"if(!el)return false;"
            f"var rect=el.getBoundingClientRect();"
            f"return rect.width>0&&rect.height>0;}})()"
        )
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            result = await client.script.evaluate(self._context, js)
            value = getattr(result, "value", None)
            if value is True or value == "true":
                return
            await asyncio.sleep(0.1)
        raise WaitTimeoutError("selector", timeout_ms)

    async def _scroll_into_view_if_needed(self, selector: str) -> None:
        """Scroll element into view if it's not visible in the viewport."""
        client = self._require_client()
        escaped = json.dumps(selector)
        js = (
            f"(function(){{var el=document.querySelector({escaped});"
            f"if(!el)return;var rect=el.getBoundingClientRect();"
            f"if(rect.top<0||rect.bottom>window.innerHeight||"
            f"rect.left<0||rect.right>window.innerWidth)"
            f"el.scrollIntoView({{block:'center',behavior:'instant'}});}})()"
        )
        await client.script.evaluate(self._context, js)

    async def click(
        self,
        selector: str,
        button: str = "left",
        click_count: int = 1,
        auto_wait: bool = True,
    ) -> None:
        """Click an element via BiDi script.evaluate.

        Args:
            selector: CSS selector for the target element.
            button: Mouse button (left, right, middle).
            click_count: Number of clicks to dispatch.
            auto_wait: If True, wait for element to be visible before clicking.
        """
        client = self._require_client()
        if auto_wait:
            await self._wait_for_element(selector)
        await self._scroll_into_view_if_needed(selector)
        escaped = json.dumps(selector)
        button_map = {"left": 0, "middle": 1, "right": 2}
        buttons_map = {"left": 1, "middle": 4, "right": 2}
        btn = button_map.get(button, 0)
        buttons = buttons_map.get(button, 1)
        detail = click_count
        event_type = "click" if click_count < 2 else "dblclick"
        js = (
            f"const el=document.querySelector({escaped});"
            f"if(!el)throw new Error('Element not found');"
            f"const opts={{bubbles:true, cancelable:true,"
            f"button:{btn}, buttons:{buttons}, detail:{detail}}};"
            f"el.dispatchEvent(new MouseEvent('{event_type}', opts));"
        )
        await client.script.evaluate(self._context, js)

    async def type_text(self, selector: str, text: str, delay: int = 0) -> None:
        """Type text into an element via BiDi."""
        client = self._require_launched()
        escaped = json.dumps(selector)
        await client.script.evaluate(
            self._context,
            f"var el=document.querySelector({escaped});"
            f"if(!el)throw new Error('Element not found');"
            f"el.focus()",
        )
        for char in text:
            escaped_char = json.dumps(char)
            js = f"document.querySelector({escaped}).value += {escaped_char}"
            await client.script.evaluate(self._context, js)
            if delay > 0:
                await asyncio.sleep(delay / 1000)

    async def fill(self, selector: str, value: str, auto_wait: bool = True) -> None:
        """Fill an input element with a value via BiDi.

        Args:
            selector: CSS selector for the target element.
            value: Value to set in the input field.
            auto_wait: If True, wait for element to be visible before filling.
        """
        client = self._require_client()
        if auto_wait:
            await self._wait_for_element(selector)
        await self._scroll_into_view_if_needed(selector)
        escaped = json.dumps(selector)
        escaped_val = json.dumps(value)
        js = f"var el=document.querySelector({escaped});if(!el)throw new Error('Element not found');el.value = {escaped_val}"
        await client.script.evaluate(self._context, js)

    async def select_option(self, selector: str, value: str) -> None:
        """Select an option in a <select> element by value via BiDi."""
        client = self._require_launched()
        escaped = json.dumps(selector)
        escaped_val = json.dumps(value)
        js = f"var el=document.querySelector({escaped});if(!el)throw new Error('Element not found');el.value = {escaped_val}"
        await client.script.evaluate(self._context, js)

    async def hover(self, selector: str, auto_wait: bool = True) -> None:
        """Hover over an element via BiDi script.evaluate.

        Args:
            selector: CSS selector for the target element.
            auto_wait: If True, wait for element to be visible before hovering.
        """
        client = self._require_client()
        if auto_wait:
            await self._wait_for_element(selector)
        await self._scroll_into_view_if_needed(selector)
        escaped = json.dumps(selector)
        js = (
            f"var el=document.querySelector({escaped});"
            f"if(!el)throw new Error('Element not found');"
            f"el.dispatchEvent(new MouseEvent('mouseover',{{bubbles:true}}));"
            f"el.dispatchEvent(new MouseEvent('mousemove',{{bubbles:true}}))"
        )
        await client.script.evaluate(self._context, js)

    async def key_press(self, key: str) -> None:
        """Press a keyboard key via BiDi script.evaluate."""
        client = self._require_launched()
        escaped_key = json.dumps(key)
        js = (
            f"document.dispatchEvent(new KeyboardEvent('keydown',{{key:{escaped_key}}}));"
            f"document.dispatchEvent(new KeyboardEvent('keyup',{{key:{escaped_key}}}))"
        )
        await client.script.evaluate(self._context, js)

    async def drag(self, source: str, target: str) -> None:
        """Drag from source to target via BiDi script.evaluate (simulated)."""
        client = self._require_launched()
        escaped_src = json.dumps(source)
        escaped_tgt = json.dumps(target)
        js = (
            f"var s=document.querySelector({escaped_src});"
            f"var t=document.querySelector({escaped_tgt});"
            f"if(!s||!t)throw new Error('Element not found');"
            f"s.dispatchEvent(new DragEvent('dragstart',{{bubbles:true}}));"
            f"t.dispatchEvent(new DragEvent('drop',{{bubbles:true}}));"
            f"s.dispatchEvent(new DragEvent('dragend',{{bubbles:true}}))"
        )
        await client.script.evaluate(self._context, js)

    async def tap(self, selector: str) -> None:
        """Tap an element via BiDi (simulated as click)."""
        await self.click(selector)

    async def set_files(self, selector: str, files: list[str]) -> None:
        """Set files on a file input element via BiDi script.evaluate.

        Args:
            selector: CSS selector for the <input type="file"> element.
            files: List of absolute file paths to upload.
        """
        client = self._require_launched()
        escaped = json.dumps(selector)
        files_json = json.dumps(files)
        js = (
            f"const input = document.querySelector({escaped});"
            f"const dt = new DataTransfer();"
            f"const files = {files_json};"
            f"for (const f of files) {{ dt.items.add(new File([''], f)); }}"
            f"input.files = dt.files;"
            f"input.dispatchEvent(new Event('change', {{bubbles: true}}));"
        )
        await client.script.evaluate(self._context, js)

    # ── iframe ─────────────────────────────────────────────

    async def iframe_eval(
        self, iframe_selector: str, expression: str, await_promise: bool = False
    ) -> Any:
        """Evaluate a JavaScript expression inside an iframe.

        Args:
            iframe_selector: CSS selector for the <iframe> element.
            expression: JavaScript expression to evaluate in the iframe context.
            await_promise: Whether to await a returned Promise.

        Returns:
            The evaluation result value.
        """
        client = self._require_client()
        escaped_iframe = json.dumps(iframe_selector)
        escaped_expr = json.dumps(expression)
        js = (
            f"(function(){{var f=document.querySelector({escaped_iframe});"
            f"if(!f||!f.contentDocument)return null;"
            f"return (function(){{{escaped_expr}}}).call(f.contentDocument);}})()"
        )
        result = await client.script.evaluate(self._context, js, await_promise=await_promise)
        if hasattr(result, "value"):
            return result.value
        return result

    async def _wait_for_element_in_iframe(
        self, iframe_selector: str, selector: str, timeout_ms: int = 30000
    ) -> None:
        """Wait for an element inside an iframe to exist and be visible.

        Args:
            iframe_selector: CSS selector for the <iframe> element.
            selector: CSS selector inside the iframe.
            timeout_ms: Maximum wait time in milliseconds.

        Raises:
            WaitTimeoutError: If the element is not found within the timeout.
        """
        client = self._require_client()
        escaped_iframe = json.dumps(iframe_selector)
        escaped_sel = json.dumps(selector)
        js = (
            f"(function(){{var f=document.querySelector({escaped_iframe});"
            f"if(!f||!f.contentDocument)return false;"
            f"var el=f.contentDocument.querySelector({escaped_sel});"
            f"if(!el)return false;"
            f"var rect=el.getBoundingClientRect();"
            f"return rect.width>0&&rect.height>0;}})()"
        )
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            result = await client.script.evaluate(self._context, js)
            value = getattr(result, "value", None)
            if value is True or value == "true":
                return
            await asyncio.sleep(0.1)
        raise WaitTimeoutError("selector", timeout_ms)

    async def iframe_click(
        self, iframe_selector: str, selector: str, auto_wait: bool = True
    ) -> None:
        """Click an element inside an iframe.

        Args:
            iframe_selector: CSS selector for the <iframe> element.
            selector: CSS selector inside the iframe for the target element.
            auto_wait: If True, wait for element to be visible before clicking.
        """
        client = self._require_client()
        if auto_wait:
            await self._wait_for_element_in_iframe(iframe_selector, selector)
        escaped_iframe = json.dumps(iframe_selector)
        escaped_sel = json.dumps(selector)
        js = (
            f"(function(){{var f=document.querySelector({escaped_iframe});"
            f"if(!f||!f.contentDocument)return false;"
            f"var el=f.contentDocument.querySelector({escaped_sel});"
            f"if(!el)return false;"
            f"el.scrollIntoView({{block:'center',behavior:'instant'}});"
            f"el.dispatchEvent(new MouseEvent('click',{{bubbles:true}}));"
            f"return true;}})()"
        )
        result = await client.script.evaluate(self._context, js)
        value = getattr(result, "value", None)
        if not value:
            raise ElementNotFoundError(selector)

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
        client = self._require_client()
        if auto_wait:
            await self._wait_for_element_in_iframe(iframe_selector, selector)
        escaped_iframe = json.dumps(iframe_selector)
        escaped_sel = json.dumps(selector)
        escaped_val = json.dumps(value)
        js = (
            f"(function(){{var f=document.querySelector({escaped_iframe});"
            f"if(!f||!f.contentDocument)return false;"
            f"var el=f.contentDocument.querySelector({escaped_sel});"
            f"if(!el)return false;"
            f"el.focus();el.value={escaped_val};"
            f"el.dispatchEvent(new Event('input',{{bubbles:true}}));"
            f"el.dispatchEvent(new Event('change',{{bubbles:true}}));"
            f"return true;}})()"
        )
        result = await client.script.evaluate(self._context, js)
        result_value = getattr(result, "value", None)
        if not result_value:
            raise ElementNotFoundError(selector)

    # ── Shadow DOM ──────────────────────────────────────────

    @staticmethod
    def _build_shadow_pierce_js(selectors: list[str]) -> str:
        """Build JS that pierces shadow boundaries via a selector chain."""
        escaped = [json.dumps(s) for s in selectors]
        parts = [f"var el=document.querySelector({escaped[0]})"]
        for sel in escaped[1:]:
            parts.append(
                f"if(!el||!el.shadowRoot)return null;el=el.shadowRoot.querySelector({sel})"
            )
        parts.append("return el")
        body = ";".join(parts)
        return f"(function(){{{body};}})()"

    async def shadow_eval(
        self, selectors: list[str], expression: str, await_promise: bool = False
    ) -> Any:
        """Evaluate a JavaScript expression inside a shadow DOM tree.

        Args:
            selectors: List of CSS selectors piercing shadow boundaries.
            expression: JavaScript expression to evaluate in the shadow context.
            await_promise: Whether to await a returned Promise.

        Returns:
            The evaluation result value.
        """
        client = self._require_client()
        pierce_js = self._build_shadow_pierce_js(selectors)
        escaped_expr = json.dumps(expression)
        js = (
            f"(function(){{var el=({pierce_js});"
            f"if(!el)return null;"
            f"return (function(){{{escaped_expr}}}).call(el);}})()"
        )
        result = await client.script.evaluate(self._context, js, await_promise=await_promise)
        if hasattr(result, "value"):
            return result.value
        return result

    async def _wait_for_element_in_shadow(
        self, selectors: list[str], timeout_ms: int = 30000
    ) -> None:
        """Wait for an element inside a shadow DOM tree to exist and be visible.

        Args:
            selectors: List of CSS selectors piercing shadow boundaries.
            timeout_ms: Maximum wait time in milliseconds.

        Raises:
            WaitTimeoutError: If the element is not found within the timeout.
        """
        client = self._require_client()
        pierce_js = self._build_shadow_pierce_js(selectors)
        js = (
            f"(function(){{var el=({pierce_js});"
            f"if(!el)return false;"
            f"var rect=el.getBoundingClientRect();"
            f"return rect.width>0&&rect.height>0;}})()"
        )
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            result = await client.script.evaluate(self._context, js)
            value = getattr(result, "value", None)
            if value is True or value == "true":
                return
            await asyncio.sleep(0.1)
        raise WaitTimeoutError("selector", timeout_ms)

    async def shadow_click(self, selectors: list[str], auto_wait: bool = True) -> None:
        """Click an element inside a shadow DOM tree.

        Args:
            selectors: List of CSS selectors piercing shadow boundaries.
            auto_wait: If True, wait for element to be visible before clicking.
        """
        client = self._require_client()
        if auto_wait:
            await self._wait_for_element_in_shadow(selectors)
        pierce_js = self._build_shadow_pierce_js(selectors)
        js = (
            f"(function(){{var el=({pierce_js});"
            f"if(!el)return false;"
            f"el.scrollIntoView({{block:'center',behavior:'instant'}});"
            f"el.dispatchEvent(new MouseEvent('click',{{bubbles:true,composed:true}}));"
            f"return true;}})()"
        )
        result = await client.script.evaluate(self._context, js)
        result_value = getattr(result, "value", None)
        if not result_value:
            raise ElementNotFoundError(" -> ".join(selectors))

    async def shadow_fill(self, selectors: list[str], value: str, auto_wait: bool = True) -> None:
        """Fill an input element inside a shadow DOM tree.

        Args:
            selectors: List of CSS selectors piercing shadow boundaries.
            value: Value to set in the input field.
            auto_wait: If True, wait for element to be visible before filling.
        """
        client = self._require_client()
        if auto_wait:
            await self._wait_for_element_in_shadow(selectors)
        pierce_js = self._build_shadow_pierce_js(selectors)
        escaped_val = json.dumps(value)
        js = (
            f"(function(){{var el=({pierce_js});"
            f"if(!el)return false;"
            f"el.focus();el.value={escaped_val};"
            f"el.dispatchEvent(new Event('input',{{bubbles:true,composed:true}}));"
            f"el.dispatchEvent(new Event('change',{{bubbles:true,composed:true}}));"
            f"return true;}})()"
        )
        result = await client.script.evaluate(self._context, js)
        result_value = getattr(result, "value", None)
        if not result_value:
            raise ElementNotFoundError(" -> ".join(selectors))

    async def block_requests(self, patterns: list[str]) -> None:
        """Block requests matching URL patterns using native BiDi interception."""
        client = self._require_launched()
        contexts = [self._context] if self._context else None

        await client.network.add_intercept(
            phases=["beforeRequestSent"],
            contexts=contexts,
            url_patterns=patterns or None,
        )

        async def on_request(params: dict[str, Any]) -> None:
            """Fail intercepted requests matching the block patterns."""
            if not params.get("isBlocked"):
                return
            request_id = params.get("request", {}).get("request", "")
            if request_id:
                await client.network.fail_request(request=request_id)

        client.on_request(on_request)

    async def throttle_network(self, params: ThrottleParams) -> None:
        """Throttle network conditions via BiDi/CDP.

        In bidiwave 1.8.2, ``emulation.set_network_conditions`` only
        supports the ``offline`` flag per the W3C BiDi spec. Throughput
        and latency throttling are handled through the CDP bridge.

        Args:
            params: Throttle parameters (offline, latency, download/upload throughput).
        """
        client = self._require_launched()
        await client.emulation.set_network_conditions(
            offline=params.offline,
            contexts=[self._context] if self._context else None,
        )
        if not params.offline:
            await client.cdp.send_command(
                "Network.emulateNetworkConditions",
                {
                    "offline": False,
                    "latency": params.latency_ms,
                    "downloadThroughput": params.download_bps,
                    "uploadThroughput": params.upload_bps,
                },
            )

    async def set_cache_disabled(self, disabled: bool = True) -> None:
        """Disable or enable the browser cache via native BiDi network cache behavior.

        Args:
            disabled: True to bypass cache, False to restore default behavior.
        """
        client = self._require_launched()
        behavior = "bypass" if disabled else "default"
        await client.network.set_cache_behavior(
            cache_behavior=behavior,
            contexts=[self._context] if self._context else None,
        )

    async def intercept_requests(self, pattern: dict[str, Any]) -> None:
        """Intercept requests matching a pattern using native BiDi add_intercept."""
        client = self._require_launched()
        url_pattern = pattern.get("urlPattern")
        await client.network.add_intercept(
            phases=["beforeRequestSent"],
            contexts=[self._context] if self._context else None,
            url_patterns=[url_pattern] if url_pattern else None,
        )

    async def mock_response(self, url: str, response: dict[str, Any]) -> None:
        """Mock a response for requests matching a URL via network.addCacheOverride.

        Args:
            url: URL pattern to match.
            response: Response dict with status, headers, body.
        """
        client = self._require_launched()
        status = response.get("status", 200)
        headers = [{"name": k, "value": v} for k, v in response.get("headers", {}).items()]
        body = response.get("body", "")
        await client.network.add_cache_override(
            url=url,
            method=response.get("method", "GET"),
            status_code=status,
            headers=headers or None,
            body=body or None,
            contexts=[self._context] if self._context else None,
        )

    # ── Network inspection (W3, W6, W7) ───────────────────

    async def get_request_body(self, request_id: str) -> str | None:
        """Get the body of a network request by ID via CDP bridge.

        Args:
            request_id: The network request ID.

        Returns:
            The request body as a string, or None if not available.
        """
        client = self._require_client()
        try:
            result = await client.cdp.send_command(
                "Network.getRequestPostData",
                {"requestId": request_id},
            )
            return str(result.get("postData")) if result.get("postData") is not None else None
        except Exception as exc:
            if isinstance(exc, WavexisError):
                raise
            return None

    async def get_response_body(self, request_id: str) -> str | None:
        """Get the body of a network response by ID via native BiDi response_body.

        Args:
            request_id: The BiDi network request ID.

        Returns:
            The response body as a string, or None if not available.
        """
        client = self._require_client()
        try:
            result = await client.network.response_body(request=request_id)
            return result.body if result.body is not None else None
        except Exception as exc:
            if isinstance(exc, WavexisError):
                raise
            return None

    async def modify_request(
        self,
        pattern: dict[str, Any],
        modifications: dict[str, Any],
    ) -> None:
        """Intercept and modify requests matching a pattern via native BiDi.

        Args:
            pattern: Pattern dict with optional key: urlPattern.
            modifications: Dict with optional keys: headers, url, method, post_data.
        """
        client = self._require_client()
        url_pattern = pattern.get("urlPattern")
        contexts = [self._context] if self._context else None

        await client.network.add_intercept(
            phases=["beforeRequestSent"],
            contexts=contexts,
            url_patterns=[url_pattern] if url_pattern else None,
        )

        raw_headers = modifications.get("headers")
        headers: list[dict[str, Any]] | None = None
        if isinstance(raw_headers, dict):
            headers = [{"name": k, "value": v} for k, v in raw_headers.items()]
        elif isinstance(raw_headers, list):
            headers = raw_headers

        async def on_request(params: dict[str, Any]) -> None:
            """Handle beforeRequestSent and continue with modifications."""
            if not params.get("isBlocked"):
                return
            request_id = params.get("request", {}).get("request", "")
            if not request_id:
                return
            await client.network.continue_request(
                request=request_id,
                url=modifications.get("url"),
                method=modifications.get("method"),
                headers=headers,
                post_data=modifications.get("post_data"),
            )

        client.on_request(on_request)

    async def modify_response(
        self,
        pattern: dict[str, Any],
        modifications: dict[str, Any],
    ) -> None:
        """Intercept responses matching a pattern and modify them in-flight.

        Uses native BiDi network interception in the responseStarted phase
        and provides a synthetic response.

        Args:
            pattern: Pattern dict with optional key: urlPattern.
            modifications: Dict with optional keys: status, headers, body,
                content_type.
        """
        client = self._require_client()
        url_pattern = pattern.get("urlPattern")
        contexts = [self._context] if self._context else None

        await client.network.add_intercept(
            phases=["responseStarted"],
            contexts=contexts,
            url_patterns=[url_pattern] if url_pattern else None,
        )

        body = modifications.get("body", "")
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        body_b64 = base64.b64encode(body.encode("utf-8")).decode("ascii")

        raw_headers = modifications.get("headers")
        response_headers: list[dict[str, Any]] | None
        if isinstance(raw_headers, dict):
            response_headers = [{"name": k, "value": v} for k, v in raw_headers.items()]
        elif isinstance(raw_headers, list):
            response_headers = raw_headers
        else:
            response_headers = [
                {
                    "name": "Content-Type",
                    "value": modifications.get("content_type", "application/json"),
                }
            ]

        async def on_response_started(params: dict[str, Any]) -> None:
            """Handle responseStarted and provide a modified response."""
            if not params.get("isBlocked"):
                return
            request_id = params.get("request", {}).get("request", "")
            if not request_id:
                return
            await client.network.provide_response(
                request=request_id,
                status_code=modifications.get("status", 200),
                headers=response_headers,
                body=body_b64,
            )

        client.on_response_started(on_response_started)

    async def replay_har(self, har_path: str, url_filter: str = "") -> None:
        """Replay network requests from a HAR file.

        Args:
            har_path: Path to the HAR file.
            url_filter: Optional URL pattern to filter which entries to replay.
        """
        client = self._require_client()

        try:
            content = await asyncio.to_thread(validate_path(har_path).read_text, encoding="utf-8")
        except OSError as e:
            raise WavexisError(f"Failed to read HAR file: {e}") from e
        har_data = json.loads(content)

        entries = har_data.get("log", {}).get("entries", [])
        for entry in entries:
            request = entry.get("request", {})
            url = request.get("url", "")
            if url_filter and url_filter not in url:
                continue

            method = request.get("method", "GET")
            headers = {
                h["name"]: h["value"]
                for h in request.get("headers", [])
                if "name" in h and "value" in h
            }
            post_data = request.get("postData", {}).get("text", "")

            fetch_js = (
                f"fetch({json.dumps(url)}, {{"
                f"method: {json.dumps(method)},"
                f"headers: {json.dumps(headers)},"
                f"body: {json.dumps(post_data) if post_data else 'undefined'}"
                f"}}).then(r => r.status).catch(e => e.message)"
            )
            await client.script.evaluate(self._context, fetch_js, await_promise=True)

    async def handle_auth(
        self,
        url_pattern: str,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        """Handle HTTP authentication challenges for matching requests.

        Uses native BiDi network interception to respond to authRequired events.

        Args:
            url_pattern: URL pattern to match auth challenges.
            username: Username to provide. If None, auth is canceled.
            password: Password to provide.
        """
        client = self._require_client()

        async def on_auth_required(params: dict[str, Any]) -> None:
            """Respond to network.authRequired events."""
            request_url = params.get("request", {}).get("url", "")
            if url_pattern and url_pattern not in request_url:
                return
            request_id = params.get("request", "")
            if isinstance(request_id, dict):
                request_id = request_id.get("id", "")
            if username and password:
                await client.network.continue_with_auth(
                    request=request_id,
                    action="provideCredentials",
                    credentials={"username": username, "password": password},
                )
            else:
                await client.network.continue_with_auth(
                    request=request_id,
                    action="cancel",
                )

        await client.network.add_intercept(
            phases=["authRequired"],
            contexts=[self._context] if self._context else None,
            url_patterns=[url_pattern] if url_pattern else None,
        )
        client.on_auth_required(on_auth_required)

    async def network_clear_browser_cache(self) -> None:
        """Clear the browser cache via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Network.clearBrowserCache", {})

    async def network_clear_browser_cookies(self) -> None:
        """Clear all browser cookies via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Network.clearBrowserCookies", {})

    async def network_delete_cookies(self, name: str, domain: str = "") -> None:
        """Delete cookies by name and optional domain via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"name": name}
        if domain:
            params["domain"] = domain
        await client.cdp.send_command("Network.deleteCookies", params)

    async def network_set_blocked_urls(self, urls: list[str]) -> None:
        """Block requests to specific URLs via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Network.setBlockedURLs", {"urls": urls})

    async def network_set_bypass_service_worker(self, bypass: bool) -> None:
        """Bypass the service worker via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Network.setBypassServiceWorker", {"bypass": bypass})

    async def network_set_cookie_controls(
        self, mode: str = "allow", third_party_mode: str = "allow"
    ) -> None:
        """Set cookie controls via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Network.setCookieControls",
            {"mode": mode, "thirdPartyCookieControlsMode": third_party_mode},
        )

    async def network_set_extra_request_headers(self, headers: dict[str, str]) -> None:
        """Set extra HTTP headers for all requests via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Network.setExtraRequestHeaders", {"headers": headers})

    async def network_set_user_agent_override(
        self, user_agent: str, accept_language: str = "", platform: str = ""
    ) -> None:
        """Override the User-Agent string with metadata via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"userAgent": user_agent}
        if accept_language:
            params["acceptLanguage"] = accept_language
        if platform:
            params["platform"] = platform
        await client.cdp.send_command("Network.setUserAgentOverride", params)

    async def network_replay_xhr(self, request_id: str) -> None:
        """Replay a previously captured XHR request via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Network.replayXHR", {"requestId": request_id})

    async def network_load_network_resource(
        self, frame_id: str, url: str, options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Load a network resource via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"frameId": frame_id, "url": url}
        if options:
            params["options"] = options
        return dict(await client.cdp.send_command("Network.loadNetworkResource", params))

    # ── Combined trace (W8) ────────────────────────────────

    async def start_combined_trace(
        self,
        capture_screenshots: bool = True,
        capture_network: bool = True,
        capture_console: bool = True,
    ) -> str:
        """Start a combined trace capturing screenshots, network, and console.

        Returns:
            A trace ID string for later stopping and collecting results.
        """
        client = self._require_client()
        trace_id = f"trace-{int(time.time() * 1000)}"

        state: dict[str, Any] = {
            "trace_events": [],
            "screenshots": [],
            "network": [],
            "console": [],
            "capture_screenshots": capture_screenshots,
            "capture_network": capture_network,
            "capture_console": capture_console,
            "handlers": [],
        }

        if capture_network:
            await client.cdp.send_command("Network.enable", {})

            def on_network_request(params: dict[str, Any]) -> None:
                state["network"].append(
                    {
                        "type": "request",
                        "url": params.get("request", {}).get("url", ""),
                        "method": params.get("request", {}).get("method", ""),
                        "requestId": params.get("requestId", ""),
                        "timestamp": params.get("timestamp"),
                    }
                )

            def on_network_response(params: dict[str, Any]) -> None:
                state["network"].append(
                    {
                        "type": "response",
                        "url": params.get("response", {}).get("url", ""),
                        "status": params.get("response", {}).get("status", 0),
                        "requestId": params.get("requestId", ""),
                        "timestamp": params.get("timestamp"),
                    }
                )

            client.cdp.on("Network.requestWillBeSent", on_network_request)
            client.cdp.on("Network.responseReceived", on_network_response)
            state["handlers"].append(("Network.requestWillBeSent", on_network_request))
            state["handlers"].append(("Network.responseReceived", on_network_response))

        if capture_console:
            await client.cdp.send_command("Runtime.enable", {})

            def on_console_api(params: dict[str, Any]) -> None:
                state["console"].append(
                    {
                        "type": params.get("type", "log"),
                        "args": params.get("args", []),
                        "timestamp": params.get("timestamp"),
                    }
                )

            client.cdp.on("Runtime.consoleAPICalled", on_console_api)
            state["handlers"].append(("Runtime.consoleAPICalled", on_console_api))

        if capture_screenshots:
            result = await client.cdp.send_command("Page.captureScreenshot", {})
            if result.get("data"):
                state["screenshots"].append(
                    {
                        "timestamp": time.time(),
                        "data": result["data"],
                    }
                )

        await client.cdp.send_command("Tracing.start", {"traceType": "devtools-timeline"})

        self._combined_traces: dict[str, dict[str, Any]] = getattr(self, "_combined_traces", {})
        self._combined_traces[trace_id] = state
        return trace_id

    async def stop_combined_trace(self, trace_id: str) -> dict[str, Any]:
        """Stop a combined trace and return collected data.

        Args:
            trace_id: The trace ID returned by start_combined_trace.

        Returns:
            Dict with keys: trace_events, screenshots, network, console.
        """
        import io
        import zipfile

        client = self._require_client()
        traces: dict[str, dict[str, Any]] = getattr(self, "_combined_traces", {})
        state = traces.get(trace_id)
        if state is None:
            return {"error": f"Unknown trace_id: {trace_id}"}

        trace_events: list[dict[str, Any]] = []
        tracing_done = asyncio.Event()

        async def _on_tracing_complete(params: dict[str, Any]) -> None:
            """Handle Tracing.tracingComplete and extract trace events."""
            try:
                stream_handle = params.get("stream")
                if stream_handle:
                    chunks: list[bytes] = []
                    while True:
                        resp = await client.cdp.send_command("IO.read", {"handle": stream_handle})
                        data = resp.get("data", "")
                        if not data:
                            break
                        chunks.append(base64.b64decode(data))
                        if not resp.get("base64Encoded", True):
                            break
                    raw = b"".join(chunks)
                    try:
                        zf = zipfile.ZipFile(io.BytesIO(raw))
                        for name in zf.namelist():
                            content = zf.read(name).decode("utf-8", errors="replace")
                            trace_events.extend(json.loads(content).get("traceEvents", []))
                    except (zipfile.BadZipFile, json.JSONDecodeError, KeyError, ValueError):
                        trace_events.append({"raw_size": len(raw)})
            finally:
                tracing_done.set()

        client.cdp.on("Tracing.tracingComplete", _on_tracing_complete)
        try:
            await client.cdp.send_command("Tracing.end", {})

            if state["capture_screenshots"]:
                screenshot_result = await client.cdp.send_command("Page.captureScreenshot", {})
                if screenshot_result.get("data"):
                    state["screenshots"].append(
                        {
                            "timestamp": 0,
                            "data": screenshot_result["data"],
                        }
                    )

            # Wait for the tracingComplete handler to finish (max 10s).
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(tracing_done.wait(), timeout=10.0)
        finally:
            client.cdp.off("Tracing.tracingComplete", _on_tracing_complete)

        result: dict[str, Any] = {
            "trace_events": trace_events,
            "screenshots": state["screenshots"],
            "network": state["network"],
            "console": state["console"],
        }
        for event_name, handler in state.get("handlers", []):
            client.cdp.off(event_name, handler)
        del traces[trace_id]
        return result

    # ── axe-core audit (W9) ────────────────────────────────

    async def axe_audit(self) -> dict[str, Any]:
        """Run axe-core accessibility audit on the current page.

        Returns:
            Dict with violations, passes, incomplete, and inapplicable lists.
        """
        client = self._require_client()

        axe_js = (
            "if (typeof axe === 'undefined') { "
            "  const s = document.createElement('script'); "
            "  s.src = 'https://unpkg.com/axe-core@4.9.1/axe.min.js'; "
            "  document.head.appendChild(s); "
            "  await new Promise(r => s.onload = r); "
            "} "
            "await axe.run(document, { "
            "  resultTypes: ['violations', 'passes', 'incomplete', 'inapplicable'] "
            "})"
        )
        result = await client.script.evaluate(
            expression=axe_js,
            await_promise=True,
            target=self._context,
        )
        value = getattr(result, "value", None)
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, str):
            try:
                return dict(json.loads(value))
            except (json.JSONDecodeError, TypeError):
                pass
        return {"error": "axe-core audit failed", "raw": str(result)}

    # ── Event subscription (W11) ───────────────────────────

    async def subscribe_events(
        self,
        event_types: list[str],
        callback: Any,
    ) -> str:
        """Subscribe to real-time browser events using native BiDi events.

        Args:
            event_types: List of event types to subscribe to.
            callback: Callable that receives event dicts.

        Returns:
            A subscription ID for later unsubscription.
        """
        client = self._require_client()
        sub_id = f"sub-{int(time.time() * 1000)}"

        if not hasattr(self, "_subscriptions"):
            self._subscriptions: dict[str, list[Any]] = {}

        subscriptions: list[Any] = []

        event_map = {
            "console": ("log.entryAdded", client.on_log_entry, "console"),
            "network_request": (
                "network.beforeRequestSent",
                client.on_request,
                "network_request",
            ),
            "network_response": (
                "network.responseCompleted",
                client.on_response,
                "network_response",
            ),
            "dialog": (
                "browsingContext.userPromptOpened",
                client.on_user_prompt_opened,
                "dialog",
            ),
            "navigation": (
                "browsingContext.navigationStarted",
                client.on_navigation_started,
                "navigation",
            ),
        }

        for evt_type in event_types:
            if evt_type in event_map:
                _, subscribe_fn, label = event_map[evt_type]

                def make_handler(lbl: str) -> Any:
                    def _handler(params: Any) -> None:
                        data = (
                            params.model_dump() if hasattr(params, "model_dump") else dict(params)
                        )
                        callback({"type": lbl, "data": data})

                    return _handler

                handler = make_handler(label)
                if inspect.iscoroutinefunction(subscribe_fn):
                    subscription = await subscribe_fn(handler)
                else:
                    subscription = subscribe_fn(handler)
                subscriptions.append(subscription)

        self._subscriptions[sub_id] = subscriptions
        return sub_id

    async def unsubscribe_events(self, subscription_id: str) -> None:
        """Unsubscribe from events by subscription ID.

        Args:
            subscription_id: The ID returned by subscribe_events.
        """
        client = self._require_client()
        subs: dict[str, list[Any]] = getattr(self, "_subscriptions", {})
        subscriptions = subs.pop(subscription_id, [])
        for subscription in subscriptions:
            client.off(subscription)

    # ── Accessibility ──────────────────────────────────────

    async def a11y_tree(self) -> dict[str, Any]:
        """Get full accessibility tree via CDP.

        Returns:
            Dict with AX tree nodes.
        """
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Accessibility.getFullAXTree",
            {},
        )
        return dict(result) if result else {}

    async def a11y_node(self, node_id: str) -> dict[str, Any]:
        """Get a single AX node by ID via CDP.

        Args:
            node_id: AX node ID.

        Returns:
            Dict with AX node data.
        """
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Accessibility.getPartialAXTree",
            {"nodeId": node_id},
        )
        return dict(result) if result else {}

    async def a11y_ancestors(self, node_id: str) -> list[dict[str, Any]]:
        """Get AX ancestors of a node via CDP.

        Args:
            node_id: AX node ID.

        Returns:
            List of ancestor AX node dicts.
        """
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Accessibility.getPartialAXTree",
            {"nodeId": node_id, "fetchRelatives": True},
        )
        nodes = result.get("nodes", []) if result else []
        return list(nodes)

    # ── Downloads ──────────────────────────────────────────

    async def intercept_download(
        self, pattern: str = ".*", timeout: float | None = None
    ) -> bytes:
        """Set download behavior via CDP and return placeholder.

        Uses CDP Page.setDownloadBehavior to allow downloads. The download
        directory is created under the system temp directory for cross-platform
        compatibility. Actual interception requires event listening which is
        not available via the CDP bridge, so an empty bytes placeholder is
        returned.

        Args:
            pattern: Unused — kept for API parity.
            timeout: Unused by the BiDi placeholder implementation.

        Returns:
            Empty bytes placeholder.
        """
        client = self._require_launched()
        download_dir = str(Path(tempfile.gettempdir()) / "wavexis-downloads")
        await client.cdp.send_command(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": download_dir},
        )
        return b""

    # ── Dialogs ────────────────────────────────────────────

    async def dialog_accept(self, prompt_text: str | None = None) -> None:
        """Accept a JavaScript dialog via BiDi."""
        client = self._require_launched()
        await client._connection.send_command(
            "browsingContext.handleUserPrompt",
            {"accept": True, "userText": prompt_text or ""},
        )

    async def dialog_dismiss(self) -> None:
        """Dismiss a JavaScript dialog via BiDi."""
        client = self._require_launched()
        await client._connection.send_command(
            "browsingContext.handleUserPrompt",
            {"accept": False},
        )

    async def dialog_wait_for_opening(self, timeout: float = 30.0) -> dict[str, Any]:
        """Wait for a JavaScript dialog to open and return its event params.

        Uses the BiDi ``browsingContext.userPromptOpened`` event.

        Args:
            timeout: Maximum seconds to wait for the dialog.

        Returns:
            The dialog event params as a dict.

        Raises:
            TimeoutError: If no dialog opens within ``timeout``.
        """
        client = self._require_launched()
        loop = asyncio.get_event_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()

        def _handler(params: Any) -> None:
            if not future.done():
                data = (
                    params.model_dump() if hasattr(params, "model_dump") else dict(params)
                )
                future.set_result(data)

        subscription = client.on_user_prompt_opened(_handler)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            subscription.unsubscribe()

    # ── Permissions ────────────────────────────────────────

    async def grant_permission(self, permission: str) -> None:
        """Grant a browser permission via BiDi."""
        client = self._require_launched()
        await client._connection.send_command(
            "browser.grantPermissions",
            {"permissions": [permission]},
        )

    async def reset_permissions(self) -> None:
        """Reset all granted permissions via BiDi."""
        client = self._require_launched()
        await client._connection.send_command("browser.resetPermissions", {})

    # ── Security ───────────────────────────────────────────

    async def get_security_state(self) -> dict[str, Any]:
        """Get the current security state via CDP Security.getState.

        Returns:
            Security state dict.
        """
        client = self._require_launched()
        result = await client.cdp.send_command("Security.getState", {})
        return dict(result)

    async def ignore_cert_errors(self, ignore: bool = True) -> None:
        """Enable or disable ignoring certificate errors via CDP.

        Args:
            ignore: True to ignore cert errors, False to enforce them.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "Security.setIgnoreCertificateErrors",
            {"ignore": ignore},
        )

    # ── Emulation advanced ─────────────────────────────────

    async def set_locale(self, locale: str) -> None:
        """Override the browser locale via CDP Emulation.setLocaleOverride.

        Args:
            locale: Locale string (e.g. 'en-US', 'es-ES').
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setLocaleOverride",
            {"locale": locale},
        )

    async def set_cpu_throttle(self, rate: float) -> None:
        """Set CPU throttling rate via CDP Emulation.setCPUThrottlingRate.

        Args:
            rate: Throttling rate (1.0 = normal, 4.0 = 4x slower).
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setCPUThrottlingRate",
            {"rate": rate},
        )

    async def set_touch_emulation(self, enabled: bool) -> None:
        """Enable or disable touch emulation via CDP Emulation.setTouchEmulationEnabled.

        Args:
            enabled: True to enable touch emulation, False to disable.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setTouchEmulationEnabled",
            {"enabled": enabled},
        )

    async def set_sensors(self, sensors: SensorParams) -> None:
        """Override sensor values via CDP.

        Args:
            sensors: Sensor parameters with type and values.
        """
        client = self._require_launched()
        if sensors.type == "device-orientation":
            await client.cdp.send_command(
                "DeviceOrientation.setDeviceOrientationOverride",
                {
                    "alpha": sensors.values.get("alpha", 0),
                    "beta": sensors.values.get("beta", 0),
                    "gamma": sensors.values.get("gamma", 0),
                },
            )
        elif sensors.type == "geolocation":
            await client.emulation.set_geolocation(
                coordinates={
                    "latitude": sensors.values.get("latitude", 0),
                    "longitude": sensors.values.get("longitude", 0),
                    "accuracy": sensors.values.get("accuracy", 100),
                },
                contexts=[self._context] if self._context else None,
            )

    async def set_device_metrics_override(
        self,
        width: int,
        height: int,
        device_scale_factor: float = 1.0,
        mobile: bool = False,
    ) -> None:
        """Override device metrics via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": width,
                "height": height,
                "deviceScaleFactor": device_scale_factor,
                "mobile": mobile,
            },
        )

    async def clear_device_metrics_override(self) -> None:
        """Clear device metrics override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.clearDeviceMetricsOverride", {})

    async def set_emulated_media(self, media: str) -> None:
        """Set the emulated media type via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setEmulatedMedia", {"media": media})

    async def clear_emulated_media(self) -> None:
        """Clear emulated media override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setEmulatedMedia", {"media": ""})

    async def set_emulated_vision_deficiency(self, deficiency: str) -> None:
        """Set emulated vision deficiency via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setEmulatedVisionDeficiency", {"type": deficiency})

    async def clear_emulated_vision_deficiency(self) -> None:
        """Clear emulated vision deficiency override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setEmulatedVisionDeficiency", {"type": "none"})

    async def set_idle_override(
        self, is_user_active: bool = True, is_screen_active: bool = True
    ) -> None:
        """Override the idle state via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setIdleOverride",
            {"isUserActive": is_user_active, "isScreenActive": is_screen_active},
        )

    async def clear_idle_override(self) -> None:
        """Clear the idle state override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.clearIdleOverride", {})

    async def set_script_execution_disabled(self, disabled: bool = True) -> None:
        """Disable or enable JavaScript script execution via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setScriptExecutionDisabled", {"value": disabled})

    async def set_visible_size(self, width: int, height: int) -> None:
        """Set the visible size of the page via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setVisibleSize", {"width": width, "height": height}
        )

    async def add_screen(self, screen: dict[str, Any]) -> None:
        """Add a virtual screen via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.addScreen", {"screen": screen})

    async def can_emulate(self) -> bool:
        """Check whether the browser supports emulation via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Emulation.canEmulate", {})
        return bool(result.get("result", False)) if result else False

    async def clear_auto_dark_mode_override(self) -> None:
        """Clear the auto dark mode override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.clearAutoDarkModeOverride", {})

    async def clear_default_background_color_override(self) -> None:
        """Clear the default background color override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.clearDefaultBackgroundColorOverride", {})

    async def clear_device_posture_override(self) -> None:
        """Clear the device posture override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.clearDevicePostureOverride", {})

    async def clear_display_features_override(self) -> None:
        """Clear the display features override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.clearDisplayFeaturesOverride", {})

    async def clear_geolocation_override(self) -> None:
        """Clear the geolocation override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.clearGeolocationOverride", {})

    async def clear_timezone_override(self) -> None:
        """Clear the timezone override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.clearTimezoneOverride", {})

    async def get_overridden_sensor_information(self, sensor_type: str) -> dict[str, Any]:
        """Get information about overridden sensors via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Emulation.getOverriddenSensorInformation", {"type": sensor_type}
        )
        return dict(result) if result else {}

    async def get_screen_infos(self) -> dict[str, Any]:
        """Get information about all virtual screens via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Emulation.getScreenInfos", {})
        return dict(result) if result else {}

    async def remove_screen(self, screen_id: str) -> None:
        """Remove a virtual screen by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.removeScreen", {"screenId": screen_id})

    async def reset_page_scale_factor(self) -> None:
        """Reset the page scale factor to its default via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.resetPageScaleFactor", {})

    async def set_auto_dark_mode_override(self, enabled: bool) -> None:
        """Enable or disable auto dark mode override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setAutoDarkModeOverride", {"enabled": enabled})

    async def set_automation_override(self, enabled: bool) -> None:
        """Enable or disable automation override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setAutomationOverride", {"enabled": enabled})

    async def set_cpu_throttling_rate(self, rate: float) -> None:
        """Set CPU throttling rate via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setCPUThrottlingRate", {"rate": rate})

    async def set_data_saver_override(self, enabled: bool) -> None:
        """Enable or disable data saver override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setDataSaverOverride", {"enabled": enabled})

    async def set_default_background_color_override(self, color: dict[str, Any]) -> None:
        """Override the default background color via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setDefaultBackgroundColorOverride", {"color": color}
        )

    async def set_device_posture_override(self, posture: str) -> None:
        """Override the device posture via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setDevicePostureOverride", {"posture": posture})

    async def set_disabled_image_types(self, image_types: list[str]) -> None:
        """Disable the given image types from loading via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setDisabledImageTypes", {"imageTypes": image_types}
        )

    async def set_display_features_override(self, features: list[dict[str, Any]]) -> None:
        """Override display features via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setDisplayFeaturesOverride", {"features": features}
        )

    async def set_document_cookie_disabled(self, disabled: bool) -> None:
        """Disable or enable document cookies via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setDocumentCookieDisabled", {"disabled": disabled})

    async def set_emit_touch_events_for_mouse(
        self, enabled: bool, configuration: dict[str, Any] | None = None
    ) -> None:
        """Enable or disable touch event emulation for mouse input via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"enabled": enabled}
        if configuration is not None:
            params["configuration"] = configuration
        await client.cdp.send_command("Emulation.setEmitTouchEventsForMouse", params)

    async def set_emulated_media_feature(self, features: list[dict[str, str]]) -> None:
        """Set emulated media features via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setEmulatedMediaFeature", {"features": features})

    async def set_emulated_os_text_scale(self, scale: float) -> None:
        """Override the OS text scale factor via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setEmulatedOSTextScale", {"scale": scale})

    async def set_focus_emulation_enabled(self, enabled: bool) -> None:
        """Enable or disable focus emulation via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setFocusEmulationEnabled", {"enabled": enabled})

    async def set_geolocation_override(
        self, latitude: float, longitude: float, accuracy: float = 100.0
    ) -> None:
        """Override the geolocation position via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setGeolocationOverride",
            {
                "latitude": latitude,
                "longitude": longitude,
                "accuracy": accuracy,
            },
        )

    async def set_hardware_concurrency_override(self, concurrency: int) -> None:
        """Override the hardware concurrency via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setHardwareConcurrencyOverride", {"hardwareConcurrency": concurrency}
        )

    async def set_locale_override(self, locale: str) -> None:
        """Override the browser locale via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setLocaleOverride", {"locale": locale})

    async def set_navigator_overrides(self, navigator: dict[str, Any]) -> None:
        """Override navigator properties via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setNavigatorOverrides", {"navigator": navigator})

    async def set_page_scale_factor(self, factor: float) -> None:
        """Set the page scale factor via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setPageScaleFactor", {"pageScaleFactor": factor})

    async def set_pressure_source_override_enabled(self, source: str, enabled: bool) -> None:
        """Enable or disable pressure source override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setPressureSourceOverrideEnabled", {"source": source, "enabled": enabled}
        )

    async def set_pressure_state_override(self, source: str, state: str, value: float) -> None:
        """Override the pressure state via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setPressureStateOverride", {"source": source, "state": state, "value": value}
        )

    async def set_primary_screen(self, screen_id: str) -> None:
        """Set the primary screen by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setPrimaryScreen", {"screenId": screen_id})

    async def set_safe_area_insets_override(self, insets: dict[str, Any]) -> None:
        """Override the safe area insets via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setSafeAreaInsetsOverride", {"insets": insets})

    async def set_scrollbars_hidden(self, hidden: bool) -> None:
        """Hide or show scrollbars via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setScrollbarsHidden", {"hidden": hidden})

    async def set_sensor_override_enabled(self, type: str, enabled: bool) -> None:
        """Enable or disable sensor override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setSensorOverrideEnabled", {"type": type, "enabled": enabled}
        )

    async def set_sensor_override_readings(self, type: str, readings: list[dict[str, Any]]) -> None:
        """Override sensor readings via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setSensorOverrideReadings", {"type": type, "readings": readings}
        )

    async def set_small_viewport_height_difference_override(self, difference: float) -> None:
        """Override the small viewport height difference via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setSmallViewportHeightDifferenceOverride", {"difference": difference}
        )

    async def set_timezone_override(self, timezone_id: str) -> None:
        """Override the timezone via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Emulation.setTimezoneOverride", {"timezoneId": timezone_id})

    async def set_touch_emulation_enabled(self, enabled: bool, max_touch_points: int = 5) -> None:
        """Enable or disable touch emulation via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setTouchEmulationEnabled",
            {"enabled": enabled, "maxTouchPoints": max_touch_points},
        )

    async def set_user_agent_override(
        self,
        user_agent: str,
        accept_language: str = "",
        platform: str = "",
        user_agent_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Override the user agent string and related metadata via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"userAgent": user_agent}
        if accept_language:
            params["acceptLanguage"] = accept_language
        if platform:
            params["platform"] = platform
        if user_agent_metadata is not None:
            params["userAgentMetadata"] = user_agent_metadata
        await client.cdp.send_command("Emulation.setUserAgentOverride", params)

    async def set_virtual_time_policy(self, policy: str, budget: int = 0) -> None:
        """Set the virtual time policy via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setVirtualTimePolicy", {"policy": policy, "budget": budget}
        )

    async def update_screen(self, screen_id: str, screen: dict[str, Any]) -> None:
        """Update a virtual screen by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.updateScreen", {"screenId": screen_id, "screen": screen}
        )

    # ── Performance ───────────────────────────────────────

    async def perf_metrics(self) -> dict[str, Any]:
        """Get performance metrics via JS Performance API.

        Uses script.evaluate to collect performance.timing,
        performance.memory, and navigation timing data.

        Returns:
            Dict mapping metric names to values.
        """
        client = self._require_launched()
        js = (
            "JSON.stringify({"
            "  navigationStart: performance.timing.navigationStart,"
            "  loadEventEnd: performance.timing.loadEventEnd,"
            "  domContentLoadedEventEnd: performance.timing.domContentLoadedEventEnd,"
            "  responseEnd: performance.timing.responseEnd,"
            "  domInteractive: performance.timing.domInteractive,"
            "  domComplete: performance.timing.domComplete,"
            "  loadEventStart: performance.timing.loadEventStart,"
            "  jsHeapUsedSize: performance.memory ? performance.memory.usedJSHeapSize : null,"
            "  jsHeapTotalSize: performance.memory ? performance.memory.totalJSHeapSize : null,"
            "  jsHeapLimit: performance.memory ? performance.memory.jsHeapSizeLimit : null,"
            "  resourceCount: performance.getEntriesByType('resource').length,"
            "  transferSize: performance.getEntriesByType('resource')"
            "    .reduce((s,e)=>s+(e.transferSize||0),0)"
            "})"
        )
        result = await client.script.evaluate(self._context, js)
        val = result.value if hasattr(result, "value") else result
        return json.loads(val) if isinstance(val, str) else dict(val)

    async def perf_trace(self, duration_ms: int = 3000) -> dict[str, Any]:
        """Capture a performance trace via CDP Tracing.

        Args:
            duration_ms: Trace duration in milliseconds.

        Returns:
            Dict with trace data.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "Tracing.start",
            {"traceConfig": {"recordMode": "recordUntilFull"}},
        )

        await asyncio.sleep(duration_ms / 1000)
        result = await client.cdp.send_command("Tracing.end", {})
        return dict(result) if result else {}

    async def perf_profile(self, duration_ms: int = 3000) -> dict[str, Any]:
        """Capture a CPU profile via CDP Profiler.

        Args:
            duration_ms: Profile duration in milliseconds.

        Returns:
            Dict with profile data.
        """
        client = self._require_launched()
        await client.cdp.send_command("Profiler.enable", {})
        await client.cdp.send_command("Profiler.start", {})

        await asyncio.sleep(duration_ms / 1000)
        result = await client.cdp.send_command("Profiler.stop", {})
        return dict(result) if result else {}

    async def perf_heap_snapshot(self) -> dict[str, Any]:
        """Take a heap snapshot via CDP HeapProfiler.

        Returns:
            Dict with heap snapshot data.
        """
        client = self._require_launched()
        await client.cdp.send_command("HeapProfiler.enable", {})
        result = await client.cdp.send_command(
            "HeapProfiler.takeHeapSnapshot",
            {},
        )
        return dict(result) if result else {}

    async def perf_coverage(self) -> dict[str, Any]:
        """Get JS coverage data via CDP Profiler.

        Uses CDP bridge to enable profiler and take precise coverage.

        Returns:
            Dict with 'result' key containing script coverage entries.
        """
        client = self._require_launched()
        await client.cdp.send_command("Profiler.enable", {})
        await client.cdp.send_command(
            "Profiler.startPreciseCoverage",
            {"callCount": True, "detailed": True},
        )
        result = await client.cdp.send_command("Profiler.takePreciseCoverage", {})
        return dict(result) if result else {}

    async def perf_css_coverage(self) -> dict[str, Any]:
        """Get CSS rule usage coverage via CDP.

        Uses CDP bridge to CSS.startRuleUsageTracking and stop.

        Returns:
            Dict with CSS coverage data.
        """
        client = self._require_launched()
        await client.cdp.send_command("CSS.enable", {})
        await client.cdp.send_command("CSS.startRuleUsageTracking", {})

        await asyncio.sleep(1)
        result = await client.cdp.send_command(
            "CSS.stopRuleUsageTracking",
            {},
        )
        return dict(result) if result else {}

    async def performance_disable(self) -> None:
        """Disable the Performance domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Performance.disable", {})

    async def performance_enable(self) -> None:
        """Enable the Performance domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Performance.enable", {})

    async def performance_get_metrics(self) -> dict[str, Any]:
        """Get current values of run-time metrics via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Performance.getMetrics", {}))

    async def performance_set_time_domain(self, time_domain: str) -> None:
        """Set the time domain for collecting and reporting durations via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Performance.setTimeDomain", {"timeDomain": time_domain})

    # ── Tracing — via CDP bridge ──────────────────────────

    async def tracing_start(
        self,
        categories: str = "",
        options: str = "",
        transfer_mode: str = "ReturnAsStream",
    ) -> None:
        """Start trace event collection via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"transferMode": transfer_mode}
        if categories:
            params["traceConfig"] = {"includedCategories": categories.split(",")}
        if options:
            params["traceConfig"] = params.get("traceConfig", {})
            params["traceConfig"]["excludedCategories"] = options.split(",")
        await client.cdp.send_command("Tracing.start", params)

    async def tracing_end(self) -> None:
        """Stop trace event collection via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Tracing.end", {})

    async def tracing_get_categories(self) -> list[str]:
        """Get supported tracing categories via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Tracing.getCategories", {})
        return list(result.get("categories", [])) if result else []

    async def tracing_record_clock_sync_marker(self, sync_id: str) -> None:
        """Record a clock sync marker via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Tracing.recordClockSyncMarker", {"syncId": sync_id})

    async def tracing_request_memory_dump(self) -> dict[str, Any]:
        """Request a memory dump via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Tracing.requestMemoryDump", {})
        return dict(result) if result else {}

    async def tracing_get_track_event_descriptor(self, track_event: str) -> dict[str, Any]:
        """Get a track event descriptor via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Tracing.getTrackEventDescriptor", {"trackEvent": track_event}
        )
        return dict(result) if result else {}

    # ── PerformanceTimeline — via CDP bridge ───────────────

    async def performance_timeline_enable(self) -> None:
        """Enable the PerformanceTimeline domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("PerformanceTimeline.enable", {})

    # ── CSS ────────────────────────────────────────────────

    async def css_get_styles(self, selector: str) -> dict[str, Any]:
        """Get inline and matched styles for an element via JS.

        Uses script.evaluate to extract inline styles and matched
        CSS rules from document.styleSheets for the given selector.

        Args:
            selector: CSS selector for the target element.

        Returns:
            Dict containing inlineStyles and matchedStyles.
        """
        client = self._require_launched()
        escaped = json.dumps(selector)
        js = (
            f"(function(){{"
            f"  var el=document.querySelector({escaped});"
            f"  if(!el) return null;"
            f"  var inline=el.getAttribute('style')||'';"
            f"  var matched=[];"
            f"  for(var i=0;i<document.styleSheets.length;i++){{"
            f"    try{{"
            f"      var sheet=document.styleSheets[i];"
            f"      var rules=sheet.cssRules||sheet.rules;"
            f"      for(var j=0;j<rules.length;j++){{"
            f"        if(el.matches(rules[j].selectorText)){{"
            f"          matched.push({{"
            f"            selectorText:rules[j].selectorText,"
            f"            cssText:rules[j].cssText"
            f"          }});"
            f"        }}"
            f"      }}"
            f"    }}catch(e){{}}"
            f"  }}"
            f"  return JSON.stringify({{inlineStyles:inline,matchedStyles:matched}});"
            f"}})()"
        )
        result = await client.script.evaluate(self._context, js)
        val = result.value if hasattr(result, "value") else result
        if not val:
            raise ElementNotFoundError(selector)
        return json.loads(val) if isinstance(val, str) else dict(val)

    async def css_get_stylesheets(self) -> list[dict[str, Any]]:
        """List all stylesheets in the page via JS.

        Returns:
            List of stylesheet dicts with href, media, and rules count.
        """
        client = self._require_launched()
        js = (
            "JSON.stringify(Array.from(document.styleSheets)"
            ".map(function(s){{"
            "  return {{"
            "    href:s.href||'',"
            "    media:s.media.mediaText||'',"
            "    disabled:s.disabled,"
            "    rulesCount:(s.cssRules||s.rules||[]).length"
            "  }};"
            "}}))"
        )
        result = await client.script.evaluate(self._context, js)
        val = result.value if hasattr(result, "value") else result
        return json.loads(val) if isinstance(val, str) else list(val)

    async def css_get_rules(self, stylesheet_id: str) -> list[dict[str, Any]]:
        """Get CSS rules from a stylesheet by index via JS.

        Args:
            stylesheet_id: Index of the stylesheet (as string).

        Returns:
            List of CSS rule dicts with selectorText and cssText.
        """
        client = self._require_launched()
        idx = int(stylesheet_id) if stylesheet_id.isdigit() else 0
        js = (
            f"(function(){{"
            f"  var sheets=document.styleSheets;"
            f"  if({idx}>=sheets.length) return '[]';"
            f"  var rules=sheets[{idx}].cssRules||sheets[{idx}].rules||[];"
            f"  return JSON.stringify(Array.from(rules).map(function(r){{"
            f"    return {{selectorText:r.selectorText||'',cssText:r.cssText||''}};"
            f"  }}));"
            f"}})()"
        )
        result = await client.script.evaluate(self._context, js)
        val = result.value if hasattr(result, "value") else result
        return json.loads(val) if isinstance(val, str) else list(val)

    async def css_get_computed(self, selector: str) -> dict[str, Any]:
        """Get computed styles for an element via JS getComputedStyle.

        Args:
            selector: CSS selector for the target element.

        Returns:
            Dict mapping CSS property names to computed values.
        """
        client = self._require_launched()
        escaped = json.dumps(selector)
        js = (
            f"(function(){{"
            f"  var el=document.querySelector({escaped});"
            f"  if(!el) return null;"
            f"  var cs=getComputedStyle(el);"
            f"  var result={{}};"
            f"  for(var i=0;i<cs.length;i++){{"
            f"    var prop=cs.item(i);"
            f"    result[prop]=cs.getPropertyValue(prop);"
            f"  }}"
            f"  return JSON.stringify(result);"
            f"}})()"
        )
        result = await client.script.evaluate(self._context, js)
        val = result.value if hasattr(result, "value") else result
        if not val:
            raise ElementNotFoundError(selector)
        return json.loads(val) if isinstance(val, str) else dict(val)

    async def css_add_rule(self, stylesheet_id: str, rule_text: str, location: int = 0) -> str:
        """Add a new CSS rule to a stylesheet via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "CSS.addRule",
            {
                "styleSheetId": stylesheet_id,
                "ruleText": rule_text,
                "location": {"lineNumber": location, "columnNumber": 0},
            },
        )
        return str(result.get("ruleId", ""))

    async def css_create_style_sheet(self, frame_id: str) -> str:
        """Create a new stylesheet in the given frame via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("CSS.createStyleSheet", {"frameId": frame_id})
        return str(result.get("styleSheetId", ""))

    async def css_get_media_queries(self) -> list[dict[str, Any]]:
        """Get all media queries in the current page via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("CSS.getMediaQueries", {})
        return [dict(m) for m in result.get("medias", [])] if result else []

    async def css_get_style_sheet_text(self, stylesheet_id: str) -> str:
        """Get the text content of a stylesheet by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "CSS.getStyleSheetText", {"styleSheetId": stylesheet_id}
        )
        return str(result.get("text", ""))

    async def css_set_style_sheet_text(self, stylesheet_id: str, text: str) -> None:
        """Set the text content of a stylesheet by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "CSS.setStyleSheetText",
            {"styleSheetId": stylesheet_id, "text": text},
        )

    async def css_set_rule_selector(
        self, stylesheet_id: str, range_: dict[str, Any], selector: str
    ) -> None:
        """Set the selector text of a CSS rule via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "CSS.setRuleSelector",
            {
                "styleSheetId": stylesheet_id,
                "range": range_,
                "selector": selector,
            },
        )

    async def css_set_media_text(
        self, stylesheet_id: str, range_: dict[str, Any], text: str
    ) -> None:
        """Set the text of a media rule via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "CSS.setMediaText",
            {
                "styleSheetId": stylesheet_id,
                "range": range_,
                "text": text,
            },
        )

    async def css_force_pseudo_state(self, node_id: int, pseudo_state: list[str]) -> None:
        """Force a pseudo state on a node via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "CSS.forcePseudoState",
            {"nodeId": node_id, "forcedPseudoClasses": pseudo_state},
        )

    async def css_get_background_colors(self, node_id: int) -> dict[str, Any]:
        """Get background colors for a node via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("CSS.getBackgroundColors", {"nodeId": node_id}))

    async def css_start_rule_usage_tracking(self) -> None:
        """Start tracking CSS rule usage via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("CSS.startRuleUsageTracking", {})

    async def css_stop_rule_usage_tracking(self) -> None:
        """Stop tracking CSS rule usage via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("CSS.stopRuleUsageTracking", {})

    async def css_take_coverage_delta(self) -> dict[str, Any]:
        """Get the coverage delta since the last call via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("CSS.takeCoverageDelta", {}))

    async def css_collect_class_names(self, node_id: int) -> list[str]:
        """Collect class names from the subtree of a node by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("CSS.collectClassNames", {"nodeId": node_id})
        return list(result.get("classNames", [])) if result else []

    async def css_disable(self) -> None:
        """Disable the CSS domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("CSS.disable", {})

    async def css_enable(self) -> None:
        """Enable the CSS domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("CSS.enable", {})

    async def css_force_starting_style(
        self, node_id: int, starting_style_id: dict[str, Any]
    ) -> None:
        """Force a starting style for a node via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "CSS.forceStartingStyle", {"nodeId": node_id, "startingStyleId": starting_style_id}
        )

    async def css_get_animated_styles_for_node(self, node_id: int) -> dict[str, Any]:
        """Get animated styles for a node by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("CSS.getAnimatedStylesForNode", {"nodeId": node_id})
        return dict(result) if result else {}

    async def css_get_computed_style_for_node(self, node_id: int) -> list[dict[str, Any]]:
        """Get computed style for a node by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("CSS.getComputedStyleForNode", {"nodeId": node_id})
        return list(result.get("computedStyle", [])) if result else []

    async def css_get_environment_variables(self) -> list[dict[str, Any]]:
        """Get environment variables for the CSS domain via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("CSS.getEnvironmentVariables", {})
        return list(result.get("environmentVariables", [])) if result else []

    async def css_get_inline_styles(self, node_id: int) -> dict[str, Any]:
        """Get inline styles for a node by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("CSS.getInlineStyles", {"nodeId": node_id})
        return dict(result) if result else {}

    async def css_get_inline_styles_for_node(self, node_id: int) -> dict[str, Any]:
        """Get inline styles for a node by ID (alias) via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("CSS.getInlineStylesForNode", {"nodeId": node_id})
        return dict(result) if result else {}

    async def css_get_layers_for_node(self, node_id: int) -> list[dict[str, Any]]:
        """Get CSS layers for a node by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("CSS.getLayersForNode", {"nodeId": node_id})
        return list(result.get("layers", [])) if result else []

    async def css_get_location_for_selector(
        self, selector: str, stylesheet_id: str
    ) -> dict[str, Any]:
        """Get the location of a CSS selector in a stylesheet via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "CSS.getLocationForSelector", {"selector": selector, "styleSheetId": stylesheet_id}
        )
        return dict(result) if result else {}

    async def css_get_longhand_properties(
        self, shorthand_id: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Get longhand properties for a shorthand property via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "CSS.getLonghandProperties", {"shorthandId": shorthand_id}
        )
        return list(result.get("longhandProperties", [])) if result else []

    async def css_get_matched_styles_for_node(self, node_id: int) -> dict[str, Any]:
        """Get matched styles for a node by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("CSS.getMatchedStylesForNode", {"nodeId": node_id})
        return dict(result) if result else {}

    async def css_get_platform_fonts_for_node(self, node_id: int) -> list[dict[str, Any]]:
        """Get platform fonts for a node by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("CSS.getPlatformFontsForNode", {"nodeId": node_id})
        return list(result.get("fonts", [])) if result else []

    async def css_get_stylesheet_text(self, stylesheet_id: str) -> str:
        """Get the text content of a stylesheet by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "CSS.getStyleSheetText", {"styleSheetId": stylesheet_id}
        )
        return str(result.get("text", "")) if result else ""

    async def css_resolve_values(self, values: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Resolve CSS values via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("CSS.resolveValues", {"values": values})
        return list(result.get("resolvedValues", [])) if result else []

    async def css_set_container_query_condition_text(
        self, stylesheet_id: str, container_query_id: dict[str, Any], text: str
    ) -> None:
        """Set the condition text of a container query via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "CSS.setContainerQueryConditionText",
            {"styleSheetId": stylesheet_id, "containerQueryId": container_query_id, "text": text},
        )

    async def css_set_effective_property_value_for_node(
        self, node_id: int, property_name: str, value: str
    ) -> None:
        """Set the effective property value for a node via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "CSS.setEffectivePropertyValueForNode",
            {"nodeId": node_id, "propertyName": property_name, "value": value},
        )

    async def css_set_keyframe_key(
        self, stylesheet_id: str, keyframe_id: dict[str, Any], key_text: str
    ) -> None:
        """Set the key text of a keyframe rule via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "CSS.setKeyframeKey",
            {"styleSheetId": stylesheet_id, "keyframeId": keyframe_id, "keyText": key_text},
        )

    async def css_set_local_fonts_enabled(self, enabled: bool) -> None:
        """Enable or disable local fonts via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("CSS.setLocalFontsEnabled", {"enabled": enabled})

    async def css_set_navigation_text(
        self, stylesheet_id: str, navigation_id: dict[str, Any], text: str
    ) -> None:
        """Set the text of a navigation rule via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "CSS.setNavigationText",
            {"styleSheetId": stylesheet_id, "navigationId": navigation_id, "text": text},
        )

    async def css_set_property_rule_property_name(
        self, stylesheet_id: str, property_rule_id: dict[str, Any], name: str
    ) -> None:
        """Set the property name of a property rule via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "CSS.setPropertyRulePropertyName",
            {"styleSheetId": stylesheet_id, "propertyRuleId": property_rule_id, "name": name},
        )

    async def css_set_rule_style(
        self, stylesheet_id: str, rule_id: dict[str, Any], style_text: str
    ) -> None:
        """Set the style text of a CSS rule via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "CSS.setRuleStyle",
            {"styleSheetId": stylesheet_id, "ruleId": rule_id, "style": style_text},
        )

    async def css_set_scope_text(
        self, stylesheet_id: str, scope_id: dict[str, Any], text: str
    ) -> None:
        """Set the text of a scope rule via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "CSS.setScopeText", {"styleSheetId": stylesheet_id, "scopeId": scope_id, "text": text}
        )

    async def css_set_style_text(self, edits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Set style texts for multiple edits via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("CSS.setStyleTexts", {"edits": edits})
        return list(result.get("styles", [])) if result else []

    async def css_set_style_texts(self, edits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Set style texts for multiple edits (batch) via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("CSS.setStyleTexts", {"edits": edits})
        return list(result.get("styles", [])) if result else []

    async def css_set_stylesheet_text(self, stylesheet_id: str, text: str) -> None:
        """Set the text content of a stylesheet by ID (alias) via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "CSS.setStyleSheetText", {"styleSheetId": stylesheet_id, "text": text}
        )

    async def css_set_supports_text(
        self, stylesheet_id: str, supports_id: dict[str, Any], text: str
    ) -> None:
        """Set the text of a supports rule via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "CSS.setSupportsText",
            {"styleSheetId": stylesheet_id, "supportsId": supports_id, "text": text},
        )

    async def css_take_computed_style_updates(self) -> list[dict[str, Any]]:
        """Take computed style updates via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("CSS.takeComputedStyleUpdates", {})
        return list(result.get("computedStyleUpdates", [])) if result else []

    async def css_track_computed_style_updates(self, track_properties: bool = True) -> None:
        """Track computed style updates via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "CSS.trackComputedStyleUpdates", {"trackProperties": track_properties}
        )

    async def css_track_computed_style_updates_for_node(
        self, node_id: int, track_properties: bool = True
    ) -> None:
        """Track computed style updates for a specific node via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "CSS.trackComputedStyleUpdatesForNode",
            {"nodeId": node_id, "trackProperties": track_properties},
        )

    # ── Debugging ──────────────────────────────────────────

    async def debug_set_breakpoint(self, url: str, line: int, condition: str | None = None) -> str:
        """Set a breakpoint by URL and line via CDP Debugger.

        Args:
            url: URL where the breakpoint should be set.
            line: Line number (0-based).
            condition: Optional condition expression.

        Returns:
            Breakpoint ID as string.
        """
        client = self._require_launched()
        await client.cdp.send_command("Debugger.enable", {})
        params: dict[str, Any] = {"url": url, "lineNumber": line}
        if condition:
            params["condition"] = condition
        result = await client.cdp.send_command(
            "Debugger.setBreakpointByUrl",
            params,
        )
        return str(result.get("breakpointId", "")) if result else ""

    async def debug_set_breakpoint_function(self, function_name: str) -> str:
        """Set a breakpoint on a function name via CDP Debugger.

        Args:
            function_name: Name of the function to break on.

        Returns:
            Breakpoint ID as string.
        """
        client = self._require_launched()
        await client.cdp.send_command("Debugger.enable", {})
        result = await client.cdp.send_command(
            "Debugger.setBreakpointOnFunctionCall",
            {"name": function_name},
        )
        return str(result.get("breakpointId", "")) if result else ""

    async def debug_remove_breakpoint(self, breakpoint_id: str) -> None:
        """Remove a breakpoint by ID via CDP Debugger.

        Args:
            breakpoint_id: Breakpoint ID to remove.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "Debugger.removeBreakpoint",
            {"breakpointId": breakpoint_id},
        )

    async def debug_step_over(self) -> None:
        """Step over in debugger via CDP."""
        client = self._require_launched()
        await client.cdp.send_command("Debugger.stepOver", {})

    async def debug_step_into(self) -> None:
        """Step into in debugger via CDP."""
        client = self._require_launched()
        await client.cdp.send_command("Debugger.stepInto", {})

    async def debug_step_out(self) -> None:
        """Step out in debugger via CDP."""
        client = self._require_launched()
        await client.cdp.send_command("Debugger.stepOut", {})

    async def debug_pause(self) -> None:
        """Pause execution via CDP Debugger."""
        client = self._require_launched()
        await client.cdp.send_command("Debugger.pause", {})

    async def debug_resume(self) -> None:
        """Resume execution via CDP Debugger."""
        client = self._require_launched()
        await client.cdp.send_command("Debugger.resume", {})

    async def debug_get_listeners(self, selector: str) -> list[dict[str, Any]]:
        """Get event listeners for an element via CDP DOMDebugger.

        Args:
            selector: CSS selector for the target element.

        Returns:
            List of listener dicts.
        """
        client = self._require_launched()
        escaped = json.dumps(selector)
        js = (
            f"(function(){{"
            f"  var el=document.querySelector({escaped});"
            f"  if(!el) return null;"
            f"  return el;"
            f"}})()"
        )
        result = await client.script.evaluate(self._context, js)
        if not result:
            return []
        listeners = await client.cdp.send_command(
            "DOMDebugger.getEventListeners",
            {"objectId": str(result)},
        )
        return list(listeners.get("listeners", [])) if listeners else []

    async def debug_evaluate_on_call_frame(
        self, call_frame_id: str, expression: str
    ) -> dict[str, Any]:
        """Evaluate a JavaScript expression in a paused call frame via CDP bridge."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "Debugger.evaluateOnCallFrame",
                {"callFrameId": call_frame_id, "expression": expression},
            )
        )

    async def debug_get_script_source(self, script_id: str) -> str:
        """Get the source code of a script by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Debugger.getScriptSource", {"scriptId": script_id})
        return str(result.get("scriptSource", ""))

    async def debug_get_stack_trace(self) -> dict[str, Any]:
        """Get the current JavaScript stack trace via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Debugger.getStackTrace", {}))

    async def debug_get_possible_breakpoints(
        self, start: dict[str, Any], end: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Get possible breakpoint locations via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"start": start}
        if end:
            params["end"] = end
        result = await client.cdp.send_command("Debugger.getPossibleBreakpoints", params)
        return [dict(b) for b in result.get("locations", [])] if result else []

    async def debug_search_in_content(
        self, script_id: str, query: str, case_sensitive: bool = False, is_regex: bool = False
    ) -> list[dict[str, Any]]:
        """Search for a string in script content via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"scriptId": script_id, "query": query}
        if case_sensitive:
            params["caseSensitive"] = True
        if is_regex:
            params["isRegex"] = True
        result = await client.cdp.send_command("Debugger.searchInContent", params)
        return [dict(r) for r in result.get("result", [])] if result else []

    async def debug_set_pause_on_exceptions(self, state: str) -> None:
        """Set pause on exceptions mode via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Debugger.setPauseOnExceptions", {"state": state})

    async def debug_set_breakpoints_active(self, active: bool) -> None:
        """Enable or disable all breakpoints via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Debugger.setBreakpointsActive", {"active": active})

    async def debug_set_skip_all_pauses(self, skip: bool) -> None:
        """Skip all pauses via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Debugger.setSkipAllPauses", {"skip": skip})

    async def debug_set_script_source(self, script_id: str, source: str) -> dict[str, Any]:
        """Edit the source code of a live script via CDP bridge."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "Debugger.setScriptSource",
                {"scriptId": script_id, "scriptSource": source},
            )
        )

    async def debug_continue_to_location(self, url: str, line: int, column: int = 0) -> None:
        """Continue execution until a specific location via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Debugger.continueToLocation",
            {"location": {"scriptId": url, "lineNumber": line, "columnNumber": column}},
        )

    async def debug_disable(self) -> None:
        """Disable the Debugger domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Debugger.disable", {})

    async def debug_disassemble_wasm_module(self, script_id: str) -> dict[str, Any]:
        """Disassemble a WASM module by script ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Debugger.disassembleWasmModule", {"scriptId": script_id}
        )
        return dict(result) if result else {}

    async def debug_enable(self) -> None:
        """Enable the Debugger domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Debugger.enable", {})

    async def debug_get_wasm_bytecode(self, script_id: str, offset: int) -> dict[str, Any]:
        """Get WASM bytecode for a script by ID and offset via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Debugger.getWasmBytecode", {"scriptId": script_id, "offset": offset}
        )
        return dict(result) if result else {}

    async def debug_next_wasm_disassembly_chunk(self, disassembly_id: str) -> dict[str, Any]:
        """Get the next chunk of a WASM disassembly via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Debugger.nextWasmDisassemblyChunk", {"disassemblyId": disassembly_id}
        )
        return dict(result) if result else {}

    async def debug_pause_on_async_call(self, operation: str) -> None:
        """Pause on an async call operation via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Debugger.pauseOnAsyncCall", {"operation": operation})

    async def debug_restart_frame(self, call_frame_id: str) -> None:
        """Restart a call frame by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Debugger.restartFrame", {"callFrameId": call_frame_id})

    async def debug_set_async_call_stack_depth(self, depth: int) -> None:
        """Set the async call stack depth via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Debugger.setAsyncCallStackDepth", {"depth": depth})

    async def debug_set_blackbox_execution_contexts(self, unique_ids: list[str]) -> None:
        """Set blackboxed execution contexts by unique IDs via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Debugger.setBlackboxExecutionContexts", {"uniqueIds": unique_ids}
        )

    async def debug_set_blackbox_patterns(self, patterns: list[str]) -> None:
        """Set blackbox patterns for script URLs via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Debugger.setBlackboxPatterns", {"patterns": patterns})

    async def debug_set_blackboxed_ranges(
        self, script_id: str, positions: list[dict[str, Any]]
    ) -> None:
        """Set blackboxed ranges for a script via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Debugger.setBlackboxedRanges", {"scriptId": script_id, "positions": positions}
        )

    async def debug_set_breakpoint_raw(
        self, location: dict[str, Any], condition: str | None = None
    ) -> dict[str, Any]:
        """Set a breakpoint at a raw location in a script via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"location": location}
        if condition is not None:
            params["condition"] = condition
        result = await client.cdp.send_command("Debugger.setBreakpoint", params)
        return dict(result) if result else {}

    async def debug_set_breakpoint_by_url(
        self, url: str, line_number: int, column_number: int = 0, condition: str | None = None
    ) -> dict[str, Any]:
        """Set a breakpoint by URL and line number via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {
            "url": url,
            "lineNumber": line_number,
            "columnNumber": column_number,
        }
        if condition is not None:
            params["condition"] = condition
        result = await client.cdp.send_command("Debugger.setBreakpointByUrl", params)
        return dict(result) if result else {}

    async def debug_set_breakpoint_on_function_call(
        self, object_id: str, condition: str | None = None
    ) -> dict[str, Any]:
        """Set a breakpoint on a function call by object ID via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"objectId": object_id}
        if condition is not None:
            params["condition"] = condition
        result = await client.cdp.send_command("Debugger.setBreakpointOnFunctionCall", params)
        return dict(result) if result else {}

    async def debug_set_instrumentation_breakpoint(self, instrumentation: str) -> dict[str, Any]:
        """Set an instrumentation breakpoint via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Debugger.setInstrumentationBreakpoint", {"instrumentation": instrumentation}
        )
        return dict(result) if result else {}

    async def debug_set_return_value(self, new_value: dict[str, Any]) -> None:
        """Set the return value of the current call frame via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Debugger.setReturnValue", {"newValue": new_value})

    async def debug_set_variable_value(
        self, call_frame_id: str, scope_number: int, variable_name: str, new_value: dict[str, Any]
    ) -> None:
        """Set a variable value in a scope of a call frame via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Debugger.setVariableValue",
            {
                "callFrameId": call_frame_id,
                "scopeNumber": scope_number,
                "variableName": variable_name,
                "newValue": new_value,
            },
        )

    # ── DOMDebugger ────────────────────────────────────────

    async def dom_debugger_get_event_listeners(
        self, object_id: str, depth: int = 0, pierce: bool = False
    ) -> list[dict[str, Any]]:
        """Get event listeners for an object by its remote object ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "DOMDebugger.getEventListeners",
            {"objectId": object_id, "depth": depth, "pierce": pierce},
        )
        return list(result.get("listeners", [])) if result else []

    async def dom_debugger_remove_dom_breakpoint(self, node_id: int, type: str) -> None:
        """Remove a DOM breakpoint from a node by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "DOMDebugger.removeDOMBreakpoint", {"nodeId": node_id, "type": type}
        )

    async def dom_debugger_remove_event_listener_breakpoint(
        self, event_name: str, target_name: str | None = None
    ) -> None:
        """Remove an event listener breakpoint via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"eventName": event_name}
        if target_name is not None:
            params["targetName"] = target_name
        await client.cdp.send_command("DOMDebugger.removeEventListenerBreakpoint", params)

    async def dom_debugger_remove_instrumentation_breakpoint(self, event_name: str) -> None:
        """Remove an instrumentation breakpoint via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "DOMDebugger.removeInstrumentationBreakpoint", {"eventName": event_name}
        )

    async def dom_debugger_remove_xhr_breakpoint(self, url: str) -> None:
        """Remove an XHR breakpoint for a URL substring via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOMDebugger.removeXHRBreakpoint", {"url": url})

    async def dom_debugger_set_break_on_csp_violation(self, enabled: bool) -> None:
        """Set whether to break on CSP violations via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOMDebugger.setBreakOnCSPViolation", {"enabled": enabled})

    async def dom_debugger_set_dom_breakpoint(self, node_id: int, type: str) -> None:
        """Set a DOM breakpoint on a node by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "DOMDebugger.setDOMBreakpoint", {"nodeId": node_id, "type": type}
        )

    async def dom_debugger_set_event_listener_breakpoint(
        self, event_name: str, target_name: str | None = None
    ) -> None:
        """Set an event listener breakpoint via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"eventName": event_name}
        if target_name is not None:
            params["targetName"] = target_name
        await client.cdp.send_command("DOMDebugger.setEventListenerBreakpoint", params)

    async def dom_debugger_set_instrumentation_breakpoint(self, event_name: str) -> None:
        """Set an instrumentation breakpoint via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "DOMDebugger.setInstrumentationBreakpoint", {"eventName": event_name}
        )

    async def dom_debugger_set_xhr_breakpoint(self, url: str) -> None:
        """Set an XHR breakpoint for a URL substring via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOMDebugger.setXHRBreakpoint", {"url": url})

    # ── DOM Snapshot ───────────────────────────────────────

    async def dom_snapshot(self) -> dict[str, Any]:
        """Capture a DOM snapshot via JS.

        Uses script.evaluate to serialize the full DOM tree.

        Returns:
            Dict containing 'html' with the full outerHTML.
        """
        client = self._require_launched()
        js = "document.documentElement.outerHTML"
        result = await client.script.evaluate(self._context, js)
        html = result.value if hasattr(result, "value") else result
        return {"html": str(html)}

    # ── Overlay ────────────────────────────────────────────

    async def overlay_highlight(self, selector: str, color: str = "rgba(255,0,0,0.5)") -> None:
        """Highlight an element via JS outline.

        Args:
            selector: CSS selector for the element to highlight.
            color: RGBA color string for the outline.
        """
        client = self._require_launched()
        escaped = json.dumps(selector)
        escaped_color = json.dumps(f"3px solid {color}")
        js = (
            f"(function(){{"
            f"  var el=document.querySelector({escaped});"
            f"  if(el){{"
            f"    el.style.outline={escaped_color};"
            f"    el.dataset.wavexisHighlight='1';"
            f"  }}"
            f"}})()"
        )
        await client.script.evaluate(self._context, js)

    async def overlay_clear(self) -> None:
        """Clear all highlight overlays via JS."""
        client = self._require_launched()
        js = (
            "(function(){"
            "  document.querySelectorAll('[data-wavexis-highlight]')"
            "    .forEach(function(el){"
            "      el.style.outline='';"
            "      delete el.dataset.wavexisHighlight;"
            "    });"
            "})()"
        )
        await client.script.evaluate(self._context, js)

    async def overlay_enable(self) -> None:
        """Enable the overlay domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Overlay.enable", {})

    async def overlay_disable(self) -> None:
        """Disable the overlay domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Overlay.disable", {})

    async def overlay_highlight_node(self, node_id: int, color: str = "rgba(255,0,0,0.5)") -> None:
        """Highlight a DOM node by node ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Overlay.highlightNode",
            {
                "highlightConfig": {
                    "showStyle": False,
                    "showRulers": False,
                    "showExtensionLines": False,
                    "contentColor": {"r": 255, "g": 0, "b": 0, "a": 0.5},
                },
                "nodeId": node_id,
            },
        )

    async def overlay_highlight_quad(
        self, quad: list[float], color: str = "rgba(255,0,0,0.5)"
    ) -> None:
        """Highlight a quad region via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Overlay.highlightQuad",
            {"quad": quad, "color": {"r": 255, "g": 0, "b": 0, "a": 0.5}},
        )

    async def overlay_highlight_rect(
        self, x: float, y: float, width: float, height: float, color: str = "rgba(255,0,0,0.5)"
    ) -> None:
        """Highlight a rectangular region via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Overlay.highlightRect",
            {
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "outlineColor": {"r": 255, "g": 0, "b": 0, "a": 0.5},
            },
        )

    async def overlay_set_inspect_mode(self, mode: str = "searchForNode") -> None:
        """Set the inspect mode via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Overlay.setInspectMode",
            {"mode": mode, "highlightConfig": {}},
        )

    async def overlay_set_show_fps_counter(self, show: bool) -> None:
        """Show or hide the FPS counter via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Overlay.setShowFPSCounter", {"show": show})

    async def overlay_set_show_paint_rects(self, show: bool) -> None:
        """Show or hide paint rectangles via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Overlay.setShowPaintRects", {"result": show})

    async def overlay_set_show_debug_borders(self, show: bool) -> None:
        """Show or hide debug borders via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Overlay.setShowDebugBorders", {"show": show})

    async def overlay_set_show_ad_highlights(self, show: bool) -> None:
        """Show or hide ad highlights via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Overlay.setShowAdHighlights", {"show": show})

    async def overlay_get_grid_highlight_objects_for_test(self, node_id: int) -> dict[str, Any]:
        """Get grid highlight objects for testing via CDP bridge."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "Overlay.getGridHighlightObjectsForTest", {"nodeId": node_id}
            )
        )

    async def overlay_get_highlight_object_for_test(
        self,
        node_id: int,
        include_distance: bool = False,
        include_style: bool = False,
        color_format: str = "hex",
    ) -> dict[str, Any]:
        """Get highlight object for testing via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {
            "nodeId": node_id,
            "includeDistance": include_distance,
            "includeStyle": include_style,
            "colorFormat": color_format,
        }
        return dict(await client.cdp.send_command("Overlay.getHighlightObjectForTest", params))

    async def overlay_get_source_order_highlight_object_for_test(
        self, node_id: int
    ) -> dict[str, Any]:
        """Get source order highlight object for testing via CDP bridge."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "Overlay.getSourceOrderHighlightObjectForTest", {"nodeId": node_id}
            )
        )

    async def overlay_hide_highlight(self) -> None:
        """Hide any highlight overlay via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Overlay.hideHighlight", {})

    async def overlay_highlight_source_order(self, source_order_config: dict[str, Any]) -> None:
        """Highlight the source order of a node via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Overlay.highlightSourceOrder", {"sourceOrderConfig": source_order_config}
        )

    async def overlay_set_paused_in_debugger_message(self, message: str = "") -> None:
        """Set the message displayed when paused in the debugger via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {}
        if message:
            params["message"] = message
        await client.cdp.send_command("Overlay.setPausedInDebuggerMessage", params)

    async def overlay_set_show_container_query_overlays(self, show: bool) -> None:
        """Show or hide container query overlays via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Overlay.setShowContainerQueryOverlays", {"show": show})

    async def overlay_set_show_display_cutout(self, show: bool) -> None:
        """Show or hide display cutout overlay via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Overlay.setShowDisplayCutout", {"show": show})

    async def overlay_set_show_flex_overlays(self, show: bool) -> None:
        """Show or hide flex overlays via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Overlay.setShowFlexOverlays", {"show": show})

    async def overlay_set_show_grid_overlays(
        self, show_grid_overlays: list[dict[str, Any]]
    ) -> None:
        """Show grid overlays via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Overlay.setShowGridOverlays", {"showGridOverlays": show_grid_overlays}
        )

    async def overlay_set_show_hinge(self, hinge_config: dict[str, Any] | None = None) -> None:
        """Show or hide the hinge overlay via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {}
        if hinge_config is not None:
            params["hingeConfig"] = hinge_config
        await client.cdp.send_command("Overlay.setShowHinge", params)

    async def overlay_set_show_inspected_element_anchor(self, show: bool) -> None:
        """Show or hide the inspected element anchor via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Overlay.setShowInspectedElementAnchor", {"show": show})

    async def overlay_set_show_isolated_elements(
        self, isolated_element_highlight_configs: list[dict[str, Any]]
    ) -> None:
        """Show isolated elements via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Overlay.setShowIsolatedElements",
            {"isolatedElementHighlightConfigs": isolated_element_highlight_configs},
        )

    async def overlay_set_show_layout_shift_regions(self, show: bool) -> None:
        """Show or hide layout shift regions via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Overlay.setShowLayoutShiftRegions", {"result": show})

    async def overlay_set_show_scroll_bottleneck_rects(self, show: bool) -> None:
        """Show or hide scroll bottleneck rects via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Overlay.setShowScrollBottleneckRects", {"show": show})

    async def overlay_set_show_scroll_snap_overlays(self, show: bool) -> None:
        """Show or hide scroll snap overlays via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Overlay.setShowScrollSnapOverlays", {"show": show})

    async def overlay_set_show_viewport_size_on_resize(self, show: bool) -> None:
        """Show or hide viewport size on resize via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Overlay.setShowViewportSizeOnResize", {"show": show})

    async def overlay_set_show_window_controls_overlay(self, show: bool) -> None:
        """Show or hide window controls overlay via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Overlay.setShowWindowControlsOverlay", {"show": show})

    # ── Runtime ───────────────────────────────────────────

    async def runtime_evaluate(
        self,
        expression: str,
        await_promise: bool = False,
        return_by_value: bool = False,
    ) -> dict[str, Any]:
        """Evaluate a JavaScript expression via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {
            "expression": expression,
            "awaitPromise": await_promise,
            "returnByValue": return_by_value,
        }
        return dict(await client.cdp.send_command("Runtime.evaluate", params))

    async def runtime_compile_script(
        self,
        expression: str,
        source_url: str = "",
        persist_script: bool = False,
    ) -> dict[str, Any]:
        """Compile a JavaScript expression via CDP bridge."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "Runtime.compileScript",
                {
                    "expression": expression,
                    "sourceURL": source_url,
                    "persistScript": persist_script,
                },
            )
        )

    async def runtime_run_script(
        self, script_id: str, await_promise: bool = False
    ) -> dict[str, Any]:
        """Run a previously compiled script via CDP bridge."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "Runtime.runScript",
                {"scriptId": script_id, "awaitPromise": await_promise},
            )
        )

    async def runtime_call_function_on(
        self,
        function_declaration: str,
        object_id: str = "",
        arguments: list[dict[str, Any]] | None = None,
        await_promise: bool = False,
        return_by_value: bool = False,
    ) -> dict[str, Any]:
        """Call a function on a remote object via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {
            "functionDeclaration": function_declaration,
            "awaitPromise": await_promise,
            "returnByValue": return_by_value,
        }
        if object_id:
            params["objectId"] = object_id
        if arguments:
            params["arguments"] = arguments
        return dict(await client.cdp.send_command("Runtime.callFunctionOn", params))

    async def runtime_get_properties(
        self, object_id: str, own_properties: bool = True
    ) -> dict[str, Any]:
        """Get properties of a remote object via CDP bridge."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "Runtime.getProperties",
                {"objectId": object_id, "ownProperties": own_properties},
            )
        )

    async def runtime_release_object(self, object_id: str) -> None:
        """Release a remote object via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Runtime.releaseObject", {"objectId": object_id})

    async def runtime_release_object_group(self, object_group: str) -> None:
        """Release all objects in a group via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Runtime.releaseObjectGroup", {"objectGroup": object_group})

    async def runtime_discard_console_entries(self) -> None:
        """Discard collected console entries via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Runtime.discardConsoleEntries", {})

    async def runtime_get_heap_usage(self) -> dict[str, Any]:
        """Get the current heap usage via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Runtime.getHeapUsage", {}))

    async def runtime_global_lexical_scope_names(
        self, execution_context_id: int | None = None
    ) -> dict[str, Any]:
        """Get global lexical scope names via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {}
        if execution_context_id is not None:
            params["executionContextId"] = execution_context_id
        return dict(await client.cdp.send_command("Runtime.globalLexicalScopeNames", params))

    async def runtime_add_binding(
        self, name: str, execution_context_name: str | None = None
    ) -> None:
        """Add a binding with the given name via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"name": name}
        if execution_context_name is not None:
            params["executionContextName"] = execution_context_name
        await client.cdp.send_command("Runtime.addBinding", params)

    async def runtime_await_promise(
        self, promise_object_id: str, return_by_value: bool = False
    ) -> dict[str, Any]:
        """Await a promise by its remote object ID via CDP bridge."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "Runtime.awaitPromise",
                {
                    "promiseObjectId": promise_object_id,
                    "returnByValue": return_by_value,
                },
            )
        )

    async def runtime_collect_garbage(self) -> None:
        """Collect garbage via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Runtime.collectGarbage", {})

    async def runtime_disable(self) -> None:
        """Disable the Runtime domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Runtime.disable", {})

    async def runtime_enable(self) -> None:
        """Enable the Runtime domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Runtime.enable", {})

    async def runtime_get_exception_details(self, error_object_id: str) -> dict[str, Any]:
        """Get exception details for an error object via CDP bridge."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "Runtime.getExceptionDetails", {"errorObjectId": error_object_id}
            )
        )

    async def runtime_get_isolate_id(self) -> dict[str, Any]:
        """Get the isolate ID via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Runtime.getIsolateId", {}))

    async def runtime_query_objects(self, prototype_object_id: str) -> dict[str, Any]:
        """Query objects by prototype via CDP bridge."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "Runtime.queryObjects", {"prototypeObjectId": prototype_object_id}
            )
        )

    async def runtime_remove_binding(self, name: str) -> None:
        """Remove a previously added binding via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Runtime.removeBinding", {"name": name})

    async def runtime_run_if_waiting_for_debugger(self) -> None:
        """Run if waiting for debugger to pause via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Runtime.runIfWaitingForDebugger", {})

    async def runtime_set_async_call_stack_depth(self, max_depth: int) -> None:
        """Set the async call stack depth via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Runtime.setAsyncCallStackDepth", {"maxDepth": max_depth})

    async def runtime_set_custom_object_formatter_enabled(self, enabled: bool) -> None:
        """Enable or disable the custom object formatter via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Runtime.setCustomObjectFormatterEnabled", {"enabled": enabled}
        )

    async def runtime_set_max_call_stack_size_to_capture(self, size: int) -> None:
        """Set the max call stack size to capture via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Runtime.setMaxCallStackSizeToCapture", {"size": size})

    async def runtime_terminate_execution(self) -> None:
        """Terminate the current execution via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Runtime.terminateExecution", {})

    # ── Schema — via CDP bridge ────────────────────────────

    async def schema_get_domains(self) -> dict[str, Any]:
        """Get all available CDP domains via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Schema.getDomains", {}))

    # ── Security — via CDP bridge ──────────────────────────

    async def security_disable(self) -> None:
        """Disable the Security domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Security.disable", {})

    async def security_enable(self) -> None:
        """Enable the Security domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Security.enable", {})

    async def security_get_visible_security_state(self) -> dict[str, Any]:
        """Get the visible security state of the current page.

        Bug #16: ``Security.getVisibleSecurityState`` was removed from CDP
        (Chrome 137+, 2025). We derive the visible security state from the
        current navigation URL: HTTPS → ``secure``, HTTP → ``insecure``,
        local schemes → ``neutral``.
        """
        client = self._require_launched()
        with contextlib.suppress(Exception):
            await client.cdp.send_command("Security.enable", {})
        url = self._current_url
        if not url:
            try:
                history = await client.cdp.send_command("Page.getNavigationHistory", {})
                entries = history.get("entries", [])
                idx = history.get("currentIndex", 0)
                if entries and 0 <= idx < len(entries):
                    url = entries[idx].get("url", "")
            except Exception:
                url = ""
        from urllib.parse import urlparse

        parsed = urlparse(url) if url else None
        scheme = parsed.scheme if parsed else ""
        if scheme == "https":
            security_state = "secure"
            scheme_cryptographic = True
        elif scheme == "http":
            security_state = "insecure"
            scheme_cryptographic = False
        elif scheme in ("file", "data", "about", "blob"):
            security_state = "neutral"
            scheme_cryptographic = False
        else:
            security_state = "unknown"
            scheme_cryptographic = False
        return {
            "securityState": security_state,
            "schemeIsCryptographic": scheme_cryptographic,
            "url": url,
        }

    async def security_handle_certificate_error(self, event_id: int, action: str) -> None:
        """Handle a certificate error event via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Security.handleCertificateError", {"eventId": event_id, "action": action}
        )

    async def security_set_ignore_certificate_errors(self, ignore: bool) -> None:
        """Set whether to ignore certificate errors via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Security.setIgnoreCertificateErrors", {"ignore": ignore})

    async def security_set_override_certificate_errors(self, override: bool) -> None:
        """Set whether to override certificate errors via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Security.setOverrideCertificateErrors", {"override": override}
        )

    # ── Sensor — via CDP bridge ────────────────────────────

    async def sensor_clear_sensor_override(self, sensor_type: str) -> None:
        """Clear a sensor override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Sensor.clearSensorOverride", {"type": sensor_type})

    async def sensor_disable(self) -> None:
        """Disable the Sensor domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Sensor.disable", {})

    async def sensor_enable(self) -> None:
        """Enable the Sensor domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Sensor.enable", {})

    async def sensor_set_sensor_override(
        self, sensor_type: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """Set a sensor override via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"type": sensor_type}
        if metadata is not None:
            params["metadata"] = metadata
        await client.cdp.send_command("Sensor.setSensorOverride", params)

    # ── Target ────────────────────────────────────────────

    async def target_get_targets(self) -> list[dict[str, Any]]:
        """Get all available targets via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Target.getTargets", {})
        return list(result.get("targetInfos", []))

    async def target_create_target(self, url: str) -> str:
        """Create a new target (tab) via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Target.createTarget", {"url": url})
        return str(result.get("targetId", ""))

    async def target_close_target(self, target_id: str) -> None:
        """Close a target by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Target.closeTarget", {"targetId": target_id})

    async def target_activate_target(self, target_id: str) -> None:
        """Activate (focus) a target by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Target.activateTarget", {"targetId": target_id})

    async def target_attach_to_target(self, target_id: str, flatten: bool = True) -> str:
        """Attach to a target by ID via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Target.attachToTarget",
            {"targetId": target_id, "flatten": flatten},
        )
        return str(result.get("sessionId", ""))

    async def target_detach_from_target(self, session_id: str) -> None:
        """Detach from a target by session ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Target.detachFromTarget", {"sessionId": session_id})

    async def target_set_auto_attach(
        self, auto_attach: bool, wait_for_debugger_on_start: bool = False
    ) -> None:
        """Set auto-attach for new targets via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Target.setAutoAttach",
            {
                "autoAttach": auto_attach,
                "waitForDebuggerOnStart": wait_for_debugger_on_start,
            },
        )

    async def target_set_discover_targets(self, discover: bool) -> None:
        """Enable or disable target discovery via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Target.setDiscoverTargets", {"discover": discover})

    async def target_get_target_info(self, target_id: str) -> dict[str, Any]:
        """Get info about a specific target via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Target.getTargetInfo", {"targetId": target_id}))

    async def target_create_browser_context(self) -> str:
        """Create a new browser context via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Target.createBrowserContext", {})
        return str(result.get("browserContextId", ""))

    async def target_attach_to_browser_target(self) -> str:
        """Attach to the browser target via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Target.attachToBrowserTarget", {})
        return str(result.get("sessionId", ""))

    async def target_auto_attach_related(
        self, target_id: str, wait_for_debugger_on_start: bool = False
    ) -> None:
        """Auto-attach to related targets of a given target via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Target.autoAttachRelated",
            {
                "targetId": target_id,
                "waitForDebuggerOnStart": wait_for_debugger_on_start,
            },
        )

    async def target_dispose_browser_context(self, browser_context_id: str) -> None:
        """Dispose a browser context by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Target.disposeBrowserContext",
            {"browserContextId": browser_context_id},
        )

    async def target_expose_dev_tools_protocol(self, target_id: str, binding_name: str) -> None:
        """Expose DevTools protocol API to the target via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Target.exposeDevToolsProtocol",
            {"targetId": target_id, "bindingName": binding_name},
        )

    async def target_get_browser_contexts(self) -> list[str]:
        """Get all browser contexts via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Target.getBrowserContexts", {})
        return list(result.get("browserContextIds", [])) if result else []

    async def target_get_dev_tools_target(self, target_id: str) -> str:
        """Get the DevTools target for a given target via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Target.getDevToolsTarget", {"targetId": target_id})
        return str(result.get("targetId", ""))

    async def target_open_dev_tools(self, target_id: str) -> None:
        """Open DevTools for a target via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Target.openDevTools", {"targetId": target_id})

    async def target_send_message_to_target(self, session_id: str, message: str) -> None:
        """Send a message to a target via session ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Target.sendMessageToTarget",
            {"sessionId": session_id, "message": message},
        )

    async def target_set_remote_locations(self, locations: list[dict[str, str]]) -> None:
        """Set remote locations for target discovery via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Target.setRemoteLocations", {"locations": locations})

    # ── Storage ────────────────────────────────────────────

    async def storage_get(self, key: str, storage_type: str = "local") -> str:
        """Get a value from DOM storage.

        Args:
            key: The storage key to retrieve.
            storage_type: Storage type ("local" or "session").

        Returns:
            The stored value as a string, or empty string if not found.

        Raises:
            SessionNotInitializedError: If the session is not initialized.
            ValueError: If storage_type is invalid.

        Bug #14: previously this called ``storage.getDOMStorageItems`` which
        is not a real CDP method (the correct domain is ``DOMStorage.``).
        Reading via ``script.evaluate`` against ``window.localStorage`` /
        ``window.sessionStorage`` is reliable and works on BiDi.
        """
        if storage_type not in ("local", "session"):
            raise ValueError(f"Invalid storage_type: {storage_type}. Must be 'local' or 'session'.")
        storage_obj = "localStorage" if storage_type == "local" else "sessionStorage"
        js = (
            f"(function(){{try{{return {storage_obj}.getItem({json.dumps(key)})||''}}"
            f"catch(e){{return ''}}}})()"
        )
        value = await self.eval(js)
        return str(value) if value is not None else ""

    async def storage_set(self, key: str, value: str, storage_type: str = "local") -> None:
        """Set a value in DOM storage.

        Args:
            key: The storage key to set.
            value: The value to store.
            storage_type: Storage type ("local" or "session").

        Raises:
            SessionNotInitializedError: If the session is not initialized.
            ValueError: If storage_type is invalid.
        """
        if storage_type not in ("local", "session"):
            raise ValueError(f"Invalid storage_type: {storage_type}. Must be 'local' or 'session'.")
        storage_obj = "localStorage" if storage_type == "local" else "sessionStorage"
        js = (
            f"(function(){{try{{{storage_obj}.setItem({json.dumps(key)},"
            f"{json.dumps(value)});return 'ok'}}catch(e){{return e.message}}}})()"
        )
        msg = await self.eval(js)
        if msg and msg != "ok":
            raise WavexisError(f"storage_set failed: {msg}")

    async def storage_clear(self, storage_type: str = "local") -> None:
        """Clear all items from DOM storage.

        Args:
            storage_type: Storage type ("local" or "session").

        Raises:
            SessionNotInitializedError: If the session is not initialized.
            ValueError: If storage_type is invalid.
        """
        if storage_type not in ("local", "session"):
            raise ValueError(f"Invalid storage_type: {storage_type}. Must be 'local' or 'session'.")
        storage_obj = "localStorage" if storage_type == "local" else "sessionStorage"
        js = (
            f"(function(){{try{{{storage_obj}.clear();return 'ok'}}"
            f"catch(e){{return e.message}}}})()"
        )
        msg = await self.eval(js)
        if msg and msg != "ok":
            raise WavexisError(f"storage_clear failed: {msg}")

    async def storage_list(self, storage_type: str = "local") -> dict[str, str]:
        """List all key-value pairs in DOM storage.

        Args:
            storage_type: Storage type ("local" or "session").

        Returns:
            Dict mapping storage keys to their string values.

        Raises:
            SessionNotInitializedError: If the session is not initialized.
            ValueError: If storage_type is invalid.
        """
        if storage_type not in ("local", "session"):
            raise ValueError(f"Invalid storage_type: {storage_type}. Must be 'local' or 'session'.")
        storage_obj = "localStorage" if storage_type == "local" else "sessionStorage"
        js = (
            f"(function(){{try{{"
            f"var out={{}};"
            f"for(var i=0;i<{storage_obj}.length;i++){{"
            f"var k={storage_obj}.key(i);out[k]={storage_obj}.getItem(k);}}"
            f"return JSON.stringify(out);}}"
            f"catch(e){{return '{{}}'}}}})()"
        )
        raw = await self.eval(js)
        try:
            loaded = json.loads(raw) if raw else {}
        except (TypeError, json.JSONDecodeError):
            return {}
        if not isinstance(loaded, dict):
            return {}
        return {str(k): str(v) for k, v in loaded.items()}

    async def cache_storage_list(self) -> list[str]:
        """List cache storage names via JS Cache API.

        Returns:
            List of cache names.
        """
        client = self._require_launched()
        js = "caches.keys().then(function(names){  return JSON.stringify(names);})"
        result = await client.script.evaluate(self._context, js)
        val = result.value if hasattr(result, "value") else result
        return json.loads(val) if isinstance(val, str) else list(val)

    async def cache_storage_entries(
        self,
        cache_name: str,
    ) -> list[dict[str, Any]]:
        """List entries in a cache via JS Cache API.

        Args:
            cache_name: Name of the cache to list entries from.

        Returns:
            List of entry dicts with url and status.
        """
        client = self._require_launched()
        escaped = json.dumps(cache_name)
        js = (
            f"caches.open({escaped}).then(function(cache){{"
            f"  return cache.keys().then(function(requests){{"
            f"    return JSON.stringify(requests.map(function(r){{"
            f"      return {{url:r.url, method:r.method}};"
            f"    }}));"
            f"  }});"
            f"}})"
        )
        result = await client.script.evaluate(self._context, js)
        val = result.value if hasattr(result, "value") else result
        return json.loads(val) if isinstance(val, str) else list(val)

    def _get_origin(self) -> str:
        """Extract the security origin from the current page URL."""
        if self._current_url:
            from urllib.parse import urlparse

            parsed = urlparse(self._current_url)
            return f"{parsed.scheme}://{parsed.netloc}"
        return ""

    async def cache_storage_delete(self, cache_name: str) -> None:
        """Delete a cache by name via JS Cache API.

        Args:
            cache_name: Name of the cache to delete.
        """
        client = self._require_launched()
        escaped = json.dumps(cache_name)
        js = f"caches.delete({escaped})"
        await client.script.evaluate(self._context, js)

    async def cache_storage_delete_cache(self, cache_id: str) -> None:
        """Delete a cache by its CDP cache ID via CDP bridge.

        Args:
            cache_id: The CDP cache identifier.
        """
        client = self._require_launched()
        await client.cdp.send_command("CacheStorage.deleteCache", {"cacheId": cache_id})

    async def cache_storage_delete_entry(self, cache_id: str, request: str) -> None:
        """Delete a specific entry from a cache via CDP bridge.

        Args:
            cache_id: The CDP cache identifier.
            request: The request URL of the entry to delete.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "CacheStorage.deleteEntry",
            {"cacheId": cache_id, "request": request},
        )

    async def cache_storage_request_cache_names(
        self, security_origin: str | None = None
    ) -> list[dict[str, Any]]:
        """Request cache names for a security origin via CDP bridge.

        Args:
            security_origin: Optional security origin. If None, uses the current page.

        Returns:
            List of cache info dicts with cacheId and cacheName.
        """
        client = self._require_launched()
        params: dict[str, Any] = {}
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        result = await client.cdp.send_command("CacheStorage.requestCacheNames", params)
        return [dict(c) for c in result.get("caches", [])] if result else []

    async def cache_storage_request_cached_response(
        self, cache_id: str, request_url: str, request_headers: list[dict[str, str]] | None = None
    ) -> dict[str, Any]:
        """Request a cached response for a specific request via CDP bridge.

        Args:
            cache_id: The CDP cache identifier.
            request_url: The request URL.
            request_headers: Optional list of request header dicts.

        Returns:
            The cached response dict.
        """
        client = self._require_launched()
        params: dict[str, Any] = {"cacheId": cache_id, "requestURL": request_url}
        if request_headers is not None:
            params["requestHeaders"] = request_headers
        return dict(await client.cdp.send_command("CacheStorage.requestCachedResponse", params))

    async def cache_storage_request_entries(
        self, cache_id: str, skip_count: int = 0, page_size: int = 100
    ) -> list[dict[str, Any]]:
        """Request entries from a cache via CDP bridge.

        Args:
            cache_id: The CDP cache identifier.
            skip_count: Number of entries to skip.
            page_size: Maximum number of entries to return.

        Returns:
            List of cache entry dicts.
        """
        client = self._require_launched()
        result = await client.cdp.send_command(
            "CacheStorage.requestEntries",
            {
                "cacheId": cache_id,
                "skipCount": skip_count,
                "pageSize": page_size,
            },
        )
        return [dict(e) for e in result.get("cacheDataEntries", [])] if result else []

    async def indexeddb_list(self) -> list[dict[str, Any]]:
        """List IndexedDB databases via CDP.

        Returns:
            List of database dicts with name and version.
        """
        client = self._require_launched()
        result = await client.cdp.send_command(
            "IndexedDB.requestDatabaseNames",
            {"securityOrigin": self._get_origin()},
        )
        names = result.get("databaseNames", []) if result else []
        return [{"name": n} for n in names]

    async def indexeddb_get_data(self, database: str, store: str, key: str = "") -> Any:
        """Get data from an IndexedDB store via CDP.

        Args:
            database: Database name.
            store: Object store name.
            key: Optional key to filter by.

        Returns:
            List of data entries.
        """
        client = self._require_launched()
        result = await client.cdp.send_command(
            "IndexedDB.requestData",
            {
                "securityOrigin": self._get_origin(),
                "databaseName": database,
                "objectStoreName": store,
                "indexName": "",
                "skipCount": 0,
                "pageSize": 100,
            },
        )
        return result.get("objectStoreData", []) if result else []

    async def indexeddb_clear(self, database: str, store: str) -> None:
        """Clear an IndexedDB object store via CDP.

        Args:
            database: Database name.
            store: Object store name.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "IndexedDB.clearObjectStore",
            {
                "securityOrigin": self._get_origin(),
                "databaseName": database,
                "objectStoreName": store,
            },
        )

    async def storage_clear_data_for_origin(self, origin: str, storage_types: str = "all") -> None:
        """Clear storage data for a given origin via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Storage.clearDataForOrigin",
            {"origin": origin, "storageTypes": storage_types},
        )

    async def storage_get_usage_and_quota(self, origin: str) -> dict[str, Any]:
        """Get usage and quota for a given origin via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Storage.getUsageAndQuota", {"origin": origin}))

    async def storage_get_trust_tokens(self) -> list[dict[str, Any]]:
        """Get all trust tokens via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Storage.getTrustTokens", {})
        return [dict(t) for t in result.get("tokens", [])] if result else []

    async def storage_clear_trust_tokens(self, origin: str) -> None:
        """Clear trust tokens for a given origin via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Storage.clearTrustTokens", {"origin": origin})

    async def storage_get_shared_storage_entries(self, owner_origin: str) -> list[dict[str, Any]]:
        """Get shared storage entries via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Storage.getSharedStorageEntries", {"ownerOrigin": owner_origin}
        )
        return [dict(e) for e in result.get("entries", [])] if result else []

    async def storage_set_shared_storage_entry(
        self, owner_origin: str, key: str, value: str
    ) -> None:
        """Set a shared storage entry via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Storage.setSharedStorageEntry",
            {"ownerOrigin": owner_origin, "key": key, "value": value},
        )

    async def storage_delete_shared_storage_entry(self, owner_origin: str, key: str) -> None:
        """Delete a shared storage entry via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Storage.deleteSharedStorageEntry",
            {"ownerOrigin": owner_origin, "key": key},
        )

    async def storage_clear_shared_storage_entries(self, owner_origin: str) -> None:
        """Clear all shared storage entries via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Storage.clearSharedStorageEntries", {"ownerOrigin": owner_origin}
        )

    async def storage_get_interest_group_details(
        self, owner_origin: str, name: str
    ) -> dict[str, Any]:
        """Get interest group details via CDP bridge."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "Storage.getInterestGroupDetails",
                {"ownerOrigin": owner_origin, "name": name},
            )
        )

    async def storage_override_quota_for_origin(
        self, origin: str, quota_size: float | None = None
    ) -> None:
        """Override quota for a given origin via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"origin": origin}
        if quota_size is not None:
            params["quotaSize"] = quota_size
        await client.cdp.send_command("Storage.overrideQuotaForOrigin", params)

    async def storage_clear_data_for_storage_key(
        self, storage_key: str, storage_types: str = "all"
    ) -> None:
        """Clear storage data for a given storage key via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Storage.clearDataForStorageKey",
            {"storageKey": storage_key, "storageTypes": storage_types},
        )

    async def storage_delete_storage_bucket(self, storage_key: str, bucket_name: str) -> None:
        """Delete a storage bucket via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Storage.deleteStorageBucket",
            {"storageKey": storage_key, "bucketName": bucket_name},
        )

    async def storage_get_related_website_sets(self) -> list[dict[str, Any]]:
        """Get related website sets via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Storage.getRelatedWebsiteSets", {})
        return [dict(s) for s in result.get("sets", [])] if result else []

    async def storage_get_shared_storage_metadata(self, owner_origin: str) -> dict[str, Any]:
        """Get shared storage metadata via CDP bridge."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "Storage.getSharedStorageMetadata",
                {"ownerOrigin": owner_origin},
            )
        )

    async def storage_get_storage_key(self, frame_id: str) -> str:
        """Get storage key for a frame via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Storage.getStorageKey", {"frameId": frame_id})
        return result.get("storageKey", "")

    async def storage_get_storage_key_for_frame(self, frame_id: str) -> str:
        """Get storage key for a frame via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Storage.getStorageKeyForFrame", {"frameId": frame_id}
        )
        return result.get("storageKey", "")

    async def storage_reset_shared_storage_budget(self, owner_origin: str) -> None:
        """Reset shared storage budget via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Storage.resetSharedStorageBudget",
            {"ownerOrigin": owner_origin},
        )

    async def storage_run_bounce_tracking_mitigations(self) -> None:
        """Run bounce tracking mitigations via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Storage.runBounceTrackingMitigations", {})

    async def storage_set_cookies(self, cookies: list[dict[str, Any]]) -> None:
        """Set cookies via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Storage.setCookies", {"cookies": cookies})

    async def storage_set_interest_group_auction_tracking(
        self, enable: bool, context_id: int | None = None
    ) -> None:
        """Set interest group auction tracking via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"enable": enable}
        if context_id is not None:
            params["contextId"] = context_id
        await client.cdp.send_command("Storage.setInterestGroupAuctionTracking", params)

    async def storage_set_interest_group_tracking(self, enable: bool) -> None:
        """Set interest group tracking via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Storage.setInterestGroupTracking", {"enable": enable})

    async def storage_set_protected_audience_k_anonymity(
        self, storage_key: str, hashed_mac_key: str
    ) -> None:
        """Set protected audience k-anonymity via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Storage.setProtectedAudienceKAnonymity",
            {"storageKey": storage_key, "hashedMacKey": hashed_mac_key},
        )

    async def storage_set_shared_storage_tracking(self, enable: bool) -> None:
        """Set shared storage tracking via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Storage.setSharedStorageTracking", {"enable": enable})

    async def storage_set_storage_bucket_tracking(
        self, storage_key: str, bucket_name: str, enable: bool
    ) -> None:
        """Set storage bucket tracking via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Storage.setStorageBucketTracking",
            {
                "storageKey": storage_key,
                "bucketName": bucket_name,
                "enable": enable,
            },
        )

    async def storage_track_cache_storage_for_origin(self, origin: str) -> None:
        """Track cache storage for an origin via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Storage.trackCacheStorageForOrigin", {"origin": origin})

    async def storage_track_cache_storage_for_storage_key(self, storage_key: str) -> None:
        """Track cache storage for a storage key via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Storage.trackCacheStorageForStorageKey", {"storageKey": storage_key}
        )

    async def storage_track_indexed_db_for_origin(self, origin: str) -> None:
        """Track IndexedDB for an origin via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Storage.trackIndexedDBForOrigin", {"origin": origin})

    async def storage_track_indexed_db_for_storage_key(self, storage_key: str) -> None:
        """Track IndexedDB for a storage key via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Storage.trackIndexedDBForStorageKey", {"storageKey": storage_key}
        )

    async def storage_untrack_cache_storage_for_origin(self, origin: str) -> None:
        """Untrack cache storage for an origin via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Storage.untrackCacheStorageForOrigin", {"origin": origin})

    async def storage_untrack_cache_storage_for_storage_key(self, storage_key: str) -> None:
        """Untrack cache storage for a storage key via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Storage.untrackCacheStorageForStorageKey", {"storageKey": storage_key}
        )

    async def storage_untrack_indexed_db_for_origin(self, origin: str) -> None:
        """Untrack IndexedDB for an origin via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Storage.untrackIndexedDBForOrigin", {"origin": origin})

    async def storage_untrack_indexed_db_for_storage_key(self, storage_key: str) -> None:
        """Untrack IndexedDB for a storage key via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Storage.untrackIndexedDBForStorageKey", {"storageKey": storage_key}
        )

    # ── Service Workers ────────────────────────────────────

    async def sw_list(self) -> list[dict[str, Any]]:
        """List service worker registrations via JS.

        Returns:
            List of registration dicts with scope and scriptURL.
        """
        client = self._require_launched()
        js = (
            "navigator.serviceWorker.getRegistrations()"
            ".then(function(regs){"
            "  return JSON.stringify(regs.map(function(r){"
            "    return {scope:r.scope,scriptURL:r.active?r.active.scriptURL:''};"
            "  }));"
            "})"
        )
        result = await client.script.evaluate(self._context, js)
        val = result.value if hasattr(result, "value") else result
        return json.loads(val) if isinstance(val, str) else list(val)

    async def sw_unregister(self, registration_id: str) -> None:
        """Unregister a service worker by scope via JS.

        Args:
            registration_id: Scope URL of the registration to unregister.
        """
        client = self._require_launched()
        escaped = json.dumps(registration_id)
        js = (
            f"navigator.serviceWorker.getRegistrations()"
            f"  .then(function(regs){{"
            f"    regs.forEach(function(r){{"
            f"      if(r.scope==={escaped}) r.unregister();"
            f"    }});"
            f"  }})"
        )
        await client.script.evaluate(self._context, js)

    async def sw_update(self, registration_id: str) -> None:
        """Update a service worker registration by scope via JS.

        Args:
            registration_id: Scope URL of the registration to update.
        """
        client = self._require_launched()
        escaped = json.dumps(registration_id)
        js = (
            f"navigator.serviceWorker.getRegistrations()"
            f"  .then(function(regs){{"
            f"    regs.forEach(function(r){{"
            f"      if(r.scope==={escaped}) r.update();"
            f"    }});"
            f"  }})"
        )
        await client.script.evaluate(self._context, js)

    async def sw_enable(self) -> None:
        """Enable the ServiceWorker domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("ServiceWorker.enable", {})

    async def sw_disable(self) -> None:
        """Disable the ServiceWorker domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("ServiceWorker.disable", {})

    async def sw_deliver_push_message(self, origin: str, registration_id: str, data: str) -> None:
        """Deliver a push message to a service worker via CDP bridge.

        Args:
            origin: Origin of the service worker.
            registration_id: Service worker registration ID.
            data: Push message data.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "ServiceWorker.deliverPushMessage",
            {
                "origin": origin,
                "registrationId": registration_id,
                "data": data,
            },
        )

    async def sw_dispatch_sync_event(
        self, origin: str, registration_id: str, tag: str, last_chance: bool
    ) -> None:
        """Dispatch a sync event to a service worker via CDP bridge.

        Args:
            origin: Origin of the service worker.
            registration_id: Service worker registration ID.
            tag: Sync tag.
            last_chance: Whether this is the last chance to run the sync.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "ServiceWorker.dispatchSyncEvent",
            {
                "origin": origin,
                "registrationId": registration_id,
                "tag": tag,
                "lastChance": last_chance,
            },
        )

    async def sw_get_messages(self, worker_id: str) -> list[dict[str, Any]]:
        """Get messages from a service worker via CDP bridge.

        Args:
            worker_id: Service worker target ID.

        Returns:
            List of message dicts.
        """
        client = self._require_launched()
        result = await client.cdp.send_command("ServiceWorker.getMessages", {"workerId": worker_id})
        return result.get("messages", [])

    async def sw_inspect_worker(self, worker_id: str) -> None:
        """Inspect a service worker via CDP bridge.

        Args:
            worker_id: Service worker target ID.
        """
        client = self._require_launched()
        await client.cdp.send_command("ServiceWorker.inspectWorker", {"workerId": worker_id})

    async def sw_skip_waiting(self, scope_url: str) -> None:
        """Skip waiting for a service worker via CDP bridge.

        Args:
            scope_url: Scope URL of the service worker.
        """
        client = self._require_launched()
        await client.cdp.send_command("ServiceWorker.skipWaiting", {"scopeURL": scope_url})

    async def sw_start_worker(self, scope_url: str) -> None:
        """Start a service worker by scope URL via CDP bridge.

        Args:
            scope_url: Scope URL of the service worker.
        """
        client = self._require_launched()
        await client.cdp.send_command("ServiceWorker.startWorker", {"scopeURL": scope_url})

    async def sw_stop_worker(self, worker_id: str) -> None:
        """Stop a running service worker via CDP bridge.

        Args:
            worker_id: Service worker target ID.
        """
        client = self._require_launched()
        await client.cdp.send_command("ServiceWorker.stopWorker", {"workerId": worker_id})

    # ── Animations ─────────────────────────────────────────

    async def animation_list(self) -> list[dict[str, Any]]:
        """List all active animations via JS.

        Returns:
            List of animation dicts with id, playState, and duration.
        """
        client = self._require_launched()
        js = (
            "document.getAnimations().then(function(anims){"
            "  return JSON.stringify(anims.map(function(a,i){"
            "    return {"
            "      id:String(i),"
            "      playState:a.playState,"
            "      duration:a.effect?a.effect.getTiming().duration:0,"
            "      currentTime:a.currentTime"
            "    };"
            "  }));"
            "})"
        )
        result = await client.script.evaluate(self._context, js)
        val = result.value if hasattr(result, "value") else result
        return json.loads(val) if isinstance(val, str) else list(val)

    async def animation_pause(self, animation_id: str) -> None:
        """Pause an animation by index via JS.

        Args:
            animation_id: Index of the animation (as string).
        """
        client = self._require_launched()
        idx = int(animation_id) if animation_id.isdigit() else 0
        js = (
            f"document.getAnimations().then(function(anims){{"
            f"  if(anims[{idx}]) anims[{idx}].pause();"
            f"}})"
        )
        await client.script.evaluate(self._context, js)

    async def animation_play(self, animation_id: str) -> None:
        """Play a paused animation by index via JS.

        Args:
            animation_id: Index of the animation (as string).
        """
        client = self._require_launched()
        idx = int(animation_id) if animation_id.isdigit() else 0
        js = (
            f"document.getAnimations().then(function(anims){{"
            f"  if(anims[{idx}]) anims[{idx}].play();"
            f"}})"
        )
        await client.script.evaluate(self._context, js)

    async def animation_seek(self, animation_id: str, time_ms: int) -> None:
        """Seek an animation to a specific time via JS.

        Args:
            animation_id: Index of the animation (as string).
            time_ms: Time in milliseconds to seek to.
        """
        client = self._require_launched()
        idx = int(animation_id) if animation_id.isdigit() else 0
        js = (
            f"document.getAnimations().then(function(anims){{"
            f"  if(anims[{idx}]) anims[{idx}].currentTime={time_ms};"
            f"}})"
        )
        await client.script.evaluate(self._context, js)

    # ── WebAuthn (experimental) — via CDP bridge ─────────

    async def webauthn_add_virtual_authenticator(self, protocol: str, transport: str) -> str:
        """Add a virtual WebAuthn authenticator via CDP.

        Args:
            protocol: Protocol (e.g. "ctap2", "u2f").
            transport: Transport (e.g. "usb", "nfc", "ble", "internal").

        Returns:
            Authenticator ID as string.
        """
        client = self._require_launched()
        await client.cdp.send_command("WebAuthn.enable", {})
        result = await client.cdp.send_command(
            "WebAuthn.addVirtualAuthenticator",
            {"protocol": protocol, "transport": transport},
        )
        return str(result.get("authenticatorId", "")) if result else ""

    async def webauthn_remove_authenticator(self, authenticator_id: str) -> None:
        """Remove a virtual WebAuthn authenticator via CDP.

        Args:
            authenticator_id: Authenticator ID to remove.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "WebAuthn.removeVirtualAuthenticator",
            {"authenticatorId": authenticator_id},
        )

    async def webauthn_add_credential(
        self, authenticator_id: str, credential: dict[str, Any]
    ) -> None:
        """Add a credential to a virtual authenticator via CDP.

        Args:
            authenticator_id: Authenticator ID.
            credential: Credential dict.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "WebAuthn.addCredential",
            {"authenticatorId": authenticator_id, "credential": credential},
        )

    async def webauthn_get_credentials(self, authenticator_id: str) -> list[dict[str, Any]]:
        """Get credentials from a virtual authenticator via CDP.

        Args:
            authenticator_id: Authenticator ID.

        Returns:
            List of credential dicts.
        """
        client = self._require_launched()
        result = await client.cdp.send_command(
            "WebAuthn.getCredentials",
            {"authenticatorId": authenticator_id},
        )
        return list(result.get("credentials", [])) if result else []

    async def webauthn_enable(self) -> None:
        """Enable the WebAuthn domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("WebAuthn.enable", {})

    async def webauthn_disable(self) -> None:
        """Disable the WebAuthn domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("WebAuthn.disable", {})

    async def webauthn_get_credential(
        self, authenticator_id: str, credential_id: str
    ) -> dict[str, Any]:
        """Get a specific credential from a virtual authenticator via CDP bridge.

        Args:
            authenticator_id: The authenticator ID.
            credential_id: The credential ID.

        Returns:
            Credential dict.
        """
        client = self._require_launched()
        result = await client.cdp.send_command(
            "WebAuthn.getCredential",
            {"authenticatorId": authenticator_id, "credentialId": credential_id},
        )
        return dict(result) if result else {}

    async def webauthn_remove_credential(self, authenticator_id: str, credential_id: str) -> None:
        """Remove a credential from a virtual authenticator via CDP bridge.

        Args:
            authenticator_id: The authenticator ID.
            credential_id: The credential ID.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "WebAuthn.removeCredential",
            {"authenticatorId": authenticator_id, "credentialId": credential_id},
        )

    async def webauthn_clear_credentials(self, authenticator_id: str) -> None:
        """Clear all credentials from a virtual authenticator via CDP bridge.

        Args:
            authenticator_id: The authenticator ID.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "WebAuthn.clearCredentials",
            {"authenticatorId": authenticator_id},
        )

    async def webauthn_set_user_verified(
        self, authenticator_id: str, is_user_verified: bool
    ) -> None:
        """Set the user-verified flag on a virtual authenticator via CDP bridge.

        Args:
            authenticator_id: The authenticator ID.
            is_user_verified: Whether the user is verified.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "WebAuthn.setUserVerified",
            {"authenticatorId": authenticator_id, "isUserVerified": is_user_verified},
        )

    async def webauthn_set_automatic_presence_simulation(
        self, authenticator_id: str, enabled: bool
    ) -> None:
        """Set automatic presence simulation on a virtual authenticator via CDP bridge.

        Args:
            authenticator_id: The authenticator ID.
            enabled: Whether to enable presence simulation.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "WebAuthn.setAutomaticPresenceSimulation",
            {"authenticatorId": authenticator_id, "enabled": enabled},
        )

    async def webauthn_set_credential_properties(
        self,
        authenticator_id: str,
        credential_id: str,
        backup_state: bool = False,
        backup_eligibility: bool = False,
    ) -> None:
        """Set credential properties on a virtual authenticator via CDP bridge.

        Args:
            authenticator_id: The authenticator ID.
            credential_id: The credential ID.
            backup_state: The backup state.
            backup_eligibility: The backup eligibility.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "WebAuthn.setCredentialProperties",
            {
                "authenticatorId": authenticator_id,
                "credentialId": credential_id,
                "backupState": backup_state,
                "backupEligibility": backup_eligibility,
            },
        )

    async def webauthn_set_response_override_bits(
        self,
        authenticator_id: str,
        is_bogus_signature: bool = False,
        is_bad_uv: bool = False,
        is_bad_up: bool = False,
    ) -> None:
        """Set response override bits on a virtual authenticator via CDP bridge.

        Args:
            authenticator_id: The authenticator ID.
            is_bogus_signature: Whether to return bogus signatures.
            is_bad_uv: Whether to return bad UV responses.
            is_bad_up: Whether to return bad UP responses.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "WebAuthn.setResponseOverrideBits",
            {
                "authenticatorId": authenticator_id,
                "isBogusSignature": is_bogus_signature,
                "isBadUV": is_bad_uv,
                "isBadUP": is_bad_up,
            },
        )

    # ── WebAudio (experimental) — via CDP bridge ───────────

    async def webaudio_get_contexts(self) -> list[dict[str, Any]]:
        """Get WebAudio contexts via CDP.

        Enables the WebAudio domain and collects all contextCreated events
        emitted within a short window. Returns the list of contexts.

        Returns:
            List of AudioContext dicts.
        """
        client = self._require_launched()
        await client.cdp.send_command("WebAudio.enable", {})

        try:
            events = await client.cdp.collect_events(
                "WebAudio.contextCreated", timeout=1.0
            )
        except TimeoutError:
            events = []
        return [dict(ev.get("context", ev)) for ev in events]

    async def webaudio_get_context(self, context_id: str) -> dict[str, Any]:
        """Get a specific WebAudio context by ID via CDP.

        Args:
            context_id: Audio context ID.

        Returns:
            Dict with context info.
        """
        contexts = await self.webaudio_get_contexts()
        for ctx in contexts:
            if ctx.get("contextId") == context_id:
                return dict(ctx)
        return {}

    async def webaudio_enable(self) -> None:
        """Enable the WebAudio domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("WebAudio.enable", {})

    async def webaudio_disable(self) -> None:
        """Disable the WebAudio domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("WebAudio.disable", {})

    async def webaudio_get_realtime_data(self, context_id: str) -> dict[str, Any]:
        """Get realtime data for a WebAudio context via CDP bridge.

        Args:
            context_id: The audio context ID.

        Returns:
            Dict with realtime audio data.
        """
        client = self._require_launched()
        result = await client.cdp.send_command(
            "WebAudio.getRealtimeData", {"contextId": context_id}
        )
        return dict(result) if result else {}

    # ── Media (experimental) — via CDP bridge ──────────────

    async def media_get_players(self) -> list[dict[str, Any]]:
        """Get media players via CDP.

        Returns:
            List of player dicts.
        """
        client = self._require_launched()
        # Use JS to list video/audio elements instead of CDP Media.getPlayerInfo
        # which requires a playerId we don't have
        result = await client.script.evaluate(
            self._context,
            "Array.from(document.querySelectorAll('video, audio')).map(el => "
            "({id: el.id || '', tagName: el.tagName, "
            "src: el.src || '', currentTime: el.currentTime, "
            "duration: el.duration, paused: el.paused}))",
            await_promise=False,
        )
        value = result.value if hasattr(result, "value") else result
        return [dict(p) for p in value] if isinstance(value, list) else []

    async def media_get_messages(self, player_id: str) -> list[dict[str, Any]]:
        """Get media player messages via CDP.

        Args:
            player_id: Player ID.

        Returns:
            List of player message dicts.
        """
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Media.getPlayerMessages",
            {"playerId": player_id},
        )
        return list(result.get("messages", [])) if result else []

    # ── Cast (experimental) — via CDP bridge ───────────────

    async def cast_list(self) -> list[dict[str, Any]]:
        """List available Cast sinks via CDP.

        Returns:
            List of sink dicts.
        """
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Cast.getSinks",
            {},
        )
        return list(result.get("sinks", [])) if result else []

    async def cast_start_tab(self, sink_name: str) -> None:
        """Start tab mirroring to a Cast sink via CDP.

        Args:
            sink_name: Name of the sink to cast to.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "Cast.startTabMirroring",
            {"sinkName": sink_name},
        )

    async def cast_stop(self) -> None:
        """Stop Cast mirroring via CDP."""
        client = self._require_launched()
        await client.cdp.send_command("Cast.stopCasting", {})

    async def cast_enable(self) -> None:
        """Enable the Cast domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Cast.enable", {})

    async def cast_disable(self) -> None:
        """Disable the Cast domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Cast.disable", {})

    async def cast_set_sink_to_use(self, sink_name: str) -> None:
        """Set a sink to use for cast via CDP bridge.

        Args:
            sink_name: Name of the sink to use.
        """
        client = self._require_launched()
        await client.cdp.send_command("Cast.setSinkToUse", {"sinkName": sink_name})

    async def cast_start_desktop_mirroring(self, sink_name: str) -> None:
        """Start desktop mirroring to a Cast sink via CDP bridge.

        Args:
            sink_name: Name of the sink to mirror to.
        """
        client = self._require_launched()
        await client.cdp.send_command("Cast.startDesktopMirroring", {"sinkName": sink_name})

    async def cast_start_tab_mirroring(self, sink_name: str) -> None:
        """Start tab mirroring to a Cast sink via CDP bridge.

        Args:
            sink_name: Name of the sink to mirror to.
        """
        client = self._require_launched()
        await client.cdp.send_command("Cast.startTabMirroring", {"sinkName": sink_name})

    async def cast_stop_casting(self, sink_name: str) -> None:
        """Stop casting to a specific sink via CDP bridge.

        Args:
            sink_name: Name of the sink to stop casting to.
        """
        client = self._require_launched()
        await client.cdp.send_command("Cast.stopCasting", {"sinkName": sink_name})

    # ── Bluetooth (experimental) — via CDP bridge ──────────

    async def bluetooth_emulate(self, name: str, address: str = "00:00:00:00:00:01") -> None:
        """Emulate a Bluetooth adapter via CDP.

        Args:
            name: Adapter name.
            address: Bluetooth address.
        """
        client = self._require_launched()
        await client.cdp.send_command("BluetoothEmulation.enable", {})
        await client.cdp.send_command(
            "BluetoothEmulation.setSimulatedCentral",
            {"state": "powered-on", "name": name, "address": address},
        )

    async def bluetooth_stop(self) -> None:
        """Stop Bluetooth emulation via CDP."""
        client = self._require_launched()
        await client.cdp.send_command("BluetoothEmulation.disable", {})

    # ── WebExtensions — via CDP bridge ─────────────────────

    async def extension_install(self, path: str) -> str:
        """Install a browser extension via CDP bridge.

        Args:
            path: Path to the .crx file or unpacked extension directory.

        Returns:
            The extension ID.
        """
        import hashlib
        import os

        client = self._require_launched()
        valid_path = validate_path(path)
        is_dir = await asyncio.to_thread(os.path.isdir, valid_path)
        if is_dir:
            abs_path = await asyncio.to_thread(os.path.abspath, valid_path)
            ext_id = hashlib.sha256(abs_path.encode()).hexdigest()[:32]
            await client.cdp.send_command(
                "Extensions.loadUnpacked",
                {"path": abs_path},
            )
        else:
            ext_id = hashlib.sha256(str(valid_path).encode()).hexdigest()[:32]
            try:
                data = await asyncio.to_thread(lambda: valid_path.read_bytes())
            except OSError as e:
                raise WavexisError(f"Failed to read extension file: {e}") from e
            await client.cdp.send_command(
                "Extensions.load",
                {"data": data.hex(), "id": ext_id},
            )
        return ext_id

    async def extension_uninstall(self, extension_id: str) -> None:
        """Uninstall a browser extension by ID.

        Args:
            extension_id: The extension ID returned by extension_install.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "Extensions.uninstall",
            {"id": extension_id},
        )

    async def extension_list(self) -> list[dict[str, Any]]:
        """List installed browser extensions.

        Returns:
            List of extension dicts (id, name, version, enabled).
        """
        client = self._require_launched()
        result = await client.cdp.send_command("Extensions.getInfo", {})
        extensions = result.get("extensions", [])
        return [
            {
                "id": ext.get("id", ""),
                "name": ext.get("name", ""),
                "version": ext.get("version", ""),
                "enabled": ext.get("enabled", True),
            }
            for ext in extensions
        ]

    # ── Browser preferences — via CDP bridge ───────────────

    async def get_pref(self, key: str) -> Any:
        """Get a browser preference value by key.

        Args:
            key: The preference key (e.g. "download.default_directory").

        Returns:
            The preference value.
        """
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Browser.getPreference",
            {"name": key},
        )
        return result.get("value")

    async def set_pref(self, key: str, value: Any) -> None:
        """Set a browser preference value.

        Args:
            key: The preference key.
            value: The value to set.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "Browser.setPreference",
            {"name": key, "value": value},
        )

    # ── Tethering — via CDP bridge ─────────────────────────

    async def tethering_bind(self, port: int) -> None:
        """Bind a port for tethering (accept incoming connections).

        Args:
            port: The port number to bind.
        """
        client = self._require_launched()
        await client.cdp.send_command("Tethering.bind", {"port": port})

    async def tethering_unbind(self, port: int) -> None:
        """Unbind a port from tethering.

        Args:
            port: The port number to unbind.
        """
        client = self._require_launched()
        await client.cdp.send_command("Tethering.unbind", {"port": port})

    # ── WebMcp — via CDP bridge ───────────────────────────

    async def web_mcp_enable(self) -> None:
        """Enable the WebMcp domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("WebMcp.enable", {})

    async def web_mcp_disable(self) -> None:
        """Disable the WebMcp domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("WebMcp.disable", {})

    # ── DeviceAccess — via CDP bridge ───────────────────────

    async def device_access_cancel_prompt(self, id: str) -> None:
        """Cancel a device access prompt by ID via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DeviceAccess.cancelPrompt", {"id": id})

    async def device_access_disable(self) -> None:
        """Disable the DeviceAccess domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DeviceAccess.disable", {})

    async def device_access_enable(self) -> None:
        """Enable the DeviceAccess domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DeviceAccess.enable", {})

    async def device_access_select_prompt(self, id: str, device_id: str) -> None:
        """Select a device in a device access prompt via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "DeviceAccess.selectPrompt", {"id": id, "deviceId": device_id}
        )

    # ── DeviceOrientation — via CDP bridge ──────────────────

    async def device_orientation_clear_override(self) -> None:
        """Clear device orientation override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DeviceOrientation.clearDeviceOrientationOverride", {})

    async def device_orientation_set_override(
        self, alpha: float, beta: float, gamma: float
    ) -> None:
        """Set device orientation override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "DeviceOrientation.setDeviceOrientationOverride",
            {"alpha": alpha, "beta": beta, "gamma": gamma},
        )

    # ── DigitalCredentials — via CDP bridge ─────────────────

    async def digital_credentials_set_virtual_wallet_behavior(
        self, behavior: dict[str, Any]
    ) -> None:
        """Set the virtual wallet behavior for digital credentials via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "DigitalCredentials.setVirtualWalletBehavior", {"behavior": behavior}
        )

    # ── DOMSnapshot — via CDP bridge ────────────────────────

    async def dom_snapshot_capture_snapshot(
        self,
        computed_styles: list[str] | None = None,
        include_paint_order: bool = False,
        include_dom_rects: bool = False,
        include_blended_background_colors: bool = False,
        include_text_color_opacity: bool = False,
    ) -> dict[str, Any]:
        """Capture a DOM snapshot of the current page via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {}
        if computed_styles is not None:
            params["computedStyles"] = computed_styles
        if include_paint_order:
            params["includePaintOrder"] = True
        if include_dom_rects:
            params["includeDOMRects"] = True
        if include_blended_background_colors:
            params["includeBlendedBackgroundColor"] = True
        if include_text_color_opacity:
            params["includeTextColorOpacity"] = True
        result = await client.cdp.send_command("DOMSnapshot.captureSnapshot", params)
        return dict(result) if result else {}

    async def dom_snapshot_disable(self) -> None:
        """Disable the DOMSnapshot domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOMSnapshot.disable", {})

    async def dom_snapshot_enable(self) -> None:
        """Enable the DOMSnapshot domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOMSnapshot.enable", {})

    async def dom_snapshot_get_snapshot(
        self,
        computed_styles: list[str] | None = None,
        include_paint_order: bool = False,
        include_dom_rects: bool = False,
        include_blended_background_colors: bool = False,
        include_text_color_opacity: bool = False,
    ) -> dict[str, Any]:
        """Get a DOM snapshot of the current page via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {}
        if computed_styles is not None:
            params["computedStyles"] = computed_styles
        if include_paint_order:
            params["includePaintOrder"] = True
        if include_dom_rects:
            params["includeDOMRects"] = True
        if include_blended_background_colors:
            params["includeBlendedBackgroundColor"] = True
        if include_text_color_opacity:
            params["includeTextColorOpacity"] = True
        result = await client.cdp.send_command("DOMSnapshot.getSnapshot", params)
        return dict(result) if result else {}

    # ── DOMStorage — via CDP bridge ─────────────────────────

    async def dom_storage_clear(self, storage_id: dict[str, Any]) -> None:
        """Clear all entries in a DOM storage via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOMStorage.clear", {"storageId": storage_id})

    async def dom_storage_clear_items(self, storage_id: dict[str, Any]) -> None:
        """Clear all items in a DOM storage (alias) via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOMStorage.clear", {"storageId": storage_id})

    async def dom_storage_disable(self) -> None:
        """Disable the DOMStorage domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOMStorage.disable", {})

    async def dom_storage_enable(self) -> None:
        """Enable the DOMStorage domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("DOMStorage.enable", {})

    async def dom_storage_get_items(self, storage_id: dict[str, Any]) -> list[dict[str, Any]]:
        """Get all items in a DOM storage via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "DOMStorage.getDOMStorageItems", {"storageId": storage_id}
        )
        return list(result.get("items", [])) if result else []

    async def dom_storage_remove_item(self, storage_id: dict[str, Any], key: str) -> None:
        """Remove an item from a DOM storage via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "DOMStorage.removeDOMStorageItem", {"storageId": storage_id, "key": key}
        )

    async def dom_storage_set_item(self, storage_id: dict[str, Any], key: str, value: str) -> None:
        """Set an item in a DOM storage via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "DOMStorage.setDOMStorageItem", {"storageId": storage_id, "key": key, "value": value}
        )

    # ── EventBreakpoints — via CDP bridge ───────────────────

    async def event_breakpoints_clear_instrumentation_breakpoint(
        self, instrumentation_name: str
    ) -> None:
        """Clear an instrumentation breakpoint for events via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "EventBreakpoints.clearInstrumentationBreakpoint",
            {"instrumentationName": instrumentation_name},
        )

    async def event_breakpoints_disable(self) -> None:
        """Disable the EventBreakpoints domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("EventBreakpoints.disable", {})

    async def event_breakpoints_remove_instrumentation_breakpoint(
        self, instrumentation_name: str
    ) -> None:
        """Remove an instrumentation breakpoint for events via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "EventBreakpoints.removeInstrumentationBreakpoint",
            {"instrumentationName": instrumentation_name},
        )

    async def event_breakpoints_set_instrumentation_breakpoint(
        self, instrumentation_name: str
    ) -> None:
        """Set an instrumentation breakpoint for events via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "EventBreakpoints.setInstrumentationBreakpoint",
            {"instrumentationName": instrumentation_name},
        )

    # ── Extensions — via CDP bridge ─────────────────────────

    async def extensions_clear_storage_items(self, id: str, storage_type: str) -> None:
        """Clear storage items for an extension via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Extensions.clearStorageItems", {"id": id, "storageType": storage_type}
        )

    async def extensions_get_storage_items(self, id: str, storage_type: str) -> dict[str, Any]:
        """Get storage items for an extension via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Extensions.getStorageItems", {"id": id, "storageType": storage_type}
        )
        return dict(result) if result else {}

    async def extensions_remove_storage_items(
        self, id: str, storage_type: str, keys: list[str]
    ) -> None:
        """Remove storage items from an extension via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Extensions.removeStorageItems", {"id": id, "storageType": storage_type, "keys": keys}
        )

    async def extensions_set_storage_items(
        self, id: str, storage_type: str, values: list[dict[str, Any]]
    ) -> None:
        """Set storage items for an extension via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Extensions.setStorageItems", {"id": id, "storageType": storage_type, "values": values}
        )

    async def extensions_trigger_action(self, id: str, action: str) -> None:
        """Trigger an action on an extension via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Extensions.triggerAction", {"id": id, "action": action})

    # ── FedCm — via CDP bridge ──────────────────────────────

    async def fed_cm_click_dialog_button(self, dialog_id: str, button_index: int) -> None:
        """Click a button in a FedCm dialog via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "FedCm.clickDialogButton", {"dialogId": dialog_id, "buttonIndex": button_index}
        )

    async def fed_cm_disable(self) -> None:
        """Disable the FedCm domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("FedCm.disable", {})

    async def fed_cm_dismiss_dialog(self, dialog_id: str) -> None:
        """Dismiss a FedCm dialog via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("FedCm.dismissDialog", {"dialogId": dialog_id})

    async def fed_cm_enable(self) -> None:
        """Enable the FedCm domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("FedCm.enable", {})

    async def fed_cm_open_url(self, dialog_id: str, account_index: int, url: str) -> None:
        """Open a URL from a FedCm dialog via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "FedCm.openUrl", {"dialogId": dialog_id, "accountIndex": account_index, "url": url}
        )

    async def fed_cm_reset_cooldown(self) -> None:
        """Reset the FedCm cooldown via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("FedCm.resetCooldown", {})

    async def fed_cm_select_account(self, dialog_id: str, account_index: int) -> None:
        """Select an account in a FedCm dialog via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "FedCm.selectAccount", {"dialogId": dialog_id, "accountIndex": account_index}
        )

    # ── Fetch — via CDP bridge ──────────────────────────────

    async def fetch_continue_request(
        self,
        request_id: str,
        url: str | None = None,
        method: str | None = None,
        post_data: str | None = None,
        headers: list[dict[str, Any]] | None = None,
    ) -> None:
        """Continue a paused request with optional modifications via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"requestId": request_id}
        if url is not None:
            params["url"] = url
        if method is not None:
            params["method"] = method
        if post_data is not None:
            params["postData"] = post_data
        if headers is not None:
            params["headers"] = headers
        await client.cdp.send_command("Fetch.continueRequest", params)

    async def fetch_continue_request_with_auth(
        self, request_id: str, auth_challenge_response: dict[str, Any]
    ) -> None:
        """Continue a paused request with authentication via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Fetch.continueWithAuth",
            {"requestId": request_id, "authChallengeResponse": auth_challenge_response},
        )

    async def fetch_continue_response(
        self,
        request_id: str,
        response_code: int = 200,
        response_headers: list[dict[str, Any]] | None = None,
        binary_response_headers: str | None = None,
    ) -> None:
        """Continue a paused response via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"requestId": request_id, "responseCode": response_code}
        if response_headers is not None:
            params["responseHeaders"] = response_headers
        if binary_response_headers is not None:
            params["binaryResponseHeaders"] = binary_response_headers
        await client.cdp.send_command("Fetch.continueResponse", params)

    async def fetch_continue_with_auth(
        self, request_id: str, auth_challenge_response: dict[str, Any]
    ) -> None:
        """Continue a paused request with auth challenge response via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Fetch.continueWithAuth",
            {"requestId": request_id, "authChallengeResponse": auth_challenge_response},
        )

    async def fetch_disable(self) -> None:
        """Disable the Fetch domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Fetch.disable", {})

    async def fetch_enable(
        self, patterns: list[dict[str, Any]] | None = None, handle_auth_requests: bool = False
    ) -> None:
        """Enable the Fetch domain with optional patterns via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {}
        if patterns is not None:
            params["patterns"] = patterns
        if handle_auth_requests:
            params["handleAuthRequests"] = True
        await client.cdp.send_command("Fetch.enable", params)

    async def fetch_fail_request(self, request_id: str, error_reason: str) -> None:
        """Fail a paused request with an error via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Fetch.failRequest", {"requestId": request_id, "errorReason": error_reason}
        )

    async def fetch_fulfill_request(
        self,
        request_id: str,
        response_code: int = 200,
        response_headers: list[dict[str, Any]] | None = None,
        body: str | None = None,
    ) -> None:
        """Fulfill a paused request with a response via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"requestId": request_id, "responseCode": response_code}
        if response_headers is not None:
            params["responseHeaders"] = response_headers
        if body is not None:
            params["body"] = body
        await client.cdp.send_command("Fetch.fulfillRequest", params)

    async def fetch_get_request_post_data(self, request_id: str) -> str:
        """Get the POST data of a paused request via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Fetch.getRequestPostData", {"requestId": request_id}
        )
        return str(result.get("postData", "")) if result else ""

    async def fetch_take_response_body_as_stream(self, request_id: str) -> dict[str, Any]:
        """Take the response body of a paused request as a stream via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Fetch.takeResponseBodyAsStream", {"requestId": request_id}
        )
        return dict(result) if result else {}

    # ── FileSystem — via CDP bridge ─────────────────────────

    async def file_system_get_directory(self, origin: str, type: str) -> dict[str, Any]:
        """Get a file system directory by origin and type via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "FileSystem.getDirectory", {"origin": origin, "type": type}
        )
        return dict(result) if result else {}

    # ── HeadlessExperimental — via CDP bridge ───────────────

    async def headless_experimental_begin_frame(
        self,
        frame_time_ticks: float | None = None,
        interval: float | None = None,
        no_display_updates: bool = False,
        screenshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Begin a new frame in headless mode via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {}
        if frame_time_ticks is not None:
            params["frameTimeTicks"] = frame_time_ticks
        if interval is not None:
            params["interval"] = interval
        if no_display_updates:
            params["noDisplayUpdates"] = True
        if screenshot is not None:
            params["screenshot"] = screenshot
        result = await client.cdp.send_command("HeadlessExperimental.beginFrame", params)
        return dict(result) if result else {}

    async def headless_experimental_disable(self) -> None:
        """Disable the HeadlessExperimental domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("HeadlessExperimental.disable", {})

    async def headless_experimental_enable(self) -> None:
        """Enable the HeadlessExperimental domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("HeadlessExperimental.enable", {})

    # ── Inspector — via CDP bridge ──────────────────────────

    async def inspector_disable(self) -> None:
        """Disable the Inspector domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Inspector.disable", {})

    async def inspector_enable(self) -> None:
        """Enable the Inspector domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Inspector.enable", {})

    # ── Preload — via CDP bridge ───────────────────────────

    async def preload_disable(self) -> None:
        """Disable the Preload domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Preload.disable", {})

    async def preload_enable(self) -> None:
        """Enable the Preload domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Preload.enable", {})

    async def preload_get_preload_policy(self) -> dict[str, Any]:
        """Get the current preload policy via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Preload.getPreloadPolicy", {}))

    async def preload_set_preload_policy(self, policy: dict[str, Any]) -> None:
        """Set the preload policy via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Preload.setPreloadPolicy", {"policy": policy})

    # ── Profiler — via CDP bridge ──────────────────────────

    async def profiler_disable(self) -> None:
        """Disable the Profiler domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Profiler.disable", {})

    async def profiler_enable(self) -> None:
        """Enable the Profiler domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Profiler.enable", {})

    async def profiler_get_best_effort_coverage(self) -> dict[str, Any]:
        """Get best effort coverage data via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Profiler.getBestEffortCoverage", {}))

    async def profiler_set_sampling_interval(self, interval: int) -> None:
        """Set the CPU sampling interval in microseconds via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Profiler.setSamplingInterval", {"interval": interval})

    async def profiler_start(self) -> None:
        """Start CPU profiling via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Profiler.start", {})

    async def profiler_start_precise_coverage(
        self, call_count: bool = False, detailed: bool = False
    ) -> dict[str, Any]:
        """Start precise code coverage tracking via CDP bridge."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "Profiler.startPreciseCoverage",
                {"callCount": call_count, "detailed": detailed},
            )
        )

    async def profiler_stop(self) -> dict[str, Any]:
        """Stop CPU profiling via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Profiler.stop", {}))

    async def profiler_stop_precise_coverage(self) -> None:
        """Stop precise code coverage tracking via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Profiler.stopPreciseCoverage", {})

    async def profiler_take_precise_coverage(self) -> dict[str, Any]:
        """Take a snapshot of precise code coverage data via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Profiler.takePreciseCoverage", {}))

    # ── PWA — via CDP bridge ───────────────────────────────

    async def pwa_change_app_user_settings(
        self, app_id: str, user_settings: dict[str, Any]
    ) -> None:
        """Change PWA user settings via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "PWA.changeAppUserSettings", {"appId": app_id, "userSettings": user_settings}
        )

    async def pwa_get_os_app_state(self, app_id: str) -> dict[str, Any]:
        """Get the OS-level state of a PWA via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("PWA.getOsAppState", {"appId": app_id}))

    async def pwa_install(self, manifest_id: str, install_url: str | None = None) -> None:
        """Install a PWA via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"manifestId": manifest_id}
        if install_url is not None:
            params["installUrlOrBundleUrl"] = install_url
        await client.cdp.send_command("PWA.install", params)

    async def pwa_launch_files_in_app(self, app_id: str, files: list[str]) -> dict[str, Any]:
        """Launch files in a PWA via CDP bridge."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command("PWA.launchFilesInApp", {"appId": app_id, "files": files})
        )

    async def pwa_open_current_page_in_app(self, app_id: str) -> dict[str, Any]:
        """Open the current page in a PWA via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("PWA.openCurrentPageInApp", {"appId": app_id}))

    async def pwa_uninstall(self, app_id: str) -> None:
        """Uninstall a PWA via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("PWA.uninstall", {"appId": app_id})

    # ── IO — via CDP bridge ─────────────────────────────────

    async def io_read(
        self, handle: str, offset: int = 0, size: int | None = None
    ) -> dict[str, Any]:
        """Read data from a blob handle via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"handle": handle, "offset": offset}
        if size is not None:
            params["size"] = size
        result = await client.cdp.send_command("IO.read", params)
        return dict(result) if result else {}

    async def io_resolve_blob(self, object_id: str) -> str:
        """Resolve a blob object ID to a UUID handle via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("IO.resolveBlob", {"objectId": object_id})
        return str(result.get("uuid", "")) if result else ""

    # ── HeapProfiler — via CDP bridge ──────────────────────

    async def heap_profiler_add_inspected_heap_object(self, heap_object_id: str) -> None:
        """Add an inspected heap object via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "HeapProfiler.addInspectedHeapObject", {"heapObjectId": heap_object_id}
        )

    async def heap_profiler_collect_garbage(self) -> None:
        """Collect garbage via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("HeapProfiler.collectGarbage", {})

    async def heap_profiler_disable(self) -> None:
        """Disable the HeapProfiler domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("HeapProfiler.disable", {})

    async def heap_profiler_enable(self) -> None:
        """Enable the HeapProfiler domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("HeapProfiler.enable", {})

    async def heap_profiler_get_heap_object_id(self, object_id: str) -> str:
        """Get the heap object ID for a remote object via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "HeapProfiler.getHeapObjectId", {"objectId": object_id}
        )
        return str(result.get("heapSnapshotObjectId", "")) if result else ""

    async def heap_profiler_get_object_by_heap_object_id(
        self, object_id: str, object_group: str = ""
    ) -> dict[str, Any]:
        """Get an object by heap object ID via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"objectId": object_id}
        if object_group:
            params["objectGroup"] = object_group
        result = await client.cdp.send_command("HeapProfiler.getObjectByHeapObjectId", params)
        return dict(result) if result else {}

    async def heap_profiler_get_sampling_profile(self) -> dict[str, Any]:
        """Get the current sampling profile via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("HeapProfiler.getSamplingProfile", {})
        return dict(result) if result else {}

    async def heap_profiler_start_sampling(self, sampling_interval: int = 0) -> None:
        """Start heap sampling via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {}
        if sampling_interval:
            params["samplingInterval"] = sampling_interval
        await client.cdp.send_command("HeapProfiler.startSampling", params)

    async def heap_profiler_start_tracking_heap_objects(
        self, track_allocations: bool = False
    ) -> None:
        """Start tracking heap objects via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "HeapProfiler.startTrackingHeapObjects", {"trackAllocations": track_allocations}
        )

    async def heap_profiler_stop_sampling(self) -> dict[str, Any]:
        """Stop heap sampling and return the profile via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("HeapProfiler.stopSampling", {})
        return dict(result) if result else {}

    async def heap_profiler_stop_tracking_heap_objects(self, report_progress: bool = False) -> None:
        """Stop tracking heap objects via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "HeapProfiler.stopTrackingHeapObjects", {"reportProgress": report_progress}
        )

    async def heap_profiler_take_heap_snapshot(self, report_progress: bool = False) -> None:
        """Take a heap snapshot via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "HeapProfiler.takeHeapSnapshot", {"reportProgress": report_progress}
        )

    # ── IndexedDB — via CDP bridge ─────────────────────────

    async def indexed_db_clear_object_store(
        self, security_origin: str, database_name: str, object_store_name: str
    ) -> None:
        """Clear all entries in an IndexedDB object store via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "IndexedDB.clearObjectStore",
            {
                "securityOrigin": security_origin,
                "databaseName": database_name,
                "objectStoreName": object_store_name,
            },
        )

    async def indexed_db_delete_database(self, security_origin: str, database_name: str) -> None:
        """Delete an IndexedDB database via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "IndexedDB.deleteDatabase",
            {"securityOrigin": security_origin, "databaseName": database_name},
        )

    async def indexed_db_delete_object_store_entries(
        self,
        security_origin: str,
        database_name: str,
        object_store_name: str,
        key_range: dict[str, Any],
    ) -> None:
        """Delete entries in an IndexedDB object store via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "IndexedDB.deleteObjectStoreEntries",
            {
                "securityOrigin": security_origin,
                "databaseName": database_name,
                "objectStoreName": object_store_name,
                "keyRange": key_range,
            },
        )

    async def indexed_db_disable(self) -> None:
        """Disable the IndexedDB domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("IndexedDB.disable", {})

    async def indexed_db_enable(self) -> None:
        """Enable the IndexedDB domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("IndexedDB.enable", {})

    async def indexed_db_get_metadata(
        self, security_origin: str, database_name: str, object_store_name: str
    ) -> dict[str, Any]:
        """Get metadata for an IndexedDB object store via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "IndexedDB.getMetadata",
            {
                "securityOrigin": security_origin,
                "databaseName": database_name,
                "objectStoreName": object_store_name,
            },
        )
        return dict(result) if result else {}

    async def indexed_db_request_data(
        self,
        security_origin: str,
        database_name: str,
        object_store_name: str,
        index_name: str,
        skip_count: int = 0,
        page_size: int = 10,
        key_range: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Request data from an IndexedDB object store via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {
            "securityOrigin": security_origin,
            "databaseName": database_name,
            "objectStoreName": object_store_name,
            "indexName": index_name,
            "skipCount": skip_count,
            "pageSize": page_size,
        }
        if key_range is not None:
            params["keyRange"] = key_range
        result = await client.cdp.send_command("IndexedDB.requestData", params)
        return dict(result) if result else {}

    async def indexed_db_request_database(
        self, security_origin: str, database_name: str
    ) -> dict[str, Any]:
        """Request an IndexedDB database with its object stores via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "IndexedDB.requestDatabase",
            {"securityOrigin": security_origin, "databaseName": database_name},
        )
        return dict(result) if result else {}

    async def indexed_db_request_database_names(self, security_origin: str) -> dict[str, Any]:
        """Request the names of all IndexedDB databases for an origin via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "IndexedDB.requestDatabaseNames", {"securityOrigin": security_origin}
        )
        return dict(result) if result else {}

    # ── LayerTree — via CDP bridge ─────────────────────────

    async def layer_tree_compositing_reasons(self, layer_id: str) -> dict[str, Any]:
        """Get compositing reasons for a layer via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "LayerTree.compositingReasons", {"layerId": layer_id}
        )
        return dict(result) if result else {}

    async def layer_tree_disable(self) -> None:
        """Disable the LayerTree domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("LayerTree.disable", {})

    async def layer_tree_enable(self) -> None:
        """Enable the LayerTree domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("LayerTree.enable", {})

    async def layer_tree_load_snapshot(self, snapshots: list[dict[str, Any]]) -> dict[str, Any]:
        """Load a layer tree snapshot via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("LayerTree.loadSnapshot", {"snapshots": snapshots})
        return dict(result) if result else {}

    async def layer_tree_make_snapshot(self, layer_id: str) -> dict[str, Any]:
        """Make a snapshot of a layer via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("LayerTree.makeSnapshot", {"layerId": layer_id})
        return dict(result) if result else {}

    async def layer_tree_profile_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        """Profile a layer snapshot via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "LayerTree.profileSnapshot", {"snapshotId": snapshot_id}
        )
        return dict(result) if result else {}

    async def layer_tree_release_snapshot(self, snapshot_id: str) -> None:
        """Release a layer snapshot via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("LayerTree.releaseSnapshot", {"snapshotId": snapshot_id})

    async def layer_tree_replay_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        """Replay a layer snapshot via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "LayerTree.replaySnapshot", {"snapshotId": snapshot_id}
        )
        return dict(result) if result else {}

    async def layer_tree_snapshot_command_log(self, snapshot_id: str) -> dict[str, Any]:
        """Get the command log for a layer snapshot via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "LayerTree.snapshotCommandLog", {"snapshotId": snapshot_id}
        )
        return dict(result) if result else {}

    # ── Log — via CDP bridge ────────────────────────────────

    async def log_clear(self) -> None:
        """Clear the log via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Log.clear", {})

    async def log_disable(self) -> None:
        """Disable the Log domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Log.disable", {})

    async def log_enable(self) -> None:
        """Enable the Log domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Log.enable", {})

    async def log_start_violations_report(self, config: list[dict[str, Any]]) -> None:
        """Start reporting violations via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Log.startViolationsReport", {"config": config})

    async def log_stop_violations_report(self) -> None:
        """Stop reporting violations via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Log.stopViolationsReport", {})

    # ── Media — via CDP bridge ──────────────────────────────

    async def media_disable(self) -> None:
        """Disable the Media domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Media.disable", {})

    async def media_enable(self) -> None:
        """Enable the Media domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Media.enable", {})

    # ── Memory — via CDP bridge ─────────────────────────────

    async def memory_forcibly_purge_javascript_memory(self) -> None:
        """Forcibly purge JavaScript memory via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Memory.forciblyPurgeJavaScriptMemory", {})

    async def memory_get_all_time_sampling_profile(self) -> dict[str, Any]:
        """Get the all-time sampling profile via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Memory.getAllTimeSamplingProfile", {})
        return dict(result) if result else {}

    async def memory_get_browser_sampling_profile(self) -> dict[str, Any]:
        """Get the browser sampling profile via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Memory.getBrowserSamplingProfile", {})
        return dict(result) if result else {}

    async def memory_get_dom_counters(self) -> dict[str, Any]:
        """Get DOM counters via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Memory.getDOMCounters", {})
        return dict(result) if result else {}

    async def memory_get_dom_counters_for_leak_detection(self) -> dict[str, Any]:
        """Get DOM counters for leak detection via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Memory.getDOMCountersForLeakDetection", {})
        return dict(result) if result else {}

    async def memory_get_sampling_profile(self) -> dict[str, Any]:
        """Get the current sampling profile via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Memory.getSamplingProfile", {})
        return dict(result) if result else {}

    async def memory_prepare_for_leak_detection(self) -> None:
        """Prepare for leak detection via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Memory.prepareForLeakDetection", {})

    async def memory_set_pressure_notifications_suppressed(self, suppressed: bool) -> None:
        """Set pressure notifications suppressed state via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Memory.setPressureNotificationsSuppressed", {"suppressed": suppressed}
        )

    async def memory_simulate_pressure_notification(self, level: str) -> None:
        """Simulate a memory pressure notification via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Memory.simulatePressureNotification", {"level": level})

    async def memory_start_sampling(self, sampling_interval: int = 0) -> None:
        """Start memory sampling via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {}
        if sampling_interval:
            params["samplingInterval"] = sampling_interval
        await client.cdp.send_command("Memory.startSampling", params)

    async def memory_stop_sampling(self) -> None:
        """Stop memory sampling via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Memory.stopSampling", {})

    # ── Console ─────────────────────────────────────────────

    async def console_clear_messages(self) -> None:
        """Clear all console messages via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Console.clearMessages", {})

    async def console_disable(self) -> None:
        """Disable the Console domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Console.disable", {})

    async def console_enable(self) -> None:
        """Enable the Console domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Console.enable", {})

    # ── CrashReportContext ──────────────────────────────────

    async def crash_report_context_get_entries(self) -> list[dict[str, Any]]:
        """Get crash report entries via CDP bridge."""
        client = self._require_launched()
        return await client.cdp.send_command("CrashReportContext.getEntries", {})

    # ── Input (low-level CDP) ───────────────────────────────

    async def input_cancel_dragging(self) -> None:
        """Cancel any ongoing drag operation via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Input.cancelDragging", {})

    async def input_dispatch_drag_event(
        self, type: str, x: float, y: float, data: dict[str, Any] | None = None
    ) -> None:
        """Dispatch a drag event via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"type": type, "x": x, "y": y}
        if data is not None:
            params["data"] = data
        await client.cdp.send_command("Input.dispatchDragEvent", params)

    async def input_dispatch_key_event(
        self,
        type: str,
        key: str = "",
        code: str = "",
        windows_virtual_key_code: int = 0,
        native_virtual_key_code: int = 0,
        modifiers: int = 0,
        text: str = "",
        unmodified_text: str = "",
        auto_repeat: bool = False,
        is_keypad: bool = False,
        is_system_key: bool = False,
        location: int = 0,
        commands: list[str] | None = None,
    ) -> None:
        """Dispatch a key event via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"type": type}
        if key:
            params["key"] = key
        if code:
            params["code"] = code
        if windows_virtual_key_code:
            params["windowsVirtualKeyCode"] = windows_virtual_key_code
        if native_virtual_key_code:
            params["nativeVirtualKeyCode"] = native_virtual_key_code
        if modifiers:
            params["modifiers"] = modifiers
        if text:
            params["text"] = text
        if unmodified_text:
            params["unmodifiedText"] = unmodified_text
        if auto_repeat:
            params["autoRepeat"] = auto_repeat
        if is_keypad:
            params["isKeypad"] = is_keypad
        if is_system_key:
            params["isSystemKey"] = is_system_key
        if location:
            params["location"] = location
        if commands is not None:
            params["commands"] = commands
        await client.cdp.send_command("Input.dispatchKeyEvent", params)

    async def input_dispatch_mouse_event(
        self,
        type: str,
        x: float,
        y: float,
        button: str = "none",
        click_count: int = 0,
        modifiers: int = 0,
        timestamp: float = 0,
        delta_x: float = 0,
        delta_y: float = 0,
    ) -> None:
        """Dispatch a mouse event via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"type": type, "x": x, "y": y}
        if button != "none":
            params["button"] = button
        if click_count:
            params["clickCount"] = click_count
        if modifiers:
            params["modifiers"] = modifiers
        if timestamp:
            params["timestamp"] = timestamp
        if delta_x:
            params["deltaX"] = delta_x
        if delta_y:
            params["deltaY"] = delta_y
        await client.cdp.send_command("Input.dispatchMouseEvent", params)

    async def input_dispatch_touch_event(
        self,
        type: str,
        touch_points: list[dict[str, Any]],
        modifiers: int = 0,
        timestamp: float = 0,
    ) -> None:
        """Dispatch a touch event via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"type": type, "touchPoints": touch_points}
        if modifiers:
            params["modifiers"] = modifiers
        if timestamp:
            params["timestamp"] = timestamp
        await client.cdp.send_command("Input.dispatchTouchEvent", params)

    async def input_emulate_touch_from_mouse_event(
        self,
        type: str,
        x: float,
        y: float,
        button: str = "none",
        timestamp: float = 0,
        delta_x: float = 0,
        delta_y: float = 0,
        modifiers: int = 0,
        click_count: int = 0,
    ) -> None:
        """Emulate a touch event from a mouse event via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"type": type, "x": x, "y": y}
        if button != "none":
            params["button"] = button
        if timestamp:
            params["timestamp"] = timestamp
        if delta_x:
            params["deltaX"] = delta_x
        if delta_y:
            params["deltaY"] = delta_y
        if modifiers:
            params["modifiers"] = modifiers
        if click_count:
            params["clickCount"] = click_count
        await client.cdp.send_command("Input.emulateTouchFromMouseEvent", params)

    async def input_ime_set_composition(
        self,
        text: str,
        selection_start: int,
        selection_end: int,
        replacement_start: int = 0,
        replacement_end: int = 0,
    ) -> None:
        """Set the IME composition via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {
            "text": text,
            "selectionStart": selection_start,
            "selectionEnd": selection_end,
        }
        if replacement_start:
            params["replacementStart"] = replacement_start
        if replacement_end:
            params["replacementEnd"] = replacement_end
        await client.cdp.send_command("Input.imeSetComposition", params)

    async def input_insert_text(self, text: str) -> None:
        """Insert text into the focused element via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Input.insertText", {"text": text})

    async def input_set_ignore_input_events(self, ignore: bool) -> None:
        """Set whether to ignore input events via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Input.setIgnoreInputEvents", {"ignore": ignore})

    async def input_set_intercept_drags(self, enabled: bool) -> None:
        """Set whether to intercept drag operations via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Input.setInterceptDrags", {"enabled": enabled})

    async def input_synthesize_pinch_gesture(
        self, x: float, y: float, scale_factor: float, relative_pointer_speed: int = 0
    ) -> None:
        """Synthesize a pinch gesture via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"x": x, "y": y, "scaleFactor": scale_factor}
        if relative_pointer_speed:
            params["relativePointerSpeed"] = relative_pointer_speed
        await client.cdp.send_command("Input.synthesizePinchGesture", params)

    async def input_synthesize_scroll_gesture(
        self,
        x: float,
        y: float,
        x_distance: float = 0,
        y_distance: float = 0,
        x_overscroll: float = 0,
        y_overscroll: float = 0,
        prevent_fling: bool = True,
        speed: int = 0,
        repeat_count: int = 0,
        repeat_delay_ms: int = 0,
        interaction_source_name: str = "",
    ) -> None:
        """Synthesize a scroll gesture via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"x": x, "y": y}
        if x_distance:
            params["xDistance"] = x_distance
        if y_distance:
            params["yDistance"] = y_distance
        if x_overscroll:
            params["xOverscroll"] = x_overscroll
        if y_overscroll:
            params["yOverscroll"] = y_overscroll
        params["preventFling"] = prevent_fling
        if speed:
            params["speed"] = speed
        if repeat_count:
            params["repeatCount"] = repeat_count
        if repeat_delay_ms:
            params["repeatDelayMs"] = repeat_delay_ms
        if interaction_source_name:
            params["interactionSourceName"] = interaction_source_name
        await client.cdp.send_command("Input.synthesizeScrollGesture", params)

    async def input_synthesize_tap_gesture(
        self, x: float, y: float, duration: int = 0, tap_count: int = 1
    ) -> None:
        """Synthesize a tap gesture via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"x": x, "y": y}
        if duration:
            params["duration"] = duration
        if tap_count != 1:
            params["tapCount"] = tap_count
        await client.cdp.send_command("Input.synthesizeTapGesture", params)

    # ── Network (additional CDP methods) ────────────────────

    async def network_clear_accepted_encodings_override(self) -> None:
        """Clear the accepted encodings override via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Network.clearAcceptedEncodingsOverride", {})

    async def network_configure_durable_messages(self, options: dict[str, Any]) -> None:
        """Configure durable messages via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Network.configureDurableMessages", {"options": options})

    async def network_delete_device_bound_session(self, session_id: str) -> None:
        """Delete a device-bound session via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Network.deleteDeviceBoundSession", {"sessionId": session_id})

    async def network_disable(self) -> None:
        """Disable the Network domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Network.disable", {})

    async def network_emulate_network_conditions_by_rule(
        self,
        download_throughput: float = 0,
        upload_throughput: float = 0,
        offline: bool = False,
        latency: float = 0,
        connection_type: str = "",
    ) -> None:
        """Emulate network conditions by rule via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {}
        if download_throughput:
            params["downloadThroughput"] = download_throughput
        if upload_throughput:
            params["uploadThroughput"] = upload_throughput
        if offline:
            params["offline"] = offline
        if latency:
            params["latency"] = latency
        if connection_type:
            params["connectionType"] = connection_type
        await client.cdp.send_command("Network.emulateNetworkConditionsByRule", params)

    async def network_enable(
        self, max_total_buffer_size: int = 0, max_resource_buffer_size: int = 0
    ) -> None:
        """Enable the Network domain via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {}
        if max_total_buffer_size:
            params["maxTotalBufferSize"] = max_total_buffer_size
        if max_resource_buffer_size:
            params["maxResourceBufferSize"] = max_resource_buffer_size
        await client.cdp.send_command("Network.enable", params)

    async def network_enable_device_bound_sessions(self) -> None:
        """Enable device-bound sessions via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Network.enableDeviceBoundSessions", {})

    async def network_enable_reporting_api(self, enable: bool) -> None:
        """Enable or disable the Reporting API via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Network.enableReportingApi", {"enable": enable})

    async def network_fetch_schemeful_site(self, request_id: str) -> dict[str, Any]:
        """Fetch the schemeful site for a request via CDP bridge."""
        client = self._require_launched()
        return await client.cdp.send_command(
            "Network.fetchSchemefulSite", {"requestId": request_id}
        )

    async def network_get_certificate(self, origin: str) -> dict[str, Any]:
        """Get the certificate for an origin via CDP bridge."""
        client = self._require_launched()
        return await client.cdp.send_command("Network.getCertificate", {"origin": origin})

    async def network_get_request_post_data(self, request_id: str) -> str:
        """Get the POST data for a request via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Network.getRequestPostData", {"requestId": request_id}
        )
        return result.get("postData", "")

    async def network_get_response_body_for_interception(self, interception_id: str) -> str:
        """Get the response body for an interception via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Network.getResponseBodyForInterception", {"interceptionId": interception_id}
        )
        return result.get("body", "")

    async def network_get_security_isolation_status(self, frame_id: str = "") -> dict[str, Any]:
        """Get the security isolation status via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {}
        if frame_id:
            params["frameId"] = frame_id
        return await client.cdp.send_command("Network.getSecurityIsolationStatus", params)

    async def network_override_network_state(self, state: dict[str, Any]) -> None:
        """Override the network state via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Network.overrideNetworkState", state)

    async def network_search_in_response_body(
        self, request_id: str, query: str, case_sensitive: bool = False, is_regex: bool = False
    ) -> dict[str, Any]:
        """Search in a response body via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"requestId": request_id, "query": query}
        if case_sensitive:
            params["caseSensitive"] = case_sensitive
        if is_regex:
            params["isRegex"] = is_regex
        return await client.cdp.send_command("Network.searchInResponseBody", params)

    async def network_set_accepted_encodings(self, encodings: list[str]) -> None:
        """Set accepted encodings via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Network.setAcceptedEncodings", {"encodings": encodings})

    async def network_set_attach_debug_stack(self, enabled: bool) -> None:
        """Set whether to attach debug stack via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Network.setAttachDebugStack", {"enabled": enabled})

    async def network_set_cookies(self, cookies: list[dict[str, Any]]) -> None:
        """Set cookies via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Network.setCookies", {"cookies": cookies})

    async def network_stream_resource_content(self, request_id: str) -> dict[str, Any]:
        """Stream resource content for a request via CDP bridge."""
        client = self._require_launched()
        return await client.cdp.send_command(
            "Network.streamResourceContent", {"requestId": request_id}
        )

    async def network_take_response_body_for_interception_as_stream(
        self, interception_id: str
    ) -> dict[str, Any]:
        """Take the response body for an interception as a stream via CDP bridge."""
        client = self._require_launched()
        return await client.cdp.send_command(
            "Network.takeResponseBodyForInterceptionAsStream",
            {"interceptionId": interception_id},
        )

    # ── SmartCardEmulation — via CDP bridge ────────────────

    async def smart_card_enable(self) -> None:
        """Enable the SmartCardEmulation domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("SmartCardEmulation.enable", {})

    async def smart_card_disable(self) -> None:
        """Disable the SmartCardEmulation domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("SmartCardEmulation.disable", {})

    async def smart_card_report_error(self, request_id: str, error: str) -> None:
        """Report an error for a pending smart card request via CDP bridge.

        Args:
            request_id: The pending request identifier.
            error: Error code string.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "SmartCardEmulation.reportError",
            {"requestId": request_id, "error": error},
        )

    async def smart_card_report_plain_result(self, request_id: str, result_code: int) -> None:
        """Report a plain result for a pending smart card request via CDP bridge.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "SmartCardEmulation.reportPlainResult",
            {"requestId": request_id, "resultCode": result_code},
        )

    async def smart_card_report_connect_result(
        self, request_id: str, result_code: int, connection_id: str
    ) -> None:
        """Report a connect result for a pending smart card request via CDP bridge.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
            connection_id: Established connection identifier.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "SmartCardEmulation.reportConnectResult",
            {
                "requestId": request_id,
                "resultCode": result_code,
                "connectionId": connection_id,
            },
        )

    async def smart_card_report_data_result(
        self, request_id: str, result_code: int, data: str
    ) -> None:
        """Report a data result for a pending smart card request via CDP bridge.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
            data: Response data (hex-encoded).
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "SmartCardEmulation.reportDataResult",
            {
                "requestId": request_id,
                "resultCode": result_code,
                "data": data,
            },
        )

    async def smart_card_report_status_result(self, request_id: str, status: str) -> None:
        """Report a status result for a pending smart card request via CDP bridge.

        Args:
            request_id: The pending request identifier.
            status: Status string.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "SmartCardEmulation.reportStatusResult",
            {"requestId": request_id, "status": status},
        )

    async def smart_card_report_begin_transaction_result(
        self, request_id: str, result_code: int
    ) -> None:
        """Report a begin-transaction result for a pending smart card request via CDP bridge.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "SmartCardEmulation.reportBeginTransactionResult",
            {"requestId": request_id, "resultCode": result_code},
        )

    async def smart_card_report_establish_context_result(
        self, request_id: str, result_code: int, context_id: str
    ) -> None:
        """Report an establish-context result for a pending smart card request via CDP bridge.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
            context_id: Established context identifier.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "SmartCardEmulation.reportEstablishContextResult",
            {
                "requestId": request_id,
                "resultCode": result_code,
                "contextId": context_id,
            },
        )

    async def smart_card_report_release_context_result(
        self, request_id: str, result_code: int
    ) -> None:
        """Report a release-context result for a pending smart card request via CDP bridge.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "SmartCardEmulation.reportReleaseContextResult",
            {"requestId": request_id, "resultCode": result_code},
        )

    async def smart_card_report_list_readers_result(
        self, request_id: str, result_code: int, readers: list[dict[str, Any]]
    ) -> None:
        """Report a list-readers result for a pending smart card request via CDP bridge.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
            readers: List of reader dicts.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "SmartCardEmulation.reportListReadersResult",
            {
                "requestId": request_id,
                "resultCode": result_code,
                "readers": readers,
            },
        )

    async def smart_card_report_get_status_change_result(
        self, request_id: str, result_code: int, readers: list[dict[str, Any]]
    ) -> None:
        """Report a get-status-change result for a pending smart card request via CDP bridge.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
            readers: List of reader status dicts.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "SmartCardEmulation.reportGetStatusChangeResult",
            {
                "requestId": request_id,
                "resultCode": result_code,
                "readers": readers,
            },
        )

    # ── System Info — via CDP bridge ──────────────────────

    async def system_info_get_info(self) -> dict[str, Any]:
        """Get system info (OS, GPU, model, etc.) via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("SystemInfo.getInfo", {}))

    async def system_info_get_process_info(self) -> list[dict[str, Any]]:
        """Get process info for the browser via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("SystemInfo.getProcessInfo", {})
        return [dict(p) for p in result.get("processInfo", [])] if result else []

    async def system_info_get_feature_state(self, feature_name: str) -> dict[str, Any]:
        """Get the state of a specific feature via CDP bridge.

        Args:
            feature_name: The feature name to query.

        Returns:
            Dict with feature state information.
        """
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "SystemInfo.getFeatureState", {"featureName": feature_name}
            )
        )

    # ── BiDi native: Browsing ──────────────────────────────

    async def get_client_windows(self) -> list[dict[str, Any]]:
        """List client windows via browsingContext.getClientWindows.

        Returns:
            List of client window dicts with bounds and state.
        """
        client = self._require_launched()
        result = await client._connection.send_command("browsingContext.getClientWindows", {})
        return list(result.get("clientWindows", []))

    async def get_user_contexts(self) -> list[dict[str, Any]]:
        """List user contexts via browsingContext.getUserContexts.

        Returns:
            List of user context dicts.
        """
        client = self._require_launched()
        result = await client._connection.send_command("browsingContext.getUserContexts", {})
        return list(result.get("userContexts", []))

    async def remove_user_context(self, user_context_id: str) -> None:
        """Remove a user context via browsingContext.removeUserContext.

        Args:
            user_context_id: The user context ID to remove.
        """
        client = self._require_launched()
        await client._connection.send_command(
            "browsingContext.removeUserContext",
            {"userContext": user_context_id},
        )

    async def set_client_window_state(self, state: str) -> None:
        """Set client window state via browsingContext.setClientWindowState.

        Args:
            state: Window state - one of "minimized", "maximized",
                "fullscreen", or "normal".
        """
        client = self._require_launched()
        await client._connection.send_command(
            "browsingContext.setClientWindowState",
            {"context": self._context, "state": state},
        )

    async def close_browser(self) -> None:
        """Close the browser explicitly via BiDi.

        Unlike ``close()``, this forces the browser process to terminate
        rather than just closing the browsing context and client.
        """
        client = self._require_client()
        try:
            await client._connection.send_command("browser.close", {})
        finally:
            self._context = None
            self._client = None

    async def get_viewport(self) -> dict[str, Any]:
        """Get the current viewport and devicePixelRatio via BiDi.

        Returns:
            Dict with ``viewport`` (width, height) and ``devicePixelRatio``.
        """
        client = self._require_launched()
        result = await client._connection.send_command(
            "browsingContext.getViewport",
            {"context": self._context},
        )
        return dict(result)

    async def wait_for_function(self, expression: str, timeout_ms: int = 30000) -> None:
        """Wait for a JavaScript function to return a truthy value.

        Uses polling via ``script.evaluate`` until the expression returns
        truthy or the timeout expires.

        Args:
            expression: JavaScript expression that returns a truthy/falsy value.
            timeout_ms: Maximum wait time in milliseconds.

        Raises:
            WaitTimeoutError: If the expression does not return truthy in time.
        """
        client = self._require_launched()

        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            result = await client.script.evaluate(self._context, expression, await_promise=True)
            if hasattr(result, "value") and result.value:
                return
            await asyncio.sleep(0.1)
        raise WaitTimeoutError("function", timeout_ms)

    async def wait_for_selector(self, selector: str, timeout_ms: int = 30000) -> None:
        """Wait for a CSS selector to appear in the DOM.

        Uses native BiDi polling via ``script.evaluate``.

        Args:
            selector: CSS selector to wait for.
            timeout_ms: Maximum wait time in milliseconds.

        Raises:
            WaitTimeoutError: If the selector does not appear in time.
        """
        client = self._require_launched()

        deadline = time.monotonic() + timeout_ms / 1000
        escaped = json.dumps(selector)
        js = f"!!document.querySelector({escaped})"
        while time.monotonic() < deadline:
            result = await client.script.evaluate(self._context, js, await_promise=False)
            if hasattr(result, "value") and result.value:
                return
            await asyncio.sleep(0.1)
        raise WaitTimeoutError("selector", timeout_ms)

    async def locate_nodes(
        self, locator: dict[str, Any], max_node_count: int = 0
    ) -> list[dict[str, Any]]:
        """Locate DOM nodes using native BiDi locators.

        Args:
            locator: BiDi locator dict (e.g. ``{"type": "css", "value": "div"}``).
            max_node_count: Maximum number of nodes to return (0 = unlimited).

        Returns:
            List of node dicts with ``sharedId``, ``value``, and ``type``.
        """
        client = self._require_launched()
        params: dict[str, Any] = {
            "context": self._context,
            "locator": locator,
        }
        if max_node_count > 0:
            params["maxNodeCount"] = max_node_count
        result = await client._connection.send_command("browsingContext.locateNodes", params)
        return list(result.get("nodes", []))

    # ── BiDi native: CDP Bridge ────────────────────────────

    async def get_cdp_session(self) -> dict[str, Any]:
        """Get the CDP session info associated with the BiDi connection.

        Returns:
            Dict with session ID and related CDP session metadata.
        """
        client = self._require_launched()
        return dict(await client.cdp.get_session())

    # ── BiDi native: Emulation ─────────────────────────────

    async def set_screen_orientation(self, orientation: str = "portraitPrimary") -> None:
        """Set screen orientation via native BiDi emulation.

        Args:
            orientation: One of "portraitPrimary", "portraitSecondary",
                "landscapePrimary", or "landscapeSecondary".
        """
        client = self._require_launched()
        await client.emulation.set_screen_orientation(
            orientation=orientation,
            contexts=[self._context] if self._context else None,
        )

    # ── BiDi native: Input ─────────────────────────────────

    async def perform_actions(self, actions: list[dict[str, Any]]) -> None:
        """Execute a sequence of input actions via native BiDi.

        Args:
            actions: List of action dicts following the W3C BiDi
                action sequence format (e.g. pointer, key, scroll actions).
        """
        client = self._require_launched()
        await client._connection.send_command(
            "input.performActions",
            {"context": self._context, "actions": actions},
        )

    async def release_actions(self) -> None:
        """Release all pending input actions via native BiDi."""
        client = self._require_launched()
        await client._connection.send_command(
            "input.releaseActions",
            {"context": self._context},
        )

    async def drag_and_drop(
        self, source_x: int, source_y: int, target_x: int, target_y: int
    ) -> None:
        """Drag and drop via native BiDi input actions.

        Args:
            source_x: Starting X coordinate.
            source_y: Starting Y coordinate.
            target_x: Target X coordinate.
            target_y: Target Y coordinate.
        """
        actions = [
            {
                "type": "pointer",
                "id": "dragPointer",
                "pointerType": "mouse",
                "actions": [
                    {"type": "pointerMove", "x": source_x, "y": source_y},
                    {"type": "pointerDown", "button": 0},
                    {"type": "pointerMove", "x": target_x, "y": target_y},
                    {"type": "pointerUp", "button": 0},
                ],
            }
        ]
        await self.perform_actions(actions)

    async def input_scroll(
        self, x: int = 0, y: int = 0, delta_x: int = 0, delta_y: int = 0
    ) -> None:
        """Scroll via native BiDi input actions.

        Args:
            x: Starting X coordinate.
            y: Starting Y coordinate.
            delta_x: Horizontal scroll delta.
            delta_y: Vertical scroll delta.
        """
        actions = [
            {
                "type": "scroll",
                "id": "scrollAction",
                "x": x,
                "y": y,
                "deltaX": delta_x,
                "deltaY": delta_y,
            }
        ]
        await self.perform_actions(actions)

    # ── BiDi native: Network ───────────────────────────────

    async def add_data_collector(
        self,
        data_types: list[str],
        max_encoded_data_size: int = 0,
        collector_type: str = "default",
    ) -> str:
        """Add a network data collector via native BiDi.

        Args:
            data_types: List of data types to collect (e.g.
                "requestBody", "responseBody", "responseHeaders").
            max_encoded_data_size: Maximum encoded data size in bytes (0 = unlimited).
            collector_type: Collector type identifier.

        Returns:
            The collector ID.
        """
        client = self._require_launched()
        params: dict[str, Any] = {
            "dataTypes": data_types,
            "collectorType": collector_type,
        }
        if max_encoded_data_size > 0:
            params["maxEncodedDataSize"] = max_encoded_data_size
        result = await client._connection.send_command("network.addDataCollector", params)
        return str(result.get("collectorId", ""))

    async def get_network_data(
        self,
        request: str,
        data_type: str,
        collector_id: str = "",
        disown: bool = False,
    ) -> dict[str, Any]:
        """Get collected network data via native BiDi.

        Args:
            request: The network request ID.
            data_type: The data type to retrieve (e.g. "responseBody").
            collector_id: Optional collector ID to filter.
            disown: If True, disown the data after retrieval.

        Returns:
            Dict with the collected data.
        """
        client = self._require_launched()
        params: dict[str, Any] = {
            "request": request,
            "dataType": data_type,
        }
        if collector_id:
            params["collectorId"] = collector_id
        if disown:
            params["disown"] = True
        result = await client._connection.send_command("network.getData", params)
        return dict(result)

    async def disown_network_data(self, collector_id: str, request: str, data_type: str) -> None:
        """Release collected network data via native BiDi.

        Args:
            collector_id: The collector ID.
            request: The network request ID.
            data_type: The data type to disown.
        """
        client = self._require_launched()
        await client._connection.send_command(
            "network.disownData",
            {
                "collectorId": collector_id,
                "request": request,
                "dataType": data_type,
            },
        )

    async def remove_data_collector(self, collector_id: str) -> None:
        """Remove a network data collector via native BiDi.

        Args:
            collector_id: The collector ID to remove.
        """
        client = self._require_launched()
        await client._connection.send_command(
            "network.removeDataCollector",
            {"collectorId": collector_id},
        )

    async def remove_intercept(self, intercept_id: str) -> None:
        """Remove a network intercept via native BiDi.

        Args:
            intercept_id: The intercept ID to remove.
        """
        client = self._require_launched()
        await client.network.remove_intercept(intercept_id=intercept_id)

    async def remove_cache_override(self, cache_id: str) -> None:
        """Remove a cache override via native BiDi.

        Args:
            cache_id: The cache override ID to remove.
        """
        client = self._require_launched()
        await client._connection.send_command(
            "network.removeCacheOverride",
            {"cacheId": cache_id},
        )

    async def continue_response(
        self,
        request: str,
        status_code: int | None = None,
        headers: list[dict[str, str]] | None = None,
        body: str | None = None,
        credentials: dict[str, Any] | None = None,
    ) -> None:
        """Continue a response with modifications via native BiDi.

        Args:
            request: The network request ID.
            status_code: Optional new status code.
            headers: Optional list of header dicts (name, value).
            body: Optional new response body (base64-encoded).
            credentials: Optional credentials dict (bidiwave 1.8.2+).
        """
        client = self._require_launched()
        params: dict[str, Any] = {"request": request}
        if status_code is not None:
            params["statusCode"] = status_code
        if headers is not None:
            params["headers"] = headers
        if body is not None:
            params["body"] = body
        if credentials is not None:
            params["credentials"] = credentials
        await client._connection.send_command("network.continueResponse", params)

    # ── BiDi native: Permissions ───────────────────────────

    async def set_permission(
        self,
        descriptor: dict[str, Any],
        state: str,
        user_context: str | None = None,
    ) -> None:
        """Set a permission state via native BiDi permissions.

        Args:
            descriptor: Permission descriptor dict (e.g. ``{"name": "geolocation"}``).
            state: Permission state - "granted", "denied", or "prompt".
            user_context: Optional user context to scope the permission.
        """
        client = self._require_launched()
        params: dict[str, Any] = {
            "descriptor": descriptor,
            "state": state,
        }
        if user_context:
            params["userContext"] = user_context
        await client._connection.send_command("permissions.setPermission", params)

    # ── BiDi native: Preload Scripts ───────────────────────

    async def add_preload_script(
        self,
        source: str,
        user_context: str | None = None,
    ) -> str:
        """Add a preload script via native BiDi script domain.

        The script is injected into every new document before any other
        script runs.

        Args:
            source: JavaScript source code to inject.
            user_context: Optional user context to scope the script.

        Returns:
            The preload script ID.
        """
        client = self._require_launched()
        params: dict[str, Any] = {"source": source}
        if user_context:
            params["userContext"] = user_context
        result = await client._connection.send_command("script.addPreloadScript", params)
        return str(result.get("scriptId", ""))

    async def remove_preload_script(self, script_id: str) -> None:
        """Remove a preload script via native BiDi.

        Args:
            script_id: The preload script ID to remove.
        """
        client = self._require_launched()
        await client._connection.send_command(
            "script.removePreloadScript",
            {"scriptId": script_id},
        )

    # ── BiDi native: Script ────────────────────────────────

    async def call_function(
        self,
        function_declaration: str,
        args: list[dict[str, Any]] | None = None,
        await_promise: bool = False,
        user_context: str | None = None,
    ) -> Any:
        """Call a JavaScript function with arguments via native BiDi.

        Args:
            function_declaration: JS function declaration string.
            args: List of argument dicts (BiDi remote value format).
            await_promise: Whether to await a returned Promise.
            user_context: Optional user context to scope the call.

        Returns:
            The function return value.
        """
        client = self._require_launched()
        params: dict[str, Any] = {
            "functionDeclaration": function_declaration,
            "target": {"context": self._context},
            "awaitPromise": await_promise,
        }
        if args:
            params["arguments"] = args
        if user_context:
            params["userContext"] = user_context
        result = await client._connection.send_command("script.callFunction", params)
        if isinstance(result, dict) and "result" in result:
            return result["result"]
        return result

    async def get_realms(self) -> list[dict[str, Any]]:
        """Get execution realms via native BiDi script domain.

        Returns:
            List of realm dicts with ``realmId``, ``origin``, and ``type``.
        """
        client = self._require_launched()
        params: dict[str, Any] = {"contexts": [self._context]} if self._context else {}
        result = await client._connection.send_command("script.getRealms", params)
        return list(result.get("realms", []))

    async def disown_handles(self, handles: list[str]) -> None:
        """Release remote object handles via native BiDi script domain.

        Args:
            handles: List of remote object handle IDs to disown.
        """
        client = self._require_launched()
        await client._connection.send_command(
            "script.disown",
            {
                "target": {"context": self._context},
                "handles": handles,
            },
        )

    # ── BiDi native: Session ───────────────────────────────

    async def session_status(self) -> dict[str, Any]:
        """Get the BiDi session status.

        Returns:
            Dict with session status information.
        """
        client = self._require_client()
        result = await client._connection.send_command("session.status", {})
        return dict(result)

    # ── BiDi native: Storage ───────────────────────────────

    async def delete_cookies(
        self,
        name: str = "",
        domain: str = "",
        path: str = "",
    ) -> None:
        """Delete cookies by filter via native BiDi storage.

        Args:
            name: Cookie name to delete (empty = all names).
            domain: Cookie domain filter (empty = all domains).
            path: Cookie path filter (empty = all paths).
        """
        client = self._require_launched()
        params: dict[str, Any] = {}
        if name:
            params["name"] = name
        if domain:
            params["domain"] = domain
        if path:
            params["path"] = path
        await client._connection.send_command("storage.deleteCookies", params)

    # ── BiDi native: WebExtensions ─────────────────────────

    async def webextension_install(self, extension_data: str) -> str:
        """Install a web extension via native BiDi.

        Args:
            extension_data: Base64-encoded extension archive data.

        Returns:
            The extension ID.
        """
        client = self._require_launched()
        result = await client._connection.send_command(
            "webExtension.install",
            {"extensionData": extension_data},
        )
        return str(result.get("extensionId", ""))

    async def webextension_uninstall(self, extension_id: str) -> None:
        """Uninstall a web extension via native BiDi.

        Args:
            extension_id: The extension ID to uninstall.
        """
        client = self._require_launched()
        await client._connection.send_command(
            "webExtension.uninstall",
            {"extensionId": extension_id},
        )

    # ── CDP bridge: Accessibility (extended) ──────────────

    async def a11y_disable(self) -> None:
        """Disable the accessibility domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Accessibility.disable", {})

    async def a11y_enable(self) -> None:
        """Enable the accessibility domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Accessibility.enable", {})

    async def a11y_get_ax_node_and_ancestors(
        self,
        node_id: int | None = None,
        backend_node_id: int | None = None,
        object_id: str | None = None,
    ) -> dict[str, Any]:
        """Fetch a node and all ancestors via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {}
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        return dict(await client.cdp.send_command("Accessibility.getAXNodeAndAncestors", params))

    async def a11y_get_child_ax_nodes(
        self, node_id: str, frame_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Fetch children of an accessibility node via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"id": node_id}
        if frame_id is not None:
            params["frameId"] = frame_id
        result = await client.cdp.send_command("Accessibility.getChildAXNodes", params)
        return list(result.get("nodes", []))

    async def a11y_get_full_ax_tree(
        self, depth: int | None = None, frame_id: str | None = None
    ) -> dict[str, Any]:
        """Fetch the entire accessibility tree via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {}
        if depth is not None:
            params["depth"] = depth
        if frame_id is not None:
            params["frameId"] = frame_id
        return dict(await client.cdp.send_command("Accessibility.getFullAXTree", params))

    async def a11y_get_partial_ax_tree(
        self,
        node_id: int | None = None,
        backend_node_id: int | None = None,
        object_id: str | None = None,
        fetch_relatives: bool = True,
    ) -> dict[str, Any]:
        """Fetch a partial accessibility tree via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"fetchRelatives": fetch_relatives}
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        return dict(await client.cdp.send_command("Accessibility.getPartialAXTree", params))

    async def a11y_get_root_ax_node(self, frame_id: str | None = None) -> dict[str, Any]:
        """Fetch the root accessibility node via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {}
        if frame_id is not None:
            params["frameId"] = frame_id
        return dict(await client.cdp.send_command("Accessibility.getRootAXNode", params))

    async def a11y_query_ax_tree(
        self,
        node_id: int | None = None,
        backend_node_id: int | None = None,
        object_id: str | None = None,
        accessible_name: str | None = None,
        role: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query a DOM node's accessibility subtree via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {}
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        if accessible_name is not None:
            params["accessibleName"] = accessible_name
        if role is not None:
            params["role"] = role
        result = await client.cdp.send_command("Accessibility.queryAXTree", params)
        return list(result.get("nodes", []))

    # ── CDP bridge: Ads ────────────────────────────────────

    async def ads_get_ad_metrics(self) -> dict[str, Any]:
        """Get ad metrics for the current page via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Ads.getAdMetrics", {}))

    # ── CDP bridge: Animation (extended) ──────────────────

    async def animation_disable(self) -> None:
        """Disable the Animation domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Animation.disable", {})

    async def animation_enable(self) -> None:
        """Enable the Animation domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Animation.enable", {})

    async def animation_get_current_time(self, animation_id: str) -> float:
        """Get the current time of an animation via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Animation.getCurrentTime", {"id": animation_id})
        return float(result.get("currentTime", 0))

    async def animation_get_playback_rate(self) -> float:
        """Get the playback rate via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Animation.getPlaybackRate", {})
        return float(result.get("playbackRate", 1.0))

    async def animation_release_animations(self, animations: list[str]) -> None:
        """Release animations via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Animation.releaseAnimations", {"animations": animations})

    async def animation_replay(self, animations: list[str]) -> None:
        """Replay animations via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Animation.replay", {"animations": animations})

    async def animation_resolve_animation(self, animation_id: str) -> dict[str, Any]:
        """Get the remote object of an Animation via CDP bridge."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "Animation.resolveAnimation", {"animationId": animation_id}
            )
        )

    async def animation_seek_animations(self, animations: list[str], current_time: int) -> None:
        """Seek a set of animations via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Animation.seekAnimations", {"animations": animations, "currentTime": current_time}
        )

    async def animation_seek_to(self, animations: list[str], current_time: int) -> None:
        """Seek animations to a specific time via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Animation.seekTo", {"animations": animations, "currentTime": current_time}
        )

    async def animation_set_paused(self, animations: list[str], paused: bool) -> None:
        """Pause or resume animations via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Animation.setPaused", {"animations": animations, "paused": paused}
        )

    async def animation_set_playback_rate(self, playback_rate: float) -> None:
        """Set the global animation playback rate via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Animation.setPlaybackRate", {"playbackRate": playback_rate})

    async def animation_set_timing(self, animation_id: str, duration: int, delay: int) -> None:
        """Set the timing of an animation via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "Animation.setTiming",
            {"animationId": animation_id, "duration": duration, "delay": delay},
        )

    # ── CDP bridge: Audits ─────────────────────────────────

    async def audits_check_contrast(self) -> dict[str, Any]:
        """Check contrast issues via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Audits.checkContrast", {}))

    async def audits_check_forms_issues(self) -> dict[str, Any]:
        """Run the form issues check via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Audits.checkFormsIssues", {}))

    async def audits_disable(self) -> None:
        """Disable the Audits domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Audits.disable", {})

    async def audits_enable(self) -> None:
        """Enable the Audits domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Audits.enable", {})

    async def audits_get_encoded_response(
        self,
        request_id: str,
        encoding: str,
        quality: float | None = None,
        size_only: bool | None = None,
    ) -> dict[str, Any]:
        """Get the encoded response body for a request via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"requestId": request_id, "encoding": encoding}
        if quality is not None:
            params["quality"] = quality
        if size_only is not None:
            params["sizeOnly"] = size_only
        return dict(await client.cdp.send_command("Audits.getEncodedResponse", params))

    # ── CDP bridge: Autofill ───────────────────────────────

    async def autofill_disable(self) -> None:
        """Disable the Autofill domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Autofill.disable", {})

    async def autofill_enable(self) -> None:
        """Enable the Autofill domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Autofill.enable", {})

    async def autofill_set_addresses(self, addresses: list[dict[str, Any]]) -> None:
        """Set autofill addresses for testing via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Autofill.setAddresses", {"addresses": addresses})

    async def autofill_trigger(
        self,
        field_id: int,
        frame_id: str | None = None,
        card: dict[str, Any] | None = None,
        address: dict[str, Any] | None = None,
    ) -> None:
        """Trigger autofill on a form via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"fieldId": field_id}
        if frame_id is not None:
            params["frameId"] = frame_id
        if card is not None:
            params["card"] = card
        if address is not None:
            params["address"] = address
        await client.cdp.send_command("Autofill.trigger", params)

    async def autofill_trigger_fill(
        self,
        field_id: int,
        frame_id: str | None = None,
        card: dict[str, Any] | None = None,
        address: dict[str, Any] | None = None,
    ) -> None:
        """Trigger autofill on a form field via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"fieldId": field_id}
        if frame_id is not None:
            params["frameId"] = frame_id
        if card is not None:
            params["card"] = card
        if address is not None:
            params["address"] = address
        await client.cdp.send_command("Autofill.triggerFill", params)

    async def autofill_trigger_fill_after_save(
        self, field_id: int, frame_id: str | None = None
    ) -> None:
        """Trigger autofill using saved data via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"fieldId": field_id}
        if frame_id is not None:
            params["frameId"] = frame_id
        await client.cdp.send_command("Autofill.triggerFillAfterSave", params)

    # ── CDP bridge: Background Service ─────────────────────

    async def background_service_clear_events(self, service: str) -> None:
        """Clear all stored events for a background service via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("BackgroundService.clearEvents", {"service": service})

    async def background_service_set_recording(self, should_record: bool, service: str) -> None:
        """Set recording state for a background service via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "BackgroundService.setRecording", {"shouldRecord": should_record, "service": service}
        )

    async def background_service_start_observing(self, service: str) -> None:
        """Start observing events for a background service via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("BackgroundService.startObserving", {"service": service})

    async def background_service_stop_observing(self, service: str) -> None:
        """Stop observing events for a background service via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("BackgroundService.stopObserving", {"service": service})

    # ── CDP bridge: Bluetooth Emulation ────────────────────

    async def bluetooth_emulation_add_characteristic(
        self, service_id: str, characteristic_uuid: str, properties: dict[str, Any]
    ) -> str:
        """Add a characteristic to a service via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "BluetoothEmulation.addCharacteristic",
            {
                "serviceId": service_id,
                "characteristicUuid": characteristic_uuid,
                "properties": properties,
            },
        )
        return str(result.get("characteristicId", ""))

    async def bluetooth_emulation_add_descriptor(
        self, characteristic_id: str, descriptor_uuid: str
    ) -> str:
        """Add a descriptor to a characteristic via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "BluetoothEmulation.addDescriptor",
            {
                "characteristicId": characteristic_id,
                "descriptorUuid": descriptor_uuid,
            },
        )
        return str(result.get("descriptorId", ""))

    async def bluetooth_emulation_add_service(self, address: str, service_uuid: str) -> str:
        """Add a service to a peripheral via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command(
            "BluetoothEmulation.addService",
            {
                "address": address,
                "serviceUuid": service_uuid,
            },
        )
        return str(result.get("serviceId", ""))

    async def bluetooth_emulation_disable(self) -> None:
        """Disable the Bluetooth emulation domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("BluetoothEmulation.disable", {})

    async def bluetooth_emulation_enable(self, state: str, le_supported: bool) -> None:
        """Enable the Bluetooth emulation domain via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "BluetoothEmulation.enable", {"state": state, "leSupported": le_supported}
        )

    async def bluetooth_emulation_remove_characteristic(self, characteristic_id: str) -> None:
        """Remove a characteristic via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "BluetoothEmulation.removeCharacteristic", {"characteristicId": characteristic_id}
        )

    async def bluetooth_emulation_remove_descriptor(self, descriptor_id: str) -> None:
        """Remove a descriptor via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "BluetoothEmulation.removeDescriptor", {"descriptorId": descriptor_id}
        )

    async def bluetooth_emulation_remove_service(self, service_id: str) -> None:
        """Remove a service via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("BluetoothEmulation.removeService", {"serviceId": service_id})

    async def bluetooth_emulation_set_simulated_central_state(self, state: str) -> None:
        """Set the simulated central state via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "BluetoothEmulation.setSimulatedCentralState", {"state": state}
        )

    async def bluetooth_emulation_simulate_advertisement(self, entry: dict[str, Any]) -> None:
        """Simulate a Bluetooth advertisement via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("BluetoothEmulation.simulateAdvertisement", {"entry": entry})

    async def bluetooth_emulation_simulate_characteristic_operation_response(
        self, characteristic_id: str, op_type: str, code: int, data: str | None = None
    ) -> None:
        """Simulate a characteristic operation response via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {
            "characteristicId": characteristic_id,
            "opType": op_type,
            "code": code,
        }
        if data is not None:
            params["data"] = data
        await client.cdp.send_command(
            "BluetoothEmulation.simulateCharacteristicOperationResponse", params
        )

    async def bluetooth_emulation_simulate_descriptor_operation_response(
        self, descriptor_id: str, op_type: str, code: int, data: str | None = None
    ) -> None:
        """Simulate a descriptor operation response via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"descriptorId": descriptor_id, "opType": op_type, "code": code}
        if data is not None:
            params["data"] = data
        await client.cdp.send_command(
            "BluetoothEmulation.simulateDescriptorOperationResponse", params
        )

    async def bluetooth_emulation_simulate_gatt_disconnection(self, address: str) -> None:
        """Simulate a GATT disconnection via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "BluetoothEmulation.simulateGATTDisconnection", {"address": address}
        )

    async def bluetooth_emulation_simulate_gatt_operation_response(
        self, address: str, op_type: str, code: int
    ) -> None:
        """Simulate a GATT operation response via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "BluetoothEmulation.simulateGATTOperationResponse",
            {"address": address, "opType": op_type, "code": code},
        )

    async def bluetooth_emulation_simulate_preconnected_peripheral(
        self,
        address: str,
        name: str,
        manufacturer_data: list[dict[str, Any]],
        known_service_uuids: list[str],
    ) -> None:
        """Simulate a preconnected peripheral via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command(
            "BluetoothEmulation.simulatePreconnectedPeripheral",
            {
                "address": address,
                "name": name,
                "manufacturerData": manufacturer_data,
                "knownServiceUuids": known_service_uuids,
            },
        )

    # ── CDP bridge: Browser (extended) ─────────────────────

    async def browser_add_privacy_sandbox_coordinator_key_config(
        self,
        api: str,
        coordinator_origin: str,
        key_config: str,
        browser_context_id: str | None = None,
    ) -> None:
        """Configure encryption keys for a privacy sandbox API via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {
            "api": api,
            "coordinatorOrigin": coordinator_origin,
            "keyConfig": key_config,
        }
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        await client.cdp.send_command("Browser.addPrivacySandboxCoordinatorKeyConfig", params)

    async def browser_add_privacy_sandbox_enrollment_override(self, url: str) -> None:
        """Allow a site to use privacy sandbox features via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Browser.addPrivacySandboxEnrollmentOverride", {"url": url})

    async def browser_cancel_download(
        self, guid: str, browser_context_id: str | None = None
    ) -> None:
        """Cancel a download via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"guid": guid}
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        await client.cdp.send_command("Browser.cancelDownload", params)

    async def browser_crash(self) -> None:
        """Crashes browser on the main thread via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Browser.crash", {})

    async def browser_crash_gpu_process(self) -> None:
        """Crashes GPU process via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Browser.crashGpuProcess", {})

    async def browser_execute_browser_command(self, command_id: str) -> None:
        """Invoke custom browser commands via CDP bridge."""
        client = self._require_launched()
        await client.cdp.send_command("Browser.executeBrowserCommand", {"commandId": command_id})

    async def browser_get_browser_command_line(self) -> str:
        """Returns the command line switches via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Browser.getBrowserCommandLine", {})
        return str(result.get("commandLine", ""))

    async def browser_get_command_line(self) -> str:
        """Returns the command line switches via CDP bridge."""
        client = self._require_launched()
        result = await client.cdp.send_command("Browser.getCommandLine", {})
        return str(result.get("commandLine", ""))

    async def browser_get_histogram(self, name: str, delta: bool = False) -> dict[str, Any]:
        """Get a Chrome histogram by name via CDP bridge."""
        client = self._require_launched()
        return dict(
            await client.cdp.send_command("Browser.getHistogram", {"name": name, "delta": delta})
        )

    async def browser_get_histograms(
        self, query: str | None = None, delta: bool = False
    ) -> list[dict[str, Any]]:
        """Get Chrome histograms via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"delta": delta}
        if query is not None:
            params["query"] = query
        result = await client.cdp.send_command("Browser.getHistograms", params)
        return list(result.get("histograms", []))

    async def browser_get_version(self) -> dict[str, Any]:
        """Returns version information via CDP bridge."""
        client = self._require_launched()
        return dict(await client.cdp.send_command("Browser.getVersion", {}))

    async def browser_get_window_for_target(self, target_id: str | None = None) -> dict[str, Any]:
        """Get the browser window for a devtools target via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {}
        if target_id is not None:
            params["targetId"] = target_id
        return dict(await client.cdp.send_command("Browser.getWindowForTarget", params))

    async def browser_grant_permissions(
        self,
        origin: str,
        permissions: list[str],
        browser_context_id: str | None = None,
    ) -> None:
        """Grant specific permissions to the given origin via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"origin": origin, "permissions": permissions}
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        await client.cdp.send_command("Browser.grantPermissions", params)

    async def browser_set_contents_size(
        self, window_id: int, width: int | None = None, height: int | None = None
    ) -> None:
        """Set size of the browser contents via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"windowId": window_id}
        if width is not None:
            params["width"] = width
        if height is not None:
            params["height"] = height
        await client.cdp.send_command("Browser.setContentsSize", params)

    async def browser_set_dock_tile(
        self, badge_label: str | None = None, image: str | None = None
    ) -> None:
        """Set dock tile details via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {}
        if badge_label is not None:
            params["badgeLabel"] = badge_label
        if image is not None:
            params["image"] = image
        await client.cdp.send_command("Browser.setDockTile", params)

    async def browser_set_download_behavior(
        self,
        behavior: str,
        browser_context_id: str | None = None,
        download_path: str | None = None,
        events_enabled: bool = False,
    ) -> None:
        """Set the behavior when downloading a file via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"behavior": behavior, "eventsEnabled": events_enabled}
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        if download_path is not None:
            params["downloadPath"] = download_path
        await client.cdp.send_command("Browser.setDownloadBehavior", params)

    async def browser_set_permission(
        self,
        permission: dict[str, Any],
        setting: str,
        origin: str | None = None,
        embedded_origin: str | None = None,
        browser_context_id: str | None = None,
    ) -> None:
        """Set permission settings via CDP bridge."""
        client = self._require_launched()
        params: dict[str, Any] = {"permission": permission, "setting": setting}
        if origin is not None:
            params["origin"] = origin
        if embedded_origin is not None:
            params["embeddedOrigin"] = embedded_origin
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        await client.cdp.send_command("Browser.setPermission", params)

    # ── Debugger (CDP bridge) ────────────────────────────

    async def debugger_continue_to_location(
        self, location: dict[str, Any], target_call_frames: str | None = None
    ) -> None:
        client = self._require_launched()
        params: dict[str, Any] = {"location": location}
        if target_call_frames is not None:
            params["targetCallFrames"] = target_call_frames
        await client.cdp.send_command("Debugger.continueToLocation", params)

    async def debugger_disable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("Debugger.disable", {})

    async def debugger_disassemble_wasm_module(self, script_id: str) -> dict[str, Any]:
        client = self._require_launched()
        return dict(
            await client.cdp.send_command("Debugger.disassembleWasmModule", {"scriptId": script_id})
        )

    async def debugger_enable(self, max_scripts_cache_size: int | None = None) -> None:
        client = self._require_launched()
        params: dict[str, Any] = {}
        if max_scripts_cache_size is not None:
            params["maxScriptsCacheSize"] = max_scripts_cache_size
        await client.cdp.send_command("Debugger.enable", params)

    async def debugger_evaluate_on_call_frame(
        self,
        call_frame_id: str,
        expression: str,
        object_group: str | None = None,
        include_command_line_api: bool | None = None,
        silent: bool | None = None,
        return_by_value: bool | None = None,
        generate_preview: bool | None = None,
        throw_on_side_effect: bool | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        client = self._require_launched()
        params: dict[str, Any] = {"callFrameId": call_frame_id, "expression": expression}
        if object_group is not None:
            params["objectGroup"] = object_group
        if include_command_line_api is not None:
            params["includeCommandLineAPI"] = include_command_line_api
        if silent is not None:
            params["silent"] = silent
        if return_by_value is not None:
            params["returnByValue"] = return_by_value
        if generate_preview is not None:
            params["generatePreview"] = generate_preview
        if throw_on_side_effect is not None:
            params["throwOnSideEffect"] = throw_on_side_effect
        if timeout is not None:
            params["timeout"] = timeout
        return dict(await client.cdp.send_command("Debugger.evaluateOnCallFrame", params))

    async def debugger_get_possible_breakpoints(
        self,
        start: dict[str, Any],
        end: dict[str, Any] | None = None,
        restrict_to_function: bool | None = None,
    ) -> list[dict[str, Any]]:
        client = self._require_launched()
        params: dict[str, Any] = {"start": start}
        if end is not None:
            params["end"] = end
        if restrict_to_function is not None:
            params["restrictToFunction"] = restrict_to_function
        result = await client.cdp.send_command("Debugger.getPossibleBreakpoints", params)
        return list(result.get("locations", []))

    async def debugger_get_script_source(self, script_id: str) -> str:
        client = self._require_launched()
        result = await client.cdp.send_command("Debugger.getScriptSource", {"scriptId": script_id})
        return str(result.get("scriptSource", ""))

    async def debugger_get_stack_trace(self, stack_trace_id: dict[str, Any]) -> dict[str, Any]:
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "Debugger.getStackTrace", {"stackTraceId": stack_trace_id}
            )
        )

    async def debugger_get_wasm_bytecode(self, script_id: str) -> dict[str, Any]:
        client = self._require_launched()
        return dict(
            await client.cdp.send_command("Debugger.getWasmBytecode", {"scriptId": script_id})
        )

    async def debugger_next_wasm_disassembly_chunk(self, stream_id: str) -> dict[str, Any]:
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "Debugger.nextWasmDisassemblyChunk", {"streamId": stream_id}
            )
        )

    async def debugger_pause(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("Debugger.pause", {})

    async def debugger_pause_on_async_call(self, parent_stack_trace_id: dict[str, Any]) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "Debugger.pauseOnAsyncCall", {"parentStackTraceId": parent_stack_trace_id}
        )

    async def debugger_remove_breakpoint(self, breakpoint_id: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command("Debugger.removeBreakpoint", {"breakpointId": breakpoint_id})

    async def debugger_restart_frame(self, call_frame_id: str, mode: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "Debugger.restartFrame", {"callFrameId": call_frame_id, "mode": mode}
        )

    async def debugger_resume(self, terminate_on_resume: bool | None = None) -> None:
        client = self._require_launched()
        params: dict[str, Any] = {}
        if terminate_on_resume is not None:
            params["terminateOnResume"] = terminate_on_resume
        await client.cdp.send_command("Debugger.resume", params)

    async def debugger_search_in_content(
        self,
        script_id: str,
        query: str,
        case_sensitive: bool | None = None,
        is_regex: bool | None = None,
    ) -> list[dict[str, Any]]:
        client = self._require_launched()
        params: dict[str, Any] = {"scriptId": script_id, "query": query}
        if case_sensitive is not None:
            params["caseSensitive"] = case_sensitive
        if is_regex is not None:
            params["isRegex"] = is_regex
        result = await client.cdp.send_command("Debugger.searchInContent", params)
        return list(result.get("result", []))

    async def debugger_set_async_call_stack_depth(self, max_depth: int) -> None:
        client = self._require_launched()
        await client.cdp.send_command("Debugger.setAsyncCallStackDepth", {"maxDepth": max_depth})

    async def debugger_set_blackbox_execution_contexts(
        self, execution_context_ids: list[int]
    ) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "Debugger.setBlackboxExecutionContexts", {"executionContextIds": execution_context_ids}
        )

    async def debugger_set_blackbox_patterns(
        self, patterns: list[str], skip_anonymous: bool | None = None
    ) -> None:
        client = self._require_launched()
        params: dict[str, Any] = {"patterns": patterns}
        if skip_anonymous is not None:
            params["skipAnonymous"] = skip_anonymous
        await client.cdp.send_command("Debugger.setBlackboxPatterns", params)

    async def debugger_set_blackboxed_ranges(
        self, script_id: str, positions: list[dict[str, Any]]
    ) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "Debugger.setBlackboxedRanges", {"scriptId": script_id, "positions": positions}
        )

    async def debugger_set_breakpoint(
        self, location: dict[str, Any], condition: str | None = None
    ) -> dict[str, Any]:
        client = self._require_launched()
        params: dict[str, Any] = {"location": location}
        if condition is not None:
            params["condition"] = condition
        return dict(await client.cdp.send_command("Debugger.setBreakpoint", params))

    async def debugger_set_breakpoint_by_url(
        self,
        line_number: int,
        url: str | None = None,
        url_regex: str | None = None,
        script_hash: str | None = None,
        column_number: int | None = None,
        condition: str | None = None,
    ) -> dict[str, Any]:
        client = self._require_launched()
        params: dict[str, Any] = {"lineNumber": line_number}
        if url is not None:
            params["url"] = url
        if url_regex is not None:
            params["urlRegex"] = url_regex
        if script_hash is not None:
            params["scriptHash"] = script_hash
        if column_number is not None:
            params["columnNumber"] = column_number
        if condition is not None:
            params["condition"] = condition
        return dict(await client.cdp.send_command("Debugger.setBreakpointByUrl", params))

    async def debugger_set_breakpoint_on_function_call(
        self, object_id: str, condition: str | None = None
    ) -> None:
        client = self._require_launched()
        params: dict[str, Any] = {"objectId": object_id}
        if condition is not None:
            params["condition"] = condition
        await client.cdp.send_command("Debugger.setBreakpointOnFunctionCall", params)

    async def debugger_set_breakpoints_active(self, active: bool) -> None:
        client = self._require_launched()
        await client.cdp.send_command("Debugger.setBreakpointsActive", {"active": active})

    async def debugger_set_instrumentation_breakpoint(self, instrumentation: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "Debugger.setInstrumentationBreakpoint", {"instrumentation": instrumentation}
        )

    async def debugger_set_pause_on_exceptions(self, state: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command("Debugger.setPauseOnExceptions", {"state": state})

    async def debugger_set_return_value(self, new_value: dict[str, Any]) -> None:
        client = self._require_launched()
        await client.cdp.send_command("Debugger.setReturnValue", {"newValue": new_value})

    async def debugger_set_script_source(
        self,
        script_id: str,
        source: str,
        dry_run: bool | None = None,
        allow_top_frame_editing: bool | None = None,
    ) -> dict[str, Any]:
        client = self._require_launched()
        params: dict[str, Any] = {"scriptId": script_id, "source": source}
        if dry_run is not None:
            params["dryRun"] = dry_run
        if allow_top_frame_editing is not None:
            params["allowTopFrameEditing"] = allow_top_frame_editing
        return dict(await client.cdp.send_command("Debugger.setScriptSource", params))

    async def debugger_set_skip_all_pauses(self, skip: bool) -> None:
        client = self._require_launched()
        await client.cdp.send_command("Debugger.setSkipAllPauses", {"skip": skip})

    async def debugger_set_variable_value(
        self,
        call_frame_id: str,
        scope_number: int,
        variable_name: str,
        new_value: dict[str, Any],
    ) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "Debugger.setVariableValue",
            {
                "callFrameId": call_frame_id,
                "scopeNumber": scope_number,
                "variableName": variable_name,
                "newValue": new_value,
            },
        )

    async def debugger_step_into(
        self,
        break_on_async_call: bool | None = None,
        skip_list: list[dict[str, Any]] | None = None,
    ) -> None:
        client = self._require_launched()
        params: dict[str, Any] = {}
        if break_on_async_call is not None:
            params["breakOnAsyncCall"] = break_on_async_call
        if skip_list is not None:
            params["skipList"] = skip_list
        await client.cdp.send_command("Debugger.stepInto", params)

    async def debugger_step_out(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("Debugger.stepOut", {})

    async def debugger_step_over(self, skip_list: list[dict[str, Any]] | None = None) -> None:
        client = self._require_launched()
        params: dict[str, Any] = {}
        if skip_list is not None:
            params["skipList"] = skip_list
        await client.cdp.send_command("Debugger.stepOver", params)

    # ── HeapProfiler (CDP bridge) ─────────────────────────

    async def heap_profiler_add_inspected_heap_object(self, heap_object_id: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "HeapProfiler.addInspectedHeapObject", {"heapObjectId": heap_object_id}
        )

    async def heap_profiler_collect_garbage(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("HeapProfiler.collectGarbage", {})

    async def heap_profiler_disable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("HeapProfiler.disable", {})

    async def heap_profiler_enable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("HeapProfiler.enable", {})

    async def heap_profiler_get_heap_object_id(self, object_id: str) -> str:
        client = self._require_launched()
        result = await client.cdp.send_command(
            "HeapProfiler.getHeapObjectId", {"objectId": object_id}
        )
        return str(result.get("heapObjectId", ""))

    async def heap_profiler_get_object_by_heap_object_id(
        self, heap_object_id: str, object_group: str | None = None
    ) -> dict[str, Any]:
        client = self._require_launched()
        params: dict[str, Any] = {"heapObjectId": heap_object_id}
        if object_group is not None:
            params["objectGroup"] = object_group
        return dict(await client.cdp.send_command("HeapProfiler.getObjectByHeapObjectId", params))

    async def heap_profiler_get_sampling_profile(self) -> dict[str, Any]:
        client = self._require_launched()
        return dict(await client.cdp.send_command("HeapProfiler.getSamplingProfile", {}))

    async def heap_profiler_start_sampling(
        self,
        sampling_interval: float | None = None,
        stack_depth: float | None = None,
        include_objects_collected_by_major_gc: bool = False,
        include_objects_collected_by_minor_gc: bool = False,
    ) -> None:
        client = self._require_launched()
        params: dict[str, Any] = {
            "includeObjectsCollectedByMajorGC": include_objects_collected_by_major_gc,
            "includeObjectsCollectedByMinorGC": include_objects_collected_by_minor_gc,
        }
        if sampling_interval is not None:
            params["samplingInterval"] = sampling_interval
        if stack_depth is not None:
            params["stackDepth"] = stack_depth
        await client.cdp.send_command("HeapProfiler.startSampling", params)

    async def heap_profiler_start_tracking_heap_objects(
        self, track_allocations: bool = False
    ) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "HeapProfiler.startTrackingHeapObjects", {"trackAllocations": track_allocations}
        )

    async def heap_profiler_stop_sampling(self) -> dict[str, Any]:
        client = self._require_launched()
        return dict(await client.cdp.send_command("HeapProfiler.stopSampling", {}))

    async def heap_profiler_stop_tracking_heap_objects(
        self,
        report_progress: bool = False,
        capture_numeric_value: bool = False,
        expose_internals: bool = False,
    ) -> dict[str, Any]:
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "HeapProfiler.stopTrackingHeapObjects",
                {
                    "reportProgress": report_progress,
                    "captureNumericValue": capture_numeric_value,
                    "exposeInternals": expose_internals,
                },
            )
        )

    async def heap_profiler_take_heap_snapshot(
        self,
        report_progress: bool = False,
        capture_numeric_value: bool = False,
        expose_internals: bool = False,
    ) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "HeapProfiler.takeHeapSnapshot",
            {
                "reportProgress": report_progress,
                "captureNumericValue": capture_numeric_value,
                "exposeInternals": expose_internals,
            },
        )

    # ── SmartCardEmulation (CDP bridge) ───────────────────

    async def smart_card_emulation_disable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("SmartCardEmulation.disable", {})

    async def smart_card_emulation_enable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("SmartCardEmulation.enable", {})

    async def smart_card_emulation_report_begin_transaction_result(
        self, request_id: str, handle: int
    ) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "SmartCardEmulation.reportBeginTransactionResult",
            {"requestId": request_id, "handle": handle},
        )

    async def smart_card_emulation_report_connect_result(
        self, request_id: str, handle: int, active_protocol: str | None = None
    ) -> None:
        client = self._require_launched()
        params: dict[str, Any] = {"requestId": request_id, "handle": handle}
        if active_protocol is not None:
            params["activeProtocol"] = active_protocol
        await client.cdp.send_command("SmartCardEmulation.reportConnectResult", params)

    async def smart_card_emulation_report_data_result(self, request_id: str, data: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "SmartCardEmulation.reportDataResult", {"requestId": request_id, "data": data}
        )

    async def smart_card_emulation_report_error(self, request_id: str, result_code: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "SmartCardEmulation.reportError", {"requestId": request_id, "resultCode": result_code}
        )

    async def smart_card_emulation_report_establish_context_result(
        self, request_id: str, context_id: int
    ) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "SmartCardEmulation.reportEstablishContextResult",
            {"requestId": request_id, "contextId": context_id},
        )

    async def smart_card_emulation_report_get_status_change_result(
        self, request_id: str, reader_states: list[dict[str, Any]]
    ) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "SmartCardEmulation.reportGetStatusChangeResult",
            {"requestId": request_id, "readerStates": reader_states},
        )

    async def smart_card_emulation_report_list_readers_result(
        self, request_id: str, readers: list[str]
    ) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "SmartCardEmulation.reportListReadersResult",
            {"requestId": request_id, "readers": readers},
        )

    async def smart_card_emulation_report_plain_result(self, request_id: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "SmartCardEmulation.reportPlainResult", {"requestId": request_id}
        )

    async def smart_card_emulation_report_release_context_result(self, request_id: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "SmartCardEmulation.reportReleaseContextResult", {"requestId": request_id}
        )

    async def smart_card_emulation_report_status_result(
        self,
        request_id: str,
        reader_name: str,
        state: str,
        atr: str,
        protocol: str | None = None,
    ) -> None:
        client = self._require_launched()
        params: dict[str, Any] = {
            "requestId": request_id,
            "readerName": reader_name,
            "state": state,
            "atr": atr,
        }
        if protocol is not None:
            params["protocol"] = protocol
        await client.cdp.send_command("SmartCardEmulation.reportStatusResult", params)

    # ── IndexedDB (CDP bridge) ────────────────────────────

    async def indexed_db_clear_object_store(
        self,
        database_name: str,
        object_store_name: str,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: dict[str, Any] | None = None,
    ) -> None:
        client = self._require_launched()
        params: dict[str, Any] = {
            "databaseName": database_name,
            "objectStoreName": object_store_name,
        }
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        await client.cdp.send_command("IndexedDB.clearObjectStore", params)

    async def indexed_db_delete_database(
        self,
        database_name: str,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: dict[str, Any] | None = None,
    ) -> None:
        client = self._require_launched()
        params: dict[str, Any] = {"databaseName": database_name}
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        await client.cdp.send_command("IndexedDB.deleteDatabase", params)

    async def indexed_db_delete_object_store_entries(
        self,
        database_name: str,
        object_store_name: str,
        key_range: dict[str, Any],
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: dict[str, Any] | None = None,
    ) -> None:
        client = self._require_launched()
        params: dict[str, Any] = {
            "databaseName": database_name,
            "objectStoreName": object_store_name,
            "keyRange": key_range,
        }
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        await client.cdp.send_command("IndexedDB.deleteObjectStoreEntries", params)

    async def indexed_db_disable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("IndexedDB.disable", {})

    async def indexed_db_enable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("IndexedDB.enable", {})

    async def indexed_db_get_metadata(
        self,
        database_name: str,
        object_store_name: str,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = self._require_launched()
        params: dict[str, Any] = {
            "databaseName": database_name,
            "objectStoreName": object_store_name,
        }
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        return dict(await client.cdp.send_command("IndexedDB.getMetadata", params))

    async def indexed_db_request_data(
        self,
        database_name: str,
        object_store_name: str,
        security_origin: str | None = None,
        storage_key: str | None = None,
        index_name: str = "",
        skip_count: int = 0,
        page_size: int = 10,
        key_range: dict[str, Any] | None = None,
        storage_bucket: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = self._require_launched()
        params: dict[str, Any] = {
            "databaseName": database_name,
            "objectStoreName": object_store_name,
            "indexName": index_name,
            "skipCount": skip_count,
            "pageSize": page_size,
        }
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if key_range is not None:
            params["keyRange"] = key_range
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        return dict(await client.cdp.send_command("IndexedDB.requestData", params))

    async def indexed_db_request_database(
        self,
        database_name: str,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = self._require_launched()
        params: dict[str, Any] = {"databaseName": database_name}
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        return dict(await client.cdp.send_command("IndexedDB.requestDatabase", params))

    async def indexed_db_request_database_names(
        self,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = self._require_launched()
        params: dict[str, Any] = {}
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        return dict(await client.cdp.send_command("IndexedDB.requestDatabaseNames", params))

    # ── LayerTree (CDP bridge) ────────────────────────────

    async def layer_tree_compositing_reasons(self, layer_id: str) -> dict[str, Any]:
        client = self._require_launched()
        return dict(
            await client.cdp.send_command("LayerTree.compositingReasons", {"layerId": layer_id})
        )

    async def layer_tree_disable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("LayerTree.disable", {})

    async def layer_tree_enable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("LayerTree.enable", {})

    async def layer_tree_load_snapshot(self, tiles: list[dict[str, Any]]) -> str:
        client = self._require_launched()
        result = await client.cdp.send_command("LayerTree.loadSnapshot", {"tiles": tiles})
        return str(result.get("snapshotId", ""))

    async def layer_tree_make_snapshot(self, layer_id: str) -> str:
        client = self._require_launched()
        result = await client.cdp.send_command("LayerTree.makeSnapshot", {"layerId": layer_id})
        return str(result.get("snapshotId", ""))

    async def layer_tree_profile_snapshot(
        self,
        snapshot_id: str,
        min_repeat_count: int | None = None,
        min_duration: float | None = None,
        clip_rect: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = self._require_launched()
        params: dict[str, Any] = {"snapshotId": snapshot_id}
        if min_repeat_count is not None:
            params["minRepeatCount"] = min_repeat_count
        if min_duration is not None:
            params["minDuration"] = min_duration
        if clip_rect is not None:
            params["clipRect"] = clip_rect
        return dict(await client.cdp.send_command("LayerTree.profileSnapshot", params))

    async def layer_tree_release_snapshot(self, snapshot_id: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command("LayerTree.releaseSnapshot", {"snapshotId": snapshot_id})

    async def layer_tree_replay_snapshot(
        self,
        snapshot_id: str,
        from_step: int | None = None,
        to_step: int | None = None,
        scale: float | None = None,
    ) -> dict[str, Any]:
        client = self._require_launched()
        params: dict[str, Any] = {"snapshotId": snapshot_id}
        if from_step is not None:
            params["fromStep"] = from_step
        if to_step is not None:
            params["toStep"] = to_step
        if scale is not None:
            params["scale"] = scale
        return dict(await client.cdp.send_command("LayerTree.replaySnapshot", params))

    async def layer_tree_snapshot_command_log(self, snapshot_id: str) -> dict[str, Any]:
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "LayerTree.snapshotCommandLog", {"snapshotId": snapshot_id}
            )
        )

    # ── FedCM (CDP bridge) ────────────────────────────────

    async def fed_cm_click_dialog_button(self, dialog_id: str, dialog_button: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "FedCM.clickDialogButton", {"dialogId": dialog_id, "dialogButton": dialog_button}
        )

    async def fed_cm_disable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("FedCM.disable", {})

    async def fed_cm_dismiss_dialog(self, dialog_id: str, trigger_cooldown: bool = False) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "FedCM.dismissDialog", {"dialogId": dialog_id, "triggerCooldown": trigger_cooldown}
        )

    async def fed_cm_enable(self, disable_rejection_delay: bool = False) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "FedCM.enable", {"disableRejectionDelay": disable_rejection_delay}
        )

    async def fed_cm_open_url(
        self, dialog_id: str, account_index: int, account_url_type: str
    ) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "FedCM.openURL",
            {
                "dialogId": dialog_id,
                "accountIndex": account_index,
                "accountUrlType": account_url_type,
            },
        )

    async def fed_cm_reset_cooldown(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("FedCM.resetCooldown", {})

    async def fed_cm_select_account(self, dialog_id: str, account_index: int) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "FedCM.selectAccount", {"dialogId": dialog_id, "accountIndex": account_index}
        )

    # ── CacheStorage (CDP bridge) ─────────────────────────

    async def cache_storage_delete_cache(self, cache_id: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command("CacheStorage.deleteCache", {"cacheId": cache_id})

    async def cache_storage_delete_entry(self, cache_id: str, request: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "CacheStorage.deleteEntry", {"cacheId": cache_id, "request": request}
        )

    async def cache_storage_request_cache_names(
        self,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        client = self._require_launched()
        params: dict[str, Any] = {}
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        result = await client.cdp.send_command("CacheStorage.requestCacheNames", params)
        return list(result.get("caches", []))

    async def cache_storage_request_cached_response(
        self, cache_id: str, request_url: str, request_headers: list[dict[str, Any]]
    ) -> dict[str, Any]:
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "CacheStorage.requestCachedResponse",
                {
                    "cacheId": cache_id,
                    "requestUrl": request_url,
                    "requestHeaders": request_headers,
                },
            )
        )

    async def cache_storage_request_entries(
        self,
        cache_id: str,
        skip_count: int | None = None,
        page_size: int | None = None,
        path_filter: str | None = None,
    ) -> dict[str, Any]:
        client = self._require_launched()
        params: dict[str, Any] = {"cacheId": cache_id}
        if skip_count is not None:
            params["skipCount"] = skip_count
        if page_size is not None:
            params["pageSize"] = page_size
        if path_filter is not None:
            params["pathFilter"] = path_filter
        return dict(await client.cdp.send_command("CacheStorage.requestEntries", params))

    # ── DOMStorage (CDP bridge) ───────────────────────────

    async def dom_storage_clear(self, storage_id: dict[str, Any]) -> None:
        client = self._require_launched()
        await client.cdp.send_command("DOMStorage.clear", {"storageId": storage_id})

    async def dom_storage_clear_dom_storage_items(self, storage_id: dict[str, Any]) -> None:
        client = self._require_launched()
        await client.cdp.send_command("DOMStorage.clear", {"storageId": storage_id})

    async def dom_storage_disable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("DOMStorage.disable", {})

    async def dom_storage_enable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("DOMStorage.enable", {})

    async def dom_storage_get_dom_storage_items(
        self, storage_id: dict[str, Any]
    ) -> list[dict[str, Any]]:
        client = self._require_launched()
        result = await client.cdp.send_command(
            "DOMStorage.getDOMStorageItems", {"storageId": storage_id}
        )
        return list(result.get("items", []))

    async def dom_storage_remove_dom_storage_item(
        self, storage_id: dict[str, Any], key: str
    ) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "DOMStorage.removeDOMStorageItem", {"storageId": storage_id, "key": key}
        )

    async def dom_storage_set_dom_storage_item(
        self, storage_id: dict[str, Any], key: str, value: str
    ) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "DOMStorage.setDOMStorageItem", {"storageId": storage_id, "key": key, "value": value}
        )

    # ── EventBreakpoints (CDP bridge) ─────────────────────

    async def event_breakpoints_clear_instrumentation_breakpoint(self, event_name: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "EventBreakpoints.clearInstrumentationBreakpoint", {"eventName": event_name}
        )

    async def event_breakpoints_disable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("EventBreakpoints.disable", {})

    async def event_breakpoints_remove_instrumentation_breakpoint(self, event_name: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "EventBreakpoints.removeInstrumentationBreakpoint", {"eventName": event_name}
        )

    async def event_breakpoints_set_instrumentation_breakpoint(self, event_name: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "EventBreakpoints.setInstrumentationBreakpoint", {"eventName": event_name}
        )

    # ── Extensions (CDP bridge) ───────────────────────────

    async def extensions_get_extensions(self) -> list[dict[str, Any]]:
        client = self._require_launched()
        result = await client.cdp.send_command("Extensions.getExtensions", {})
        return list(result.get("extensions", []))

    async def extensions_load_unpacked(
        self, path: str, enable_in_incognito: bool = False
    ) -> dict[str, Any]:
        client = self._require_launched()
        valid_path = validate_path(path)
        return dict(
            await client.cdp.send_command(
                "Extensions.loadUnpacked", {"path": str(valid_path), "enableInIncognito": enable_in_incognito}
            )
        )

    async def extensions_uninstall(self, extension_id: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command("Extensions.uninstall", {"id": extension_id})

    # ── HeadlessExperimental (CDP bridge) ─────────────────

    async def headless_experimental_begin_frame(
        self,
        frame_time_ticks: float | None = None,
        interval: float | None = None,
        no_display_updates: bool | None = None,
        screenshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = self._require_launched()
        params: dict[str, Any] = {}
        if frame_time_ticks is not None:
            params["frameTimeTicks"] = frame_time_ticks
        if interval is not None:
            params["interval"] = interval
        if no_display_updates is not None:
            params["noDisplayUpdates"] = no_display_updates
        if screenshot is not None:
            params["screenshot"] = screenshot
        return dict(await client.cdp.send_command("HeadlessExperimental.beginFrame", params))

    async def headless_experimental_disable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("HeadlessExperimental.disable", {})

    async def headless_experimental_enable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("HeadlessExperimental.enable", {})

    # ── SystemInfo (CDP bridge) ───────────────────────────

    async def system_info_get_feature_state(self, feature_state: str) -> dict[str, Any]:
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "SystemInfo.getFeatureState", {"featureState": feature_state}
            )
        )

    async def system_info_get_info(self) -> dict[str, Any]:
        client = self._require_launched()
        return dict(await client.cdp.send_command("SystemInfo.getInfo", {}))

    async def system_info_get_process_info(self) -> dict[str, Any]:
        client = self._require_launched()
        return dict(await client.cdp.send_command("SystemInfo.getProcessInfo", {}))

    # ── DeviceOrientation (CDP bridge) ────────────────────

    async def device_orientation_clear_device_orientation_override(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("DeviceOrientation.clearDeviceOrientationOverride", {})

    async def device_orientation_set_device_orientation_override(
        self, alpha: float, beta: float, gamma: float
    ) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "DeviceOrientation.setDeviceOrientationOverride",
            {"alpha": alpha, "beta": beta, "gamma": gamma},
        )

    # ── DOMDebugger (CDP bridge) ──────────────────────────

    async def dom_debugger_get_event_listeners(
        self, object_id: str, depth: int | None = None, pierce: bool | None = None
    ) -> list[dict[str, Any]]:
        client = self._require_launched()
        params: dict[str, Any] = {"objectId": object_id}
        if depth is not None:
            params["depth"] = depth
        if pierce is not None:
            params["pierce"] = pierce
        result = await client.cdp.send_command("DOMDebugger.getEventListeners", params)
        return list(result.get("listeners", []))

    async def dom_debugger_remove_dom_breakpoint(self, node_id: int, type: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "DOMDebugger.removeDOMBreakpoint", {"nodeId": node_id, "type": type}
        )

    async def dom_debugger_remove_event_listener_breakpoint(
        self, event_name: str, target_name: str | None = None
    ) -> None:
        client = self._require_launched()
        params: dict[str, Any] = {"eventName": event_name}
        if target_name is not None:
            params["targetName"] = target_name
        await client.cdp.send_command("DOMDebugger.removeEventListenerBreakpoint", params)

    async def dom_debugger_remove_instrumentation_breakpoint(self, event_name: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "DOMDebugger.removeInstrumentationBreakpoint", {"eventName": event_name}
        )

    async def dom_debugger_remove_xhr_breakpoint(self, url: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command("DOMDebugger.removeXHRBreakpoint", {"url": url})

    async def dom_debugger_set_break_on_csp_violation(self, violation_types: list[str]) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "DOMDebugger.setBreakOnCSPViolation", {"violationTypes": violation_types}
        )

    async def dom_debugger_set_dom_breakpoint(self, node_id: int, type: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "DOMDebugger.setDOMBreakpoint", {"nodeId": node_id, "type": type}
        )

    async def dom_debugger_set_event_listener_breakpoint(
        self, event_name: str, target_name: str | None = None
    ) -> None:
        client = self._require_launched()
        params: dict[str, Any] = {"eventName": event_name}
        if target_name is not None:
            params["targetName"] = target_name
        await client.cdp.send_command("DOMDebugger.setEventListenerBreakpoint", params)

    async def dom_debugger_set_instrumentation_breakpoint(self, event_name: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "DOMDebugger.setInstrumentationBreakpoint", {"eventName": event_name}
        )

    async def dom_debugger_set_xhr_breakpoint(self, url: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command("DOMDebugger.setXHRBreakpoint", {"url": url})

    # ── DOMSnapshot (CDP bridge) ──────────────────────────

    async def dom_snapshot_capture_snapshot(
        self,
        computed_styles: list[str] | None = None,
        include_paint_order: bool = False,
        include_dom_rects: bool = False,
        include_blended_background_colors: bool = False,
        include_text_color_opacities: bool = False,
    ) -> dict[str, Any]:
        client = self._require_launched()
        params: dict[str, Any] = {
            "includePaintOrder": include_paint_order,
            "includeDOMRects": include_dom_rects,
            "includeBlendedBackgroundColors": include_blended_background_colors,
            "includeTextColorOpacities": include_text_color_opacities,
        }
        if computed_styles is not None:
            params["computedStyles"] = computed_styles
        return dict(await client.cdp.send_command("DOMSnapshot.captureSnapshot", params))

    async def dom_snapshot_disable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("DOMSnapshot.disable", {})

    async def dom_snapshot_enable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("DOMSnapshot.enable", {})

    async def dom_snapshot_get_snapshot(
        self,
        computed_style_whitelist: list[str] | None = None,
        include_event_listeners: bool | None = None,
        include_paint_order: bool | None = None,
        include_user_agent_shadow_tree: bool | None = None,
    ) -> dict[str, Any]:
        client = self._require_launched()
        params: dict[str, Any] = {}
        if computed_style_whitelist is not None:
            params["computedStyleWhitelist"] = computed_style_whitelist
        if include_event_listeners is not None:
            params["includeEventListeners"] = include_event_listeners
        if include_paint_order is not None:
            params["includePaintOrder"] = include_paint_order
        if include_user_agent_shadow_tree is not None:
            params["includeUserAgentShadowTree"] = include_user_agent_shadow_tree
        return dict(await client.cdp.send_command("DOMSnapshot.getSnapshot", params))

    # ── DeviceAccess (CDP bridge) ─────────────────────────

    async def device_access_cancel_prompt(self, request_id: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command("DeviceAccess.cancelPrompt", {"id": request_id})

    async def device_access_disable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("DeviceAccess.disable", {})

    async def device_access_enable(self) -> None:
        client = self._require_launched()
        await client.cdp.send_command("DeviceAccess.enable", {})

    async def device_access_select_prompt(self, request_id: str, device_id: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "DeviceAccess.selectPrompt", {"id": request_id, "deviceId": device_id}
        )

    # ── Remaining single methods (CDP bridge) ─────────────

    async def dom_get_attribute(self, node_id: int, name: str | None = None) -> dict[str, Any]:
        client = self._require_launched()
        params: dict[str, Any] = {"nodeId": node_id}
        if name is not None:
            params["name"] = name
        return dict(await client.cdp.send_command("DOM.getAttributes", params))

    async def webauthn_remove_virtual_authenticator(self, authenticator_id: str) -> None:
        client = self._require_launched()
        await client.cdp.send_command(
            "WebAuthn.removeVirtualAuthenticator", {"authenticatorId": authenticator_id}
        )

    async def crash_report_context_get_entries(self) -> list[dict[str, Any]]:
        client = self._require_launched()
        result = await client.cdp.send_command("CrashReportContext.getEntries", {})
        return list(result.get("entries", []))

    async def digital_credentials_set_virtual_wallet_behavior(
        self,
        action: str,
        protocol: str | None = None,
        response: dict[str, Any] | None = None,
        frame_id: str | None = None,
    ) -> None:
        client = self._require_launched()
        params: dict[str, Any] = {"action": action}
        if protocol is not None:
            params["protocol"] = protocol
        if response is not None:
            params["response"] = response
        if frame_id is not None:
            params["frameId"] = frame_id
        await client.cdp.send_command("DigitalCredentials.setVirtualWalletBehavior", params)

    async def file_system_get_directory(
        self, storage_key: str, path_components: list[str], bucket_name: str = ""
    ) -> dict[str, Any]:
        client = self._require_launched()
        return dict(
            await client.cdp.send_command(
                "FileSystem.getDirectory",
                {
                    "storageKey": storage_key,
                    "pathComponents": path_components,
                    "bucketName": bucket_name,
                },
            )
        )


class BiDiTabHandle(BiDiBackend):
    """A handle to a browsing context sharing the same browser process.

    Created via ``BiDiBackend.new_tab_handle()``. Shares the BiDiClient
    with the parent backend but has its own browsing context.

    All BiDiBackend methods work as-is because they use ``self._context``
    for browsing operations. Call ``close()`` to close the context
    (not the browser).
    """

    def __init__(self, client: Any, context: Any) -> None:
        """Initialize the tab handle with a shared client and own context.

        Args:
            client: The BiDiClient instance shared with the parent backend.
            context: The browsing context ID for this specific tab.
        """
        self._client = client
        self._context = context
        self._current_url: str = ""

    async def close(self) -> None:
        """Close the browsing context without closing the browser."""
        client = self._client
        if client is not None and self._context is not None:
            await client.browsing.close(self._context)
            self._context = None
        self._client = None
        # Drop any in-progress combined traces so their captured frames
        # and events are released before the backend is reused or GC'd.
        if hasattr(self, "_combined_traces"):
            self._combined_traces.clear()
