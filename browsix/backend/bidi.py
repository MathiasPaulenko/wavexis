"""WebDriver BiDi backend using bidiwave.

Supports launch, navigate, screenshot, eval, raw, close, and BiDi paridad
for navigation, tabs, DOM, storage, contexts, window bounds, dialogs, and permissions.
Experimental CDP domains (WebAuthn, WebAudio, Media, Cast, Bluetooth) raise
NotImplementedError — use --backend cdp for those features.
"""

from __future__ import annotations

import base64
from typing import Any

from browsix.backend.base import AbstractBackend
from browsix.config import (
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

try:
    from bidiwave import BiDiClient  # type: ignore[import-not-found,unused-ignore]
except ImportError:
    BiDiClient = None


class BiDiBackend(AbstractBackend):
    """WebDriver BiDi backend via bidiwave.

    Supports: launch, navigate, screenshot, screenshot_selector, eval, raw,
    close, go_back, go_forward, reload, stop_loading, wait_for, list_tabs,
    new_tab, close_tab, activate_tab, capture_console, capture_logs,
    DOM methods, storage methods, cookies (get/set/delete/clear),
    set_headers, set_user_agent, browser_version, set_viewport,
    set_geolocation, set_timezone, set_dark_mode, set_locale,
    set_touch_emulation, new_context, list_contexts, close_context,
    get_window_bounds, set_window_bounds, dialog_accept, dialog_dismiss,
    grant_permission, reset_permissions, click, type_text, fill,
    select_option, hover, key_press, drag, tap, block_requests,
    throttle_network, set_cache_disabled, intercept_requests, mock_response.

    CDP-only features (HAR, PDF, screencast, a11y, downloads, security,
    CPU throttle, sensors, performance, CSS, debug, DOM snapshot, overlay,
    cache storage, IndexedDB, service workers, animations, WebAuthn,
    WebAudio, Media, Cast, Bluetooth) raise NotImplementedError.
    """

    def __init__(self) -> None:
        if BiDiClient is None:
            raise ImportError(
                "bidiwave is not installed. Run: pip install browsix[bidi]"
            )
        self._client: BiDiClient | None = None
        self._context: Any = None

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
        import json as _json
        rect = _json.loads(rect_str) if isinstance(rect_str, str) else rect_str
        clip = {
            "x": int(rect.get("x", 0)),
            "y": int(rect.get("y", 0)),
            "width": int(rect.get("width", 0)),
            "height": int(rect.get("height", 0)),
        }
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
        raise NotImplementedError("pdf is not supported by BiDiBackend")

    async def screencast(self, params: ScreencastParams) -> list[bytes]:
        raise NotImplementedError("screencast is not supported by BiDiBackend")

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

    async def capture_har(self, params: HarParams) -> dict[str, Any]:
        raise NotImplementedError("capture_har is not supported by BiDiBackend")

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
            expires=params.expires,
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
        raise NotImplementedError("emulate_device is not supported by BiDiBackend")

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

    async def click(
        self, selector: str, button: str = "left", click_count: int = 1
    ) -> None:
        """Click an element via BiDi script.evaluate."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
        js = (
            f"document.querySelector('{escaped}')"
            f".dispatchEvent(new MouseEvent('click',{{bubbles:true}}))"
        )
        for _ in range(click_count):
            await self._client.script.evaluate(self._context, js)

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

    async def fill(self, selector: str, value: str) -> None:
        """Fill an input element with a value via BiDi."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
        escaped_val = value.replace("\\", "\\\\").replace("'", "\\'")
        js = f"document.querySelector('{escaped}').value = '{escaped_val}'"
        await self._client.script.evaluate(self._context, js)

    async def select_option(self, selector: str, value: str) -> None:
        """Select an option in a <select> element by value via BiDi."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
        escaped_val = value.replace("\\", "\\\\").replace("'", "\\'")
        js = f"document.querySelector('{escaped}').value = '{escaped_val}'"
        await self._client.script.evaluate(self._context, js)

    async def hover(self, selector: str) -> None:
        """Hover over an element via BiDi script.evaluate."""
        if self._client is None or self._context is None:
            raise RuntimeError("BiDiBackend not launched. Call launch() first.")
        escaped = selector.replace("'", "\\'")
        js = (
            f"var el=document.querySelector('{escaped}');"
            f"el.dispatchEvent(new MouseEvent('mouseover',{{bubbles:true}}));"
            f"el.dispatchEvent(new MouseEvent('mousemove',{{bubbles:true}}))"
        )
        await self._client.script.evaluate(self._context, js)

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

    # ── Network advanced ───────────────────────────────────

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
        raise NotImplementedError("a11y_tree is not supported by BiDiBackend")

    async def a11y_node(self, node_id: str) -> dict[str, Any]:
        raise NotImplementedError("a11y_node is not supported by BiDiBackend")

    async def a11y_ancestors(self, node_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError("a11y_ancestors is not supported by BiDiBackend")

    # ── Downloads ──────────────────────────────────────────

    async def intercept_download(self, pattern: str = ".*") -> bytes:
        raise NotImplementedError("intercept_download is not supported by BiDiBackend")

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
        raise NotImplementedError("get_security_state is not supported by BiDiBackend")

    async def ignore_cert_errors(self, ignore: bool = True) -> None:
        raise NotImplementedError("ignore_cert_errors is not supported by BiDiBackend")

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
        raise NotImplementedError("set_cpu_throttle is not supported by BiDiBackend")

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
        raise NotImplementedError("set_sensors is not supported by BiDiBackend")

    # ── Performance ───────────────────────────────────────

    async def perf_metrics(self) -> dict[str, Any]:
        raise NotImplementedError("perf_metrics is not supported by BiDiBackend")

    async def perf_trace(self, duration_ms: int = 3000) -> dict[str, Any]:
        raise NotImplementedError("perf_trace is not supported by BiDiBackend")

    async def perf_profile(self, duration_ms: int = 3000) -> dict[str, Any]:
        raise NotImplementedError("perf_profile is not supported by BiDiBackend")

    async def perf_heap_snapshot(self) -> dict[str, Any]:
        raise NotImplementedError(
            "perf_heap_snapshot is not supported by BiDiBackend"
        )

    async def perf_coverage(self) -> dict[str, Any]:
        raise NotImplementedError("perf_coverage is not supported by BiDiBackend")

    async def perf_css_coverage(self) -> dict[str, Any]:
        raise NotImplementedError(
            "perf_css_coverage is not supported by BiDiBackend"
        )

    # ── CSS ────────────────────────────────────────────────

    async def css_get_styles(self, selector: str) -> dict[str, Any]:
        raise NotImplementedError("css_get_styles is not supported by BiDiBackend")

    async def css_get_stylesheets(self) -> list[dict[str, Any]]:
        raise NotImplementedError(
            "css_get_stylesheets is not supported by BiDiBackend"
        )

    async def css_get_rules(self, stylesheet_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError("css_get_rules is not supported by BiDiBackend")

    async def css_get_computed(self, selector: str) -> dict[str, Any]:
        raise NotImplementedError(
            "css_get_computed is not supported by BiDiBackend"
        )

    # ── Debugging ──────────────────────────────────────────

    async def debug_set_breakpoint(
        self, url: str, line: int, condition: str | None = None
    ) -> str:
        raise NotImplementedError(
            "debug_set_breakpoint is not supported by BiDiBackend"
        )

    async def debug_set_breakpoint_function(self, function_name: str) -> str:
        raise NotImplementedError(
            "debug_set_breakpoint_function is not supported by BiDiBackend"
        )

    async def debug_remove_breakpoint(self, breakpoint_id: str) -> None:
        raise NotImplementedError(
            "debug_remove_breakpoint is not supported by BiDiBackend"
        )

    async def debug_step_over(self) -> None:
        raise NotImplementedError("debug_step_over is not supported by BiDiBackend")

    async def debug_step_into(self) -> None:
        raise NotImplementedError("debug_step_into is not supported by BiDiBackend")

    async def debug_step_out(self) -> None:
        raise NotImplementedError("debug_step_out is not supported by BiDiBackend")

    async def debug_pause(self) -> None:
        raise NotImplementedError("debug_pause is not supported by BiDiBackend")

    async def debug_resume(self) -> None:
        raise NotImplementedError("debug_resume is not supported by BiDiBackend")

    async def debug_get_listeners(self, selector: str) -> list[dict[str, Any]]:
        raise NotImplementedError(
            "debug_get_listeners is not supported by BiDiBackend"
        )

    # ── DOM Snapshot ───────────────────────────────────────

    async def dom_snapshot(self) -> dict[str, Any]:
        raise NotImplementedError("dom_snapshot is not supported by BiDiBackend")

    # ── Overlay ────────────────────────────────────────────

    async def overlay_highlight(
        self, selector: str, color: str = "rgba(255,0,0,0.5)"
    ) -> None:
        raise NotImplementedError(
            "overlay_highlight is not supported by BiDiBackend"
        )

    async def overlay_clear(self) -> None:
        raise NotImplementedError("overlay_clear is not supported by BiDiBackend")

    # ── Storage ────────────────────────────────────────────

    async def storage_get(self, key: str, storage_type: str = "local") -> str:
        if self._client is None:
            raise RuntimeError("Session not initialized.")
        if storage_type not in ("local", "session"):
            raise ValueError(
                f"Invalid storage_type: {storage_type}. Must be 'local' or 'session'."
            )
        result = await self._client.send(
            "storage.getDOMStorageItems",
            {"storageType": storage_type, "key": key},
        )
        return str(result.get("value", ""))

    async def storage_set(
        self, key: str, value: str, storage_type: str = "local"
    ) -> None:
        if self._client is None:
            raise RuntimeError("Session not initialized.")
        if storage_type not in ("local", "session"):
            raise ValueError(
                f"Invalid storage_type: {storage_type}. Must be 'local' or 'session'."
            )
        await self._client.send(
            "storage.setDOMStorageItem",
            {"storageType": storage_type, "key": key, "value": value},
        )

    async def storage_clear(self, storage_type: str = "local") -> None:
        if self._client is None:
            raise RuntimeError("Session not initialized.")
        if storage_type not in ("local", "session"):
            raise ValueError(
                f"Invalid storage_type: {storage_type}. Must be 'local' or 'session'."
            )
        await self._client.send(
            "storage.clearDOMStorageItems",
            {"storageType": storage_type},
        )

    async def storage_list(self, storage_type: str = "local") -> dict[str, str]:
        if self._client is None:
            raise RuntimeError("Session not initialized.")
        if storage_type not in ("local", "session"):
            raise ValueError(
                f"Invalid storage_type: {storage_type}. Must be 'local' or 'session'."
            )
        result = await self._client.send(
            "storage.getDOMStorageItems",
            {"storageType": storage_type},
        )
        items: dict[str, str] = {}
        for entry in result.get("entries", []):
            if len(entry) >= 2:
                items[str(entry[0])] = str(entry[1])
        return items

    async def cache_storage_list(self) -> list[str]:
        raise NotImplementedError("cache_storage_list is not supported by BiDiBackend")

    async def cache_storage_entries(self, cache_name: str) -> list[dict[str, Any]]:
        raise NotImplementedError(
            "cache_storage_entries is not supported by BiDiBackend"
        )

    async def cache_storage_delete(self, cache_name: str) -> None:
        raise NotImplementedError(
            "cache_storage_delete is not supported by BiDiBackend"
        )

    async def indexeddb_list(self) -> list[dict[str, Any]]:
        raise NotImplementedError("indexeddb_list is not supported by BiDiBackend")

    async def indexeddb_get_data(
        self, database: str, store: str, key: str = ""
    ) -> Any:
        raise NotImplementedError(
            "indexeddb_get_data is not supported by BiDiBackend"
        )

    async def indexeddb_clear(self, database: str, store: str) -> None:
        raise NotImplementedError("indexeddb_clear is not supported by BiDiBackend")

    # ── Service Workers ────────────────────────────────────

    async def sw_list(self) -> list[dict[str, Any]]:
        raise NotImplementedError("sw_list is not supported by BiDiBackend")

    async def sw_unregister(self, registration_id: str) -> None:
        raise NotImplementedError("sw_unregister is not supported by BiDiBackend")

    async def sw_update(self, registration_id: str) -> None:
        raise NotImplementedError("sw_update is not supported by BiDiBackend")

    # ── Animations ─────────────────────────────────────────

    async def animation_list(self) -> list[dict[str, Any]]:
        raise NotImplementedError("animation_list is not supported by BiDiBackend")

    async def animation_pause(self, animation_id: str) -> None:
        raise NotImplementedError("animation_pause is not supported by BiDiBackend")

    async def animation_play(self, animation_id: str) -> None:
        raise NotImplementedError("animation_play is not supported by BiDiBackend")

    async def animation_seek(self, animation_id: str, time_ms: int) -> None:
        raise NotImplementedError("animation_seek is not supported by BiDiBackend")

    # ── WebAuthn (experimental) — not supported by BiDi ────

    async def webauthn_add_virtual_authenticator(
        self, protocol: str, transport: str
    ) -> str:
        raise NotImplementedError(
            "webauthn_add_virtual_authenticator is not supported by BiDiBackend. "
            "Use --backend cdp."
        )

    async def webauthn_remove_authenticator(self, authenticator_id: str) -> None:
        raise NotImplementedError(
            "webauthn_remove_authenticator is not supported by BiDiBackend. "
            "Use --backend cdp."
        )

    async def webauthn_add_credential(
        self, authenticator_id: str, credential: dict[str, Any]
    ) -> None:
        raise NotImplementedError(
            "webauthn_add_credential is not supported by BiDiBackend. "
            "Use --backend cdp."
        )

    async def webauthn_get_credentials(
        self, authenticator_id: str
    ) -> list[dict[str, Any]]:
        raise NotImplementedError(
            "webauthn_get_credentials is not supported by BiDiBackend. "
            "Use --backend cdp."
        )

    # ── WebAudio (experimental) — not supported by BiDi ────

    async def webaudio_get_contexts(self) -> list[dict[str, Any]]:
        raise NotImplementedError(
            "webaudio_get_contexts is not supported by BiDiBackend. "
            "Use --backend cdp."
        )

    async def webaudio_get_context(self, context_id: str) -> dict[str, Any]:
        raise NotImplementedError(
            "webaudio_get_context is not supported by BiDiBackend. "
            "Use --backend cdp."
        )

    # ── Media (experimental) — not supported by BiDi ───────

    async def media_get_players(self) -> list[dict[str, Any]]:
        raise NotImplementedError(
            "media_get_players is not supported by BiDiBackend. "
            "Use --backend cdp."
        )

    async def media_get_messages(self, player_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError(
            "media_get_messages is not supported by BiDiBackend. "
            "Use --backend cdp."
        )

    # ── Cast (experimental) — not supported by BiDi ────────

    async def cast_list(self) -> list[dict[str, Any]]:
        raise NotImplementedError(
            "cast_list is not supported by BiDiBackend. "
            "Use --backend cdp."
        )

    async def cast_start_tab(self, sink_name: str) -> None:
        raise NotImplementedError(
            "cast_start_tab is not supported by BiDiBackend. "
            "Use --backend cdp."
        )

    async def cast_stop(self) -> None:
        raise NotImplementedError(
            "cast_stop is not supported by BiDiBackend. "
            "Use --backend cdp."
        )

    # ── Bluetooth (experimental) — not supported by BiDi ───

    async def bluetooth_emulate(
        self, name: str, address: str = "00:00:00:00:00:01"
    ) -> None:
        raise NotImplementedError(
            "bluetooth_emulate is not supported by BiDiBackend. "
            "Use --backend cdp."
        )

    async def bluetooth_stop(self) -> None:
        raise NotImplementedError(
            "bluetooth_stop is not supported by BiDiBackend. "
            "Use --backend cdp."
        )
