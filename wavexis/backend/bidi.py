"""WebDriver BiDi backend using bidiwave.

Supports launch, navigate, screenshot, eval, raw, close, and BiDi parity
for navigation, tabs, DOM, storage, contexts, window bounds, dialogs, and permissions.
Experimental CDP domains (WebAuthn, WebAudio, Media, Cast, Bluetooth) raise
NotImplementedError — use --backend cdp for those features.
"""

from __future__ import annotations

import asyncio
import base64
import json
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
)

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
            raise SessionNotInitializedError(
                "Session not initialized. Call launch() first."
            )
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
            raise SessionNotInitializedError(
                "BiDiBackend not launched. Call launch() first."
            )
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
            raise ImportError(
                "bidiwave is not installed. Run: pip install wavexis[bidi]"
            )
        
        # BiDi connects to existing browser, cannot control launch options
        if options.headless is not None:
            import warnings
            warnings.warn(
                "BiDi backend ignores 'headless' option - it connects to "
                "an existing ChromeDriver instance. Use CDP backend for headless control.",
                UserWarning,
                stacklevel=2
            )
        if options.user_data_dir:
            import warnings
            warnings.warn(
                "BiDi backend ignores 'user_data_dir' option - it connects to "
                "an existing ChromeDriver instance. Use CDP backend for profile control.",
                UserWarning,
                stacklevel=2
            )
        if options.timeout:
            import warnings
            warnings.warn(
                "BiDi backend ignores 'timeout' option - it connects to "
                "an existing ChromeDriver instance. Use CDP backend for timeout control.",
                UserWarning,
                stacklevel=2
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
        client = await BiDiClient.connect(ws_url)
        self._client = client
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

            await client.script.evaluate(
                self._context, get_stealth_js()
            )

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
            elif wait.strategy == "selector":
                # For selector, we navigate first then wait separately
                await client.browsing.navigate(self._context, url, wait="complete")
                self._current_url = url
                await self.wait_for(wait)
                return
            else:
                raise ValueError(
                    f"Unsupported wait strategy for BiDi navigate: {wait.strategy}. "
                    "Use 'load', 'domcontentloaded', or 'selector'."
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
            if params.wait:
                if params.wait.strategy == "load":
                    bidi_wait = "complete"
                elif params.wait.strategy == "domcontentloaded":
                    bidi_wait = "interactive"
                elif params.wait.strategy == "selector":
                    # For selector, navigate first then wait separately
                    await client.browsing.navigate(self._context, params.url, wait="complete")
                    await self.wait_for(params.wait)
                else:
                    bidi_wait = "complete"
            
            timeout_ms: int = params.wait.timeout if params.wait is not None else 30000
            try:
                await client.browsing.navigate(
                    self._context, params.url, wait=bidi_wait
                )
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
            f"var el=document.querySelector('{escaped}');"
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
            "(function(){var e=document.getElementById"
            "('__wavexis_annotate');if(e)e.remove();})()"
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
        label_map: dict[str, str] = (
            json.loads(raw) if isinstance(raw, str) else {}
        )
        screenshot_result = await client.browsing.screenshot(
            self._context, format=format
        )
        await client.script.evaluate(
            self._context, self._remove_annotate_js()
        )
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

    async def raw(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
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

    async def wait_for(self, strategy: WaitStrategy) -> None:
        """Wait for a condition via polling script.evaluate."""
        client = self._require_launched()
        import asyncio as _asyncio
        import time as _time
        deadline = _time.monotonic() + strategy.timeout / 1000
        while _time.monotonic() < deadline:
            if strategy.strategy == "selector" and strategy.selector:
                escaped = json.dumps(strategy.selector)
                js = f"!!document.querySelector('{escaped}')"
                result = await client.script.evaluate(
                    self._context, js, await_promise=False
                )
                if hasattr(result, "value") and result.value:
                    return
            elif strategy.strategy == "load":
                # For load, wait for document.readyState == 'complete'
                js = "document.readyState === 'complete'"
                result = await client.script.evaluate(
                    self._context, js, await_promise=False
                )
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
                result = await client.script.evaluate(
                    self._context, js, await_promise=False
                )
                is_idle = getattr(result, "value", False)
                if is_idle:
                    if not hasattr(self, "_networkidle_start"):
                        self._networkidle_start = _time.monotonic()
                    elif _time.monotonic() - self._networkidle_start >= 0.5:
                        delattr(self, "_networkidle_start")
                        return
                else:
                    if hasattr(self, "_networkidle_start"):
                        delattr(self, "_networkidle_start")
            else:
                raise ValueError(f"Unsupported wait strategy: {strategy.strategy}")
            await _asyncio.sleep(0.1)
        raise WaitTimeoutError(strategy.strategy, strategy.timeout)

    async def pdf(self, params: PDFParams) -> bytes:
        """Generate a PDF via browsingContext.print.

        Args:
            params: PDF parameters (url, paper, landscape, margin, etc.).

        Returns:
            PDF bytes.
        """
        client = self._require_launched()
        await client.browsing.navigate(
            self._context, params.url, wait="complete"
        )
        paper = PAPER_SIZES.get(params.paper, PAPER_SIZES["letter"])
        margin_val = float(params.margin.replace("in", "").replace("cm", ""))
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
        await client.browsing.navigate(
            self._context, params.url, wait="complete",
        )
        import asyncio as _asyncio
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
            await _asyncio.sleep(interval)
            elapsed += interval
        return frames

    async def list_tabs(self) -> list[dict[str, Any]]:
        """List browsing contexts (tabs) via browsingContext.getTree."""
        client = self._require_launched()
        result = await client._connection.send_command(
            "browsingContext.getTree", {}
        )
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
        import asyncio as _asyncio
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
                entries.append({
                    "type": getattr(event, "type", "console"),
                    "level": entry_level,
                    "text": getattr(event, "text", ""),
                    "timestamp": getattr(event, "timestamp", None),
                    "args": getattr(event, "args", []),
                })

        sub = await client.on_log_entry(_handler)
        await _asyncio.sleep(0.5)
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
        js = f"document.querySelector('{escaped}').{prop}"
        result = await client.script.evaluate(self._context, js)
        return str(result.value if hasattr(result, "value") else result)

    async def dom_query(
        self, selector: str, all: bool = False
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Query elements via script.evaluate."""
        client = self._require_launched()
        escaped = json.dumps(selector)
        if all:
            js = (
                f"Array.from(document.querySelectorAll('{escaped}'))"
                f".map(e=>({{tagName:e.tagName,id:e.id,className:e.className}}))"
            )
            result = await client.script.evaluate(self._context, js)
            return list(result.value if hasattr(result, "value") else result)
        js = (
            f"var e=document.querySelector('{escaped}');"
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
            f"document.querySelector('{escaped}')"
            f".setAttribute('{escaped_name}','{escaped_val}')"
        )
        await client.script.evaluate(self._context, js)

    async def dom_get_attr(self, selector: str, name: str) -> str:
        """Get an attribute from an element via script.evaluate."""
        client = self._require_launched()
        escaped = json.dumps(selector)
        escaped_name = json.dumps(name)
        js = (
            f"document.querySelector('{escaped}')"
            f".getAttribute('{escaped_name}')"
        )
        result = await client.script.evaluate(self._context, js)
        return str(result.value if hasattr(result, "value") else result)

    async def dom_remove_attr(self, selector: str, name: str) -> None:
        """Remove an attribute from an element via script.evaluate."""
        client = self._require_launched()
        escaped = json.dumps(selector)
        escaped_name = json.dumps(name)
        js = (
            f"document.querySelector('{escaped}')"
            f".removeAttribute('{escaped_name}')"
        )
        await client.script.evaluate(self._context, js)

    async def dom_remove(self, selector: str) -> None:
        """Remove an element via script.evaluate."""
        client = self._require_launched()
        escaped = json.dumps(selector)
        js = f"document.querySelector('{escaped}')?.remove()"
        await client.script.evaluate(self._context, js)

    async def dom_focus(self, selector: str) -> None:
        """Focus an element via script.evaluate."""
        client = self._require_launched()
        escaped = json.dumps(selector)
        js = f"document.querySelector('{escaped}')?.focus()"
        await client.script.evaluate(self._context, js)

    async def dom_scroll(
        self, selector: str | None = None, x: int = 0, y: int = 0
    ) -> None:
        """Scroll to a position or element via script.evaluate."""
        client = self._require_launched()
        if selector:
            escaped = json.dumps(selector)
            js = f"document.querySelector('{escaped}')?.scrollIntoView()"
        else:
            js = f"window.scrollTo({x},{y})"
        await client.script.evaluate(self._context, js)

    async def suggest_locator(
        self, selector: str, all: bool = False
    ) -> list[str] | str:
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
            f"var el=document.querySelector('{escaped}');"
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
        """Build JS that finds elements by natural language text query."""
        escaped = json.dumps(query)
        return (
            f"(function(){{"
            f"var q='{escaped}'.toLowerCase().trim();"
            f"var words=q.split(/\\s+/);"
            f"var els=Array.from(document.querySelectorAll('*'));"
            f"var results=[];"
            f"for(var i=0;i<els.length;i++){{"
            f"var el=els[i];"
            f"var rect=el.getBoundingClientRect();"
            f"if(rect.width===0||rect.height===0)continue;"
            f"var texts=["
            f"(el.textContent||'').trim(),"
            f"el.getAttribute('aria-label')||'',"
            f"el.getAttribute('placeholder')||'',"
            f"el.getAttribute('title')||'',"
            f"el.getAttribute('alt')||'',"
            f"el.getAttribute('value')||''"
            f"].map(function(t){{return t.toLowerCase()}});"
            f"var bestScore=0;"
            f"for(var j=0;j<texts.length;j++){{"
            f"var t=texts[j];if(!t)continue;"
            f"if(t===q){{bestScore=100;break;}}"
            f"if(t.indexOf(q)>=0){{bestScore=Math.max(bestScore,80);}}"
            f"if(q.indexOf(t)>=0&&t.length>3){{bestScore=Math.max(bestScore,60);}}"
            f"var matched=0;"
            f"for(var k=0;k<words.length;k++){{"
            f"if(t.indexOf(words[k])>=0)matched++;"
            f"}}"
            f"if(matched>0)bestScore=Math.max(bestScore,"
            f"Math.round(matched/words.length*50));"
            f"}}"
            f"if(bestScore>0){{"
            f"var tag=el.tagName.toLowerCase();"
            f"var sel=tag;"
            f"if(el.id)sel='#'+CSS.escape(el.id);"
            f"else if(el.getAttribute('data-testid'))"
            f"sel='[data-testid=\"'+el.getAttribute('data-testid')+'\"]';"
            f"else if(el.getAttribute('aria-label'))"
            f"sel=tag+'[aria-label=\"'+el.getAttribute('aria-label')+'\"]';"
            f"else if(el.classList.length>0)"
            f"sel=tag+'.'+Array.from(el.classList).join('.');"
            f"results.push({{score:bestScore,sel:sel}});"
            f"}}"
            f"}}"
            f"results.sort(function(a,b){{return b.score-a.score}});"
            f"return JSON.stringify(results.map(function(r){{return r.sel}}));"
            f"}})()"
        )

    async def find_by_text(
        self, query: str, all: bool = False
    ) -> list[str] | str:
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

    async def nl_click(
        self, query: str, auto_wait: bool = True
    ) -> None:
        """Click an element found by natural language text query.

        Args:
            query: Natural language query (e.g. "login button").
            auto_wait: If True, wait for element to be visible before clicking.
        """
        selector = await self.find_by_text(query)
        assert isinstance(selector, str)
        await self.click(selector, auto_wait=auto_wait)

    async def nl_fill(
        self, query: str, value: str, auto_wait: bool = True
    ) -> None:
        """Fill an input element found by natural language text query.

        Args:
            query: Natural language query (e.g. "email field").
            value: Value to set in the input field.
            auto_wait: If True, wait for element to be visible before filling.
        """
        selector = await self.find_by_text(query)
        assert isinstance(selector, str)
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
            self._context, params.url, wait="complete",
        )
        import asyncio as _asyncio
        await _asyncio.sleep(params.timeout / 1000)
        result = await client.cdp.send_command(
            "Network.getResponseBody", {"requestId": ""},
        )
        har_log = await client.cdp.send_command(
            "Page.frameNavigated", {},
        )
        entries = await client.cdp.send_command(
            "Network.getCookies", {},
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
        return [
            c.model_dump() if hasattr(c, "model_dump") else dict(c)
            for c in cookies
        ]

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
        await client.cdp.send_command(
            "Network.setExtraRequestHeaders", {"headers": header_list}
        )

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

    async def set_window_bounds(
        self, width: int, height: int, x: int = 0, y: int = 0
    ) -> None:
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
                "Emulation.setTouchEmulationEnabled", {"enabled": True},
            )

    async def set_viewport(
        self, width: int, height: int, device_scale_factor: float = 1.0
    ) -> None:
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
        feature = 'dark' if enabled else 'light'
        await client.cdp.send_command(
            'Emulation.setEmulatedMedia',
            {'features': [{'name': 'prefers-color-scheme', 'value': feature}]},
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
        import asyncio as _asyncio
        import time as _time

        client = self._require_client()
        escaped = json.dumps(selector)
        js = (
            f"(function(){{var el=document.querySelector('{escaped}');"
            f"if(!el)return false;"
            f"var rect=el.getBoundingClientRect();"
            f"return rect.width>0&&rect.height>0;}})()"
        )
        deadline = _time.monotonic() + timeout_ms / 1000
        while _time.monotonic() < deadline:
            result = await client.script.evaluate(self._context, js)
            value = getattr(result, "value", None)
            if value is True or value == "true":
                return
            await _asyncio.sleep(0.1)
        raise WaitTimeoutError("selector", timeout_ms)

    async def _scroll_into_view_if_needed(self, selector: str) -> None:
        """Scroll element into view if it's not visible in the viewport."""
        client = self._require_client()
        escaped = json.dumps(selector)
        js = (
            f"(function(){{var el=document.querySelector('{escaped}');"
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
            f"const el=document.querySelector('{escaped}');"
            f"const opts={{bubbles:true, cancelable:true,"
            f"button:{btn}, buttons:{buttons}, detail:{detail}}};"
            f"el.dispatchEvent(new MouseEvent('{event_type}', opts));"
        )
        await client.script.evaluate(self._context, js)

    async def type_text(self, selector: str, text: str, delay: int = 0) -> None:
        """Type text into an element via BiDi."""
        import asyncio as _asyncio

        client = self._require_launched()
        escaped = json.dumps(selector)
        await client.script.evaluate(
            self._context, f"document.querySelector('{escaped}').focus()"
        )
        for char in text:
            escaped_char = json.dumps(char)
            js = (
                f"document.querySelector('{escaped}')"
                f".value += '{escaped_char}'"
            )
            await client.script.evaluate(self._context, js)
            if delay > 0:
                await _asyncio.sleep(delay / 1000)

    async def fill(
        self, selector: str, value: str, auto_wait: bool = True
    ) -> None:
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
        js = f"document.querySelector('{escaped}').value = '{escaped_val}'"
        await client.script.evaluate(self._context, js)

    async def select_option(self, selector: str, value: str) -> None:
        """Select an option in a <select> element by value via BiDi."""
        client = self._require_launched()
        escaped = json.dumps(selector)
        escaped_val = json.dumps(value)
        js = f"document.querySelector('{escaped}').value = '{escaped_val}'"
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
            f"var el=document.querySelector('{escaped}');"
            f"el.dispatchEvent(new MouseEvent('mouseover',{{bubbles:true}}));"
            f"el.dispatchEvent(new MouseEvent('mousemove',{{bubbles:true}}))"
        )
        await client.script.evaluate(self._context, js)

    async def key_press(self, key: str) -> None:
        """Press a keyboard key via BiDi script.evaluate."""
        client = self._require_launched()
        escaped_key = json.dumps(key)
        js = (
            f"document.dispatchEvent(new KeyboardEvent('keydown',{{key:'{escaped_key}'}}));"
            f"document.dispatchEvent(new KeyboardEvent('keyup',{{key:'{escaped_key}'}}))"
        )
        await client.script.evaluate(self._context, js)

    async def drag(self, source: str, target: str) -> None:
        """Drag from source to target via BiDi script.evaluate (simulated)."""
        client = self._require_launched()
        escaped_src = json.dumps(source)
        escaped_tgt = json.dumps(target)
        js = (
            f"var s=document.querySelector('{escaped_src}');"
            f"var t=document.querySelector('{escaped_tgt}');"
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
            f"const input = document.querySelector('{escaped}');"
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
            f"(function(){{var f=document.querySelector('{escaped_iframe}');"
            f"if(!f||!f.contentDocument)return null;"
            f"return (function(){{{escaped_expr}}}).call(f.contentDocument);}})()"
        )
        result = await client.script.evaluate(
            self._context, js, await_promise=await_promise
        )
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
        import asyncio as _asyncio
        import time as _time

        client = self._require_client()
        escaped_iframe = json.dumps(iframe_selector)
        escaped_sel = json.dumps(selector)
        js = (
            f"(function(){{var f=document.querySelector('{escaped_iframe}');"
            f"if(!f||!f.contentDocument)return false;"
            f"var el=f.contentDocument.querySelector('{escaped_sel}');"
            f"if(!el)return false;"
            f"var rect=el.getBoundingClientRect();"
            f"return rect.width>0&&rect.height>0;}})()"
        )
        deadline = _time.monotonic() + timeout_ms / 1000
        while _time.monotonic() < deadline:
            result = await client.script.evaluate(self._context, js)
            value = getattr(result, "value", None)
            if value is True or value == "true":
                return
            await _asyncio.sleep(0.1)
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
            f"(function(){{var f=document.querySelector('{escaped_iframe}');"
            f"if(!f||!f.contentDocument)return false;"
            f"var el=f.contentDocument.querySelector('{escaped_sel}');"
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
            f"(function(){{var f=document.querySelector('{escaped_iframe}');"
            f"if(!f||!f.contentDocument)return false;"
            f"var el=f.contentDocument.querySelector('{escaped_sel}');"
            f"if(!el)return false;"
            f"el.focus();el.value='{escaped_val}';"
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
        parts = [f"var el=document.querySelector('{escaped[0]}')"]
        for sel in escaped[1:]:
            parts.append(
                f"if(!el||!el.shadowRoot)return null;"
                f"el=el.shadowRoot.querySelector('{sel}')"
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
        result = await client.script.evaluate(
            self._context, js, await_promise=await_promise
        )
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
        import asyncio as _asyncio
        import time as _time

        client = self._require_client()
        pierce_js = self._build_shadow_pierce_js(selectors)
        js = (
            f"(function(){{var el=({pierce_js});"
            f"if(!el)return false;"
            f"var rect=el.getBoundingClientRect();"
            f"return rect.width>0&&rect.height>0;}})()"
        )
        deadline = _time.monotonic() + timeout_ms / 1000
        while _time.monotonic() < deadline:
            result = await client.script.evaluate(self._context, js)
            value = getattr(result, "value", None)
            if value is True or value == "true":
                return
            await _asyncio.sleep(0.1)
        raise WaitTimeoutError("selector", timeout_ms)

    async def shadow_click(
        self, selectors: list[str], auto_wait: bool = True
    ) -> None:
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

    async def shadow_fill(
        self, selectors: list[str], value: str, auto_wait: bool = True
    ) -> None:
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
            f"el.focus();el.value='{escaped_val}';"
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
        """Throttle network conditions via emulation.setNetworkConditions.

        Args:
            params: Throttle parameters (offline, latency, download/upload throughput).
        """
        client = self._require_launched()
        await client.emulation.set_network_conditions(
            offline=params.offline,
            download_throughput=params.download_bps,
            upload_throughput=params.upload_bps,
            latency=params.latency_ms,
            contexts=[self._context] if self._context else None,
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
        status = response.get('status', 200)
        headers = [
            {'name': k, 'value': v} for k, v in response.get('headers', {}).items()
        ]
        body = response.get('body', '')
        await client.network.add_cache_override(
            url=url,
            method=response.get('method', 'GET'),
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
        except Exception:
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
        except Exception:
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
            response_headers = [
                {"name": k, "value": v} for k, v in raw_headers.items()
            ]
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
        import asyncio as _asyncio
        from pathlib import Path

        content = await _asyncio.to_thread(Path(har_path).read_text, encoding="utf-8")
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
            await client.script.evaluate(
                self._context, fetch_js, await_promise=True
            )

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
        import time as _time

        client = self._require_client()
        trace_id = f"trace-{int(_time.time() * 1000)}"

        state: dict[str, Any] = {
            "trace_events": [],
            "screenshots": [],
            "network": [],
            "console": [],
            "capture_screenshots": capture_screenshots,
            "capture_network": capture_network,
            "capture_console": capture_console,
        }

        if capture_network:
            await client.cdp.send_command("Network.enable", {})

            def on_network_request(params: dict[str, Any]) -> None:
                state["network"].append({
                    "type": "request",
                    "url": params.get("request", {}).get("url", ""),
                    "method": params.get("request", {}).get("method", ""),
                    "requestId": params.get("requestId", ""),
                    "timestamp": params.get("timestamp"),
                })

            def on_network_response(params: dict[str, Any]) -> None:
                state["network"].append({
                    "type": "response",
                    "url": params.get("response", {}).get("url", ""),
                    "status": params.get("response", {}).get("status", 0),
                    "requestId": params.get("requestId", ""),
                    "timestamp": params.get("timestamp"),
                })

            client.cdp.on("Network.requestWillBeSent", on_network_request)
            client.cdp.on("Network.responseReceived", on_network_response)

        if capture_console:
            await client.cdp.send_command("Runtime.enable", {})

            def on_console_api(params: dict[str, Any]) -> None:
                state["console"].append({
                    "type": params.get("type", "log"),
                    "args": params.get("args", []),
                    "timestamp": params.get("timestamp"),
                })

            client.cdp.on("Runtime.consoleAPICalled", on_console_api)

        if capture_screenshots:
            result = await client.cdp.send_command("Page.captureScreenshot", {})
            if result.get("data"):
                state["screenshots"].append({
                    "timestamp": _time.time(),
                    "data": result["data"],
                })

        await client.cdp.send_command("Tracing.start", {"traceType": "devtools-timeline"})

        self._combined_traces: dict[str, dict[str, Any]] = getattr(
            self, "_combined_traces", {}
        )
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

        async def _on_tracing_complete(params: dict[str, Any]) -> None:
            """Handle Tracing.tracingComplete and extract trace events."""
            stream_handle = params.get("stream")
            if stream_handle:
                chunks: list[bytes] = []
                while True:
                    resp = await client.cdp.send_command(
                        "IO.read", {"handle": stream_handle}
                    )
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
                        trace_events.extend(
                            json.loads(content).get("traceEvents", [])
                        )
                except (zipfile.BadZipFile, json.JSONDecodeError, KeyError, ValueError):
                    trace_events.append({"raw_size": len(raw)})

        client.cdp.on("Tracing.tracingComplete", _on_tracing_complete)
        await client.cdp.send_command("Tracing.end", {})

        if state["capture_screenshots"]:
            screenshot_result = await client.cdp.send_command("Page.captureScreenshot", {})
            if screenshot_result.get("data"):
                state["screenshots"].append({
                    "timestamp": 0,
                    "data": screenshot_result["data"],
                })

        import asyncio as _asyncio

        await _asyncio.sleep(0.5)

        result: dict[str, Any] = {
            "trace_events": trace_events,
            "screenshots": state["screenshots"],
            "network": state["network"],
            "console": state["console"],
        }
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
        """Subscribe to real-time browser events.

        Args:
            event_types: List of event types to subscribe to.
            callback: Callable that receives event dicts.

        Returns:
            A subscription ID for later unsubscription.
        """
        import time as _time

        client = self._require_client()
        sub_id = f"sub-{int(_time.time() * 1000)}"

        if not hasattr(self, "_subscriptions"):
            self._subscriptions: dict[str, dict[str, Any]] = {}

        handlers: dict[str, Any] = {}

        event_map = {
            "console": ("Runtime.consoleAPICalled", "console"),
            "network_request": ("Network.requestWillBeSent", "network_request"),
            "network_response": ("Network.responseReceived", "network_response"),
            "dialog": ("Page.javascriptDialogOpening", "dialog"),
            "navigation": ("Page.frameNavigated", "navigation"),
        }

        for evt_type in event_types:
            if evt_type in event_map:
                cdp_event, label = event_map[evt_type]

                def make_handler(lbl: str) -> Any:
                    def _handler(params: dict[str, Any]) -> None:
                        callback({"type": lbl, "data": params})
                    return _handler

                handler = make_handler(label)
                client.cdp.on(cdp_event, handler)
                handlers[cdp_event] = handler

                if evt_type in ("network_request", "network_response"):
                    import asyncio as _asyncio

                    _asyncio.ensure_future(
                        client.cdp.send_command("Network.enable", {})
                    )
                elif evt_type == "console":
                    import asyncio as _asyncio

                    _asyncio.ensure_future(
                        client.cdp.send_command("Runtime.enable", {})
                    )

        self._subscriptions[sub_id] = handlers
        return sub_id

    async def unsubscribe_events(self, subscription_id: str) -> None:
        """Unsubscribe from events by subscription ID.

        Args:
            subscription_id: The ID returned by subscribe_events.
        """
        client = self._require_client()
        subs: dict[str, dict[str, Any]] = getattr(self, "_subscriptions", {})
        handlers = subs.pop(subscription_id, {})
        for cdp_event, handler in handlers.items():
            client.cdp.off(cdp_event, handler)

    # ── Accessibility ──────────────────────────────────────

    async def a11y_tree(self) -> dict[str, Any]:
        """Get full accessibility tree via CDP.

        Returns:
            Dict with AX tree nodes.
        """
        client = self._require_launched()
        result = await client.cdp.send_command(
            "Accessibility.getFullAXTree", {},
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

    async def intercept_download(self, pattern: str = ".*") -> bytes:
        """Set download behavior via CDP and return placeholder.

        Uses CDP Page.setDownloadBehavior to allow downloads.
        Actual interception requires event listening which is
        not available via the CDP bridge.

        Args:
            pattern: Unused — kept for API parity.

        Returns:
            Empty bytes placeholder.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": "/tmp/wavexis-downloads"},
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
        await client._connection.send_command(
            "browser.resetPermissions", {}
        )

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
            "Security.setIgnoreCertificateErrors", {"ignore": ignore},
        )

    # ── Emulation advanced ─────────────────────────────────

    async def set_locale(self, locale: str) -> None:
        """Override the browser locale via CDP Emulation.setLocaleOverride.

        Args:
            locale: Locale string (e.g. 'en-US', 'es-ES').
        """
        client = self._require_launched()
        await client.cdp.send_command(
            'Emulation.setLocaleOverride', {'locale': locale},
        )

    async def set_cpu_throttle(self, rate: float) -> None:
        """Set CPU throttling rate via CDP Emulation.setCPUThrottlingRate.

        Args:
            rate: Throttling rate (1.0 = normal, 4.0 = 4x slower).
        """
        client = self._require_launched()
        await client.cdp.send_command(
            "Emulation.setCPUThrottlingRate", {"rate": rate},
        )

    async def set_touch_emulation(self, enabled: bool) -> None:
        """Enable or disable touch emulation via CDP Emulation.setTouchEmulationEnabled.

        Args:
            enabled: True to enable touch emulation, False to disable.
        """
        client = self._require_launched()
        await client.cdp.send_command(
            'Emulation.setTouchEmulationEnabled', {'enabled': enabled},
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
        import asyncio as _asyncio
        await _asyncio.sleep(duration_ms / 1000)
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
        import asyncio as _asyncio
        await _asyncio.sleep(duration_ms / 1000)
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
            "HeapProfiler.takeHeapSnapshot", {},
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
        import asyncio as _asyncio
        await _asyncio.sleep(1)
        result = await client.cdp.send_command(
            "CSS.stopRuleUsageTracking", {},
        )
        return dict(result) if result else {}

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
            f"  var el=document.querySelector('{escaped}');"
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
            f"  var el=document.querySelector('{escaped}');"
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

    # ── Debugging ──────────────────────────────────────────

    async def debug_set_breakpoint(
        self, url: str, line: int, condition: str | None = None
    ) -> str:
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
            "Debugger.setBreakpointByUrl", params,
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
            f"  var el=document.querySelector('{escaped}');"
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

    async def overlay_highlight(
        self, selector: str, color: str = "rgba(255,0,0,0.5)"
    ) -> None:
        """Highlight an element via JS outline.

        Args:
            selector: CSS selector for the element to highlight.
            color: RGBA color string for the outline.
        """
        client = self._require_launched()
        escaped = json.dumps(selector)
        js = (
            f"(function(){{"
            f"  var el=document.querySelector('{escaped}');"
            f"  if(el){{"
            f"    el.style.outline='3px solid {color}';"
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
        """
        client = self._require_client()
        if storage_type not in ("local", "session"):
            raise ValueError(
                f"Invalid storage_type: {storage_type}. Must be 'local' or 'session'."
            )
        result = await client.send(
            "storage.getDOMStorageItems",
            {"storageType": storage_type, "key": key},
        )
        return str(result.get("value", ""))

    async def storage_set(
        self, key: str, value: str, storage_type: str = "local"
    ) -> None:
        """Set a value in DOM storage.

        Args:
            key: The storage key to set.
            value: The value to store.
            storage_type: Storage type ("local" or "session").

        Raises:
            SessionNotInitializedError: If the session is not initialized.
            ValueError: If storage_type is invalid.
        """
        client = self._require_client()
        if storage_type not in ("local", "session"):
            raise ValueError(
                f"Invalid storage_type: {storage_type}. Must be 'local' or 'session'."
            )
        await client.send(
            "storage.setDOMStorageItem",
            {"storageType": storage_type, "key": key, "value": value},
        )

    async def storage_clear(self, storage_type: str = "local") -> None:
        """Clear all items from DOM storage.

        Args:
            storage_type: Storage type ("local" or "session").

        Raises:
            SessionNotInitializedError: If the session is not initialized.
            ValueError: If storage_type is invalid.
        """
        client = self._require_client()
        if storage_type not in ("local", "session"):
            raise ValueError(
                f"Invalid storage_type: {storage_type}. Must be 'local' or 'session'."
            )
        await client.send(
            "storage.clearDOMStorageItems",
            {"storageType": storage_type},
        )

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
        client = self._require_client()
        if storage_type not in ("local", "session"):
            raise ValueError(
                f"Invalid storage_type: {storage_type}. Must be 'local' or 'session'."
            )
        result = await client.send(
            "storage.getDOMStorageItems",
            {"storageType": storage_type},
        )
        items: dict[str, str] = {}
        for entry in result.get("entries", []):
            if len(entry) >= 2:
                items[str(entry[0])] = str(entry[1])
        return items

    async def cache_storage_list(self) -> list[str]:
        """List cache storage names via JS Cache API.

        Returns:
            List of cache names.
        """
        client = self._require_launched()
        js = (
            "caches.keys().then(function(names){"
            "  return JSON.stringify(names);"
            "})"
        )
        result = await client.script.evaluate(self._context, js)
        val = result.value if hasattr(result, "value") else result
        return json.loads(val) if isinstance(val, str) else list(val)

    async def cache_storage_entries(
        self, cache_name: str,
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
            f"caches.open('{escaped}').then(function(cache){{"
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
        js = f"caches.delete('{escaped}')"
        await client.script.evaluate(self._context, js)

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

    async def indexeddb_get_data(
        self, database: str, store: str, key: str = ""
    ) -> Any:
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
            f"      if(r.scope==='{escaped}') r.unregister();"
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
            f"      if(r.scope==='{escaped}') r.update();"
            f"    }});"
            f"  }})"
        )
        await client.script.evaluate(self._context, js)

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

    async def webauthn_add_virtual_authenticator(
        self, protocol: str, transport: str
    ) -> str:
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

    async def webauthn_get_credentials(
        self, authenticator_id: str
    ) -> list[dict[str, Any]]:
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

    # ── WebAudio (experimental) — via CDP bridge ───────────

    async def webaudio_get_contexts(self) -> list[dict[str, Any]]:
        """Get WebAudio contexts via CDP.

        Returns:
            List of AudioContext dicts.
        """
        client = self._require_launched()
        await client.cdp.send_command("WebAudio.enable", {})
        
        contexts: list[dict[str, Any]] = []
        try:
            event = await asyncio.wait_for(
                client.cdp.wait_for_event("WebAudio.contextCreated"),
                timeout=1.0,
            )
            contexts.append(dict(event.get("context", event)))
        except TimeoutError:
            pass
        return contexts

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
            "Cast.getSinks", {},
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

    # ── Bluetooth (experimental) — via CDP bridge ──────────

    async def bluetooth_emulate(
        self, name: str, address: str = "00:00:00:00:00:01"
    ) -> None:
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
        is_dir = await asyncio.to_thread(os.path.isdir, path)
        if is_dir:
            abs_path = await asyncio.to_thread(os.path.abspath, path)
            ext_id = hashlib.sha256(abs_path.encode()).hexdigest()[:32]
            await client.cdp.send_command(
                "Extensions.loadUnpacked",
                {"path": abs_path},
            )
        else:
            ext_id = hashlib.sha256(path.encode()).hexdigest()[:32]
            data = await asyncio.to_thread(
                lambda: open(path, "rb").read()  # noqa: SIM115
            )
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

    async def close(self) -> None:
        """Close the browsing context without closing the browser."""
        client = self._client
        if client is not None and self._context is not None:
            await client.browsing.close(self._context)
            self._context = None
        self._client = None
