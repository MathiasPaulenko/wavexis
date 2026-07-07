"""CDP backend implementation using cdpwave."""

from __future__ import annotations

import asyncio
import base64
import json
import time
from pathlib import Path
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
    NavigationError,
    SessionNotInitializedError,
    WaitTimeoutError,
)

try:
    from cdpwave import CDPClient, CDPSession
except ImportError:
    CDPClient = None  # type: ignore[assignment,misc]
    CDPSession = None  # type: ignore[assignment,misc]


class CDPBackend(AbstractBackend):
    """Chrome DevTools Protocol backend via cdpwave."""

    def __init__(self) -> None:
        """Initialize the CDP backend.

        Raises:
            ImportError: If cdpwave is not installed.
        """
        if CDPClient is None:
            raise ImportError(
                "cdpwave is not installed. Run: pip install wavexis[cdp]"
            )
        self._client: CDPClient | None = None
        self._session: CDPSession | None = None
        self._console_entries: list[dict[str, Any]] = []
        self._log_entries: list[dict[str, Any]] = []
        self._current_url: str = ""

    def _require_session(self) -> CDPSession:
        """Return the current session or raise if not initialized.

        Returns:
            The active CDPSession instance.

        Raises:
            SessionNotInitializedError: If launch() has not been called.
        """
        if self._session is None:
            raise SessionNotInitializedError(
                "Session not initialized. Call launch() first."
            )
        return self._session

    async def launch(self, options: BrowserOptions) -> None:
        """Launch Chrome and create a new page session.

        Args:
            options: Browser launch options (headless, width, height, proxy, etc.).
        """
        extra_args: list[str] = []
        if options.width and options.height:
            extra_args.append(f"--window-size={options.width},{options.height}")
        if options.proxy:
            extra_args.append(f"--proxy-server={options.proxy}")

        if options.browser_url:
            from urllib.parse import urlparse

            parsed = urlparse(options.browser_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 9222
            self._client = await CDPClient.connect(host=host, port=port)  # type: ignore[attr-defined]
        else:
            self._client = await CDPClient.launch(
                headless=options.headless,
                user_data_dir=options.user_data_dir,  # type: ignore[call-arg]
                extra_args=extra_args if extra_args else None,
            )
        self._session = await self._client.new_page()

        if options.user_agent:
            await self._session.emulation.set_user_agent_override(
                user_agent=options.user_agent
            )

        if options.extra_headers:
            await self._session.network.set_extra_http_headers(
                options.extra_headers
            )

        if options.stealth:
            from wavexis.actions.stealth import get_stealth_js

            await self._session.runtime.evaluate(
                get_stealth_js(), await_promise=False
            )

    async def close(self) -> None:
        """Close the browser client and release resources."""
        if self._session is not None:
            await self._session.close()
            self._session = None
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def navigate(self, url: str, wait: WaitStrategy | None = None) -> None:
        """Navigate to a URL and optionally wait for a condition.

        Args:
            url: The URL to navigate to.
            wait: Wait strategy to apply after navigation.

        Raises:
            SessionNotInitializedError: If launch() has not been called.
            WaitTimeoutError: If the wait strategy times out.
        """
        session = self._require_session()

        await session.page.enable()
        await session.page.navigate(url)
        self._current_url = url

        if wait is None or wait.strategy == "load":
            timeout_sec = (wait.timeout if wait else 30000) / 1000
            try:
                await session.wait_for_event(
                    "Page.loadEventFired", timeout=timeout_sec
                )
            except TimeoutError:
                raise WaitTimeoutError("load", wait.timeout if wait else 30000) from None
        elif wait.strategy == "selector":
            await self.wait_for(wait)
        elif wait.strategy == "domcontentloaded":
            timeout_sec = wait.timeout / 1000
            try:
                await session.wait_for_event(
                    "Page.domContentEventFired", timeout=timeout_sec
                )
            except TimeoutError:
                raise WaitTimeoutError("domcontentloaded", wait.timeout) from None

    async def screenshot(self, params: ScreenshotParams) -> bytes:
        """Take a screenshot of the current page.

        Args:
            params: Screenshot parameters (format, quality, full_page, etc.).

        Returns:
            Screenshot image bytes (PNG or JPEG).

        Raises:
            SessionNotInitializedError: If launch() has not been called.
        """
        session = self._require_session()

        if params.device and params.device in DEVICE_PRESETS:
            preset = DEVICE_PRESETS[params.device]
            await session.emulation.set_device_metrics_override(
                width=preset["width"],
                height=preset["height"],
                device_scale_factor=preset["device_scale_factor"],
                mobile=preset["mobile"],
                user_agent=preset["user_agent"],
            )
            if preset.get("touch"):
                await session.emulation.set_touch_emulation_enabled(True)

        result = await session.page.capture_screenshot(
            format=params.format,
            quality=params.quality,
            capture_beyond_viewport=params.full_page,
        )
        data_b64 = result.get("data", "")
        return base64.b64decode(data_b64)

    async def screenshot_selector(
        self, selector: str, format: str = "png", quality: int = 80
    ) -> bytes:
        """Take a screenshot of an element matching a CSS selector.

        Uses CDP to get the element's bounding box and clips the screenshot.

        Args:
            selector: CSS selector for the target element.
            format: Image format ("png" or "jpeg").
            quality: JPEG quality (0-100).

        Returns:
            Screenshot image bytes.
        """
        session = self._require_session()

        doc = await session.dom.get_document()
        root_node_id = doc.get("root", {}).get("nodeId", 0)
        node = await session.dom.query_selector(root_node_id, selector)
        node_id = node.get("nodeId", 0)
        box = await session.dom.get_box_model(node_id)
        model = box.get("model", {})
        borders = model.get("border", [])
        if len(borders) >= 8:
            x = min(borders[0], borders[2], borders[4], borders[6])
            y = min(borders[1], borders[3], borders[5], borders[7])
            width = max(borders[0], borders[2], borders[4], borders[6]) - x
            height = max(borders[1], borders[3], borders[5], borders[7]) - y
        else:
            raise NavigationError(selector, "Could not determine element bounds.")

        clip = {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "scale": 1,
        }
        result = await session.page.capture_screenshot(
            format=format,
            quality=quality,
            clip=clip,
        )
        data_b64 = result.get("data", "")
        return base64.b64decode(data_b64)

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
        session = self._require_session()
        js = self._annotate_js(selectors)
        result = await session.runtime.evaluate(js)
        raw = result.get("result", {}).get("value")
        label_map: dict[str, str] = (
            json.loads(raw) if isinstance(raw, str) else {}
        )
        screenshot = await session.page.capture_screenshot(format=format)
        await session.runtime.evaluate(self._remove_annotate_js())
        data_b64 = screenshot.get("data", "")
        return base64.b64decode(data_b64), label_map

    async def eval(self, expression: str, await_promise: bool = False) -> Any:
        """Evaluate a JavaScript expression.

        Args:
            expression: JavaScript expression to evaluate.
            await_promise: Whether to await a returned Promise.

        Returns:
            The evaluation result value.
        """
        session = self._require_session()

        await session.runtime.enable()
        result = await session.runtime.evaluate(
            expression,
            await_promise=await_promise,
        )
        return result.get("result", {}).get("value")

    async def raw(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a raw CDP command.

        Args:
            method: CDP method name (e.g. "Page.navigate").
            params: Optional command parameters.

        Returns:
            The CDP response result dict.
        """
        session = self._require_session()
        result: dict[str, Any] = await session.send(method, params)
        return result

    async def go_back(self) -> None:
        """Navigate back in browser history."""
        session = self._require_session()
        history = await session.page.get_navigation_history()
        current_idx = history.get("currentIndex", 0)
        entries = history.get("entries", [])
        if current_idx > 0 and entries:
            prev_entry = entries[current_idx - 1]
            await session.page.navigate_to_history_entry(
                prev_entry.get("id", 0)
            )

    async def go_forward(self) -> None:
        """Navigate forward in browser history."""
        session = self._require_session()
        history = await session.page.get_navigation_history()
        current_idx = history.get("currentIndex", 0)
        entries = history.get("entries", [])
        if current_idx < len(entries) - 1:
            next_entry = entries[current_idx + 1]
            await session.page.navigate_to_history_entry(
                next_entry.get("id", 0)
            )

    async def reload(self, ignore_cache: bool = False) -> None:
        """Reload the current page.

        Args:
            ignore_cache: If True, bypass the browser cache.
        """
        session = self._require_session()
        await session.page.reload(ignore_cache=ignore_cache)

    async def stop_loading(self) -> None:
        """Stop all pending navigations and resource loads."""
        session = self._require_session()
        await session.page.stop()

    async def wait_for(self, strategy: WaitStrategy) -> None:
        """Wait for a specific condition.

        Args:
            strategy: Wait strategy (selector, load, url).

        Raises:
            WaitTimeoutError: If the condition is not met within the timeout.
        """
        session = self._require_session()

        timeout_sec = strategy.timeout / 1000
        deadline = time.monotonic() + timeout_sec

        if strategy.strategy == "selector" and strategy.selector:
            escaped = strategy.selector.replace("'", "\\'")
            js = f"document.querySelector('{escaped}') !== null"
            while time.monotonic() < deadline:
                result = await session.runtime.evaluate(js)
                if result.get("result", {}).get("value") is True:
                    return
                await asyncio.sleep(0.1)
            raise WaitTimeoutError("selector", strategy.timeout)

        if strategy.strategy == "load":
            try:
                await session.wait_for_event(
                    "Page.loadEventFired", timeout=timeout_sec
                )
            except TimeoutError:
                raise WaitTimeoutError("load", strategy.timeout) from None
            return

        if strategy.strategy == "url" and strategy.url_pattern:
            while time.monotonic() < deadline:
                result = await session.runtime.evaluate("window.location.href")
                href = result.get("result", {}).get("value", "")
                if strategy.url_pattern in href:
                    return
                await asyncio.sleep(0.1)
            raise WaitTimeoutError("url", strategy.timeout)

    async def pdf(self, params: PDFParams) -> bytes:
        """Generate a PDF of the current page.

        Args:
            params: PDF generation parameters.

        Returns:
            PDF bytes.
        """
        session = self._require_session()

        await session.emulation.set_emulated_media(media=params.media)

        paper_dims = PAPER_SIZES.get(params.paper, PAPER_SIZES["letter"])
        margin_val = float(params.margin.replace("in", ""))

        result = await session.page.print_to_pdf(
            landscape=params.landscape,
            display_header_footer=not params.no_header_footer,
            print_background=True,
            paper_width=paper_dims["width"],
            paper_height=paper_dims["height"],
            margin_top=margin_val,
            margin_bottom=margin_val,
            margin_left=margin_val,
            margin_right=margin_val,
        )
        data_b64 = result.get("data", "")
        return base64.b64decode(data_b64)

    async def screencast(self, params: ScreencastParams) -> list[bytes]:
        """Capture a screencast and return a list of frame bytes.

        Args:
            params: Screencast parameters.

        Returns:
            List of frame image bytes.
        """
        session = self._require_session()

        frames: list[bytes] = []

        def on_frame(event_params: dict[str, Any]) -> None:
            """Handle a screencast frame event and decode the image data.

            Args:
                event_params: CDP event parameters containing base64-encoded frame data.
            """
            data = event_params.get("data")
            if data:
                frames.append(base64.b64decode(data))

        session.on("Page.screencastFrame", on_frame)

        await session.send("Page.startScreencast", {
            "format": params.format,
            "quality": params.quality,
            "maxWidth": params.max_width,
            "maxHeight": params.max_height,
        })

        await asyncio.sleep(params.duration)

        await session.send("Page.stopScreencast")

        return frames

    async def list_tabs(self) -> list[dict[str, Any]]:
        """List all open browser tabs/targets.

        Returns:
            List of target info dicts.
        """
        session = self._require_session()
        result = await session.target.get_targets()
        targets = result.get("targetInfos", [])
        return [t for t in targets if t.get("type") == "page"]

    async def new_tab(self, url: str = "about:blank") -> str:
        """Create a new tab and return its target ID.

        Args:
            url: Initial URL for the new tab.

        Returns:
            The target ID of the new tab.
        """
        session = self._require_session()
        result = await session.target.create_target(url)
        return str(result.get("targetId", ""))

    async def close_tab(self, tab_id: str) -> None:
        """Close a tab by its target ID.

        Args:
            tab_id: The target ID of the tab to close.
        """
        session = self._require_session()
        await session.target.close_target(tab_id)

    async def activate_tab(self, tab_id: str) -> None:
        """Activate (focus) a tab by its target ID.

        Args:
            tab_id: The target ID of the tab to activate.
        """
        session = self._require_session()
        await session.target.activate_target(tab_id)

    async def capture_console(self, level: str = "all") -> list[dict[str, Any]]:
        """Capture console messages at or above the given level.

        Args:
            level: Minimum log level ("all", "error", "warning", "info", "log").

        Returns:
            List of console entry dicts with type, args, and timestamp.
        """
        session = self._require_session()

        entries: list[dict[str, Any]] = []

        def on_console_api(event_params: dict[str, Any]) -> None:
            """Handle a Runtime.consoleAPICalled event and append matching entries.

            Args:
                event_params: CDP event parameters with console API call data.
            """
            entry_type = event_params.get("type", "log")
            if level == "all" or entry_type == level:
                entries.append({
                    "type": entry_type,
                    "args": event_params.get("args", []),
                    "executionContextId": event_params.get("executionContextId"),
                    "timestamp": event_params.get("timestamp"),
                })

        session.on("Runtime.consoleAPICalled", on_console_api)

        await session.runtime.enable()
        await asyncio.sleep(0.5)

        return entries

    async def capture_logs(self) -> list[dict[str, Any]]:
        """Capture browser log entries.

        Returns:
            List of log entry dicts with level, text, and timestamp.
        """
        session = self._require_session()

        entries: list[dict[str, Any]] = []

        def on_log_entry(event_params: dict[str, Any]) -> None:
            """Handle a Log.entryAdded event and append the log entry.

            Args:
                event_params: CDP event parameters containing the log entry.
            """
            entry = event_params.get("entry", {})
            entries.append({
                "level": entry.get("level", "info"),
                "text": entry.get("text", ""),
                "timestamp": entry.get("timestamp"),
                "url": entry.get("url"),
                "lineNumber": entry.get("lineNumber"),
                "stackTrace": entry.get("stackTrace", []),
            })

        session.on("Log.entryAdded", on_log_entry)

        await session.log.enable()
        await asyncio.sleep(0.5)

        return entries

    # ── DOM ────────────────────────────────────────────────

    async def _find_node(self, selector: str) -> int:
        """Find a node by CSS selector and return its nodeId."""
        session = self._require_session()
        await session.dom.enable()
        doc = await session.dom.get_document()
        root_node_id = doc.get("root", {}).get("nodeId", 0)
        result = await session.dom.query_selector(root_node_id, selector)
        node_id = result.get("nodeId", 0)
        if node_id == 0:
            raise ElementNotFoundError(selector)
        return int(node_id)

    async def dom_get(self, selector: str, outer: bool = True) -> str:
        """Get the HTML of an element matching a CSS selector.

        Args:
            selector: CSS selector for the target element.
            outer: If True, return outerHTML; otherwise innerHTML.

        Returns:
            The HTML string of the element.
        """
        session = self._require_session()
        node_id = await self._find_node(selector)
        if outer:
            result = await session.dom.get_outer_html(node_id)
        else:
            result = await session.dom.get_inner_html(node_id)
        html = result.get("outerHTML", "") if outer else result.get("innerHTML", "")
        return str(html)

    async def dom_query(
        self, selector: str, all: bool = False
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Query elements by CSS selector.

        Args:
            selector: CSS selector string.
            all: If True, return all matches as a list; otherwise first match.

        Returns:
            List of node dicts when all=True, single dict when all=False.
        """
        session = self._require_session()
        await session.dom.enable()
        doc = await session.dom.get_document()
        root_node_id = doc.get("root", {}).get("nodeId", 0)

        if all:
            result = await session.dom.query_selector_all(root_node_id, selector)
            node_ids = result.get("nodeIds", [])
            nodes: list[dict[str, Any]] = []
            for nid in node_ids:
                desc = await session.dom.describe_node(node_id=nid)
                nodes.append(desc.get("node", {}))
            return nodes

        result = await session.dom.query_selector(root_node_id, selector)
        node_id = result.get("nodeId", 0)
        if node_id == 0:
            raise ElementNotFoundError(selector)
        desc = await session.dom.describe_node(node_id=node_id)
        return dict(desc.get("node", {}))

    async def dom_set_attr(self, selector: str, name: str, value: str) -> None:
        """Set an attribute on an element matching a CSS selector."""
        session = self._require_session()
        node_id = await self._find_node(selector)
        await session.dom.set_attribute_value(node_id, name, value)

    async def dom_get_attr(self, selector: str, name: str) -> str:
        """Get an attribute value from an element matching a CSS selector."""
        session = self._require_session()
        node_id = await self._find_node(selector)
        result = await session.dom.get_attribute(node_id, name)
        attrs = result.get("attributes", [])
        for i in range(0, len(attrs) - 1, 2):
            if attrs[i] == name:
                return str(attrs[i + 1])
        return ""

    async def dom_remove_attr(self, selector: str, name: str) -> None:
        """Remove an attribute from an element matching a CSS selector."""
        session = self._require_session()
        node_id = await self._find_node(selector)
        await session.dom.remove_attribute(node_id, name)

    async def dom_remove(self, selector: str) -> None:
        """Remove an element matching a CSS selector from the DOM."""
        session = self._require_session()
        node_id = await self._find_node(selector)
        await session.dom.remove_node(node_id)

    async def dom_focus(self, selector: str) -> None:
        """Focus an element matching a CSS selector."""
        session = self._require_session()
        node_id = await self._find_node(selector)
        await session.dom.focus(node_id)

    async def dom_scroll(
        self, selector: str | None = None, x: int = 0, y: int = 0
    ) -> None:
        """Scroll to an element or by offset.

        Args:
            selector: CSS selector to scroll to. If None, scroll by offset.
            x: Horizontal scroll offset.
            y: Vertical scroll offset.
        """
        session = self._require_session()
        if selector:
            escaped = selector.replace("'", "\\'")
            js = f"document.querySelector('{escaped}').scrollIntoView()"
        else:
            js = f"window.scrollBy({x}, {y})"
        await session.runtime.evaluate(js)

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
        session = self._require_session()
        escaped = selector.replace("'", "\\'")
        js = self._suggest_locator_js(escaped)
        result = await session.runtime.evaluate(js)
        raw = result.get("result", {}).get("value")
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
        session = self._require_session()
        js = self._find_by_text_js(query)
        result = await session.runtime.evaluate(js)
        raw = result.get("result", {}).get("value")
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

    # ── Network ────────────────────────────────────────────

    async def capture_har(self, params: HarParams) -> dict[str, Any]:
        """Navigate to a URL and capture network traffic as HAR 1.2 dict.

        Args:
            params: HAR capture parameters.

        Returns:
            HAR 1.2 compliant dict with log.entries.
        """
        session = self._require_session()

        requests: dict[str, dict[str, Any]] = {}
        responses: dict[str, dict[str, Any]] = {}
        finished: dict[str, dict[str, Any]] = {}

        def on_request(event_params: dict[str, Any]) -> None:
            """Handle Network.requestWillBeSent and record the request.

            Args:
                event_params: CDP event parameters with request data.
            """
            req_id = event_params.get("requestId", "")
            request = event_params.get("request", {})
            requests[req_id] = {
                "method": request.get("method", "GET"),
                "url": request.get("url", ""),
                "headers": [
                    {"name": k, "value": v}
                    for k, v in request.get("headers", {}).items()
                ],
                "queryString": [
                    {"name": k, "value": v}
                    for k, v in request.get("queryString", {}).items()
                ],
                "headersSize": -1,
                "bodySize": -1,
                "timestamp": event_params.get("timestamp", 0),
                "wallTime": event_params.get("wallTime", 0),
                "type": event_params.get("type", ""),
            }

        def on_response(event_params: dict[str, Any]) -> None:
            """Handle Network.responseReceived and record the response.

            Args:
                event_params: CDP event parameters with response data.
            """
            req_id = event_params.get("requestId", "")
            response = event_params.get("response", {})
            responses[req_id] = {
                "status": response.get("status", 0),
                "statusText": response.get("statusText", ""),
                "headers": [
                    {"name": k, "value": v}
                    for k, v in response.get("headers", {}).items()
                ],
                "mimeType": response.get("mimeType", ""),
                "redirectURL": response.get("redirectUrl", ""),
                "headersSize": response.get("headersSize", -1),
                "bodySize": response.get("encodedDataLength", -1),
                "content": {
                    "size": response.get("content", {}).get("size", 0),
                    "mimeType": response.get("content", {}).get("mimeType", ""),
                },
            }

        def on_loading_finished(event_params: dict[str, Any]) -> None:
            """Handle Network.loadingFinished and mark a request as complete.

            Args:
                event_params: CDP event parameters with loading finish data.
            """
            req_id = event_params.get("requestId", "")
            finished[req_id] = {
                "timestamp": event_params.get("timestamp", 0),
                "encodedDataLength": event_params.get("encodedDataLength", 0),
            }

        session.on("Network.requestWillBeSent", on_request)
        session.on("Network.responseReceived", on_response)
        session.on("Network.loadingFinished", on_loading_finished)

        await session.network.enable()
        await self.navigate(params.url, WaitStrategy(strategy="load"))
        await asyncio.sleep(params.wait / 1000)

        entries: list[dict[str, Any]] = []
        for req_id, req_data in requests.items():
            url = req_data.get("url", "")
            if params.filter and params.filter not in url:
                continue
            resp = responses.get(req_id, {})
            fin = finished.get(req_id, {})
            wall_time = req_data.get("wallTime", 0)
            started_dt = (
                f"{time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(wall_time))}"
                if wall_time
                else ""
            )
            send_time = 0
            wait_time = max(
                float(fin.get("timestamp", 0)) - float(req_data.get("timestamp", 0)),
                0.0,
            )
            receive_time = 0
            entries.append({
                "request": {
                    "method": req_data.get("method", "GET"),
                    "url": url,
                    "headers": req_data.get("headers", []),
                    "queryString": req_data.get("queryString", []),
                    "headersSize": req_data.get("headersSize", -1),
                    "bodySize": req_data.get("bodySize", -1),
                },
                "response": {
                    "status": resp.get("status", 0),
                    "statusText": resp.get("statusText", ""),
                    "headers": resp.get("headers", []),
                    "content": resp.get("content", {"size": 0, "mimeType": ""}),
                    "redirectURL": resp.get("redirectURL", ""),
                    "headersSize": resp.get("headersSize", -1),
                    "bodySize": resp.get("bodySize", -1),
                },
                "timings": {
                    "send": send_time,
                    "wait": round(wait_time * 1000, 2),
                    "receive": receive_time,
                },
                "time": round((wait_time + send_time + receive_time) * 1000, 2),
                "startedDateTime": started_dt,
            })

        return {
            "log": {
                "version": "1.2",
                "creator": {"name": "wavexis", "version": "0.3.0"},
                "entries": entries,
            }
        }

    async def get_cookies(self) -> list[dict[str, Any]]:
        """Get all cookies for the current page.

        Returns:
            List of cookie dicts.
        """
        session = self._require_session()
        result = await session.network.get_cookies()
        return list(result.get("cookies", []))

    async def set_cookie(self, params: CookieParams) -> None:
        """Set a cookie in the browser.

        Args:
            params: Cookie parameters.
        """
        session = self._require_session()
        await session.network.set_cookie(
            name=params.name,
            value=params.value,
            domain=params.domain or None,
            path=params.path,
            secure=params.secure,
            http_only=params.http_only,
            same_site=params.same_site,
        )

    async def delete_cookie(self, name: str, domain: str) -> None:
        """Delete cookies matching name and domain.

        Args:
            name: Cookie name to delete.
            domain: Cookie domain to scope deletion.
        """
        session = self._require_session()
        await session.network.delete_cookies(name=name, domain=domain)

    async def clear_cookies(self) -> None:
        """Clear all browser cookies."""
        session = self._require_session()
        await session.network.clear_browser_cookies()

    async def set_headers(self, headers: dict[str, str]) -> None:
        """Set extra HTTP headers for all requests.

        Args:
            headers: Dict of header name to value.
        """
        session = self._require_session()
        await session.network.enable()
        await session.network.set_extra_request_headers(headers)

    async def set_user_agent(self, user_agent: str) -> None:
        """Override the browser's User-Agent string.

        Args:
            user_agent: The User-Agent string to use.
        """
        session = self._require_session()
        await session.network.set_user_agent_override(user_agent=user_agent)

    # ── Browser management ─────────────────────────────────

    async def new_context(self) -> str:
        """Create a new browser context and return its ID.

        Returns:
            The browser context ID string.
        """
        session = self._require_session()
        result = await session.target.create_browser_context()
        return str(result.get("browserContextId", ""))

    async def list_contexts(self) -> list[dict[str, Any]]:
        """List all browser contexts.

        Returns:
            List of context info dicts.
        """
        session = self._require_session()
        result = await session.send("Target.getBrowserContexts")
        contexts = result.get("browserContextIds", [])
        return [{"contextId": ctx} for ctx in contexts]

    async def close_context(self, context_id: str) -> None:
        """Close a browser context by ID.

        Args:
            context_id: The browser context ID to close.
        """
        session = self._require_session()
        await session.target.dispose_browser_context(context_id)

    async def get_window_bounds(self) -> dict[str, Any]:
        """Get the current window bounds.

        Returns:
            Dict with width, height, left, top.
        """
        if self._client is None:
            raise NavigationError("", "Client not initialized.")
        result = await self._client.browser.get_window_for_target()
        bounds = result.get("bounds", {})
        return {
            "width": bounds.get("width", 0),
            "height": bounds.get("height", 0),
            "x": bounds.get("left", 0),
            "y": bounds.get("top", 0),
        }

    async def set_window_bounds(
        self, width: int, height: int, x: int = 0, y: int = 0
    ) -> None:
        """Set the window bounds.

        Args:
            width: Window width in pixels.
            height: Window height in pixels.
            x: Window X position.
            y: Window Y position.
        """
        if self._client is None:
            raise NavigationError("", "Client not initialized.")
        result = await self._client.browser.get_window_for_target()
        window_id = result.get("windowId", 0)
        bounds = {
            "left": x,
            "top": y,
            "width": width,
            "height": height,
            "windowState": "normal",
        }
        await self._client.browser.set_window_bounds(window_id, bounds)

    async def browser_version(self) -> str:
        """Get the browser version string.

        Returns:
            The browser product/version string.
        """
        if self._client is None:
            raise NavigationError("", "Client not initialized.")
        result = await self._client.browser.get_version()
        return str(result.get("product", ""))

    # ── Emulation ─────────────────────────────────────────

    async def emulate_device(self, device: str) -> None:
        """Emulate a device by preset name.

        Args:
            device: Device preset name (e.g. 'iphone-15').

        Raises:
            ValueError: If the device name is not in DEVICE_PRESETS.
        """
        session = self._require_session()
        preset = DEVICE_PRESETS.get(device)
        if preset is None:
            raise ValueError(f"Unknown device preset: {device}")
        await session.emulation.set_device_metrics_override(
            width=int(preset["width"]),
            height=int(preset["height"]),
            device_scale_factor=float(preset["device_scale_factor"]),
            mobile=bool(preset["mobile"]),
            user_agent=str(preset["user_agent"]),
        )
        if preset.get("touch"):
            await session.emulation.set_touch_emulation_enabled(True)

    async def set_viewport(
        self, width: int, height: int, device_scale_factor: float = 1.0
    ) -> None:
        """Set a custom viewport with given dimensions and scale factor.

        Args:
            width: Viewport width in CSS pixels.
            height: Viewport height in CSS pixels.
            device_scale_factor: Device pixel scale factor.
        """
        session = self._require_session()
        await session.emulation.set_device_metrics_override(
            width=width,
            height=height,
            device_scale_factor=device_scale_factor,
            mobile=False,
        )

    async def set_geolocation(
        self, latitude: float, longitude: float, accuracy: float = 100.0
    ) -> None:
        """Override the geolocation position.

        Args:
            latitude: Latitude in degrees.
            longitude: Longitude in degrees.
            accuracy: Accuracy in meters.
        """
        session = self._require_session()
        await session.emulation.set_geolocation_override(
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
        )

    async def set_timezone(self, timezone: str) -> None:
        """Override the system timezone.

        Args:
            timezone: IANA timezone ID (e.g. 'America/New_York').
        """
        session = self._require_session()
        await session.emulation.set_timezone_override(timezone)

    async def set_dark_mode(self, enabled: bool) -> None:
        """Enable or disable dark mode emulation.

        Args:
            enabled: True to enable dark mode, False to disable.
        """
        session = self._require_session()
        features = [{"name": "prefers-color-scheme", "value": "dark" if enabled else "light"}]
        await session.emulation.set_emulated_media(features=features)

    # ── Input ──────────────────────────────────────────────

    async def _get_box_center(self, selector: str) -> tuple[float, float]:
        """Find an element by selector and return the center of its bounding box."""
        session = self._require_session()
        node_id = await self._find_node(selector)
        box = await session.dom.get_box_model(node_id)
        model = box.get("model", {})
        borders = model.get("border", [])
        if len(borders) < 8:
            raise ElementNotFoundError(selector)
        xs = [borders[0], borders[2], borders[4], borders[6]]
        ys = [borders[1], borders[3], borders[5], borders[7]]
        cx = (min(xs) + max(xs)) / 2
        cy = (min(ys) + max(ys)) / 2
        return cx, cy

    async def _wait_for_element(self, selector: str, timeout_ms: int = 30000) -> None:
        """Wait for an element to exist and be visible in the DOM.

        Polls until the element matches, is attached, and has non-zero size.

        Args:
            selector: CSS selector for the target element.
            timeout_ms: Maximum wait time in milliseconds.

        Raises:
            WaitTimeoutError: If the element is not found within the timeout.
        """
        session = self._require_session()
        escaped = selector.replace("'", "\\'")
        js = (
            f"(function(){{var el=document.querySelector('{escaped}');"
            f"if(!el)return false;"
            f"var rect=el.getBoundingClientRect();"
            f"return rect.width>0&&rect.height>0;}})()"
        )
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            result = await session.runtime.evaluate(js)
            if result.get("result", {}).get("value") is True:
                return
            await asyncio.sleep(0.1)
        raise WaitTimeoutError("selector", timeout_ms)

    async def _scroll_into_view_if_needed(self, selector: str) -> None:
        """Scroll element into view if it's not visible in the viewport.

        Args:
            selector: CSS selector for the target element.
        """
        session = self._require_session()
        escaped = selector.replace("'", "\\'")
        js = (
            f"(function(){{var el=document.querySelector('{escaped}');"
            f"if(!el)return;var rect=el.getBoundingClientRect();"
            f"if(rect.top<0||rect.bottom>window.innerHeight||"
            f"rect.left<0||rect.right>window.innerWidth)"
            f"el.scrollIntoView({{block:'center',behavior:'instant'}});}})()"
        )
        await session.runtime.evaluate(js)

    async def click(
        self,
        selector: str,
        button: str = "left",
        click_count: int = 1,
        auto_wait: bool = True,
    ) -> None:
        """Click an element matching a CSS selector.

        Args:
            selector: CSS selector for the target element.
            button: Mouse button — "left", "right", or "middle".
            click_count: Number of clicks to dispatch.
            auto_wait: If True, wait for element to be visible before clicking.
        """
        session = self._require_session()
        if auto_wait:
            await self._wait_for_element(selector)
        await self._scroll_into_view_if_needed(selector)
        x, y = await self._get_box_center(selector)
        btn_map = {"left": "left", "right": "right", "middle": "middle"}
        btn = btn_map.get(button, "left")
        for _ in range(click_count):
            await session.input.dispatch_mouse_event(
                type_="mousePressed", x=x, y=y, button=btn, click_count=1
            )
            await session.input.dispatch_mouse_event(
                type_="mouseReleased", x=x, y=y, button=btn, click_count=1
            )

    async def type_text(self, selector: str, text: str, delay: int = 0) -> None:
        """Type text into an element, optionally with delay between keystrokes.

        Args:
            selector: CSS selector for the target element.
            text: Text to type character by character.
            delay: Delay between keystrokes in milliseconds.
        """
        session = self._require_session()
        node_id = await self._find_node(selector)
        await session.dom.focus(node_id)
        for char in text:
            await session.input.dispatch_key_event(
                type_="char", text=char
            )
            if delay > 0:
                await asyncio.sleep(delay / 1000)

    async def fill(
        self, selector: str, value: str, auto_wait: bool = True
    ) -> None:
        """Fill an input element with a value (replaces existing content).

        Args:
            selector: CSS selector for the target element.
            value: Value to set in the input field.
            auto_wait: If True, wait for element to be visible before filling.
        """
        session = self._require_session()
        if auto_wait:
            await self._wait_for_element(selector)
        await self._scroll_into_view_if_needed(selector)
        escaped = selector.replace("'", "\\'")
        js = (
            f"(function(){{var el=document.querySelector('{escaped}');"
            f"if(!el)return false;el.focus();el.value='{value}';"
            f"el.dispatchEvent(new Event('input',{{bubbles:true}}));"
            f"el.dispatchEvent(new Event('change',{{bubbles:true}}));"
            f"return true;}})()"
        )
        result = await session.runtime.evaluate(js)
        if not result.get("result", {}).get("value"):
            raise ElementNotFoundError(selector)

    async def select_option(self, selector: str, value: str) -> None:
        """Select an option in a <select> element by value.

        Args:
            selector: CSS selector for the <select> element.
            value: Option value to select.
        """
        session = self._require_session()
        escaped = selector.replace("'", "\\'")
        escaped_val = value.replace("'", "\\'")
        js = (
            f"(function(){{var el=document.querySelector('{escaped}');"
            f"if(!el)return false;el.value='{escaped_val}';"
            f"el.dispatchEvent(new Event('change',{{bubbles:true}}));"
            f"return true;}})()"
        )
        result = await session.runtime.evaluate(js)
        if not result.get("result", {}).get("value"):
            raise ElementNotFoundError(selector)

    async def hover(self, selector: str, auto_wait: bool = True) -> None:
        """Hover over an element matching a CSS selector.

        Args:
            selector: CSS selector for the target element.
            auto_wait: If True, wait for element to be visible before hovering.
        """
        session = self._require_session()
        if auto_wait:
            await self._wait_for_element(selector)
        await self._scroll_into_view_if_needed(selector)
        x, y = await self._get_box_center(selector)
        await session.input.dispatch_mouse_event(
            type_="mouseMoved", x=x, y=y
        )

    async def key_press(self, key: str) -> None:
        """Press a keyboard key.

        Args:
            key: Key name (e.g. 'Enter', 'Tab', 'Escape').
        """
        session = self._require_session()
        key_map = {
            "Enter": {"key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13},
            "Tab": {"key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9},
            "Escape": {"key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27},
            "Space": {"key": " ", "code": "Space", "windowsVirtualKeyCode": 32},
            "Backspace": {"key": "Backspace", "code": "Backspace", "windowsVirtualKeyCode": 8},
        }
        key_info = key_map.get(key, {"key": key, "code": key})
        await session.input.dispatch_key_event(
            type_="keyDown", **key_info
        )
        await session.input.dispatch_key_event(
            type_="keyUp", **key_info
        )

    async def drag(self, source: str, target: str) -> None:
        """Drag an element from source selector to target selector.

        Args:
            source: CSS selector for the element to drag.
            target: CSS selector for the drop target.
        """
        session = self._require_session()
        sx, sy = await self._get_box_center(source)
        tx, ty = await self._get_box_center(target)
        await session.input.dispatch_mouse_event(
            type_="mousePressed", x=sx, y=sy, button="left", click_count=1
        )
        await session.input.dispatch_mouse_event(
            type_="mouseMoved", x=tx, y=ty
        )
        await session.input.dispatch_mouse_event(
            type_="mouseReleased", x=tx, y=ty, button="left", click_count=1
        )

    async def tap(self, selector: str) -> None:
        """Tap an element (touch emulation click).

        Args:
            selector: CSS selector for the target element.
        """
        session = self._require_session()
        x, y = await self._get_box_center(selector)
        await session.input.dispatch_touch_event(
            type_="touchStart", touch_points=[{"x": x, "y": y}]
        )
        await session.input.dispatch_touch_event(
            type_="touchEnd", touch_points=[]
        )

    async def set_files(self, selector: str, files: list[str]) -> None:
        """Set files on a file input element.

        Args:
            selector: CSS selector for the <input type="file"> element.
            files: List of absolute file paths to upload.
        """
        session = self._require_session()
        node_id = await self._find_node(selector)
        await session.send(
            "DOM.setFileInputFiles",
            {"files": files, "nodeId": node_id},
        )

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
        session = self._require_session()
        escaped_iframe = iframe_selector.replace("'", "\\'")
        escaped_expr = expression.replace("\\", "\\\\").replace("'", "\\'")
        js = (
            f"(function(){{var f=document.querySelector('{escaped_iframe}');"
            f"if(!f||!f.contentDocument)return null;"
            f"return (function(){{{escaped_expr}}}).call(f.contentDocument);}})()"
        )
        result = await session.runtime.evaluate(js, await_promise=await_promise)
        return result.get("result", {}).get("value")

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
        session = self._require_session()
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
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            result = await session.runtime.evaluate(js)
            if result.get("result", {}).get("value") is True:
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
        session = self._require_session()
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
        result = await session.runtime.evaluate(js)
        if not result.get("result", {}).get("value"):
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
        session = self._require_session()
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
        result = await session.runtime.evaluate(js)
        if not result.get("result", {}).get("value"):
            raise ElementNotFoundError(selector)

    # ── Shadow DOM ──────────────────────────────────────────

    @staticmethod
    def _build_shadow_pierce_js(selectors: list[str]) -> str:
        """Build JS that pierces shadow boundaries via a selector chain.

        Args:
            selectors: List of CSS selectors. selectors[0] in document,
                each subsequent selector in the previous element's shadowRoot.

        Returns:
            JavaScript IIFE that returns the final element or null.
        """
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
        session = self._require_session()
        pierce_js = self._build_shadow_pierce_js(selectors)
        escaped_expr = expression.replace("\\", "\\\\").replace("'", "\\'")
        js = (
            f"(function(){{var el=({pierce_js});"
            f"if(!el)return null;"
            f"return (function(){{{escaped_expr}}}).call(el);}})()"
        )
        result = await session.runtime.evaluate(js, await_promise=await_promise)
        return result.get("result", {}).get("value")

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
        session = self._require_session()
        pierce_js = self._build_shadow_pierce_js(selectors)
        js = (
            f"(function(){{var el=({pierce_js});"
            f"if(!el)return false;"
            f"var rect=el.getBoundingClientRect();"
            f"return rect.width>0&&rect.height>0;}})()"
        )
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            result = await session.runtime.evaluate(js)
            if result.get("result", {}).get("value") is True:
                return
            await asyncio.sleep(0.1)
        raise WaitTimeoutError("selector", timeout_ms)

    async def shadow_click(
        self, selectors: list[str], auto_wait: bool = True
    ) -> None:
        """Click an element inside a shadow DOM tree.

        Args:
            selectors: List of CSS selectors piercing shadow boundaries.
            auto_wait: If True, wait for element to be visible before clicking.
        """
        session = self._require_session()
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
        result = await session.runtime.evaluate(js)
        if not result.get("result", {}).get("value"):
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
        session = self._require_session()
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
        result = await session.runtime.evaluate(js)
        if not result.get("result", {}).get("value"):
            raise ElementNotFoundError(" -> ".join(selectors))

    # ── Network advanced ───────────────────────────────────

    async def block_requests(self, patterns: list[str]) -> None:
        """Block requests matching URL patterns.

        Args:
            patterns: List of glob-style URL patterns to block.
        """
        session = self._require_session()
        await session.network.enable()
        for pattern in patterns:
            await session.send(
                "Network.setBlockedURLs",
                {"urls": [pattern]},
            )

    async def throttle_network(self, params: ThrottleParams) -> None:
        """Throttle network conditions.

        Args:
            params: Throttle parameters (offline, latency, throughput).
        """
        session = self._require_session()
        await session.network.enable()
        await session.send(
            "Network.emulateNetworkConditions",
            {
                "offline": params.offline,
                "latency": params.latency_ms,
                "downloadThroughput": params.download_bps,
                "uploadThroughput": params.upload_bps,
            },
        )

    async def set_cache_disabled(self, disabled: bool = True) -> None:
        """Disable or enable the browser cache.

        Args:
            disabled: True to disable cache, False to enable.
        """
        session = self._require_session()
        await session.network.enable()
        await session.network.set_cache_disabled(disabled)

    async def intercept_requests(self, pattern: dict[str, Any]) -> None:
        """Intercept requests matching a pattern dict.

        Args:
            pattern: Fetch.enable pattern dict (urlPattern, resourceType, requestStage).
        """
        session = self._require_session()
        await session.send(
            "Fetch.enable",
            {"patterns": [pattern]},
        )

    async def mock_response(self, url: str, response: dict[str, Any]) -> None:
        """Mock a response for requests matching a URL pattern.

        Uses Fetch.enable to intercept and fulfill requests with a mocked response.

        Args:
            url: URL pattern to intercept.
            response: Response dict with optional keys: status, headers, body.
        """
        session = self._require_session()

        body = response.get("body", "")
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        body_b64 = base64.b64encode(body.encode("utf-8")).decode("ascii")

        fulfilled: list[bool] = [False]

        async def on_request_paused(event_params: dict[str, Any]) -> None:
            """Handle Fetch.requestPaused and fulfill with the mocked response.

            Args:
                event_params: CDP event parameters with the paused request ID.
            """
            request_id = event_params.get("requestId", "")
            await session.send(
                "Fetch.fulfillRequest",
                {
                    "requestId": request_id,
                    "responseCode": response.get("status", 200),
                    "responseHeaders": [
                        {
                            "name": "Content-Type",
                            "value": response.get("content_type", "application/json"),
                        }
                    ],
                    "body": body_b64,
                },
            )
            fulfilled[0] = True

        session.on("Fetch.requestPaused", on_request_paused)
        await session.send(
            "Fetch.enable",
            {"patterns": [{"urlPattern": url, "requestStage": "Response"}]},
        )

    # ── Network inspection (W3, W6, W7) ───────────────────

    async def get_request_body(self, request_id: str) -> str | None:
        """Get the body of a network request by ID.

        Args:
            request_id: The CDP network request ID.

        Returns:
            The request body as a string, or None if not available.
        """
        session = self._require_session()
        try:
            result = await session.send(
                "Network.getRequestPostData",
                {"requestId": request_id},
            )
            return result.get("postData")
        except Exception:
            return None

    async def get_response_body(self, request_id: str) -> str | None:
        """Get the body of a network response by ID.

        Args:
            request_id: The CDP network request ID.

        Returns:
            The response body as a string, or None if not available.
        """
        session = self._require_session()
        try:
            result = await session.send(
                "Network.getResponseBody",
                {"requestId": request_id},
            )
            return result.get("body")
        except Exception:
            return None

    async def modify_request(
        self,
        pattern: dict[str, Any],
        modifications: dict[str, Any],
    ) -> None:
        """Intercept and modify requests matching a pattern.

        Uses CDP Fetch domain to pause requests and continue with modifications.

        Args:
            pattern: Pattern dict with optional keys: urlPattern, resourceType,
                requestStage.
            modifications: Dict with optional keys: headers, url, method, post_data.
        """
        session = self._require_session()

        async def on_request_paused(event_params: dict[str, Any]) -> None:
            """Handle Fetch.requestPaused and continue with modifications."""
            request_id = event_params.get("requestId", "")
            await session.send(
                "Fetch.continueRequest",
                {
                    "requestId": request_id,
                    "url": modifications.get("url", event_params.get("request", {}).get("url", "")),
                    "method": modifications.get(
                        "method", event_params.get("request", {}).get("method", "GET")
                    ),
                    "headers": modifications.get(
                        "headers", event_params.get("request", {}).get("headers", [])
                    ),
                    "postData": modifications.get("post_data"),
                },
            )

        session.on("Fetch.requestPaused", on_request_paused)
        await session.send("Fetch.enable", {"patterns": [pattern]})

    async def replay_har(self, har_path: str, url_filter: str = "") -> None:
        """Replay network requests from a HAR file.

        Reads the HAR JSON, iterates entries, and replays each request using
        the browser's fetch API.

        Args:
            har_path: Path to the HAR file.
            url_filter: Optional URL pattern to filter which entries to replay.
        """
        session = self._require_session()
        from pathlib import Path

        content = await asyncio.to_thread(Path(har_path).read_text, encoding="utf-8")
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
            await session.runtime.evaluate(fetch_js)

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
        session = self._require_session()
        trace_id = f"trace-{int(time.time() * 1000)}"

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
            await session.network.enable()

            def on_network_request(event_params: dict[str, Any]) -> None:
                state["network"].append({
                    "type": "request",
                    "url": event_params.get("request", {}).get("url", ""),
                    "method": event_params.get("request", {}).get("method", ""),
                    "requestId": event_params.get("requestId", ""),
                    "timestamp": event_params.get("timestamp"),
                })

            def on_network_response(event_params: dict[str, Any]) -> None:
                state["network"].append({
                    "type": "response",
                    "url": event_params.get("response", {}).get("url", ""),
                    "status": event_params.get("response", {}).get("status", 0),
                    "requestId": event_params.get("requestId", ""),
                    "timestamp": event_params.get("timestamp"),
                })

            session.on("Network.requestWillBeSent", on_network_request)
            session.on("Network.responseReceived", on_network_response)

        if capture_console:
            await session.runtime.enable()

            def on_console_api(event_params: dict[str, Any]) -> None:
                state["console"].append({
                    "type": event_params.get("type", "log"),
                    "args": event_params.get("args", []),
                    "timestamp": event_params.get("timestamp"),
                })

            session.on("Runtime.consoleAPICalled", on_console_api)

        if capture_screenshots:
            screenshot = await session.page.capture_screenshot()
            if screenshot:
                state["screenshots"].append({
                    "timestamp": time.time(),
                    "data": screenshot,
                })

        await session.send("Tracing.start", {"traceType": "devtools-timeline"})

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
        session = self._require_session()
        traces: dict[str, dict[str, Any]] = getattr(self, "_combined_traces", {})
        state = traces.get(trace_id)
        if state is None:
            return {"error": f"Unknown trace_id: {trace_id}"}

        trace_events: list[dict[str, Any]] = []

        async def _on_tracing_complete(params: dict[str, Any]) -> None:
            """Handle Tracing.tracingComplete and extract trace events."""
            import io
            import zipfile

            stream_handle = params.get("stream")
            if stream_handle:
                chunks: list[bytes] = []
                while True:
                    resp = await session.send("IO.read", {"handle": stream_handle})
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

        session.on("Tracing.tracingComplete", _on_tracing_complete)
        await session.send("Tracing.end", {})

        if state["capture_screenshots"]:
            screenshot = await session.page.capture_screenshot()
            if screenshot:
                state["screenshots"].append({
                    "timestamp": time.time(),
                    "data": screenshot,
                })

        await asyncio.sleep(0.5)

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

        Injects axe-core JS via Runtime.evaluate and returns the results.

        Returns:
            Dict with violations, passes, incomplete, and inapplicable lists.
        """
        session = self._require_session()

        axe_js = (
            "if (typeof axe === 'undefined') { "
            "  import('https://unpkg.com/axe-core@4.9.1/axe.min.js')"
            "    .then(m => { window.axe = m.default || m; }); "
            "} "
            "await new Promise(r => setTimeout(r, 2000)); "
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
        result = await session.runtime.evaluate(axe_js, await_promise=True)
        value = result.get("result", {}).get("value")
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return dict(json.loads(value))
            except (json.JSONDecodeError, TypeError):
                pass
        return {"error": "axe-core audit failed", "raw": dict(result)}

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
        session = self._require_session()
        sub_id = f"sub-{int(time.time() * 1000)}"

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
                session.on(cdp_event, handler)
                handlers[cdp_event] = handler

                if evt_type in ("network_request", "network_response"):
                    asyncio.ensure_future(session.network.enable())
                elif evt_type == "console":
                    asyncio.ensure_future(session.runtime.enable())

        self._subscriptions[sub_id] = handlers
        return sub_id

    async def unsubscribe_events(self, subscription_id: str) -> None:
        """Unsubscribe from events by subscription ID.

        Args:
            subscription_id: The ID returned by subscribe_events.
        """
        session = self._require_session()
        subs: dict[str, dict[str, Any]] = getattr(self, "_subscriptions", {})
        handlers = subs.pop(subscription_id, {})
        for cdp_event, handler in handlers.items():
            off = getattr(session, "off", None)
            if off is not None:
                off(cdp_event, handler)

    # ── Accessibility ──────────────────────────────────────

    async def a11y_tree(self) -> dict[str, Any]:
        """Get the full accessibility tree of the current page.

        Returns:
            Dict with the accessibility tree nodes.
        """
        session = self._require_session()
        result = await session.send("Accessibility.getFullAXTree")
        return dict(result)

    async def a11y_node(self, node_id: str) -> dict[str, Any]:
        """Get a specific accessibility node by its node ID.

        Args:
            node_id: The accessibility node ID.

        Returns:
            Dict with the node's accessibility properties.
        """
        session = self._require_session()
        result = await session.send("Accessibility.getFullAXTree")
        nodes = result.get("nodes", [])
        for node in nodes:
            if node.get("nodeId") == node_id:
                return dict(node)
        return {}

    async def a11y_ancestors(self, node_id: str) -> list[dict[str, Any]]:
        """Get ancestor nodes of an accessibility node.

        Args:
            node_id: The accessibility node ID.

        Returns:
            List of ancestor node dicts.
        """
        session = self._require_session()
        result = await session.send("Accessibility.getFullAXTree")
        nodes = result.get("nodes", [])
        ancestors: list[dict[str, Any]] = []
        for node in nodes:
            if node.get("nodeId") != node_id:
                ancestors.append(dict(node))
        return ancestors

    # ── Downloads ──────────────────────────────────────────

    async def intercept_download(self, pattern: str = ".*") -> bytes:
        """Intercept a file download matching a URL pattern and return bytes.

        Args:
            pattern: URL pattern to match downloads (regex, default matches all).

        Returns:
            Downloaded file bytes.
        """
        session = self._require_session()
        import tempfile

        download_dir = tempfile.mkdtemp()
        await session.send(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": download_dir},
        )

        await asyncio.sleep(2)

        def _list_files() -> list[Path]:
            return list(Path(download_dir).iterdir())

        for fpath in await asyncio.to_thread(_list_files):
            if await asyncio.to_thread(Path(fpath).is_file):
                return await asyncio.to_thread(Path(fpath).read_bytes)

        return b""

    # ── Dialogs ────────────────────────────────────────────

    async def dialog_accept(self, prompt_text: str | None = None) -> None:
        """Accept a JavaScript dialog (alert, confirm, prompt).

        Args:
            prompt_text: Text to enter in a prompt dialog (optional).
        """
        session = self._require_session()
        await session.send(
            "Page.handleJavaScriptDialog",
            {"accept": True, "promptText": prompt_text or ""},
        )

    async def dialog_dismiss(self) -> None:
        """Dismiss a JavaScript dialog."""
        session = self._require_session()
        await session.send(
            "Page.handleJavaScriptDialog",
            {"accept": False},
        )

    # ── Permissions ────────────────────────────────────────

    async def grant_permission(self, permission: str) -> None:
        """Grant a browser permission.

        Args:
            permission: Permission name (e.g. 'geolocation', 'notifications').
        """
        session = self._require_session()
        await session.send(
            "Browser.grantPermissions",
            {"permissions": [permission]},
        )

    async def reset_permissions(self) -> None:
        """Reset all granted permissions."""
        session = self._require_session()
        await session.send("Browser.resetPermissions", {})

    # ── Security ───────────────────────────────────────────

    async def get_security_state(self) -> dict[str, Any]:
        """Get the current security state of the page.

        Returns:
            Dict with security state info (secure, explanations, etc.).
        """
        session = self._require_session()
        result = await session.send("Security.setIgnoreCertificateErrors", {"ignore": False})
        return dict(result) if result else {}

    async def ignore_cert_errors(self, ignore: bool = True) -> None:
        """Enable or disable ignoring of certificate errors.

        Args:
            ignore: True to ignore cert errors, False to enforce.
        """
        session = self._require_session()
        await session.send(
            "Security.setIgnoreCertificateErrors",
            {"ignore": ignore},
        )

    # ── Emulation advanced ─────────────────────────────────

    async def set_locale(self, locale: str) -> None:
        """Override the browser locale.

        Args:
            locale: Locale string (e.g. 'en-US', 'fr-FR').
        """
        session = self._require_session()
        await session.send(
            "Emulation.setLocaleOverride",
            {"locale": locale},
        )

    async def set_cpu_throttle(self, rate: float) -> None:
        """Throttle CPU performance by a rate multiplier.

        Args:
            rate: Throttle rate (e.g. 4 = 4x slower than normal).
        """
        session = self._require_session()
        await session.send(
            "Emulation.setCPUThrottlingRate",
            {"rate": rate},
        )

    async def set_touch_emulation(self, enabled: bool) -> None:
        """Enable or disable touch emulation.

        Args:
            enabled: True to enable touch emulation, False to disable.
        """
        session = self._require_session()
        await session.emulation.set_touch_emulation_enabled(enabled)

    async def set_sensors(self, sensors: SensorParams) -> None:
        """Override sensor values.

        Args:
            sensors: Sensor parameters with type and values.
        """
        session = self._require_session()
        if sensors.type == "device-orientation":
            await session.send(
                "DeviceOrientation.setDeviceOrientationOverride",
                {
                    "alpha": sensors.values.get("alpha", 0),
                    "beta": sensors.values.get("beta", 0),
                    "gamma": sensors.values.get("gamma", 0),
                },
            )
        elif sensors.type == "geolocation":
            await session.emulation.set_geolocation_override(
                latitude=sensors.values.get("latitude", 0),
                longitude=sensors.values.get("longitude", 0),
                accuracy=sensors.values.get("accuracy", 100),
            )

    # ── Performance ───────────────────────────────────────

    async def perf_metrics(self) -> dict[str, Any]:
        """Get current performance metrics from the page.

        Returns:
            Dict mapping metric names to values (e.g. Timestamp, Documents,
            Frames, JSEventListeners, JSHeapUsedSize, etc.).
        """
        session = self._require_session()
        await session.send("Performance.enable", {})
        result = await session.send("Performance.getMetrics", {})
        metrics: dict[str, Any] = {}
        for m in result.get("metrics", []):
            metrics[m["name"]] = m["value"]
        return metrics

    async def perf_trace(self, duration_ms: int = 3000) -> dict[str, Any]:
        """Capture a performance trace for the given duration.

        Args:
            duration_ms: Trace duration in milliseconds.

        Returns:
            Dict containing trace events collected during the capture period.
        """
        session = self._require_session()
        trace_events: list[dict[str, Any]] = []

        async def _on_tracing_complete(params: dict[str, Any]) -> None:
            """Handle Tracing.tracingComplete and extract trace events from the stream.

            Args:
                params: CDP event parameters containing the trace data stream handle.
            """
            import io
            import zipfile

            stream_handle = params.get("stream")
            if stream_handle:
                chunks: list[bytes] = []
                while True:
                    resp = await session.send(
                        "IO.read",
                        {"handle": stream_handle},
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
                        trace_events.extend(json.loads(content).get("traceEvents", []))
                except (zipfile.BadZipFile, json.JSONDecodeError, KeyError, ValueError):
                    trace_events.append({"raw_size": len(raw)})
            else:
                trace_events.append({"error": "No stream handle in tracingComplete"})

        session.on("Tracing.tracingComplete", _on_tracing_complete)
        await session.send(
            "Tracing.start",
            {"traceType": "devtools-timeline"},
        )
        await asyncio.sleep(duration_ms / 1000)
        await session.send("Tracing.end", {})
        return {"traceEvents": trace_events}

    async def perf_profile(self, duration_ms: int = 3000) -> dict[str, Any]:
        """Capture a CPU profile for the given duration.

        Args:
            duration_ms: Profile duration in milliseconds.

        Returns:
            Dict containing CPU profile data (nodes, samples, timeDeltas, etc.).
        """
        session = self._require_session()
        await session.send("Profiler.enable", {})
        await session.send("Profiler.start", {})
        await asyncio.sleep(duration_ms / 1000)
        result = await session.send("Profiler.stop", {})
        profile = result.get("profile", result)
        return dict(profile) if profile else {}

    async def perf_heap_snapshot(self) -> dict[str, Any]:
        """Capture a heap snapshot and return it as a dict.

        Returns:
            Dict containing heap snapshot data (nodes, edges, etc.).
        """
        session = self._require_session()
        await session.send("HeapProfiler.enable", {})
        result = await session.send(
            "HeapProfiler.takeHeapSnapshot",
            {"reportProgress": False},
        )
        return dict(result) if result else {"snapshot": "taken"}

    async def perf_coverage(self) -> dict[str, Any]:
        """Get JavaScript code coverage for the current page.

        Returns:
            Dict with 'result' key containing a list of script coverage entries.
        """
        session = self._require_session()
        await session.send("Profiler.enable", {})
        await session.send(
            "Profiler.startPreciseCoverage",
            {"callCount": True, "detailed": True},
        )
        result = await session.send("Profiler.takePreciseCoverage", {})
        return dict(result) if result else {}

    async def perf_css_coverage(self) -> dict[str, Any]:
        """Get CSS rule usage coverage for the current page.

        Returns:
            Dict with 'result' key containing a list of CSS coverage entries.
        """
        session = self._require_session()
        await session.send("CSS.enable", {})
        await session.send("CSS.startRuleUsageTracking", {})
        await asyncio.sleep(1)
        result = await session.send("CSS.stopRuleUsageTracking", {})
        return dict(result) if result else {}

    # ── CSS ────────────────────────────────────────────────

    async def css_get_styles(self, selector: str) -> dict[str, Any]:
        """Get inline and matched styles for an element by CSS selector.

        Args:
            selector: CSS selector for the target element.

        Returns:
            Dict containing inlineStyles and matchedStyles.
        """
        session = self._require_session()
        await session.send("CSS.enable", {})
        node_id = await self._find_node(selector)
        inline = await session.send(
            "CSS.getInlineStyles", {"nodeId": node_id}
        )
        matched = await session.send(
            "CSS.getMatchedStyles", {"nodeId": node_id}
        )
        return {"inlineStyles": inline, "matchedStyles": matched}

    async def css_get_stylesheets(self) -> list[dict[str, Any]]:
        """List all stylesheets in the current page.

        Returns:
            List of stylesheet header dicts.
        """
        session = self._require_session()
        await session.send("CSS.enable", {})
        result = await session.send("CSS.getStyleSheetText", {})
        headers: list[dict[str, Any]] = []
        for sheet in result.get("headers", []):
            headers.append(dict(sheet))
        return headers

    async def css_get_rules(self, stylesheet_id: str) -> list[dict[str, Any]]:
        """Get CSS rules from a specific stylesheet.

        Args:
            stylesheet_id: The styleSheetId from css_get_stylesheets.

        Returns:
            List of CSS rule dicts.
        """
        session = self._require_session()
        await session.send("CSS.enable", {})
        result = await session.send(
            "CSS.getStyleSheetText", {"styleSheetId": stylesheet_id}
        )
        text = result.get("text", "")
        rules: list[dict[str, Any]] = []
        import re

        for match in re.finditer(r"([^{}]+)\{([^}]*)\}", text):
            selector_text = match.group(1).strip()
            body = match.group(2).strip()
            rules.append({"selectorText": selector_text, "cssText": body})
        return rules

    async def css_get_computed(self, selector: str) -> dict[str, Any]:
        """Get computed styles for an element by CSS selector.

        Args:
            selector: CSS selector for the target element.

        Returns:
            Dict mapping CSS property names to computed values.
        """
        session = self._require_session()
        await session.send("DOM.enable", {})
        await session.send("CSS.enable", {})
        node_id = await self._find_node(selector)
        resolved = await session.send(
            "DOM.resolveNode", {"nodeId": node_id}
        )
        object_id = resolved.get("object", {}).get("objectId", "")
        if not object_id:
            raise ElementNotFoundError(selector)
        result = await session.send(
            "CSS.getComputedStyleForNode", {"nodeId": node_id}
        )
        computed: dict[str, Any] = {}
        for prop in result.get("computedStyle", []):
            computed[prop.get("name", "")] = prop.get("value", "")
        return computed

    # ── Debugging ──────────────────────────────────────────

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
        session = self._require_session()
        await session.send("Debugger.enable", {})
        params: dict[str, Any] = {"url": url, "lineNumber": line}
        if condition:
            params["condition"] = condition
        result = await session.send(
            "Debugger.setBreakpointByUrl", params
        )
        return str(result.get("breakpointId", ""))

    async def debug_set_breakpoint_function(self, function_name: str) -> str:
        """Set a breakpoint by function name.

        Args:
            function_name: Name of the function to break on.

        Returns:
            The breakpoint ID string.
        """
        session = self._require_session()
        await session.send("Debugger.enable", {})
        result = await session.send(
            "Debugger.setBreakpointOnFunctionCall",
            {"functionName": function_name},
        )
        return str(result.get("breakpointId", ""))

    async def debug_remove_breakpoint(self, breakpoint_id: str) -> None:
        """Remove a breakpoint by ID.

        Args:
            breakpoint_id: The breakpoint ID returned from set_breakpoint.
        """
        session = self._require_session()
        await session.send(
            "Debugger.removeBreakpoint", {"breakpointId": breakpoint_id}
        )

    async def debug_step_over(self) -> None:
        """Step over the current statement in the debugger."""
        session = self._require_session()
        await session.send("Debugger.stepOver", {})

    async def debug_step_into(self) -> None:
        """Step into the current function call in the debugger."""
        session = self._require_session()
        await session.send("Debugger.stepInto", {})

    async def debug_step_out(self) -> None:
        """Step out of the current function in the debugger."""
        session = self._require_session()
        await session.send("Debugger.stepOut", {})

    async def debug_pause(self) -> None:
        """Pause JavaScript execution."""
        session = self._require_session()
        await session.send("Debugger.pause", {})

    async def debug_resume(self) -> None:
        """Resume JavaScript execution after a pause."""
        session = self._require_session()
        await session.send("Debugger.resume", {})

    async def debug_get_listeners(self, selector: str) -> list[dict[str, Any]]:
        """Get event listeners attached to an element by CSS selector.

        Args:
            selector: CSS selector for the target element.

        Returns:
            List of listener dicts (type, useCapture, passive, etc.).
        """
        session = self._require_session()
        node_id = await self._find_node(selector)
        resolved = await session.send(
            "DOM.resolveNode", {"nodeId": node_id}
        )
        object_id = resolved.get("object", {}).get("objectId", "")
        if not object_id:
            raise ElementNotFoundError(selector)
        result = await session.send(
            "DOMDebugger.getEventListeners", {"objectId": object_id}
        )
        listeners: list[dict[str, Any]] = []
        for listener in result.get("listeners", []):
            listeners.append(dict(listener))
        return listeners

    # ── DOM Snapshot ───────────────────────────────────────

    async def dom_snapshot(self) -> dict[str, Any]:
        """Capture a DOM snapshot of the current page.

        Returns:
            Dict containing the raw DOM snapshot (documents, strings, etc.).
        """
        session = self._require_session()
        result = await session.send(
            "DOMSnapshot.captureSnapshot",
            {"computedStyles": [], "includePaintOrder": True, "includeDOMRects": False},
        )
        return dict(result) if result else {}

    # ── Overlay ────────────────────────────────────────────

    async def overlay_highlight(
        self, selector: str, color: str = "rgba(255,0,0,0.5)"
    ) -> None:
        """Highlight an element with a colored overlay.

        Args:
            selector: CSS selector for the element to highlight.
            color: RGBA color string for the highlight overlay.
        """
        session = self._require_session()
        await session.send("Overlay.enable", {})
        node_id = await self._find_node(selector)
        highlight_config: dict[str, Any] = {
            "contentColor": color,
            "contentOutlineColor": "rgba(0,0,0,0)",
        }
        await session.send(
            "Overlay.highlightNode",
            {"highlightConfig": highlight_config, "nodeId": node_id},
        )

    async def overlay_clear(self) -> None:
        """Clear all highlight overlays from the page."""
        session = self._require_session()
        await session.send("Overlay.clearHighlight", {})

    # ── Storage ────────────────────────────────────────────

    def _get_origin(self) -> str:
        """Extract the security origin from the current page URL."""
        if self._current_url:
            from urllib.parse import urlparse

            parsed = urlparse(self._current_url)
            return f"{parsed.scheme}://{parsed.netloc}"
        return ""

    async def _get_storage_id(self, storage_type: str) -> dict[str, Any]:
        """Get a DOMStorage.StorageId with the current page's security origin."""
        if storage_type not in ("local", "session"):
            raise NavigationError(
                "", f"Invalid storage_type: {storage_type}. Must be 'local' or 'session'."
            )
        return {
            "securityOrigin": self._get_origin(),
            "isLocalStorage": storage_type == "local",
        }

    async def storage_get(self, key: str, storage_type: str = "local") -> str:
        """Get a value from DOM storage (local or session).

        Args:
            key: The storage key to retrieve.
            storage_type: "local" or "session".

        Returns:
            The stored value as a string, or empty string if not found.
        """
        session = self._require_session()
        await session.send("DOMStorage.enable", {})
        storage_id = await self._get_storage_id(storage_type)
        result = await session.send(
            "DOMStorage.getDOMStorageItems", {"storageId": storage_id}
        )
        for entry in result.get("entries", []):
            if len(entry) >= 2 and entry[0] == key:
                return str(entry[1])
        return ""

    async def storage_set(
        self, key: str, value: str, storage_type: str = "local"
    ) -> None:
        """Set a value in DOM storage (local or session).

        Args:
            key: The storage key.
            value: The value to store.
            storage_type: "local" or "session".
        """
        session = self._require_session()
        await session.send("DOMStorage.enable", {})
        storage_id = await self._get_storage_id(storage_type)
        await session.send(
            "DOMStorage.setDOMStorageItem",
            {"storageId": storage_id, "key": key, "value": value},
        )

    async def storage_clear(self, storage_type: str = "local") -> None:
        """Clear all entries in DOM storage.

        Args:
            storage_type: "local" or "session".
        """
        session = self._require_session()
        await session.send("DOMStorage.enable", {})
        storage_id = await self._get_storage_id(storage_type)
        await session.send(
            "DOMStorage.clearDOMStorageItems", {"storageId": storage_id}
        )

    async def storage_list(self, storage_type: str = "local") -> dict[str, str]:
        """List all key-value pairs in DOM storage.

        Args:
            storage_type: "local" or "session".

        Returns:
            Dict mapping keys to values.
        """
        session = self._require_session()
        await session.send("DOMStorage.enable", {})
        storage_id = await self._get_storage_id(storage_type)
        result = await session.send(
            "DOMStorage.getDOMStorageItems", {"storageId": storage_id}
        )
        items: dict[str, str] = {}
        for entry in result.get("entries", []):
            if len(entry) >= 2:
                items[str(entry[0])] = str(entry[1])
        return items

    async def cache_storage_list(self) -> list[str]:
        """List all Cache Storage cache names.

        Returns:
            List of cache names.
        """
        session = self._require_session()
        result = await session.send(
            "CacheStorage.requestCacheNames",
            {"securityOrigin": self._get_origin()},
        )
        caches: list[str] = []
        for cache in result.get("caches", []):
            name = cache.get("cacheName", "")
            if name:
                caches.append(str(name))
        return caches

    async def cache_storage_entries(self, cache_name: str) -> list[dict[str, Any]]:
        """List entries in a Cache Storage cache.

        Args:
            cache_name: Name of the cache to inspect.

        Returns:
            List of cache entry dicts (url, status, etc.).
        """
        session = self._require_session()
        result = await session.send(
            "CacheStorage.requestEntries",
            {"cacheId": f"{self._get_origin()}_{cache_name}", "skipCount": 0, "pageSize": 1000},
        )
        entries: list[dict[str, Any]] = []
        for entry in result.get("cacheDataEntries", []):
            entries.append(dict(entry))
        return entries

    async def cache_storage_delete(self, cache_name: str) -> None:
        """Delete a Cache Storage cache.

        Args:
            cache_name: Name of the cache to delete.
        """
        session = self._require_session()
        await session.send(
            "CacheStorage.deleteCache",
            {"cacheId": f"{self._get_origin()}_{cache_name}"},
        )

    async def indexeddb_list(self) -> list[dict[str, Any]]:
        """List all IndexedDB databases.

        Returns:
            List of database info dicts (name, version, etc.).
        """
        session = self._require_session()
        result = await session.send(
            "IndexedDB.requestDatabaseNames",
            {"securityOrigin": self._get_origin()},
        )
        databases: list[dict[str, Any]] = []
        for name in result.get("databaseNames", []):
            databases.append({"name": str(name)})
        return databases

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
        session = self._require_session()
        result = await session.send(
            "IndexedDB.requestObjectStoreData",
            {
                "securityOrigin": self._get_origin(),
                "databaseName": database,
                "objectStoreName": store,
                "indexName": "",
                "skipCount": 0,
                "pageSize": 1000,
                "keyRange": None,
            },
        )
        entries: list[dict[str, Any]] = []
        for entry in result.get("objectStoreDataEntries", []):
            entries.append(dict(entry))
        if key:
            for entry in entries:
                if str(entry.get("key", "")) == key:
                    return entry
            return None
        return entries

    async def indexeddb_clear(self, database: str, store: str) -> None:
        """Clear all entries in an IndexedDB object store.

        Args:
            database: Database name.
            store: Object store name.
        """
        session = self._require_session()
        await session.send(
            "IndexedDB.clearObjectStore",
            {
                "securityOrigin": self._get_origin(),
                "databaseName": database,
                "objectStoreName": store,
            },
        )

    # ── Service Workers ────────────────────────────────────

    async def sw_list(self) -> list[dict[str, Any]]:
        """List registered service workers.

        Returns:
            List of service worker registration dicts.
        """
        session = self._require_session()
        await session.send("ServiceWorker.enable", {})
        result = await session.send(
            "ServiceWorker.getRegistrations", {}
        )
        registrations: list[dict[str, Any]] = []
        for reg in result.get("registrations", []):
            registrations.append(dict(reg))
        return registrations

    async def sw_unregister(self, registration_id: str) -> None:
        """Unregister a service worker by registration ID.

        Args:
            registration_id: The service worker registration ID.
        """
        session = self._require_session()
        await session.send("ServiceWorker.enable", {})
        await session.send(
            "ServiceWorker.unregister", {"registrationId": registration_id}
        )

    async def sw_update(self, registration_id: str) -> None:
        """Trigger an update for a service worker registration.

        Args:
            registration_id: The service worker registration ID.
        """
        session = self._require_session()
        await session.send("ServiceWorker.enable", {})
        await session.send(
            "ServiceWorker.updateRegistration", {"registrationId": registration_id}
        )

    # ── Animations ─────────────────────────────────────────

    async def animation_list(self) -> list[dict[str, Any]]:
        """List all active animations on the page.

        Returns:
            List of animation dicts (id, name, state, etc.).
        """
        session = self._require_session()
        await session.send("Animation.enable", {})
        result = await session.send("Animation.getCurrentTime", {})
        animations: list[dict[str, Any]] = []
        for anim in result.get("animations", []):
            animations.append(dict(anim))
        return animations

    async def animation_pause(self, animation_id: str) -> None:
        """Pause an animation by ID.

        Args:
            animation_id: The animation ID to pause.
        """
        session = self._require_session()
        await session.send("Animation.enable", {})
        await session.send(
            "Animation.setPaused", {"animations": [animation_id], "paused": True}
        )

    async def animation_play(self, animation_id: str) -> None:
        """Play/resume an animation by ID.

        Args:
            animation_id: The animation ID to play.
        """
        session = self._require_session()
        await session.send("Animation.enable", {})
        await session.send(
            "Animation.setPaused", {"animations": [animation_id], "paused": False}
        )

    async def animation_seek(self, animation_id: str, time_ms: int) -> None:
        """Seek an animation to a specific time.

        Args:
            animation_id: The animation ID to seek.
            time_ms: Target time in milliseconds.
        """
        session = self._require_session()
        await session.send("Animation.enable", {})
        await session.send(
            "Animation.seekTo",
            {"animations": [animation_id], "currentTime": time_ms},
        )

    # ── WebAuthn (experimental) ───────────────────────────

    async def webauthn_add_virtual_authenticator(
        self, protocol: str, transport: str
    ) -> str:
        """Add a virtual authenticator via CDP WebAuthn domain."""
        session = self._require_session()
        await session.send("WebAuthn.enable", {})
        result = await session.send(
            "WebAuthn.addVirtualAuthenticator",
            {"protocol": protocol, "transport": transport},
        )
        return str(result.get("authenticatorId", ""))

    async def webauthn_remove_authenticator(self, authenticator_id: str) -> None:
        """Remove a virtual authenticator via CDP WebAuthn domain."""
        session = self._require_session()
        await session.send("WebAuthn.enable", {})
        await session.send(
            "WebAuthn.removeVirtualAuthenticator",
            {"authenticatorId": authenticator_id},
        )

    async def webauthn_add_credential(
        self, authenticator_id: str, credential: dict[str, Any]
    ) -> None:
        """Add a credential to a virtual authenticator via CDP WebAuthn domain."""
        session = self._require_session()
        await session.send("WebAuthn.enable", {})
        await session.send(
            "WebAuthn.addCredential",
            {"authenticatorId": authenticator_id, "credential": credential},
        )

    async def webauthn_get_credentials(
        self, authenticator_id: str
    ) -> list[dict[str, Any]]:
        """Get credentials from a virtual authenticator via CDP WebAuthn domain."""
        session = self._require_session()
        await session.send("WebAuthn.enable", {})
        result = await session.send(
            "WebAuthn.getCredentials",
            {"authenticatorId": authenticator_id},
        )
        return list(result.get("credentials", []))

    # ── WebAudio (experimental) ────────────────────────────

    async def webaudio_get_contexts(self) -> list[dict[str, Any]]:
        """Get all WebAudio contexts via CDP WebAudio domain."""
        session = self._require_session()
        await session.send("WebAudio.enable", {})
        result = await session.send("WebAudio.getRealtimeData", {})
        return list(result.get("contexts", []))

    async def webaudio_get_context(self, context_id: str) -> dict[str, Any]:
        """Get a specific WebAudio context by ID via CDP WebAudio domain."""
        session = self._require_session()
        await session.send("WebAudio.enable", {})
        result = await session.send("WebAudio.getRealtimeData", {})
        for ctx in result.get("contexts", []):
            if ctx.get("contextId") == context_id:
                return dict(ctx)
        return {}

    # ── Media (experimental) ───────────────────────────────

    async def media_get_players(self) -> list[dict[str, Any]]:
        """Get all media players via CDP Media domain."""
        session = self._require_session()
        await session.send("Media.enable", {})
        players: list[dict[str, Any]] = []
        try:
            events = await session.collect_events(
                "Media.playerCreated", timeout=1000
            )
            for ev in events:
                players.append(dict(ev.get("player", ev)))
        except (TimeoutError, KeyError, TypeError):
            pass
        return players

    async def media_get_messages(self, player_id: str) -> list[dict[str, Any]]:
        """Get messages for a specific media player via CDP Media domain."""
        session = self._require_session()
        await session.send("Media.enable", {})
        messages: list[dict[str, Any]] = []
        try:
            events = await session.collect_events(
                "Media.playerMessage", timeout=1000
            )
            for ev in events:
                if ev.get("playerId") == player_id:
                    messages.append(dict(ev))
        except (TimeoutError, KeyError, TypeError):
            pass
        return messages

    # ── Cast (experimental) ────────────────────────────────

    async def cast_list(self) -> list[dict[str, Any]]:
        """List available cast sinks via CDP Cast domain."""
        session = self._require_session()
        await session.send("Cast.enable", {})
        result = await session.send("Cast.getSupportedSinks", {})
        sinks = result.get("sinks", [])
        return [dict(s) for s in sinks] if sinks else []

    async def cast_start_tab(self, sink_name: str) -> None:
        """Start tab mirroring to a cast sink via CDP Cast domain."""
        session = self._require_session()
        await session.send("Cast.enable", {})
        await session.send(
            "Cast.startTabMirroring",
            {"sinkName": sink_name},
        )

    async def cast_stop(self) -> None:
        """Stop active cast mirroring via CDP Cast domain."""
        session = self._require_session()
        await session.send("Cast.enable", {})
        await session.send("Cast.stopCasting", {})

    # ── Bluetooth (experimental) ───────────────────────────

    async def bluetooth_emulate(
        self, name: str, address: str = "00:00:00:00:00:01"
    ) -> None:
        """Emulate a Bluetooth Low Energy device via CDP BluetoothEmulation domain."""
        session = self._require_session()
        await session.send("BluetoothEmulation.enable", {})
        await session.send(
            "BluetoothEmulation.simulatePreconnected",
            {"name": name, "address": address},
        )

    async def bluetooth_stop(self) -> None:
        """Stop Bluetooth emulation via CDP BluetoothEmulation domain."""
        session = self._require_session()
        await session.send("BluetoothEmulation.disable", {})

    # ── WebExtensions ──────────────────────────────────────

    async def extension_install(self, path: str) -> str:
        """Install a browser extension via CDP.

        Args:
            path: Path to the .crx file or unpacked extension directory.

        Returns:
            The extension ID.
        """
        import hashlib
        import os

        session = self._require_session()
        is_dir = await asyncio.to_thread(os.path.isdir, path)
        if is_dir:
            abs_path = await asyncio.to_thread(os.path.abspath, path)
            ext_id = hashlib.sha256(abs_path.encode()).hexdigest()[:32]
            await session.send(
                "Extensions.loadUnpacked",
                {"path": abs_path},
            )
        else:
            ext_id = hashlib.sha256(path.encode()).hexdigest()[:32]
            data = await asyncio.to_thread(
                lambda: open(path, "rb").read()  # noqa: SIM115
            )
            await session.send(
                "Extensions.load",
                {"data": data.hex(), "id": ext_id},
            )
        return ext_id

    async def extension_uninstall(self, extension_id: str) -> None:
        """Uninstall a browser extension by ID.

        Args:
            extension_id: The extension ID returned by extension_install.
        """
        session = self._require_session()
        await session.send(
            "Extensions.uninstall",
            {"id": extension_id},
        )

    async def extension_list(self) -> list[dict[str, Any]]:
        """List installed browser extensions.

        Returns:
            List of extension dicts (id, name, version, enabled).
        """
        session = self._require_session()
        result = await session.send("Extensions.getInfo", {})
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

    # ── Browser preferences ────────────────────────────────

    async def get_pref(self, key: str) -> Any:
        """Get a browser preference value by key.

        Args:
            key: The preference key (e.g. "download.default_directory").

        Returns:
            The preference value.
        """
        session = self._require_session()
        result = await session.send(
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
        session = self._require_session()
        await session.send(
            "Browser.setPreference",
            {"name": key, "value": value},
        )

    async def __aenter__(self) -> CDPBackend:
        """Enter async context manager, returning self.

        Returns:
            The CDPBackend instance.
        """
        return self

    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None:
        """Exit async context manager, closing the backend.

        Args:
            exc_type: Exception type if raised, else None.
            exc_val: Exception value if raised, else None.
            exc_tb: Traceback if raised, else None.
        """
        await self.close()
