"""CDP backend implementation using cdpwave."""

from __future__ import annotations

import asyncio
import base64
import time
from typing import Any

from browsix.backend.base import AbstractBackend
from browsix.config import (
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
from browsix.exceptions import ElementNotFoundError, NavigationError, WaitTimeoutError

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
                "cdpwave is not installed. Run: pip install browsix[cdp]"
            )
        self._client: CDPClient | None = None
        self._session: CDPSession | None = None
        self._console_entries: list[dict[str, Any]] = []
        self._log_entries: list[dict[str, Any]] = []
        self._current_url: str = ""

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

        self._client = await CDPClient.launch(
            headless=options.headless,
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
            NavigationError: If the session is not initialized.
            WaitTimeoutError: If the wait strategy times out.
        """
        if self._session is None:
            raise NavigationError(url, "Session not initialized. Call launch() first.")

        await self._session.page.enable()
        await self._session.page.navigate(url)
        self._current_url = url

        if wait is None or wait.strategy == "load":
            timeout_sec = (wait.timeout if wait else 30000) / 1000
            try:
                await self._session.wait_for_event(
                    "Page.loadEventFired", timeout=timeout_sec
                )
            except TimeoutError:
                raise WaitTimeoutError("load", wait.timeout if wait else 30000) from None
        elif wait.strategy == "selector":
            await self.wait_for(wait)
        elif wait.strategy == "domcontentloaded":
            timeout_sec = wait.timeout / 1000
            try:
                await self._session.wait_for_event(
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
            NavigationError: If the session is not initialized.
        """
        if self._session is None:
            raise NavigationError(params.url, "Session not initialized.")

        if params.device and params.device in DEVICE_PRESETS:
            preset = DEVICE_PRESETS[params.device]
            await self._session.emulation.set_device_metrics_override(
                width=preset["width"],
                height=preset["height"],
                device_scale_factor=preset["device_scale_factor"],
                mobile=preset["mobile"],
                user_agent=preset["user_agent"],
            )
            if preset.get("touch"):
                await self._session.emulation.set_touch_emulation_enabled(True)

        result = await self._session.page.capture_screenshot(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")

        doc = await self._session.dom.get_document()
        root_node_id = doc.get("root", {}).get("nodeId", 0)
        node = await self._session.dom.query_selector(root_node_id, selector)
        node_id = node.get("nodeId", 0)
        box = await self._session.dom.get_box_model(node_id)
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
        result = await self._session.page.capture_screenshot(
            format=format,
            quality=quality,
            clip=clip,
        )
        data_b64 = result.get("data", "")
        return base64.b64decode(data_b64)

    async def eval(self, expression: str, await_promise: bool = False) -> Any:
        """Evaluate a JavaScript expression.

        Args:
            expression: JavaScript expression to evaluate.
            await_promise: Whether to await a returned Promise.

        Returns:
            The evaluation result value.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")

        await self._session.runtime.enable()
        result = await self._session.runtime.evaluate(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        result: dict[str, Any] = await self._session.send(method, params)
        return result

    async def go_back(self) -> None:
        """Navigate back in browser history."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        history = await self._session.page.get_navigation_history()
        current_idx = history.get("currentIndex", 0)
        entries = history.get("entries", [])
        if current_idx > 0 and entries:
            prev_entry = entries[current_idx - 1]
            await self._session.page.navigate_to_history_entry(
                prev_entry.get("id", 0)
            )

    async def go_forward(self) -> None:
        """Navigate forward in browser history."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        history = await self._session.page.get_navigation_history()
        current_idx = history.get("currentIndex", 0)
        entries = history.get("entries", [])
        if current_idx < len(entries) - 1:
            next_entry = entries[current_idx + 1]
            await self._session.page.navigate_to_history_entry(
                next_entry.get("id", 0)
            )

    async def reload(self, ignore_cache: bool = False) -> None:
        """Reload the current page.

        Args:
            ignore_cache: If True, bypass the browser cache.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.page.reload(ignore_cache=ignore_cache)

    async def stop_loading(self) -> None:
        """Stop all pending navigations and resource loads."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.page.stop()

    async def wait_for(self, strategy: WaitStrategy) -> None:
        """Wait for a specific condition.

        Args:
            strategy: Wait strategy (selector, load, url).

        Raises:
            WaitTimeoutError: If the condition is not met within the timeout.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")

        timeout_sec = strategy.timeout / 1000
        deadline = time.monotonic() + timeout_sec

        if strategy.strategy == "selector" and strategy.selector:
            escaped = strategy.selector.replace("'", "\\'")
            js = f"document.querySelector('{escaped}') !== null"
            while time.monotonic() < deadline:
                result = await self._session.runtime.evaluate(js)
                if result.get("result", {}).get("value") is True:
                    return
                await asyncio.sleep(0.1)
            raise WaitTimeoutError("selector", strategy.timeout)

        if strategy.strategy == "load":
            try:
                await self._session.wait_for_event(
                    "Page.loadEventFired", timeout=timeout_sec
                )
            except TimeoutError:
                raise WaitTimeoutError("load", strategy.timeout) from None
            return

        if strategy.strategy == "url" and strategy.url_pattern:
            while time.monotonic() < deadline:
                result = await self._session.runtime.evaluate("window.location.href")
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
        if self._session is None:
            raise NavigationError(params.url, "Session not initialized.")

        await self._session.emulation.set_emulated_media(media=params.media)

        paper_dims = PAPER_SIZES.get(params.paper, PAPER_SIZES["letter"])
        margin_val = float(params.margin.replace("in", ""))

        result = await self._session.page.print_to_pdf(
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
        if self._session is None:
            raise NavigationError(params.url, "Session not initialized.")

        frames: list[bytes] = []

        def on_frame(event_params: dict[str, Any]) -> None:
            """Handle a screencast frame event and decode the image data.

            Args:
                event_params: CDP event parameters containing base64-encoded frame data.
            """
            data = event_params.get("data")
            if data:
                frames.append(base64.b64decode(data))

        self._session.on("Page.screencastFrame", on_frame)

        await self._session.send("Page.startScreencast", {
            "format": params.format,
            "quality": params.quality,
            "maxWidth": params.max_width,
            "maxHeight": params.max_height,
        })

        await asyncio.sleep(params.duration)

        await self._session.send("Page.stopScreencast")

        return frames

    async def list_tabs(self) -> list[dict[str, Any]]:
        """List all open browser tabs/targets.

        Returns:
            List of target info dicts.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        result = await self._session.target.get_targets()
        targets = result.get("targetInfos", [])
        return [t for t in targets if t.get("type") == "page"]

    async def new_tab(self, url: str = "about:blank") -> str:
        """Create a new tab and return its target ID.

        Args:
            url: Initial URL for the new tab.

        Returns:
            The target ID of the new tab.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        result = await self._session.target.create_target(url)
        return str(result.get("targetId", ""))

    async def close_tab(self, tab_id: str) -> None:
        """Close a tab by its target ID.

        Args:
            tab_id: The target ID of the tab to close.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.target.close_target(tab_id)

    async def activate_tab(self, tab_id: str) -> None:
        """Activate (focus) a tab by its target ID.

        Args:
            tab_id: The target ID of the tab to activate.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.target.activate_target(tab_id)

    async def capture_console(self, level: str = "all") -> list[dict[str, Any]]:
        """Capture console messages at or above the given level.

        Args:
            level: Minimum log level ("all", "error", "warning", "info", "log").

        Returns:
            List of console entry dicts with type, args, and timestamp.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")

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

        self._session.on("Runtime.consoleAPICalled", on_console_api)

        await self._session.runtime.enable()
        await asyncio.sleep(0.5)

        return entries

    async def capture_logs(self) -> list[dict[str, Any]]:
        """Capture browser log entries.

        Returns:
            List of log entry dicts with level, text, and timestamp.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")

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

        self._session.on("Log.entryAdded", on_log_entry)

        await self._session.log.enable()
        await asyncio.sleep(0.5)

        return entries

    # ── DOM ────────────────────────────────────────────────

    async def _find_node(self, selector: str) -> int:
        """Find a node by CSS selector and return its nodeId."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.dom.enable()
        doc = await self._session.dom.get_document()
        root_node_id = doc.get("root", {}).get("nodeId", 0)
        result = await self._session.dom.query_selector(root_node_id, selector)
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
        node_id = await self._find_node(selector)
        if outer:
            result = await self._session.dom.get_outer_html(node_id)  # type: ignore[union-attr]
        else:
            result = await self._session.dom.get_inner_html(node_id)  # type: ignore[union-attr]
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.dom.enable()
        doc = await self._session.dom.get_document()
        root_node_id = doc.get("root", {}).get("nodeId", 0)

        if all:
            result = await self._session.dom.query_selector_all(root_node_id, selector)
            node_ids = result.get("nodeIds", [])
            nodes: list[dict[str, Any]] = []
            for nid in node_ids:
                desc = await self._session.dom.describe_node(node_id=nid)
                nodes.append(desc.get("node", {}))
            return nodes

        result = await self._session.dom.query_selector(root_node_id, selector)
        node_id = result.get("nodeId", 0)
        if node_id == 0:
            raise ElementNotFoundError(selector)
        desc = await self._session.dom.describe_node(node_id=node_id)
        return dict(desc.get("node", {}))

    async def dom_set_attr(self, selector: str, name: str, value: str) -> None:
        """Set an attribute on an element matching a CSS selector."""
        node_id = await self._find_node(selector)
        await self._session.dom.set_attribute_value(node_id, name, value)  # type: ignore[union-attr]

    async def dom_get_attr(self, selector: str, name: str) -> str:
        """Get an attribute value from an element matching a CSS selector."""
        node_id = await self._find_node(selector)
        result = await self._session.dom.get_attribute(node_id, name)  # type: ignore[union-attr]
        attrs = result.get("attributes", [])
        for i in range(0, len(attrs) - 1, 2):
            if attrs[i] == name:
                return str(attrs[i + 1])
        return ""

    async def dom_remove_attr(self, selector: str, name: str) -> None:
        """Remove an attribute from an element matching a CSS selector."""
        node_id = await self._find_node(selector)
        await self._session.dom.remove_attribute(node_id, name)  # type: ignore[union-attr]

    async def dom_remove(self, selector: str) -> None:
        """Remove an element matching a CSS selector from the DOM."""
        node_id = await self._find_node(selector)
        await self._session.dom.remove_node(node_id)  # type: ignore[union-attr]

    async def dom_focus(self, selector: str) -> None:
        """Focus an element matching a CSS selector."""
        node_id = await self._find_node(selector)
        await self._session.dom.focus(node_id)  # type: ignore[union-attr]

    async def dom_scroll(
        self, selector: str | None = None, x: int = 0, y: int = 0
    ) -> None:
        """Scroll to an element or by offset.

        Args:
            selector: CSS selector to scroll to. If None, scroll by offset.
            x: Horizontal scroll offset.
            y: Vertical scroll offset.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        if selector:
            escaped = selector.replace("'", "\\'")
            js = f"document.querySelector('{escaped}').scrollIntoView()"
        else:
            js = f"window.scrollBy({x}, {y})"
        await self._session.runtime.evaluate(js)

    # ── Network ────────────────────────────────────────────

    async def capture_har(self, params: HarParams) -> dict[str, Any]:
        """Navigate to a URL and capture network traffic as HAR 1.2 dict.

        Args:
            params: HAR capture parameters.

        Returns:
            HAR 1.2 compliant dict with log.entries.
        """
        if self._session is None:
            raise NavigationError(params.url, "Session not initialized.")

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

        self._session.on("Network.requestWillBeSent", on_request)
        self._session.on("Network.responseReceived", on_response)
        self._session.on("Network.loadingFinished", on_loading_finished)

        await self._session.network.enable()
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
                "creator": {"name": "browsix", "version": "0.3.0"},
                "entries": entries,
            }
        }

    async def get_cookies(self) -> list[dict[str, Any]]:
        """Get all cookies for the current page.

        Returns:
            List of cookie dicts.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        result = await self._session.network.get_cookies()
        return list(result.get("cookies", []))

    async def set_cookie(self, params: CookieParams) -> None:
        """Set a cookie in the browser.

        Args:
            params: Cookie parameters.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.network.set_cookie(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.network.delete_cookies(name=name, domain=domain)

    async def clear_cookies(self) -> None:
        """Clear all browser cookies."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.network.clear_browser_cookies()

    async def set_headers(self, headers: dict[str, str]) -> None:
        """Set extra HTTP headers for all requests.

        Args:
            headers: Dict of header name to value.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.network.set_extra_request_headers(headers)

    async def set_user_agent(self, user_agent: str) -> None:
        """Override the browser's User-Agent string.

        Args:
            user_agent: The User-Agent string to use.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.network.set_user_agent_override(user_agent=user_agent)

    # ── Browser management ─────────────────────────────────

    async def new_context(self) -> str:
        """Create a new browser context and return its ID.

        Returns:
            The browser context ID string.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        result = await self._session.target.create_browser_context()
        return str(result.get("browserContextId", ""))

    async def list_contexts(self) -> list[dict[str, Any]]:
        """List all browser contexts.

        Returns:
            List of context info dicts.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        result = await self._session.send("Target.getBrowserContexts")
        contexts = result.get("browserContextIds", [])
        return [{"contextId": ctx} for ctx in contexts]

    async def close_context(self, context_id: str) -> None:
        """Close a browser context by ID.

        Args:
            context_id: The browser context ID to close.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.target.dispose_browser_context(context_id)

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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        preset = DEVICE_PRESETS.get(device)
        if preset is None:
            raise ValueError(f"Unknown device preset: {device}")
        await self._session.emulation.set_device_metrics_override(
            width=int(preset["width"]),
            height=int(preset["height"]),
            device_scale_factor=float(preset["device_scale_factor"]),
            mobile=bool(preset["mobile"]),
            user_agent=str(preset["user_agent"]),
        )
        if preset.get("touch"):
            await self._session.emulation.set_touch_emulation_enabled(True)

    async def set_viewport(
        self, width: int, height: int, device_scale_factor: float = 1.0
    ) -> None:
        """Set a custom viewport with given dimensions and scale factor.

        Args:
            width: Viewport width in CSS pixels.
            height: Viewport height in CSS pixels.
            device_scale_factor: Device pixel scale factor.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.emulation.set_device_metrics_override(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.emulation.set_geolocation_override(
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
        )

    async def set_timezone(self, timezone: str) -> None:
        """Override the system timezone.

        Args:
            timezone: IANA timezone ID (e.g. 'America/New_York').
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.emulation.set_timezone_override(timezone)

    async def set_dark_mode(self, enabled: bool) -> None:
        """Enable or disable dark mode emulation.

        Args:
            enabled: True to enable dark mode, False to disable.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        features = [{"name": "prefers-color-scheme", "value": "dark" if enabled else "light"}]
        await self._session.emulation.set_emulated_media(features=features)

    # ── Input ──────────────────────────────────────────────

    async def _get_box_center(self, selector: str) -> tuple[float, float]:
        """Find an element by selector and return the center of its bounding box."""
        node_id = await self._find_node(selector)
        box = await self._session.dom.get_box_model(node_id)  # type: ignore[union-attr]
        model = box.get("model", {})
        borders = model.get("border", [])
        if len(borders) < 8:
            raise ElementNotFoundError(selector)
        xs = [borders[0], borders[2], borders[4], borders[6]]
        ys = [borders[1], borders[3], borders[5], borders[7]]
        cx = (min(xs) + max(xs)) / 2
        cy = (min(ys) + max(ys)) / 2
        return cx, cy

    async def click(
        self, selector: str, button: str = "left", click_count: int = 1
    ) -> None:
        """Click an element matching a CSS selector.

        Args:
            selector: CSS selector for the target element.
            button: Mouse button — "left", "right", or "middle".
            click_count: Number of clicks to dispatch.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        x, y = await self._get_box_center(selector)
        btn_map = {"left": "left", "right": "right", "middle": "middle"}
        btn = btn_map.get(button, "left")
        for _ in range(click_count):
            await self._session.input.dispatch_mouse_event(
                type_="mousePressed", x=x, y=y, button=btn, click_count=1
            )
            await self._session.input.dispatch_mouse_event(
                type_="mouseReleased", x=x, y=y, button=btn, click_count=1
            )

    async def type_text(self, selector: str, text: str, delay: int = 0) -> None:
        """Type text into an element, optionally with delay between keystrokes.

        Args:
            selector: CSS selector for the target element.
            text: Text to type character by character.
            delay: Delay between keystrokes in milliseconds.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        node_id = await self._find_node(selector)
        await self._session.dom.focus(node_id)
        for char in text:
            await self._session.input.dispatch_key_event(
                type_="char", text=char
            )
            if delay > 0:
                await asyncio.sleep(delay / 1000)

    async def fill(self, selector: str, value: str) -> None:
        """Fill an input element with a value (replaces existing content).

        Args:
            selector: CSS selector for the target element.
            value: Value to set in the input field.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        escaped = selector.replace("'", "\\'")
        js = (
            f"(function(){{var el=document.querySelector('{escaped}');"
            f"if(!el)return false;el.focus();el.value='{value}';"
            f"el.dispatchEvent(new Event('input',{{bubbles:true}}));"
            f"el.dispatchEvent(new Event('change',{{bubbles:true}}));"
            f"return true;}})()"
        )
        result = await self._session.runtime.evaluate(js)
        if not result.get("result", {}).get("value"):
            raise ElementNotFoundError(selector)

    async def select_option(self, selector: str, value: str) -> None:
        """Select an option in a <select> element by value.

        Args:
            selector: CSS selector for the <select> element.
            value: Option value to select.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        escaped = selector.replace("'", "\\'")
        escaped_val = value.replace("'", "\\'")
        js = (
            f"(function(){{var el=document.querySelector('{escaped}');"
            f"if(!el)return false;el.value='{escaped_val}';"
            f"el.dispatchEvent(new Event('change',{{bubbles:true}}));"
            f"return true;}})()"
        )
        result = await self._session.runtime.evaluate(js)
        if not result.get("result", {}).get("value"):
            raise ElementNotFoundError(selector)

    async def hover(self, selector: str) -> None:
        """Hover over an element matching a CSS selector.

        Args:
            selector: CSS selector for the target element.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        x, y = await self._get_box_center(selector)
        await self._session.input.dispatch_mouse_event(
            type_="mouseMoved", x=x, y=y
        )

    async def key_press(self, key: str) -> None:
        """Press a keyboard key.

        Args:
            key: Key name (e.g. 'Enter', 'Tab', 'Escape').
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        key_map = {
            "Enter": {"key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13},
            "Tab": {"key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9},
            "Escape": {"key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27},
            "Space": {"key": " ", "code": "Space", "windowsVirtualKeyCode": 32},
            "Backspace": {"key": "Backspace", "code": "Backspace", "windowsVirtualKeyCode": 8},
        }
        key_info = key_map.get(key, {"key": key, "code": key})
        await self._session.input.dispatch_key_event(
            type_="keyDown", **key_info
        )
        await self._session.input.dispatch_key_event(
            type_="keyUp", **key_info
        )

    async def drag(self, source: str, target: str) -> None:
        """Drag an element from source selector to target selector.

        Args:
            source: CSS selector for the element to drag.
            target: CSS selector for the drop target.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        sx, sy = await self._get_box_center(source)
        tx, ty = await self._get_box_center(target)
        await self._session.input.dispatch_mouse_event(
            type_="mousePressed", x=sx, y=sy, button="left", click_count=1
        )
        await self._session.input.dispatch_mouse_event(
            type_="mouseMoved", x=tx, y=ty
        )
        await self._session.input.dispatch_mouse_event(
            type_="mouseReleased", x=tx, y=ty, button="left", click_count=1
        )

    async def tap(self, selector: str) -> None:
        """Tap an element (touch emulation click).

        Args:
            selector: CSS selector for the target element.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        x, y = await self._get_box_center(selector)
        await self._session.input.dispatch_touch_event(
            type_="touchStart", touch_points=[{"x": x, "y": y}]
        )
        await self._session.input.dispatch_touch_event(
            type_="touchEnd", touch_points=[]
        )

    # ── Network advanced ───────────────────────────────────

    async def block_requests(self, patterns: list[str]) -> None:
        """Block requests matching URL patterns.

        Args:
            patterns: List of glob-style URL patterns to block.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.network.enable()
        for pattern in patterns:
            await self._session.send(
                "Network.setBlockedURLs",
                {"urls": [pattern]},
            )

    async def throttle_network(self, params: ThrottleParams) -> None:
        """Throttle network conditions.

        Args:
            params: Throttle parameters (offline, latency, throughput).
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.network.enable()
        await self._session.send(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.network.enable()
        await self._session.network.set_cache_disabled(disabled)

    async def intercept_requests(self, pattern: dict[str, Any]) -> None:
        """Intercept requests matching a pattern dict.

        Args:
            pattern: Fetch.enable pattern dict (urlPattern, resourceType, requestStage).
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        import json as _json

        body = response.get("body", "")
        if isinstance(body, (dict, list)):
            body = _json.dumps(body)
        body_b64 = base64.b64encode(body.encode("utf-8")).decode("ascii")

        fulfilled: list[bool] = [False]

        async def on_request_paused(event_params: dict[str, Any]) -> None:
            """Handle Fetch.requestPaused and fulfill with the mocked response.

            Args:
                event_params: CDP event parameters with the paused request ID.
            """
            request_id = event_params.get("requestId", "")
            await self._session.send(  # type: ignore[union-attr]
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

        self._session.on("Fetch.requestPaused", on_request_paused)
        await self._session.send(
            "Fetch.enable",
            {"patterns": [{"urlPattern": url, "requestStage": "Response"}]},
        )

    # ── Accessibility ──────────────────────────────────────

    async def a11y_tree(self) -> dict[str, Any]:
        """Get the full accessibility tree of the current page.

        Returns:
            Dict with the accessibility tree nodes.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        result = await self._session.send("Accessibility.getFullAXTree")
        return dict(result)

    async def a11y_node(self, node_id: str) -> dict[str, Any]:
        """Get a specific accessibility node by its node ID.

        Args:
            node_id: The accessibility node ID.

        Returns:
            Dict with the node's accessibility properties.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        result = await self._session.send(
            "Accessibility.getPartialAXTree",
            {"nodeId": node_id},
        )
        nodes = result.get("nodes", [])
        for node in nodes:
            if node.get("nodeId") == node_id:
                return dict(node)
        return dict(nodes[0]) if nodes else {}

    async def a11y_ancestors(self, node_id: str) -> list[dict[str, Any]]:
        """Get ancestor nodes of an accessibility node.

        Args:
            node_id: The accessibility node ID.

        Returns:
            List of ancestor node dicts.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        result = await self._session.send(
            "Accessibility.getPartialAXTree",
            {"nodeId": node_id, "fetchRelatives": True},
        )
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        import os
        import tempfile

        download_dir = tempfile.mkdtemp()
        await self._session.send(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": download_dir},
        )

        await asyncio.sleep(2)

        for fname in os.listdir(download_dir):
            fpath = os.path.join(download_dir, fname)
            if os.path.isfile(fpath):  # noqa: ASYNC240
                with open(fpath, "rb") as f:  # noqa: ASYNC230
                    return f.read()

        return b""

    # ── Dialogs ────────────────────────────────────────────

    async def dialog_accept(self, prompt_text: str | None = None) -> None:
        """Accept a JavaScript dialog (alert, confirm, prompt).

        Args:
            prompt_text: Text to enter in a prompt dialog (optional).
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send(
            "Page.handleJavaScriptDialog",
            {"accept": True, "promptText": prompt_text or ""},
        )

    async def dialog_dismiss(self) -> None:
        """Dismiss a JavaScript dialog."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send(
            "Page.handleJavaScriptDialog",
            {"accept": False},
        )

    # ── Permissions ────────────────────────────────────────

    async def grant_permission(self, permission: str) -> None:
        """Grant a browser permission.

        Args:
            permission: Permission name (e.g. 'geolocation', 'notifications').
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send(
            "Browser.grantPermissions",
            {"permissions": [permission]},
        )

    async def reset_permissions(self) -> None:
        """Reset all granted permissions."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Browser.resetPermissions", {})

    # ── Security ───────────────────────────────────────────

    async def get_security_state(self) -> dict[str, Any]:
        """Get the current security state of the page.

        Returns:
            Dict with security state info (secure, explanations, etc.).
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        result = await self._session.send("Security.setIgnoreCertificateErrors", {"ignore": False})
        return dict(result) if result else {}

    async def ignore_cert_errors(self, ignore: bool = True) -> None:
        """Enable or disable ignoring of certificate errors.

        Args:
            ignore: True to ignore cert errors, False to enforce.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send(
            "Security.setIgnoreCertificateErrors",
            {"ignore": ignore},
        )

    # ── Emulation advanced ─────────────────────────────────

    async def set_locale(self, locale: str) -> None:
        """Override the browser locale.

        Args:
            locale: Locale string (e.g. 'en-US', 'fr-FR').
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send(
            "Emulation.setLocaleOverride",
            {"locale": locale},
        )

    async def set_cpu_throttle(self, rate: float) -> None:
        """Throttle CPU performance by a rate multiplier.

        Args:
            rate: Throttle rate (e.g. 4 = 4x slower than normal).
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send(
            "Emulation.setCPUThrottlingRate",
            {"rate": rate},
        )

    async def set_touch_emulation(self, enabled: bool) -> None:
        """Enable or disable touch emulation.

        Args:
            enabled: True to enable touch emulation, False to disable.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.emulation.set_touch_emulation_enabled(enabled)

    async def set_sensors(self, sensors: SensorParams) -> None:
        """Override sensor values.

        Args:
            sensors: Sensor parameters with type and values.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        if sensors.type == "device-orientation":
            await self._session.send(
                "DeviceOrientation.setDeviceOrientationOverride",
                {
                    "alpha": sensors.values.get("alpha", 0),
                    "beta": sensors.values.get("beta", 0),
                    "gamma": sensors.values.get("gamma", 0),
                },
            )
        elif sensors.type == "geolocation":
            await self._session.emulation.set_geolocation_override(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Performance.enable", {})
        result = await self._session.send("Performance.getMetrics", {})
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
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
                    resp = await self._session.send(  # type: ignore[union-attr]
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
                        import json as _json

                        trace_events.extend(_json.loads(content).get("traceEvents", []))
                except Exception:
                    trace_events.append({"raw_size": len(raw)})
            else:
                trace_events.append({"error": "No stream handle in tracingComplete"})

        self._session.on("Tracing.tracingComplete", _on_tracing_complete)
        await self._session.send(
            "Tracing.start",
            {"traceType": "devtools-timeline"},
        )
        await asyncio.sleep(duration_ms / 1000)
        await self._session.send("Tracing.end", {})
        return {"traceEvents": trace_events}

    async def perf_profile(self, duration_ms: int = 3000) -> dict[str, Any]:
        """Capture a CPU profile for the given duration.

        Args:
            duration_ms: Profile duration in milliseconds.

        Returns:
            Dict containing CPU profile data (nodes, samples, timeDeltas, etc.).
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Profiler.enable", {})
        await self._session.send("Profiler.start", {})
        await asyncio.sleep(duration_ms / 1000)
        result = await self._session.send("Profiler.stop", {})
        profile = result.get("profile", result)
        return dict(profile) if profile else {}

    async def perf_heap_snapshot(self) -> dict[str, Any]:
        """Capture a heap snapshot and return it as a dict.

        Returns:
            Dict containing heap snapshot data (nodes, edges, etc.).
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("HeapProfiler.enable", {})
        result = await self._session.send(
            "HeapProfiler.takeHeapSnapshot",
            {"reportProgress": False},
        )
        return dict(result) if result else {"snapshot": "taken"}

    async def perf_coverage(self) -> dict[str, Any]:
        """Get JavaScript code coverage for the current page.

        Returns:
            Dict with 'result' key containing a list of script coverage entries.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Profiler.enable", {})
        await self._session.send(
            "Profiler.startPreciseCoverage",
            {"callCount": True, "detailed": True},
        )
        result = await self._session.send("Profiler.takePreciseCoverage", {})
        return dict(result) if result else {}

    async def perf_css_coverage(self) -> dict[str, Any]:
        """Get CSS rule usage coverage for the current page.

        Returns:
            Dict with 'result' key containing a list of CSS coverage entries.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("CSS.enable", {})
        await self._session.send("CSS.startRuleUsageTracking", {})
        await asyncio.sleep(1)
        result = await self._session.send("CSS.stopRuleUsageTracking", {})
        return dict(result) if result else {}

    # ── CSS ────────────────────────────────────────────────

    async def css_get_styles(self, selector: str) -> dict[str, Any]:
        """Get inline and matched styles for an element by CSS selector.

        Args:
            selector: CSS selector for the target element.

        Returns:
            Dict containing inlineStyles and matchedStyles.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("CSS.enable", {})
        node_id = await self._find_node(selector)
        inline = await self._session.send(
            "CSS.getInlineStyles", {"nodeId": node_id}
        )
        matched = await self._session.send(
            "CSS.getMatchedStyles", {"nodeId": node_id}
        )
        return {"inlineStyles": inline, "matchedStyles": matched}

    async def css_get_stylesheets(self) -> list[dict[str, Any]]:
        """List all stylesheets in the current page.

        Returns:
            List of stylesheet header dicts.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("CSS.enable", {})
        result = await self._session.send("CSS.getStyleSheetText", {})
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("CSS.enable", {})
        result = await self._session.send(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        node_id = await self._find_node(selector)
        resolved = await self._session.send(
            "DOM.resolveNode", {"nodeId": node_id}
        )
        object_id = resolved.get("object", {}).get("objectId", "")
        if not object_id:
            raise ElementNotFoundError(selector)
        result = await self._session.send(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Debugger.enable", {})
        params: dict[str, Any] = {"url": url, "lineNumber": line}
        if condition:
            params["condition"] = condition
        result = await self._session.send(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Debugger.enable", {})
        result = await self._session.send(
            "Debugger.setBreakpointOnFunctionCall",
            {"functionName": function_name},
        )
        return str(result.get("breakpointId", ""))

    async def debug_remove_breakpoint(self, breakpoint_id: str) -> None:
        """Remove a breakpoint by ID.

        Args:
            breakpoint_id: The breakpoint ID returned from set_breakpoint.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send(
            "Debugger.removeBreakpoint", {"breakpointId": breakpoint_id}
        )

    async def debug_step_over(self) -> None:
        """Step over the current statement in the debugger."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Debugger.stepOver", {})

    async def debug_step_into(self) -> None:
        """Step into the current function call in the debugger."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Debugger.stepInto", {})

    async def debug_step_out(self) -> None:
        """Step out of the current function in the debugger."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Debugger.stepOut", {})

    async def debug_pause(self) -> None:
        """Pause JavaScript execution."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Debugger.pause", {})

    async def debug_resume(self) -> None:
        """Resume JavaScript execution after a pause."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Debugger.resume", {})

    async def debug_get_listeners(self, selector: str) -> list[dict[str, Any]]:
        """Get event listeners attached to an element by CSS selector.

        Args:
            selector: CSS selector for the target element.

        Returns:
            List of listener dicts (type, useCapture, passive, etc.).
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        node_id = await self._find_node(selector)
        resolved = await self._session.send(
            "DOM.resolveNode", {"nodeId": node_id}
        )
        object_id = resolved.get("object", {}).get("objectId", "")
        if not object_id:
            raise ElementNotFoundError(selector)
        result = await self._session.send(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        result = await self._session.send(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Overlay.enable", {})
        node_id = await self._find_node(selector)
        highlight_config: dict[str, Any] = {
            "contentColor": color,
            "contentOutlineColor": "rgba(0,0,0,0)",
        }
        await self._session.send(
            "Overlay.highlightNode",
            {"highlightConfig": highlight_config, "nodeId": node_id},
        )

    async def overlay_clear(self) -> None:
        """Clear all highlight overlays from the page."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Overlay.clearHighlight", {})

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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("DOMStorage.enable", {})
        storage_id = await self._get_storage_id(storage_type)
        result = await self._session.send(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("DOMStorage.enable", {})
        storage_id = await self._get_storage_id(storage_type)
        await self._session.send(
            "DOMStorage.setDOMStorageItem",
            {"storageId": storage_id, "key": key, "value": value},
        )

    async def storage_clear(self, storage_type: str = "local") -> None:
        """Clear all entries in DOM storage.

        Args:
            storage_type: "local" or "session".
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("DOMStorage.enable", {})
        storage_id = await self._get_storage_id(storage_type)
        await self._session.send(
            "DOMStorage.clearDOMStorageItems", {"storageId": storage_id}
        )

    async def storage_list(self, storage_type: str = "local") -> dict[str, str]:
        """List all key-value pairs in DOM storage.

        Args:
            storage_type: "local" or "session".

        Returns:
            Dict mapping keys to values.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("DOMStorage.enable", {})
        storage_id = await self._get_storage_id(storage_type)
        result = await self._session.send(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        result = await self._session.send(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        result = await self._session.send(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send(
            "CacheStorage.deleteCache",
            {"cacheId": f"{self._get_origin()}_{cache_name}"},
        )

    async def indexeddb_list(self) -> list[dict[str, Any]]:
        """List all IndexedDB databases.

        Returns:
            List of database info dicts (name, version, etc.).
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        result = await self._session.send(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        result = await self._session.send(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("ServiceWorker.enable", {})
        result = await self._session.send(
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
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("ServiceWorker.enable", {})
        await self._session.send(
            "ServiceWorker.unregister", {"registrationId": registration_id}
        )

    async def sw_update(self, registration_id: str) -> None:
        """Trigger an update for a service worker registration.

        Args:
            registration_id: The service worker registration ID.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("ServiceWorker.enable", {})
        await self._session.send(
            "ServiceWorker.updateRegistration", {"registrationId": registration_id}
        )

    # ── Animations ─────────────────────────────────────────

    async def animation_list(self) -> list[dict[str, Any]]:
        """List all active animations on the page.

        Returns:
            List of animation dicts (id, name, state, etc.).
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Animation.enable", {})
        result = await self._session.send("Animation.getCurrentTime", {})
        animations: list[dict[str, Any]] = []
        for anim in result.get("animations", []):
            animations.append(dict(anim))
        return animations

    async def animation_pause(self, animation_id: str) -> None:
        """Pause an animation by ID.

        Args:
            animation_id: The animation ID to pause.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Animation.enable", {})
        await self._session.send(
            "Animation.setPaused", {"animations": [animation_id], "paused": True}
        )

    async def animation_play(self, animation_id: str) -> None:
        """Play/resume an animation by ID.

        Args:
            animation_id: The animation ID to play.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Animation.enable", {})
        await self._session.send(
            "Animation.setPaused", {"animations": [animation_id], "paused": False}
        )

    async def animation_seek(self, animation_id: str, time_ms: int) -> None:
        """Seek an animation to a specific time.

        Args:
            animation_id: The animation ID to seek.
            time_ms: Target time in milliseconds.
        """
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Animation.enable", {})
        await self._session.send(
            "Animation.seekTo",
            {"animations": [animation_id], "currentTime": time_ms},
        )

    # ── WebAuthn (experimental) ───────────────────────────

    async def webauthn_add_virtual_authenticator(
        self, protocol: str, transport: str
    ) -> str:
        """Add a virtual authenticator via CDP WebAuthn domain."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("WebAuthn.enable", {})
        result = await self._session.send(
            "WebAuthn.addVirtualAuthenticator",
            {"protocol": protocol, "transport": transport},
        )
        return str(result.get("authenticatorId", ""))

    async def webauthn_remove_authenticator(self, authenticator_id: str) -> None:
        """Remove a virtual authenticator via CDP WebAuthn domain."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("WebAuthn.enable", {})
        await self._session.send(
            "WebAuthn.removeVirtualAuthenticator",
            {"authenticatorId": authenticator_id},
        )

    async def webauthn_add_credential(
        self, authenticator_id: str, credential: dict[str, Any]
    ) -> None:
        """Add a credential to a virtual authenticator via CDP WebAuthn domain."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("WebAuthn.enable", {})
        await self._session.send(
            "WebAuthn.addCredential",
            {"authenticatorId": authenticator_id, "credential": credential},
        )

    async def webauthn_get_credentials(
        self, authenticator_id: str
    ) -> list[dict[str, Any]]:
        """Get credentials from a virtual authenticator via CDP WebAuthn domain."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("WebAuthn.enable", {})
        result = await self._session.send(
            "WebAuthn.getCredentials",
            {"authenticatorId": authenticator_id},
        )
        return list(result.get("credentials", []))

    # ── WebAudio (experimental) ────────────────────────────

    async def webaudio_get_contexts(self) -> list[dict[str, Any]]:
        """Get all WebAudio contexts via CDP WebAudio domain."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("WebAudio.enable", {})
        result = await self._session.send("WebAudio.getRealtimeData", {})
        return list(result.get("contexts", []))

    async def webaudio_get_context(self, context_id: str) -> dict[str, Any]:
        """Get a specific WebAudio context by ID via CDP WebAudio domain."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("WebAudio.enable", {})
        result = await self._session.send("WebAudio.getRealtimeData", {})
        for ctx in result.get("contexts", []):
            if ctx.get("contextId") == context_id:
                return dict(ctx)
        return {}

    # ── Media (experimental) ───────────────────────────────

    async def media_get_players(self) -> list[dict[str, Any]]:
        """Get all media players via CDP Media domain."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Media.enable", {})
        players: list[dict[str, Any]] = []
        try:
            events = await self._session.collect_events(
                "Media.playerCreated", timeout=1000
            )
            for ev in events:
                players.append(dict(ev.get("player", ev)))
        except Exception:
            pass
        return players

    async def media_get_messages(self, player_id: str) -> list[dict[str, Any]]:
        """Get messages for a specific media player via CDP Media domain."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Media.enable", {})
        messages: list[dict[str, Any]] = []
        try:
            events = await self._session.collect_events(
                "Media.playerMessage", timeout=1000
            )
            for ev in events:
                if ev.get("playerId") == player_id:
                    messages.append(dict(ev))
        except Exception:
            pass
        return messages

    # ── Cast (experimental) ────────────────────────────────

    async def cast_list(self) -> list[dict[str, Any]]:
        """List available cast sinks via CDP Cast domain."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Cast.enable", {})
        result = await self._session.send("Cast.getSupportedSinks", {})
        sinks = result.get("sinks", [])
        return [dict(s) for s in sinks] if sinks else []

    async def cast_start_tab(self, sink_name: str) -> None:
        """Start tab mirroring to a cast sink via CDP Cast domain."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Cast.enable", {})
        await self._session.send(
            "Cast.startTabMirroring",
            {"sinkName": sink_name},
        )

    async def cast_stop(self) -> None:
        """Stop active cast mirroring via CDP Cast domain."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("Cast.enable", {})
        await self._session.send("Cast.stopCasting", {})

    # ── Bluetooth (experimental) ───────────────────────────

    async def bluetooth_emulate(
        self, name: str, address: str = "00:00:00:00:00:01"
    ) -> None:
        """Emulate a Bluetooth Low Energy device via CDP BluetoothEmulation domain."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("BluetoothEmulation.enable", {})
        await self._session.send(
            "BluetoothEmulation.simulatePreconnected",
            {"name": name, "address": address},
        )

    async def bluetooth_stop(self) -> None:
        """Stop Bluetooth emulation via CDP BluetoothEmulation domain."""
        if self._session is None:
            raise NavigationError("", "Session not initialized.")
        await self._session.send("BluetoothEmulation.disable", {})

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
