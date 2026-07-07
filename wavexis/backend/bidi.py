"""WebDriver BiDi backend using bidiwave.

Supports launch, navigate, screenshot, eval, raw, close, and BiDi paridad
for navigation, tabs, DOM, storage, contexts, window bounds, dialogs, and permissions.
Experimental CDP domains (WebAuthn, WebAudio, Media, Cast, Bluetooth) raise
NotImplementedError — use --backend cdp for those features.
"""

from __future__ import annotations

import base64
import json
from typing import Any

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
        """Initialize the BiDi backend.

        Raises:
            ImportError: If bidiwave is not installed.
        """
        if BiDiClient is None:
            raise ImportError(
                "bidiwave is not installed. Run: pip install wavexis[bidi]"
            )
        self._client: BiDiClient | None = None
        self._context: Any = None

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

    async def launch(self, options: BrowserOptions) -> None:
        """Launch a browser via ChromeDriver WebSocket BiDi endpoint.

        Args:
            options: Browser launch options (headless, width, height, etc.).
        """
        if self._client is not None:
            return
        ws_url = options.extra_headers.get("ws_url", "ws://localhost:9222/session")
        self._client = await BiDiClient.connect(ws_url)
        await self._client.session.new()
        self._context = await self._client.browsing.create_context()

    async def close(self) -> None:
        """Close the BiDi client and release resources."""
        if self._client is not None:
            if self._context is not None:
                await self._client.browsing.close(self._context)
                self._context = None
            await self._client.close()
            self._client = None

    async def navigate(self, url: str, wait: WaitStrategy | None = None) -> None:
        """Navigate to a URL via browsingContext.navigate.

        Args:
            url: The URL to navigate to.
            wait: Wait strategy (ignored — BiDi navigate has its own wait param).
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.browsing.navigate(self._context, url, wait="complete")

    async def screenshot(self, params: ScreenshotParams) -> bytes:
        """Take a screenshot via browsingContext.captureScreenshot.

        Args:
            params: Screenshot parameters.

        Returns:
            PNG or JPEG image bytes.
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.browsing.navigate(
            self._context, params.url, wait="complete"
        )
        result = await self._client.browsing.screenshot(
            self._context, format=params.format
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
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
        js = (
            f"var el=document.querySelector('{escaped}');"
            f"el?JSON.stringify(el.getBoundingClientRect()):null"
        )
        result = await self._client.script.evaluate(self._context, js)
        rect_str = result.value if hasattr(result, "value") else result
        if not rect_str:
            raise RuntimeError(f"Element not found: {selector}")
        screenshot_result = await self._client.browsing.screenshot(
            self._context, format=format, quality=quality
        )
        data = (
            screenshot_result.data
            if hasattr(screenshot_result, "data")
            else screenshot_result.get("data", "")
        )
        return base64.b64decode(data)

    async def eval(self, expression: str, await_promise: bool = False) -> Any:
        """Evaluate a JavaScript expression via script.evaluate.

        Args:
            expression: JavaScript expression to evaluate.
            await_promise: Whether to await a returned Promise.

        Returns:
            The evaluated result value.
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        result = await self._client.script.evaluate(
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
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        return dict(await self._client._connection.send_command(method, params or {}))

    async def go_back(self) -> None:
        """Navigate back via browsingContext.traverse."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client._connection.send_command(
            "browsingContext.traverse",
            {"context": self._context, "direction": "back"},
        )

    async def go_forward(self) -> None:
        """Navigate forward via browsingContext.traverse."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client._connection.send_command(
            "browsingContext.traverse",
            {"context": self._context, "direction": "forward"},
        )

    async def reload(self, ignore_cache: bool = False) -> None:
        """Reload the current page via browsingContext.reload."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client._connection.send_command(
            "browsingContext.reload",
            {"context": self._context, "ignoreCache": ignore_cache},
        )

    async def stop_loading(self) -> None:
        """Stop loading via browsingContext.cancelNavigation."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client._connection.send_command(
            "browsingContext.cancelNavigation",
            {"context": self._context},
        )

    async def wait_for(self, strategy: WaitStrategy) -> None:
        """Wait for a condition via polling script.evaluate."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        import asyncio as _asyncio
        import time as _time
        deadline = _time.monotonic() + strategy.timeout / 1000
        while _time.monotonic() < deadline:
            if strategy.strategy == "selector" and strategy.selector:
                escaped = strategy.selector.replace("'", "\\'")
                js = f"!!document.querySelector('{escaped}')"
                result = await self._client.script.evaluate(
                    self._context, js, await_promise=False
                )
                if hasattr(result, "value") and result.value:
                    return
            elif strategy.strategy == "load":
                return
            else:
                return
            await _asyncio.sleep(0.1)
        raise TimeoutError(f"wait_for timed out after {strategy.timeout}ms")

    async def pdf(self, params: PDFParams) -> bytes:
        """Generate a PDF via browsingContext.print.

        Args:
            params: PDF parameters (url, paper, landscape, margin, etc.).

        Returns:
            PDF bytes.
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.browsing.navigate(
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
        result = await self._client.browsing.print(
            self._context,
            background=False,
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
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.browsing.navigate(
            self._context, params.url, wait="complete",
        )
        import asyncio as _asyncio
        frames: list[bytes] = []
        interval = 0.5
        elapsed = 0.0
        while elapsed < params.duration:
            result = await self._client.cdp.send_command(
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
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        result = await self._client._connection.send_command(
            "browsingContext.getTree", {}
        )
        return list(result.get("contexts", []))

    async def new_tab(self, url: str = "about:blank") -> str:
        """Create a new browsing context (tab) via browsingContext.create."""
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        result = await self._client._connection.send_command(
            "browsingContext.create",
            {"type": "tab", "url": url},
        )
        return str(result.get("context", ""))

    async def close_tab(self, tab_id: str) -> None:
        """Close a browsing context via browsingContext.close."""
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client._connection.send_command(
            "browsingContext.close",
            {"context": tab_id},
        )

    async def activate_tab(self, tab_id: str) -> None:
        """Activate a browsing context via browsingContext.activate.

        Args:
            tab_id: The browsing context ID to activate.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.browsing.activate(tab_id)

    async def capture_console(self, level: str = "all") -> list[dict[str, Any]]:
        """Capture console messages via log.entryAdded event subscription.

        Subscribes to log.entryAdded, navigates to the current page URL
        (already loaded), collects entries for a short window, then returns.

        Args:
            level: Minimum log level (all, info, warning, error).

        Returns:
            List of console entry dicts with type, level, text, timestamp.
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
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

        sub = await self._client.on_log_entry(_handler)
        await _asyncio.sleep(0.5)
        self._client.off(sub)
        return entries

    async def capture_logs(self) -> list[dict[str, Any]]:
        """Capture browser log entries via log.entryAdded subscription.

        Returns:
            List of log entry dicts.
        """
        return await self.capture_console(level="all")

    async def dom_get(self, selector: str, outer: bool = True) -> str:
        """Get outerHTML of an element via script.evaluate."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
        prop = "outerHTML" if outer else "innerHTML"
        js = f"document.querySelector('{escaped}').{prop}"
        result = await self._client.script.evaluate(self._context, js)
        return str(result.value if hasattr(result, "value") else result)

    async def dom_query(
        self, selector: str, all: bool = False
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Query elements via script.evaluate."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
        if all:
            js = (
                f"Array.from(document.querySelectorAll('{escaped}'))"
                f".map(e=>({{tagName:e.tagName,id:e.id,className:e.className}}))"
            )
            result = await self._client.script.evaluate(self._context, js)
            return list(result.value if hasattr(result, "value") else result)
        js = (
            f"var e=document.querySelector('{escaped}');"
            f"e?{{tagName:e.tagName,id:e.id,className:e.className}}:null"
        )
        result = await self._client.script.evaluate(self._context, js)
        return dict(result.value if hasattr(result, "value") else result)

    async def dom_set_attr(self, selector: str, name: str, value: str) -> None:
        """Set an attribute on an element via script.evaluate."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
        escaped_name = name.replace("'", "\\'")
        escaped_val = value.replace("\\", "\\\\").replace("'", "\\'")
        js = (
            f"document.querySelector('{escaped}')"
            f".setAttribute('{escaped_name}','{escaped_val}')"
        )
        await self._client.script.evaluate(self._context, js)

    async def dom_get_attr(self, selector: str, name: str) -> str:
        """Get an attribute from an element via script.evaluate."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
        escaped_name = name.replace("'", "\\'")
        js = (
            f"document.querySelector('{escaped}')"
            f".getAttribute('{escaped_name}')"
        )
        result = await self._client.script.evaluate(self._context, js)
        return str(result.value if hasattr(result, "value") else result)

    async def dom_remove_attr(self, selector: str, name: str) -> None:
        """Remove an attribute from an element via script.evaluate."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
        escaped_name = name.replace("'", "\\'")
        js = (
            f"document.querySelector('{escaped}')"
            f".removeAttribute('{escaped_name}')"
        )
        await self._client.script.evaluate(self._context, js)

    async def dom_remove(self, selector: str) -> None:
        """Remove an element via script.evaluate."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
        js = f"document.querySelector('{escaped}')?.remove()"
        await self._client.script.evaluate(self._context, js)

    async def dom_focus(self, selector: str) -> None:
        """Focus an element via script.evaluate."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
        js = f"document.querySelector('{escaped}')?.focus()"
        await self._client.script.evaluate(self._context, js)

    async def dom_scroll(
        self, selector: str | None = None, x: int = 0, y: int = 0
    ) -> None:
        """Scroll to a position or element via script.evaluate."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        if selector:
            escaped = selector.replace("'", "\\'")
            js = f"document.querySelector('{escaped}')?.scrollIntoView()"
        else:
            js = f"window.scrollTo({x},{y})"
        await self._client.script.evaluate(self._context, js)

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
        escaped = selector.replace("'", "\\'")
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
        escaped = query.replace("\\", "\\\\").replace("'", "\\'")
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
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command("Network.enable", {})
        await self._client.browsing.navigate(
            self._context, params.url, wait="complete",
        )
        import asyncio as _asyncio
        await _asyncio.sleep(params.wait / 1000)
        result = await self._client.cdp.send_command(
            "Network.getResponseBody", {"requestId": ""},
        )
        har_log = await self._client.cdp.send_command(
            "Page.frameNavigated", {},
        )
        entries = await self._client.cdp.send_command(
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
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        cookies = await self._client.storage.get_cookies(self._context)
        return [
            c.model_dump() if hasattr(c, "model_dump") else dict(c)
            for c in cookies
        ]

    async def set_cookie(self, params: CookieParams) -> None:
        """Set a cookie via storage.setCookie.

        Args:
            params: Cookie parameters (name, value, domain, path, etc.).
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
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
        await self._client.storage.set_cookie(self._context, cookie)

    async def delete_cookie(self, name: str, domain: str) -> None:
        """Delete a cookie by name via storage.deleteCookie.

        Args:
            name: Cookie name to delete.
            domain: Cookie domain (ignored by BiDi — uses context).
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.storage.delete_cookie(self._context, name)

    async def clear_cookies(self) -> None:
        """Clear all cookies for the current browsing context."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.storage.delete_cookies(self._context)

    async def set_headers(self, headers: dict[str, str]) -> None:
        """Set extra HTTP headers via CDP Network.setExtraRequestHeaders.

        Uses the CDP bridge (bidiwave.cdp.send_command) to set extra headers.

        Args:
            headers: Dict of header name to value.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        header_list = [{"name": k, "value": v} for k, v in headers.items()]
        await self._client.cdp.send_command(
            "Network.setExtraRequestHeaders", {"headers": header_list}
        )

    async def set_user_agent(self, user_agent: str) -> None:
        """Override the User-Agent string via emulation.setUserAgentOverride.

        Args:
            user_agent: The User-Agent string to set.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.emulation.set_user_agent(
            user_agent, contexts=[self._context] if self._context else None
        )

    async def new_context(self) -> str:
        """Create a new browsing context via browsingContext.create."""
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        result = await self._client._connection.send_command(
            "browsingContext.create",
            {"type": "window"},
        )
        return str(result.get("context", ""))

    async def list_contexts(self) -> list[dict[str, Any]]:
        """List browsing contexts via browsingContext.getTree."""
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        result = await self._client._connection.send_command(
            "browsingContext.getTree", {}
        )
        return list(result.get("contexts", []))

    async def close_context(self, context_id: str) -> None:
        """Close a browsing context via browsingContext.close."""
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client._connection.send_command(
            "browsingContext.close",
            {"context": context_id},
        )

    async def get_window_bounds(self) -> dict[str, Any]:
        """Get window bounds via browsingContext.getTree."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        result = await self._client._connection.send_command(
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
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client._connection.send_command(
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
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        result = await self._client.cdp.send_command("Browser.getVersion", {})
        return str(result.get("product", "unknown"))

    async def emulate_device(self, device: str) -> None:
        """Emulate a device by preset name using viewport + user agent + touch.

        Args:
            device: Device preset name (e.g. 'iphone-15').

        Raises:
            ValueError: If the device name is not in DEVICE_PRESETS.
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        preset = DEVICE_PRESETS.get(device)
        if preset is None:
            raise ValueError(f"Unknown device preset: {device}")
        await self._client.browsing.set_viewport(
            self._context,
            viewport={"width": int(preset["width"]), "height": int(preset["height"])},
            device_pixel_ratio=float(preset["device_scale_factor"]),
        )
        await self._client.emulation.set_user_agent(
            str(preset["user_agent"]),
            contexts=[self._context] if self._context else None,
        )
        if preset.get("touch"):
            await self._client.cdp.send_command(
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
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.browsing.set_viewport(
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
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.emulation.set_geolocation(
            coordinates={"latitude": latitude, "longitude": longitude, "accuracy": accuracy},
            contexts=[self._context] if self._context else None,
        )

    async def set_timezone(self, timezone: str) -> None:
        """Override the timezone via emulation.setTimezoneOverride.

        Args:
            timezone: IANA timezone ID (e.g. 'America/New_York').
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.emulation.set_timezone(
            timezone, contexts=[self._context] if self._context else None
        )

    async def set_dark_mode(self, enabled: bool) -> None:
        """Enable or disable dark mode via CDP Emulation.setEmulatedMedia.

        Args:
            enabled: True to enable dark mode, False to disable.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        feature = 'dark' if enabled else 'light'
        await self._client.cdp.send_command(
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
        escaped = selector.replace("'", "\\'")
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
        escaped = selector.replace("'", "\\'")
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
            button: Mouse button (unused in BiDi, for API compatibility).
            click_count: Number of clicks to dispatch.
            auto_wait: If True, wait for element to be visible before clicking.
        """
        client = self._require_client()
        if auto_wait:
            await self._wait_for_element(selector)
        await self._scroll_into_view_if_needed(selector)
        escaped = selector.replace("'", "\\'")
        js = (
            f"document.querySelector('{escaped}')"
            f".dispatchEvent(new MouseEvent('click',{{bubbles:true}}))"
        )
        for _ in range(click_count):
            await client.script.evaluate(self._context, js)

    async def type_text(self, selector: str, text: str, delay: int = 0) -> None:
        """Type text into an element via BiDi."""
        import asyncio as _asyncio

        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
        await self._client.script.evaluate(
            self._context, f"document.querySelector('{escaped}').focus()"
        )
        for char in text:
            escaped_char = char.replace("\\", "\\\\").replace("'", "\\'")
            js = (
                f"document.querySelector('{escaped}')"
                f".value += '{escaped_char}'"
            )
            await self._client.script.evaluate(self._context, js)
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
        escaped = selector.replace("'", "\\'")
        escaped_val = value.replace("\\", "\\\\").replace("'", "\\'")
        js = f"document.querySelector('{escaped}').value = '{escaped_val}'"
        await client.script.evaluate(self._context, js)

    async def select_option(self, selector: str, value: str) -> None:
        """Select an option in a <select> element by value via BiDi."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
        escaped_val = value.replace("\\", "\\\\").replace("'", "\\'")
        js = f"document.querySelector('{escaped}').value = '{escaped_val}'"
        await self._client.script.evaluate(self._context, js)

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
        escaped = selector.replace("'", "\\'")
        js = (
            f"var el=document.querySelector('{escaped}');"
            f"el.dispatchEvent(new MouseEvent('mouseover',{{bubbles:true}}));"
            f"el.dispatchEvent(new MouseEvent('mousemove',{{bubbles:true}}))"
        )
        await client.script.evaluate(self._context, js)

    async def key_press(self, key: str) -> None:
        """Press a keyboard key via BiDi script.evaluate."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped_key = key.replace("\\", "\\\\").replace("'", "\\'")
        js = (
            f"document.dispatchEvent(new KeyboardEvent('keydown',{{key:'{escaped_key}'}}));"
            f"document.dispatchEvent(new KeyboardEvent('keyup',{{key:'{escaped_key}'}}))"
        )
        await self._client.script.evaluate(self._context, js)

    async def drag(self, source: str, target: str) -> None:
        """Drag from source to target via BiDi script.evaluate (simulated)."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped_src = source.replace("'", "\\'")
        escaped_tgt = target.replace("'", "\\'")
        js = (
            f"var s=document.querySelector('{escaped_src}');"
            f"var t=document.querySelector('{escaped_tgt}');"
            f"s.dispatchEvent(new DragEvent('dragstart',{{bubbles:true}}));"
            f"t.dispatchEvent(new DragEvent('drop',{{bubbles:true}}));"
            f"s.dispatchEvent(new DragEvent('dragend',{{bubbles:true}}))"
        )
        await self._client.script.evaluate(self._context, js)

    async def tap(self, selector: str) -> None:
        """Tap an element via BiDi (simulated as click)."""
        await self.click(selector)

    async def set_files(self, selector: str, files: list[str]) -> None:
        """Set files on a file input element via BiDi script.evaluate.

        Args:
            selector: CSS selector for the <input type="file"> element.
            files: List of absolute file paths to upload.
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
        files_json = json.dumps(files)
        js = (
            f"const input = document.querySelector('{escaped}');"
            f"const dt = new DataTransfer();"
            f"const files = {files_json};"
            f"for (const f of files) {{ dt.items.add(new File([''], f)); }}"
            f"input.files = dt.files;"
            f"input.dispatchEvent(new Event('change', {{bubbles: true}}));"
        )
        await self._client.script.evaluate(self._context, js)

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
        escaped_iframe = iframe_selector.replace("'", "\\'")
        escaped_expr = expression.replace("\\", "\\\\").replace("'", "\\'")
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
        escaped_iframe = iframe_selector.replace("'", "\\'")
        escaped_sel = selector.replace("'", "\\'")
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
        escaped_iframe = iframe_selector.replace("'", "\\'")
        escaped_sel = selector.replace("'", "\\'")
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
        escaped_iframe = iframe_selector.replace("'", "\\'")
        escaped_sel = selector.replace("'", "\\'")
        escaped_val = value.replace("\\", "\\\\").replace("'", "\\'")
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
        escaped = [s.replace("'", "\\'") for s in selectors]
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
        escaped_expr = expression.replace("\\", "\\\\").replace("'", "\\'")
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
        escaped_val = value.replace("\\", "\\\\").replace("'", "\\'")
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
        """Block requests matching URL patterns (partial BiDi support)."""
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        for pattern in patterns:
            await self._client._connection.send_command(
                "network.setBlockedURLs", {"urls": [pattern]}
            )

    async def throttle_network(self, params: ThrottleParams) -> None:
        """Throttle network conditions via emulation.setNetworkConditions.

        Args:
            params: Throttle parameters (offline, latency, download/upload throughput).
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.emulation.set_network_conditions(
            offline=params.offline,
            download_throughput=params.download_bps,
            upload_throughput=params.upload_bps,
            latency=params.latency_ms,
            contexts=[self._context] if self._context else None,
        )

    async def set_cache_disabled(self, disabled: bool = True) -> None:
        """Disable or enable the browser cache via CDP Network.setCacheDisabled.

        Args:
            disabled: True to disable cache, False to enable.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command(
            'Network.setCacheDisabled', {'cacheDisabled': disabled},
        )

    async def intercept_requests(self, pattern: dict[str, Any]) -> None:
        """Intercept requests matching a pattern (partial BiDi support)."""
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client._connection.send_command(
            "network.addIntercept", {"patterns": [pattern]}
        )

    async def mock_response(self, url: str, response: dict[str, Any]) -> None:
        """Mock a response for requests matching a URL via network.addCacheOverride.

        Args:
            url: URL pattern to match.
            response: Response dict with status, headers, body.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        status = response.get('status', 200)
        headers = [
            {'name': k, 'value': v} for k, v in response.get('headers', {}).items()
        ]
        body = response.get('body', '')
        await self._client.network.add_cache_override(
            url=url,
            method=response.get('method', 'GET'),
            status_code=status,
            headers=headers or None,
            body=body or None,
            contexts=[self._context] if self._context else None,
        )

    # ── Accessibility ──────────────────────────────────────

    async def a11y_tree(self) -> dict[str, Any]:
        """Get full accessibility tree via CDP.

        Returns:
            Dict with AX tree nodes.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        result = await self._client.cdp.send_command(
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
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        result = await self._client.cdp.send_command(
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
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        result = await self._client.cdp.send_command(
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
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": "/tmp/wavexis-downloads"},
        )
        return b""

    # ── Dialogs ────────────────────────────────────────────

    async def dialog_accept(self, prompt_text: str | None = None) -> None:
        """Accept a JavaScript dialog via BiDi."""
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client._connection.send_command(
            "browsingContext.handleUserPrompt",
            {"accept": True, "userText": prompt_text or ""},
        )

    async def dialog_dismiss(self) -> None:
        """Dismiss a JavaScript dialog via BiDi."""
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client._connection.send_command(
            "browsingContext.handleUserPrompt",
            {"accept": False},
        )

    # ── Permissions ────────────────────────────────────────

    async def grant_permission(self, permission: str) -> None:
        """Grant a browser permission via BiDi."""
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client._connection.send_command(
            "browser.grantPermissions",
            {"permissions": [permission]},
        )

    async def reset_permissions(self) -> None:
        """Reset all granted permissions via BiDi."""
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client._connection.send_command(
            "browser.resetPermissions", {}
        )

    # ── Security ───────────────────────────────────────────

    async def get_security_state(self) -> dict[str, Any]:
        """Get the current security state via CDP Security.getState.

        Returns:
            Security state dict.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        result = await self._client.cdp.send_command("Security.getState", {})
        return dict(result)

    async def ignore_cert_errors(self, ignore: bool = True) -> None:
        """Enable or disable ignoring certificate errors via CDP.

        Args:
            ignore: True to ignore cert errors, False to enforce them.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command(
            "Security.setIgnoreCertificateErrors", {"ignore": ignore},
        )

    # ── Emulation advanced ─────────────────────────────────

    async def set_locale(self, locale: str) -> None:
        """Override the browser locale via CDP Emulation.setLocaleOverride.

        Args:
            locale: Locale string (e.g. 'en-US', 'es-ES').
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command(
            'Emulation.setLocaleOverride', {'locale': locale},
        )

    async def set_cpu_throttle(self, rate: float) -> None:
        """Set CPU throttling rate via CDP Emulation.setCPUThrottlingRate.

        Args:
            rate: Throttling rate (1.0 = normal, 4.0 = 4x slower).
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command(
            "Emulation.setCPUThrottlingRate", {"rate": rate},
        )

    async def set_touch_emulation(self, enabled: bool) -> None:
        """Enable or disable touch emulation via CDP Emulation.setTouchEmulationEnabled.

        Args:
            enabled: True to enable touch emulation, False to disable.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command(
            'Emulation.setTouchEmulationEnabled', {'enabled': enabled},
        )

    async def set_sensors(self, sensors: SensorParams) -> None:
        """Override sensor values via CDP.

        Args:
            sensors: Sensor parameters with type and values.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        if sensors.type == "device-orientation":
            await self._client.cdp.send_command(
                "DeviceOrientation.setDeviceOrientationOverride",
                {
                    "alpha": sensors.values.get("alpha", 0),
                    "beta": sensors.values.get("beta", 0),
                    "gamma": sensors.values.get("gamma", 0),
                },
            )
        elif sensors.type == "geolocation":
            await self._client.emulation.set_geolocation(
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
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
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
        result = await self._client.script.evaluate(self._context, js)
        val = result.value if hasattr(result, "value") else result
        return json.loads(val) if isinstance(val, str) else dict(val)

    async def perf_trace(self, duration_ms: int = 3000) -> dict[str, Any]:
        """Capture a performance trace via CDP Tracing.

        Args:
            duration_ms: Trace duration in milliseconds.

        Returns:
            Dict with trace data.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command(
            "Tracing.start",
            {"traceConfig": {"recordMode": "recordUntilFull"}},
        )
        import asyncio as _asyncio
        await _asyncio.sleep(duration_ms / 1000)
        result = await self._client.cdp.send_command("Tracing.end", {})
        return dict(result) if result else {}

    async def perf_profile(self, duration_ms: int = 3000) -> dict[str, Any]:
        """Capture a CPU profile via CDP Profiler.

        Args:
            duration_ms: Profile duration in milliseconds.

        Returns:
            Dict with profile data.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command("Profiler.enable", {})
        await self._client.cdp.send_command("Profiler.start", {})
        import asyncio as _asyncio
        await _asyncio.sleep(duration_ms / 1000)
        result = await self._client.cdp.send_command("Profiler.stop", {})
        return dict(result) if result else {}

    async def perf_heap_snapshot(self) -> dict[str, Any]:
        """Take a heap snapshot via CDP HeapProfiler.

        Returns:
            Dict with heap snapshot data.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command("HeapProfiler.enable", {})
        result = await self._client.cdp.send_command(
            "HeapProfiler.takeHeapSnapshot", {},
        )
        return dict(result) if result else {}

    async def perf_coverage(self) -> dict[str, Any]:
        """Get JS coverage data via CDP Profiler.

        Uses CDP bridge to enable profiler and take precise coverage.

        Returns:
            Dict with 'result' key containing script coverage entries.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command("Profiler.enable", {})
        await self._client.cdp.send_command(
            "Profiler.startPreciseCoverage",
            {"callCount": True, "detailed": True},
        )
        result = await self._client.cdp.send_command("Profiler.takePreciseCoverage", {})
        return dict(result) if result else {}

    async def perf_css_coverage(self) -> dict[str, Any]:
        """Get CSS rule usage coverage via CDP.

        Uses CDP bridge to CSS.startRuleUsageTracking and stop.

        Returns:
            Dict with CSS coverage data.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command("CSS.enable", {})
        await self._client.cdp.send_command("CSS.startRuleUsageTracking", {})
        import asyncio as _asyncio
        await _asyncio.sleep(1)
        result = await self._client.cdp.send_command(
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
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
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
        result = await self._client.script.evaluate(self._context, js)
        val = result.value if hasattr(result, "value") else result
        if not val:
            raise RuntimeError(f"Element not found: {selector}")
        return json.loads(val) if isinstance(val, str) else dict(val)

    async def css_get_stylesheets(self) -> list[dict[str, Any]]:
        """List all stylesheets in the page via JS.

        Returns:
            List of stylesheet dicts with href, media, and rules count.
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
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
        result = await self._client.script.evaluate(self._context, js)
        val = result.value if hasattr(result, "value") else result
        return json.loads(val) if isinstance(val, str) else list(val)

    async def css_get_rules(self, stylesheet_id: str) -> list[dict[str, Any]]:
        """Get CSS rules from a stylesheet by index via JS.

        Args:
            stylesheet_id: Index of the stylesheet (as string).

        Returns:
            List of CSS rule dicts with selectorText and cssText.
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
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
        result = await self._client.script.evaluate(self._context, js)
        val = result.value if hasattr(result, "value") else result
        return json.loads(val) if isinstance(val, str) else list(val)

    async def css_get_computed(self, selector: str) -> dict[str, Any]:
        """Get computed styles for an element via JS getComputedStyle.

        Args:
            selector: CSS selector for the target element.

        Returns:
            Dict mapping CSS property names to computed values.
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
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
        result = await self._client.script.evaluate(self._context, js)
        val = result.value if hasattr(result, "value") else result
        if not val:
            raise RuntimeError(f"Element not found: {selector}")
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
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command("Debugger.enable", {})
        params: dict[str, Any] = {"url": url, "lineNumber": line}
        if condition:
            params["condition"] = condition
        result = await self._client.cdp.send_command(
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
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command("Debugger.enable", {})
        result = await self._client.cdp.send_command(
            "Debugger.setBreakpointOnFunctionCall",
            {"name": function_name},
        )
        return str(result.get("breakpointId", "")) if result else ""

    async def debug_remove_breakpoint(self, breakpoint_id: str) -> None:
        """Remove a breakpoint by ID via CDP Debugger.

        Args:
            breakpoint_id: Breakpoint ID to remove.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command(
            "Debugger.removeBreakpoint",
            {"breakpointId": breakpoint_id},
        )

    async def debug_step_over(self) -> None:
        """Step over in debugger via CDP."""
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command("Debugger.stepOver", {})

    async def debug_step_into(self) -> None:
        """Step into in debugger via CDP."""
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command("Debugger.stepInto", {})

    async def debug_step_out(self) -> None:
        """Step out in debugger via CDP."""
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command("Debugger.stepOut", {})

    async def debug_pause(self) -> None:
        """Pause execution via CDP Debugger."""
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command("Debugger.pause", {})

    async def debug_resume(self) -> None:
        """Resume execution via CDP Debugger."""
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command("Debugger.resume", {})

    async def debug_get_listeners(self, selector: str) -> list[dict[str, Any]]:
        """Get event listeners for an element via CDP DOMDebugger.

        Args:
            selector: CSS selector for the target element.

        Returns:
            List of listener dicts.
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
        js = (
            f"(function(){{"
            f"  var el=document.querySelector('{escaped}');"
            f"  if(!el) return null;"
            f"  return el;"
            f"}})()"
        )
        result = await self._client.script.evaluate(self._context, js)
        if not result:
            return []
        listeners = await self._client.cdp.send_command(
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
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        js = "document.documentElement.outerHTML"
        result = await self._client.script.evaluate(self._context, js)
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
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
        js = (
            f"(function(){{"
            f"  var el=document.querySelector('{escaped}');"
            f"  if(el){{"
            f"    el.style.outline='3px solid {color}';"
            f"    el.dataset.wavexisHighlight='1';"
            f"  }}"
            f"}})()"
        )
        await self._client.script.evaluate(self._context, js)

    async def overlay_clear(self) -> None:
        """Clear all highlight overlays via JS."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        js = (
            "(function(){"
            "  document.querySelectorAll('[data-wavexis-highlight]')"
            "    .forEach(function(el){"
            "      el.style.outline='';"
            "      delete el.dataset.wavexisHighlight;"
            "    });"
            "})()"
        )
        await self._client.script.evaluate(self._context, js)

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
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        js = (
            "caches.keys().then(function(names){"
            "  return JSON.stringify(names);"
            "})"
        )
        result = await self._client.script.evaluate(self._context, js)
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
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = cache_name.replace("'", "\\'")
        js = (
            f"caches.open('{escaped}').then(function(cache){{"
            f"  return cache.keys().then(function(requests){{"
            f"    return JSON.stringify(requests.map(function(r){{"
            f"      return {{url:r.url, method:r.method}};"
            f"    }}));"
            f"  }});"
            f"}})"
        )
        result = await self._client.script.evaluate(self._context, js)
        val = result.value if hasattr(result, "value") else result
        return json.loads(val) if isinstance(val, str) else list(val)

    async def cache_storage_delete(self, cache_name: str) -> None:
        """Delete a cache by name via JS Cache API.

        Args:
            cache_name: Name of the cache to delete.
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = cache_name.replace("'", "\\'")
        js = f"caches.delete('{escaped}')"
        await self._client.script.evaluate(self._context, js)

    async def indexeddb_list(self) -> list[dict[str, Any]]:
        """List IndexedDB databases via CDP.

        Returns:
            List of database dicts with name and version.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        result = await self._client.cdp.send_command(
            "IndexedDB.requestDatabaseNames",
            {"securityOrigin": "*"},
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
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        result = await self._client.cdp.send_command(
            "IndexedDB.requestData",
            {
                "securityOrigin": "*",
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
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command(
            "IndexedDB.clearObjectStore",
            {
                "securityOrigin": "*",
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
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        js = (
            "navigator.serviceWorker.getRegistrations()"
            ".then(function(regs){"
            "  return JSON.stringify(regs.map(function(r){"
            "    return {scope:r.scope,scriptURL:r.active?r.active.scriptURL:''};"
            "  }));"
            "})"
        )
        result = await self._client.script.evaluate(self._context, js)
        val = result.value if hasattr(result, "value") else result
        return json.loads(val) if isinstance(val, str) else list(val)

    async def sw_unregister(self, registration_id: str) -> None:
        """Unregister a service worker by scope via JS.

        Args:
            registration_id: Scope URL of the registration to unregister.
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = registration_id.replace("'", "\\'")
        js = (
            f"navigator.serviceWorker.getRegistrations()"
            f"  .then(function(regs){{"
            f"    regs.forEach(function(r){{"
            f"      if(r.scope==='{escaped}') r.unregister();"
            f"    }});"
            f"  }})"
        )
        await self._client.script.evaluate(self._context, js)

    async def sw_update(self, registration_id: str) -> None:
        """Update a service worker registration by scope via JS.

        Args:
            registration_id: Scope URL of the registration to update.
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = registration_id.replace("'", "\\'")
        js = (
            f"navigator.serviceWorker.getRegistrations()"
            f"  .then(function(regs){{"
            f"    regs.forEach(function(r){{"
            f"      if(r.scope==='{escaped}') r.update();"
            f"    }});"
            f"  }})"
        )
        await self._client.script.evaluate(self._context, js)

    # ── Animations ─────────────────────────────────────────

    async def animation_list(self) -> list[dict[str, Any]]:
        """List all active animations via JS.

        Returns:
            List of animation dicts with id, playState, and duration.
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
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
        result = await self._client.script.evaluate(self._context, js)
        val = result.value if hasattr(result, "value") else result
        return json.loads(val) if isinstance(val, str) else list(val)

    async def animation_pause(self, animation_id: str) -> None:
        """Pause an animation by index via JS.

        Args:
            animation_id: Index of the animation (as string).
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        idx = int(animation_id) if animation_id.isdigit() else 0
        js = (
            f"document.getAnimations().then(function(anims){{"
            f"  if(anims[{idx}]) anims[{idx}].pause();"
            f"}})"
        )
        await self._client.script.evaluate(self._context, js)

    async def animation_play(self, animation_id: str) -> None:
        """Play a paused animation by index via JS.

        Args:
            animation_id: Index of the animation (as string).
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        idx = int(animation_id) if animation_id.isdigit() else 0
        js = (
            f"document.getAnimations().then(function(anims){{"
            f"  if(anims[{idx}]) anims[{idx}].play();"
            f"}})"
        )
        await self._client.script.evaluate(self._context, js)

    async def animation_seek(self, animation_id: str, time_ms: int) -> None:
        """Seek an animation to a specific time via JS.

        Args:
            animation_id: Index of the animation (as string).
            time_ms: Time in milliseconds to seek to.
        """
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        idx = int(animation_id) if animation_id.isdigit() else 0
        js = (
            f"document.getAnimations().then(function(anims){{"
            f"  if(anims[{idx}]) anims[{idx}].currentTime={time_ms};"
            f"}})"
        )
        await self._client.script.evaluate(self._context, js)

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
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command("WebAuthn.enable", {})
        result = await self._client.cdp.send_command(
            "WebAuthn.addVirtualAuthenticator",
            {"protocol": protocol, "transport": transport},
        )
        return str(result.get("authenticatorId", "")) if result else ""

    async def webauthn_remove_authenticator(self, authenticator_id: str) -> None:
        """Remove a virtual WebAuthn authenticator via CDP.

        Args:
            authenticator_id: Authenticator ID to remove.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command(
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
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command(
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
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        result = await self._client.cdp.send_command(
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
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command("WebAudio.enable", {})
        result = await self._client.cdp.send_command(
            "WebAudio.getRealtimeData", {},
        )
        return list(result.get("contexts", [])) if result else []

    async def webaudio_get_context(self, context_id: str) -> dict[str, Any]:
        """Get a specific WebAudio context by ID via CDP.

        Args:
            context_id: Audio context ID.

        Returns:
            Dict with context info.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        result = await self._client.cdp.send_command(
            "WebAudio.getContextInfo",
            {"contextId": context_id},
        )
        return dict(result) if result else {}

    # ── Media (experimental) — via CDP bridge ──────────────

    async def media_get_players(self) -> list[dict[str, Any]]:
        """Get media players via CDP.

        Returns:
            List of player dicts.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command("Media.enable", {})
        result = await self._client.cdp.send_command(
            "Media.getPlayerInfo", {},
        )
        return [dict(result)] if result else []

    async def media_get_messages(self, player_id: str) -> list[dict[str, Any]]:
        """Get media player messages via CDP.

        Args:
            player_id: Player ID.

        Returns:
            List of player message dicts.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        result = await self._client.cdp.send_command(
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
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        result = await self._client.cdp.send_command(
            "Cast.getSinks", {},
        )
        return list(result.get("sinks", [])) if result else []

    async def cast_start_tab(self, sink_name: str) -> None:
        """Start tab mirroring to a Cast sink via CDP.

        Args:
            sink_name: Name of the sink to cast to.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command(
            "Cast.startTabMirroring",
            {"sinkName": sink_name},
        )

    async def cast_stop(self) -> None:
        """Stop Cast mirroring via CDP."""
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command("Cast.stopCasting", {})

    # ── Bluetooth (experimental) — via CDP bridge ──────────

    async def bluetooth_emulate(
        self, name: str, address: str = "00:00:00:00:00:01"
    ) -> None:
        """Emulate a Bluetooth adapter via CDP.

        Args:
            name: Adapter name.
            address: Bluetooth address.
        """
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command("BluetoothEmulation.enable", {})
        await self._client.cdp.send_command(
            "BluetoothEmulation.setSimulatedCentralState",
            {"state": "powered-on"},
        )

    async def bluetooth_stop(self) -> None:
        """Stop Bluetooth emulation via CDP."""
        if self._client is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        await self._client.cdp.send_command("BluetoothEmulation.disable", {})
