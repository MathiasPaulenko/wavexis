"""CDP backend implementation using cdpwave."""

from __future__ import annotations

import asyncio
import base64
import binascii
import contextlib
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from wavexis import __version__
from wavexis.backend._trace import extract_trace_events, read_trace_stream
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
    _validate_url,
)
from wavexis.exceptions import (
    ElementNotFoundError,
    NavigationError,
    SessionNotInitializedError,
    WaitTimeoutError,
    WavexisError,
)
from wavexis.output import validate_path

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT = 30.0

try:
    from cdpwave import CDPClient, CDPSession
except ImportError:
    CDPClient = None  # type: ignore[assignment,misc]
    CDPSession = None  # type: ignore[assignment,misc]


def _safe_json_loads(value: Any, default: Any = None) -> Any:
    """Parse a JSON string or pass through an already-parsed structure safely.

    Returns ``default`` when the value is missing, not a string, or cannot be
    parsed as JSON. This avoids raising from remote scripts that return null
    or malformed JSON.
    """
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str) or not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def _b64decode(data: Any) -> bytes:
    """Decode base64 data safely, returning empty bytes for missing/invalid values."""
    if not data:
        return b""
    if isinstance(data, bytes):
        return data
    if not isinstance(data, str):
        return b""
    try:
        return base64.b64decode(data)
    except (binascii.Error, TypeError, ValueError):
        return b""


class CDPBackend(AbstractBackend):
    """Chrome DevTools Protocol backend via cdpwave."""

    def __init__(self) -> None:
        """Initialize the CDP backend.

        Raises:
            ImportError: If cdpwave is not installed.
        """
        if CDPClient is None:
            raise ImportError("cdpwave is not installed. Run: pip install wavexis[cdp]")
        self._client: CDPClient | None = None
        self._session: CDPSession | None = None
        self._console_entries: list[dict[str, Any]] = []
        self._log_entries: list[dict[str, Any]] = []
        self._current_url: str = ""
        self._subscriptions: dict[str, dict[str, Any]] = {}
        self._combined_traces: dict[str, dict[str, Any]] = {}
        self._subscription_counter = 0
        self._trace_counter = 0

    async def new_tab_handle(self, url: str = "about:blank") -> TabHandle:
        """Create a new tab with its own session, sharing the browser process.

        Args:
            url: Initial URL for the new tab.

        Returns:
            A TabHandle that can be used like a CDPBackend for concurrent operations.

        Raises:
            SessionNotInitializedError: If launch() has not been called.
        """
        if self._client is None:
            raise SessionNotInitializedError("Backend not launched. Call launch() first.")
        session = await self._client.new_page(url)
        return TabHandle(self._client, session)

    def _require_session(self) -> CDPSession:
        """Return the current session or raise if not initialized.

        Returns:
            The active CDPSession instance.

        Raises:
            SessionNotInitializedError: If launch() has not been called.
        """
        if self._session is None:
            raise SessionNotInitializedError("Session not initialized. Call launch() first.")
        return self._session

    @staticmethod
    async def _send_cdp(
        session: CDPSession, method: str, params: dict[str, Any] | None = None
    ) -> Any:
        """Send a CDP command and translate "method not found" / "not allowed"
        errors into a friendly :class:`WavexisError`.

        Chrome removes CDP domains between versions (e.g. ``Tethering``,
        ``WebMcp``, ``HeadlessExperimental``, ``Extensions``,
        ``BluetoothEmulation``, ``SmartCardEmulation``,
        ``Browser.getPreference``, ``Security.getVisibleSecurityState``).
        Without this wrapper the user sees a raw
        ``CommandError: [-32601] '<Domain.method>' wasn't found`` traceback;
        with it they get a one-line message that explains the cause.

        Args:
            session: The active CDPSession.
            method: The CDP method name (e.g. ``"Tethering.bind"``).
            params: Optional command parameters.

        Returns:
            The CDP response result dict.

        Raises:
            WavexisError: If the CDP response indicates the method or
                domain is not supported by the current browser.
        """
        from cdpwave.exceptions import CommandError, CommandTimeoutError

        try:
            return await session.send(method, params or {})
        except CommandError as e:
            msg = str(e)
            # -32601: "Method 'X' wasn't found" — domain/method removed.
            # -32000: "Not allowed" / "only supported on the browser target".
            if e.code == -32601 or "wasn't found" in msg or "not found" in msg:
                raise WavexisError(
                    f"CDP method '{method}' is not supported by the current "
                    f"Chrome/Edge version. This domain was removed or never "
                    f"exposed by this browser. (CDP error: {msg})"
                ) from e
            raise
        except CommandTimeoutError as e:
            # Some removed CDP domains (e.g. HeadlessExperimental) don't
            # return -32601 — Chrome simply never responds, causing a
            # timeout. Treat that as "not supported" too.
            raise WavexisError(
                f"CDP method '{method}' did not respond within the timeout. "
                f"This domain was likely removed by the current Chrome/Edge "
                f"version and the browser silently drops the command. "
                f"(CDP error: {e})"
            ) from e

    def _require_client(self) -> CDPClient:
        """Return the browser-level CDPClient or raise if not initialized.

        Use this for commands that must be sent to the browser target
        (e.g. ``Target.getBrowserContexts``, ``SystemInfo.getInfo``)
        rather than to a page session.

        Returns:
            The active CDPClient instance.

        Raises:
            SessionNotInitializedError: If launch() has not been called.
        """
        if self._client is None:
            raise SessionNotInitializedError("Backend not launched. Call launch() first.")
        return self._client

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

        # CI runners often have a small /dev/shm and a strict sandbox; cdpwave
        # already adds --no-sandbox when CI env vars are present, but these
        # companion flags prevent additional launch failures on GitHub Actions.
        if os.environ.get("CI"):
            extra_args.extend(
                [
                    "--disable-dev-shm-usage",
                    "--no-zygote",
                ]
            )

        if options.browser_url:
            from urllib.parse import urlparse

            parsed = urlparse(options.browser_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 9222
            self._client = await asyncio.wait_for(
                CDPClient.connect(host=host, port=port), timeout=_CONNECT_TIMEOUT
            )
        elif options.remote_url:
            self._client = await asyncio.wait_for(
                CDPClient.connect(ws_url=options.remote_url), timeout=_CONNECT_TIMEOUT
            )
        else:
            launch_timeout = 30.0 if os.environ.get("CI") else 10.0
            self._client = await CDPClient.launch(
                headless=options.headless,
                user_data_dir=options.user_data_dir,  # type: ignore[call-arg]
                extra_args=extra_args if extra_args else None,
                timeout=launch_timeout,
            )

        client = self._client
        try:
            # Bug #28: when connecting to an already-running browser via
            # ``--browser-url`` or ``--remote-url``, ``client.new_page()``
            # creates a brand-new tab. The user expects commands like
            # ``navigate`` to operate on the tab they already have open.
            # We instead attach to the first existing page target (or
            # fall back to creating a new one if the browser has none).
            if options.browser_url or options.remote_url:
                try:
                    pages = await client.get_pages()
                except Exception:
                    pages = []
                if pages:
                    # Prefer a non-devtools, non-blank page if available.
                    non_blank = [
                        p
                        for p in pages
                        if p.url and not p.url.startswith("devtools://") and p.url != "about:blank"
                    ]
                    target = non_blank[0] if non_blank else pages[0]
                    # TargetInfo uses ``target_id``, not ``id``.
                    target_id = getattr(target, "target_id", None) or getattr(target, "id", None)
                    if not target_id:
                        raise WavexisError(
                            "Could not determine target id of the existing page. "
                            "Use `wavexis navigate <url>` without --browser-url to "
                            "open a fresh page."
                        )
                    self._session = await client.connect_to_page(str(target_id))
                else:
                    self._session = await client.new_page()
            else:
                self._session = await client.new_page()

            if options.user_agent:
                await self._session.emulation.set_user_agent_override(user_agent=options.user_agent)

            if options.extra_headers:
                await self._session.network.set_extra_http_headers(options.extra_headers)

            if options.stealth:
                from wavexis.actions.stealth import get_stealth_js

                await self._session.runtime.evaluate(get_stealth_js(), await_promise=False)
        except Exception:
            self._session = None
            self._client = None
            with contextlib.suppress(Exception):
                await client.close()
            raise

    async def close(self) -> None:
        """Close the browser client and release resources."""
        if self._session is not None:
            for handlers in self._subscriptions.values():
                for cdp_event, handler in handlers.items():
                    with contextlib.suppress(Exception):
                        self._session.off(cdp_event, handler)
            self._subscriptions.clear()
            await self._session.close()
            self._session = None
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def navigate(self, url: str, wait: WaitStrategy | None = None) -> None:
        """Navigate to a URL and optionally wait for a condition.

        If the backend has not been launched yet, it will be launched with
        default options. This is a convenience fallback used by actions and
        integration tests that request a backend fixture without calling
        ``launch()`` explicitly.

        Args:
            url: The URL to navigate to.
            wait: Wait strategy to apply after navigation.

        Raises:
            SessionNotInitializedError: If launch() has not been called.
            WaitTimeoutError: If the wait strategy times out.
        """
        _validate_url(url, allow_empty=False)
        if self._session is None:
            await self.launch(BrowserOptions())
        session = self._require_session()

        timeout_ms: int = wait.timeout if wait is not None else 30000
        timeout_sec: float = timeout_ms / 1000

        await session.page.enable()
        await session.send("Page.setLifecycleEventsEnabled", {"enabled": True})
        await session.page.navigate(url)
        self._current_url = url

        if wait is None or wait.strategy == "load":
            try:
                await session.wait_for_load_state("load", timeout=timeout_sec)
            except TimeoutError:
                raise WaitTimeoutError("load", timeout_ms) from None
        elif wait.strategy == "none":
            pass
        elif wait.strategy == "selector":
            if wait.selector is None:
                raise ValueError("selector wait strategy requires a selector")
            deadline = time.monotonic() + timeout_sec
            js = f"document.querySelector({json.dumps(wait.selector)}) !== null"
            while time.monotonic() < deadline:
                result = await session.runtime.evaluate(js, await_promise=False)
                if result.get("result", {}).get("value", False):
                    break
                await asyncio.sleep(0.1)
            else:
                raise WaitTimeoutError("selector", timeout_ms) from None
        elif wait.strategy == "domcontentloaded":
            try:
                await session.wait_for_load_state("domcontentloaded", timeout=timeout_sec)
            except TimeoutError:
                raise WaitTimeoutError("domcontentloaded", timeout_ms) from None
        elif wait.strategy == "networkidle":
            try:
                await session.wait_for_network_idle(idle_time=0.5, timeout=timeout_sec)
            except TimeoutError:
                raise WaitTimeoutError("networkidle", timeout_ms) from None
        elif wait.strategy == "url":
            if not wait.url_pattern:
                raise ValueError("url wait strategy requires a url_pattern")
            deadline = time.monotonic() + timeout_sec
            while time.monotonic() < deadline:
                result = await session.runtime.evaluate("window.location.href")
                href = result.get("result", {}).get("value", "") or ""
                if wait.url_pattern in href:
                    break
                await asyncio.sleep(0.1)
            else:
                raise WaitTimeoutError("url", timeout_ms) from None

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
            )
            if preset.get("user_agent"):
                await session.emulation.set_user_agent_override(
                    user_agent=str(preset["user_agent"]),
                )
            if preset.get("touch"):
                await session.emulation.set_touch_emulation_enabled(True)

        result = await session.page.capture_screenshot(
            format=params.format,
            quality=params.quality,
            capture_beyond_viewport=params.full_page,
        )
        data_b64 = result.get("data", "") if result else ""
        return _b64decode(data_b64)

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
        if not doc:
            raise ElementNotFoundError(selector)
        root_node_id = doc.get("root", {}).get("nodeId", 0)
        node = await session.dom.query_selector(root_node_id, selector)
        if not node:
            raise ElementNotFoundError(selector)
        node_id = node.get("nodeId", 0)
        if node_id == 0:
            raise ElementNotFoundError(selector)
        box = await session.dom.get_box_model(node_id)
        if not box:
            raise NavigationError(selector, "Could not determine element bounds.")
        model = box.get("model", {})
        borders = model.get("border", [])
        if len(borders) >= 8 and all(isinstance(b, (int, float)) for b in borders):
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
        data_b64 = result.get("data", "") if result else ""
        return _b64decode(data_b64)

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
        session = self._require_session()
        js = self._annotate_js(selectors)
        result = await session.runtime.evaluate(js)
        raw = (result or {}).get("result", {}).get("value")
        label_map = _safe_json_loads(raw, {})
        if not isinstance(label_map, dict):
            label_map = {}
        screenshot = await session.page.capture_screenshot(format=format)
        await session.runtime.evaluate(self._remove_annotate_js())
        data_b64 = screenshot.get("data", "") if screenshot else ""
        return _b64decode(data_b64), label_map

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
            await session.page.navigate_to_history_entry(prev_entry.get("id", 0))

    async def go_forward(self) -> None:
        """Navigate forward in browser history."""
        session = self._require_session()
        history = await session.page.get_navigation_history()
        current_idx = history.get("currentIndex", 0)
        entries = history.get("entries", [])
        if current_idx < len(entries) - 1:
            next_entry = entries[current_idx + 1]
            await session.page.navigate_to_history_entry(next_entry.get("id", 0))

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

    # ── Page lifecycle ─────────────────────────────────────

    async def page_get_frame_tree(self) -> dict[str, Any]:
        """Get the current page frame tree."""
        session = self._require_session()
        return dict(await session.page.get_frame_tree())

    async def page_get_layout_metrics(self) -> dict[str, Any]:
        """Get page layout metrics (viewport, content size, etc.)."""
        session = self._require_session()
        return dict(await session.page.get_layout_metrics())

    async def page_get_navigation_history(self) -> dict[str, Any]:
        """Get the navigation history for the current page."""
        session = self._require_session()
        return dict(await session.page.get_navigation_history())

    async def page_navigate_to_history_entry(self, entry_id: int) -> None:
        """Navigate to a specific history entry by ID."""
        session = self._require_session()
        await session.page.navigate_to_history_entry(entry_id)

    async def page_bring_to_front(self) -> None:
        """Bring the current page to the foreground."""
        session = self._require_session()
        await session.page.bring_to_front()

    async def page_wait_for_debugger(self) -> None:
        """Wait for the debugger to attach."""
        session = self._require_session()
        await session.page.wait_for_debugger()

    async def page_get_resource_content(self, frame_id: str, url: str) -> dict[str, Any]:
        """Get the content of a page resource by frame ID and URL."""
        session = self._require_session()
        return dict(await session.page.get_resource_content(frame_id, url))

    async def page_set_download_behavior(self, behavior: str, download_path: str = "") -> None:
        """Set page download behavior (allow/deny and path).

        Bug #25: previously this built a ``{"downloadPath": ...}`` dict and
        unpacked it into ``session.page.set_download_behavior(**params)``,
        but cdpwave's wrapper expects the snake_case ``download_path``
        keyword argument. The camelCase key caused
        ``TypeError: ... got an unexpected keyword argument 'downloadPath'``.
        """
        session = self._require_session()
        await session.page.set_download_behavior(
            behavior=behavior,
            download_path=download_path or None,
        )

    async def page_capture_snapshot(self, format: str = "mhtml") -> str:
        """Capture a snapshot of the page as MHTML or text."""
        session = self._require_session()
        result = await session.page.capture_snapshot(format=format)
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
        """Print the page to PDF and return base64-encoded data."""
        session = self._require_session()
        result = await session.page.print_to_pdf(
            landscape=landscape,
            display_header_footer=display_header_footer,
            print_background=print_background,
            scale=scale,
            paper_width=paper_width,
            paper_height=paper_height,
            margin_top=margin_top,
            margin_bottom=margin_bottom,
            margin_left=margin_left,
            margin_right=margin_right,
        )
        return str(result.get("data", ""))

    async def page_start_screencast(
        self, format: str = "jpeg", quality: int = 80, max_width: int = 0, max_height: int = 0
    ) -> None:
        """Start screencasting the page."""
        session = self._require_session()
        await session.page.start_screencast(
            format=format, quality=quality, max_width=max_width, max_height=max_height
        )

    async def page_stop_screencast(self) -> None:
        """Stop screencasting the page."""
        session = self._require_session()
        await session.page.stop_screencast()

    async def page_set_bypass_csp(self, enabled: bool) -> None:
        """Enable or disable CSP bypass for the page."""
        session = self._require_session()
        await session.page.set_bypass_csp(enabled)

    async def page_set_ad_blocking_enabled(self, enabled: bool) -> None:
        """Enable or disable ad blocking for the page."""
        session = self._require_session()
        await session.page.set_ad_blocking_enabled(enabled)

    async def page_add_script_to_evaluate_on_new_document(
        self, source: str, world_name: str = ""
    ) -> str:
        """Add a script to evaluate on every new document. Returns script ID."""
        session = self._require_session()
        params: dict[str, Any] = {"source": source}
        if world_name:
            params["worldName"] = world_name
        result = await session.page.add_script_to_evaluate_on_new_document(**params)
        return str(result.get("identifier", ""))

    async def page_remove_script_to_evaluate_on_new_document(self, script_id: str) -> None:
        """Remove a previously added script by ID."""
        session = self._require_session()
        await session.page.remove_script_to_evaluate_on_new_document(identifier=script_id)

    async def page_generate_test_report(self, message: str, group: str = "") -> None:
        """Generate a test report for the Reporting API."""
        session = self._require_session()
        params: dict[str, Any] = {"message": message}
        if group:
            params["group"] = group
        await session.page.generate_test_report(**params)

    async def page_get_app_manifest(self) -> dict[str, Any]:
        """Get the web app manifest for the current page."""
        session = self._require_session()
        return dict(await session.page.get_app_manifest())

    async def page_get_resource_tree(self) -> dict[str, Any]:
        """Get the resource tree for the current page."""
        session = self._require_session()
        return dict(await session.page.get_resource_tree())

    async def page_add_compilation_cache(self, url: str, data: str) -> None:
        """Add data to the compilation cache for the given URL."""
        session = self._require_session()
        await session.send("Page.addCompilationCache", {"url": url, "data": data})

    async def page_add_script_to_evaluate_on_load(self, source: str) -> str:
        """Add a script to evaluate on page load. Returns script ID."""
        session = self._require_session()
        result = await session.send("Page.addScriptToEvaluateOnLoad", {"source": source})
        return str(result.get("identifier", "")) if result else ""

    async def page_capture_screenshot(
        self,
        format: str = "png",
        quality: int = 80,
        clip: dict[str, Any] | None = None,
        from_surface: bool = True,
        capture_beyond_viewport: bool = False,
    ) -> str:
        """Capture a screenshot of the page. Returns base64-encoded data."""
        session = self._require_session()
        params: dict[str, Any] = {
            "format": format,
            "quality": quality,
            "fromSurface": from_surface,
            "captureBeyondViewport": capture_beyond_viewport,
        }
        if clip is not None:
            params["clip"] = clip
        result = await session.send("Page.captureScreenshot", params)
        return str(result.get("data", "")) if result else ""

    async def page_clear_compilation_cache(self) -> None:
        """Clear the compilation cache."""
        session = self._require_session()
        await session.send("Page.clearCompilationCache", {})

    async def page_clear_device_orientation_override(self) -> None:
        """Clear the device orientation override."""
        session = self._require_session()
        await session.send("Page.clearDeviceOrientationOverride", {})

    async def page_clear_geolocation_override(self) -> None:
        """Clear the geolocation overrides."""
        session = self._require_session()
        await session.send("Page.clearGeolocationOverride", {})

    async def page_crash(self) -> None:
        """Crash the renderer."""
        session = self._require_session()
        await session.send("Page.crash", {})

    async def page_create_isolated_world(
        self, frame_id: str, world_name: str = "", grant_universal_access: bool = False
    ) -> str:
        """Create an isolated world for the given frame. Returns execution context ID."""
        session = self._require_session()
        params: dict[str, Any] = {
            "frameId": frame_id,
            "grantUniversalAccess": grant_universal_access,
        }
        if world_name:
            params["worldName"] = world_name
        result = await session.send("Page.createIsolatedWorld", params)
        return str(result.get("executionContextId", "")) if result else ""

    async def page_disable(self) -> None:
        """Disable the page domain."""
        session = self._require_session()
        await session.send("Page.disable", {})

    async def page_enable(self) -> None:
        """Enable the page domain."""
        session = self._require_session()
        await session.send("Page.enable", {})

    async def page_get_ad_script_ancestry(self, frame_id: str) -> dict[str, Any]:
        """Get the ad script ancestry for a frame."""
        session = self._require_session()
        result = await session.send("Page.getAdScriptAncestry", {"frameId": frame_id})
        return dict(result) if result else {}

    async def page_get_annotated_page_content(self) -> dict[str, Any]:
        """Get annotated page content."""
        session = self._require_session()
        result = await session.send("Page.getAnnotatedPageContent", {})
        return dict(result) if result else {}

    async def page_get_app_id(self) -> dict[str, Any]:
        """Get the app ID for the current page."""
        session = self._require_session()
        result = await session.send("Page.getAppId", {})
        return dict(result) if result else {}

    async def page_get_installability_errors(self) -> dict[str, Any]:
        """Get installability errors for the current page."""
        session = self._require_session()
        result = await session.send("Page.getInstallabilityErrors", {})
        return dict(result) if result else {}

    async def page_get_manifest_icons(self) -> dict[str, Any]:
        """Get manifest icons for the current page."""
        session = self._require_session()
        result = await session.send("Page.getManifestIcons", {})
        return dict(result) if result else {}

    async def page_get_origin_trials(self) -> dict[str, Any]:
        """Get origin trials for the current page."""
        session = self._require_session()
        result = await session.send("Page.getOriginTrials", {})
        return dict(result) if result else {}

    async def page_get_permissions_policy_state(self, frame_id: str) -> dict[str, Any]:
        """Get permissions policy state for a frame."""
        session = self._require_session()
        result = await session.send("Page.getPermissionsPolicyState", {"frameId": frame_id})
        return dict(result) if result else {}

    async def page_handle_java_script_dialog(self, accept: bool, prompt_text: str = "") -> None:
        """Handle a JavaScript dialog (alias for handle_javascript_dialog)."""
        session = self._require_session()
        params: dict[str, Any] = {"accept": accept}
        if prompt_text:
            params["promptText"] = prompt_text
        await session.send("Page.handleJavaScriptDialog", params)

    async def page_handle_javascript_dialog(self, accept: bool, prompt_text: str = "") -> None:
        """Handle a JavaScript dialog."""
        session = self._require_session()
        params: dict[str, Any] = {"accept": accept}
        if prompt_text:
            params["promptText"] = prompt_text
        await session.send("Page.handleJavaScriptDialog", params)

    async def page_produce_compilation_cache(self, url: str) -> dict[str, Any]:
        """Produce compilation cache for the given URL."""
        session = self._require_session()
        result = await session.send("Page.produceCompilationCache", {"url": url})
        return dict(result) if result else {}

    async def page_remove_script_to_evaluate_on_load(self, script_id: str) -> None:
        """Remove a script previously added to evaluate on load."""
        session = self._require_session()
        await session.send("Page.removeScriptToEvaluateOnLoad", {"identifier": script_id})

    async def page_reset_navigation_history(self) -> None:
        """Reset the navigation history."""
        session = self._require_session()
        await session.send("Page.resetNavigationHistory", {})

    async def page_screencast_frame_ack(self, session_id: int) -> None:
        """Acknowledge a screencast frame."""
        session = self._require_session()
        await session.send("Page.screencastFrameAck", {"sessionId": session_id})

    async def page_search_in_resource(
        self,
        frame_id: str,
        url: str,
        query: str,
        case_sensitive: bool = False,
        is_regex: bool = False,
    ) -> dict[str, Any]:
        """Search for a string in a resource."""
        session = self._require_session()
        params: dict[str, Any] = {
            "frameId": frame_id,
            "url": url,
            "query": query,
            "caseSensitive": case_sensitive,
            "isRegex": is_regex,
        }
        result = await session.send("Page.searchInResource", params)
        return dict(result) if result else {}

    async def page_set_device_orientation_override(
        self, alpha: float, beta: float, gamma: float
    ) -> None:
        """Override the device orientation."""
        session = self._require_session()
        await session.send(
            "Page.setDeviceOrientationOverride", {"alpha": alpha, "beta": beta, "gamma": gamma}
        )

    async def page_set_document_content(self, frame_id: str, html: str) -> None:
        """Set the document content for a frame."""
        session = self._require_session()
        await session.send("Page.setDocumentContent", {"frameId": frame_id, "html": html})

    async def page_set_font_families(self, font_families: dict[str, Any]) -> None:
        """Set font families for the page."""
        session = self._require_session()
        await session.send("Page.setFontFamilies", {"fontFamilies": font_families})

    async def page_set_font_sizes(self, font_sizes: dict[str, Any]) -> None:
        """Set font sizes for the page."""
        session = self._require_session()
        await session.send("Page.setFontSizes", {"fontSizes": font_sizes})

    async def page_set_geolocation_override(
        self, latitude: float = 0.0, longitude: float = 0.0, accuracy: float = 0.0
    ) -> None:
        """Override the geolocation."""
        session = self._require_session()
        await session.send(
            "Page.setGeolocationOverride",
            {"latitude": latitude, "longitude": longitude, "accuracy": accuracy},
        )

    async def page_set_intercept_file_chooser_dialog(self, enabled: bool) -> None:
        """Intercept file chooser dialogs."""
        session = self._require_session()
        await session.send("Page.setInterceptFileChooserDialog", {"enabled": enabled})

    async def page_set_lifecycle_events_enabled(self, enabled: bool) -> None:
        """Enable or disable lifecycle events."""
        session = self._require_session()
        await session.send("Page.setLifecycleEventsEnabled", {"enabled": enabled})

    async def page_set_prerendering_allowed(self, is_allowed: bool) -> None:
        """Set whether prerendering is allowed."""
        session = self._require_session()
        await session.send("Page.setPrerenderingAllowed", {"isAllowed": is_allowed})

    async def page_set_rph_registration_mode(self, mode: str) -> None:
        """Set the RPH registration mode."""
        session = self._require_session()
        await session.send("Page.setRPHRegistrationMode", {"mode": mode})

    async def page_set_spc_transaction_mode(self, mode: str) -> None:
        """Set the SPC transaction mode."""
        session = self._require_session()
        await session.send("Page.setSPCTransactionMode", {"mode": mode})

    async def page_set_touch_emulation_enabled(
        self, enabled: bool, configuration: str = ""
    ) -> None:
        """Enable or disable touch emulation."""
        session = self._require_session()
        params: dict[str, Any] = {"enabled": enabled}
        if configuration:
            params["configuration"] = configuration
        await session.send("Page.setTouchEmulationEnabled", params)

    async def page_set_web_lifecycle_state(self, state: str) -> None:
        """Set the web lifecycle state."""
        session = self._require_session()
        await session.send("Page.setWebLifecycleState", {"state": state})

    async def page_stop(self) -> None:
        """Stop all page loading."""
        session = self._require_session()
        await session.send("Page.stop", {})

    async def wait_for(self, strategy: WaitStrategy) -> None:
        """Wait for a specific condition.

        Args:
            strategy: Wait strategy (selector, load, url).

        Raises:
            WaitTimeoutError: If the condition is not met within the timeout.
        """
        session = self._require_session()

        timeout_ms: int = strategy.timeout
        timeout_sec: float = timeout_ms / 1000

        if strategy.strategy == "none":
            return

        if strategy.strategy == "selector" and strategy.selector:
            try:
                await session.wait_for_selector(strategy.selector, timeout=timeout_sec)
            except TimeoutError:
                raise WaitTimeoutError("selector", timeout_ms) from None
            return

        if strategy.strategy == "load":
            try:
                await session.wait_for_load_state("load", timeout=timeout_sec)
            except TimeoutError:
                raise WaitTimeoutError("load", timeout_ms) from None
            return

        if strategy.strategy == "url" and strategy.url_pattern:
            deadline = time.monotonic() + timeout_sec
            js = "window.location.href"
            while time.monotonic() < deadline:
                result = await session.runtime.evaluate(js)
                href = result.get("result", {}).get("value", "")
                if strategy.url_pattern in href:
                    return
                await asyncio.sleep(0.1)
            raise WaitTimeoutError("url", timeout_ms)

        if strategy.strategy == "domcontentloaded":
            try:
                await session.wait_for_load_state("domcontentloaded", timeout=timeout_sec)
            except TimeoutError:
                raise WaitTimeoutError("domcontentloaded", timeout_ms) from None
            return

        if strategy.strategy == "networkidle":
            try:
                await session.wait_for_network_idle(idle_time=0.5, timeout=timeout_sec)
            except TimeoutError:
                raise WaitTimeoutError("networkidle", timeout_ms) from None
            return

        # If we get here, the strategy is not supported
        raise ValueError(f"Unsupported wait strategy: {strategy.strategy}")

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
        margin_match = re.match(r"([\d.]+)", params.margin)
        margin_val = float(margin_match.group(1)) if margin_match else 0.4

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
        data_b64 = result.get("data", "") if result else ""
        return _b64decode(data_b64)

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
                frames.append(_b64decode(data))

        session.on("Page.screencastFrame", on_frame)

        try:
            await session.send(
                "Page.startScreencast",
                {
                    "format": params.format,
                    "quality": params.quality,
                    "maxWidth": params.max_width,
                    "maxHeight": params.max_height,
                },
            )

            await asyncio.sleep(params.duration)

            await session.send("Page.stopScreencast")
        finally:
            session.off("Page.screencastFrame", on_frame)

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
        _validate_url(url, allow_empty=False)
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
                entries.append(
                    {
                        "type": entry_type,
                        "args": event_params.get("args", []),
                        "executionContextId": event_params.get("executionContextId"),
                        "timestamp": event_params.get("timestamp"),
                    }
                )

        session.on("Runtime.consoleAPICalled", on_console_api)

        try:
            await session.runtime.enable()
            await asyncio.sleep(0.5)
        finally:
            session.off("Runtime.consoleAPICalled", on_console_api)

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
            entries.append(
                {
                    "level": entry.get("level", "info"),
                    "text": entry.get("text", ""),
                    "timestamp": entry.get("timestamp"),
                    "url": entry.get("url"),
                    "lineNumber": entry.get("lineNumber"),
                    "stackTrace": entry.get("stackTrace", []),
                }
            )

        session.on("Log.entryAdded", on_log_entry)

        try:
            await session.log.enable()
            await asyncio.sleep(0.5)
        finally:
            session.off("Log.entryAdded", on_log_entry)

        return entries

    # ── DOM ────────────────────────────────────────────────

    async def _find_node(self, selector: str, timeout: float = 5.0) -> int:
        """Find a node by CSS selector and return its nodeId.

        Retries for up to ``timeout`` seconds to handle race conditions
        where the DOM is not fully ready after navigation.
        """
        session = self._require_session()
        await session.dom.enable()
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        last_error: Exception | None = None
        while True:
            try:
                doc = await session.dom.get_document(depth=-1)
                if not doc:
                    raise ElementNotFoundError(selector)
                root_node_id = doc.get("root", {}).get("nodeId", 0)
                result = await session.dom.query_selector(root_node_id, selector)
                if not result:
                    raise ElementNotFoundError(selector)
                node_id = result.get("nodeId", 0)
                if node_id != 0:
                    return int(node_id)
            except Exception as e:
                last_error = e
            if loop.time() >= deadline:
                break
            await asyncio.sleep(0.25)
        if last_error:
            raise ElementNotFoundError(selector) from last_error
        raise ElementNotFoundError(selector)

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
            return str((result or {}).get("outerHTML", ""))
        result = await session.dom.get_outer_html(node_id)
        outer_html = str((result or {}).get("outerHTML", ""))
        inner = re.sub(r"^<[^>]+>", "", outer_html, count=1)
        inner = re.sub(r"<[^>]+>$", "", inner, count=1)
        return inner

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
        if not doc:
            raise ElementNotFoundError(selector)
        root_node_id = doc.get("root", {}).get("nodeId", 0)

        if all:
            result = await session.dom.query_selector_all(root_node_id, selector)
            if not result:
                return []
            node_ids = result.get("nodeIds", [])
            nodes: list[dict[str, Any]] = []
            for nid in node_ids:
                desc = await session.dom.describe_node(node_id=nid)
                nodes.append((desc or {}).get("node", {}))
            return nodes

        result = await session.dom.query_selector(root_node_id, selector)
        if not result:
            raise ElementNotFoundError(selector)
        node_id = result.get("nodeId", 0)
        if node_id == 0:
            raise ElementNotFoundError(selector)
        desc = await session.dom.describe_node(node_id=node_id)
        return dict((desc or {}).get("node", {}))

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
        value = (result or {}).get("value")
        return str(value) if value is not None else ""

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

    async def dom_scroll(self, selector: str | None = None, x: int = 0, y: int = 0) -> None:
        """Scroll to an element or by offset.

        Args:
            selector: CSS selector to scroll to. If None, scroll by offset.
            x: Horizontal scroll offset.
            y: Vertical scroll offset.
        """
        session = self._require_session()
        if selector:
            escaped = json.dumps(selector)
            js = f"document.querySelector({escaped}).scrollIntoView()"
        else:
            js = f"window.scrollBy({x}, {y})"
        await session.runtime.evaluate(js)

    async def dom_get_document(self) -> dict[str, Any]:
        """Get the document root node."""
        session = self._require_session()
        await session.dom.enable()
        return dict(await session.dom.get_document())

    async def dom_get_flattened_document(self) -> dict[str, Any]:
        """Get the flattened document tree."""
        session = self._require_session()
        await session.dom.enable()
        return dict(await session.dom.get_flattened_document())

    async def dom_get_box_model(self, selector: str) -> dict[str, Any]:
        """Get the box model for an element matching a CSS selector."""
        session = self._require_session()
        node_id = await self._find_node(selector)
        return dict(await session.dom.get_box_model(node_id))

    async def dom_get_content_quads(self, selector: str) -> list[dict[str, Any]]:
        """Get the content quads for an element matching a CSS selector."""
        session = self._require_session()
        node_id = await self._find_node(selector)
        result = await session.dom.get_content_quads(node_id)
        return list(result.get("quads", []))

    async def dom_get_node_for_location(self, x: int, y: int) -> dict[str, Any]:
        """Get the node ID for a location in the viewport (hit testing)."""
        session = self._require_session()
        await session.dom.enable()
        return dict(await session.dom.get_node_for_location(x, y))

    async def dom_perform_search(self, query: str) -> dict[str, Any]:
        """Search the DOM for the given query string."""
        session = self._require_session()
        await session.dom.enable()
        return dict(await session.dom.perform_search(query))

    async def dom_get_search_results(
        self, search_id: str, from_index: int = 0, to_index: int = 0
    ) -> list[dict[str, Any]]:
        """Get search results for a DOM search session."""
        session = self._require_session()
        result = await session.dom.get_search_results(search_id, from_index, to_index)
        return list(result.get("nodeIds", []))

    async def dom_scroll_into_view_if_needed(self, selector: str) -> None:
        """Scroll an element matching a CSS selector into view if needed."""
        session = self._require_session()
        node_id = await self._find_node(selector)
        await session.dom.scroll_into_view_if_needed(node_id)

    async def dom_describe_node(self, node_id: int) -> dict[str, Any]:
        """Describe a DOM node by node ID."""
        session = self._require_session()
        result = await session.dom.describe_node(node_id=node_id)
        return dict(result) if result else {}

    async def dom_get_outer_html(self, node_id: int) -> str:
        """Get the outer HTML of a node by ID."""
        session = self._require_session()
        result = await session.dom.get_outer_html(node_id=node_id)
        return str(result.get("outerHTML", ""))

    async def dom_remove_node(self, node_id: int) -> None:
        """Remove a node from the DOM by ID."""
        session = self._require_session()
        await session.dom.remove_node(node_id=node_id)

    async def dom_set_node_value(self, node_id: int, value: str) -> None:
        """Set the value of a node by ID."""
        session = self._require_session()
        await session.dom.set_node_value(node_id=node_id, value=value)

    async def dom_set_outer_html(self, node_id: int, outer_html: str) -> None:
        """Set the outer HTML of a node by ID."""
        session = self._require_session()
        await session.dom.set_outer_html(node_id=node_id, outer_html=outer_html)

    async def dom_request_node(self, object_id: str) -> int:
        """Request a node by JavaScript object reference and return its node ID."""
        session = self._require_session()
        result = await session.dom.request_node(object_id=object_id)
        return int(result.get("nodeId", 0))

    async def dom_resolve_node(self, node_id: int) -> dict[str, Any]:
        """Resolve a node to a remote object."""
        session = self._require_session()
        result = await session.dom.resolve_node(node_id=node_id)
        return dict(result) if result else {}

    async def dom_set_attribute_value(self, node_id: int, name: str, value: str) -> None:
        """Set an attribute value on a node by ID."""
        session = self._require_session()
        await session.dom.set_attribute_value(node_id=node_id, name=name, value=value)

    async def dom_remove_attribute(self, node_id: int, name: str) -> None:
        """Remove an attribute from a node by ID."""
        session = self._require_session()
        await session.dom.remove_attribute(node_id=node_id, name=name)

    async def dom_request_child_nodes(self, node_id: int, depth: int = -1) -> None:
        """Request child nodes of a node by ID."""
        session = self._require_session()
        await session.dom.request_child_nodes(node_id=node_id, depth=depth)

    async def dom_collect_class_names_from_subtree(self, node_id: int) -> list[str]:
        """Collect class names from the subtree of a node by ID."""
        session = self._require_session()
        result = await session.send("DOM.collectClassNamesFromSubtree", {"nodeId": node_id})
        return list(result.get("classNames", [])) if result else []

    async def dom_copy_to(
        self, node_id: int, target_node_id: int, insert_before_node_id: int | None = None
    ) -> None:
        """Copy a node to a target node, optionally before another node."""
        session = self._require_session()
        params: dict[str, Any] = {"nodeId": node_id, "targetNodeId": target_node_id}
        if insert_before_node_id is not None:
            params["insertBeforeNodeId"] = insert_before_node_id
        await session.send("DOM.copyTo", params)

    async def dom_disable(self) -> None:
        """Disable the DOM agent."""
        session = self._require_session()
        await session.send("DOM.disable", {})

    async def dom_discard_search_results(self, search_id: str) -> None:
        """Discard search results for a DOM search session."""
        session = self._require_session()
        await session.send("DOM.discardSearchResults", {"searchId": search_id})

    async def dom_enable(self) -> None:
        """Enable the DOM agent."""
        session = self._require_session()
        await session.send("DOM.enable", {})

    async def dom_focus_node(self, node_id: int) -> None:
        """Focus a node by ID."""
        session = self._require_session()
        await session.send("DOM.focus", {"nodeId": node_id})

    async def dom_force_show_popover(self, node_id: int) -> None:
        """Force show a popover for a node by ID."""
        session = self._require_session()
        await session.send("DOM.forceShowPopover", {"nodeId": node_id})

    async def dom_get_anchor_element(self, node_id: int) -> dict[str, Any]:
        """Get the anchor element for a node by ID."""
        session = self._require_session()
        result = await session.send("DOM.getAnchorElement", {"nodeId": node_id})
        return dict(result) if result else {}

    async def dom_get_node_attribute(self, node_id: int, name: str) -> str:
        """Get an attribute value from a node by ID."""
        session = self._require_session()
        result = await session.send("DOM.getAttribute", {"nodeId": node_id, "name": name})
        return str(result.get("value", "")) if result else ""

    async def dom_get_container_for_node(
        self, node_id: int, container_name: str | None = None
    ) -> dict[str, Any]:
        """Get the container for a node by ID."""
        session = self._require_session()
        params: dict[str, Any] = {"nodeId": node_id}
        if container_name is not None:
            params["containerName"] = container_name
        result = await session.send("DOM.getContainerForNode", params)
        return dict(result) if result else {}

    async def dom_get_detached_dom_nodes(self) -> list[dict[str, Any]]:
        """Get detached DOM nodes."""
        session = self._require_session()
        result = await session.send("DOM.getDetachedDomNodes", {})
        return list(result.get("detachedNodes", [])) if result else []

    async def dom_get_element_by_relation(self, node_id: int, relation: str) -> dict[str, Any]:
        """Get an element by relation from a node by ID."""
        session = self._require_session()
        result = await session.send(
            "DOM.getElementByRelation", {"nodeId": node_id, "relation": relation}
        )
        return dict(result) if result else {}

    async def dom_get_file_info(self, node_id: int) -> dict[str, Any]:
        """Get file info for a node by ID."""
        session = self._require_session()
        result = await session.send("DOM.getFileInfo", {"nodeId": node_id})
        return dict(result) if result else {}

    async def dom_get_frame_owner(self, frame_id: str) -> dict[str, Any]:
        """Get the frame owner node for a frame ID."""
        session = self._require_session()
        result = await session.send("DOM.getFrameOwner", {"frameId": frame_id})
        return dict(result) if result else {}

    async def dom_get_node_stack_traces(self, node_id: int) -> dict[str, Any]:
        """Get stack traces for a node by ID."""
        session = self._require_session()
        result = await session.send("DOM.getNodeStackTraces", {"nodeId": node_id})
        return dict(result) if result else {}

    async def dom_get_nodes_for_subtree_by_style(
        self, node_id: int, computed_styles: list[str], pierce: bool = False
    ) -> list[dict[str, Any]]:
        """Get nodes in a subtree matching the given computed styles."""
        session = self._require_session()
        result = await session.send(
            "DOM.getNodesForSubtreeByStyle",
            {"nodeId": node_id, "computedStyles": computed_styles, "pierce": pierce},
        )
        return list(result.get("nodeIds", [])) if result else []

    async def dom_get_querying_descendants_for_container(
        self, node_id: int
    ) -> list[dict[str, Any]]:
        """Get querying descendants for a container node by ID."""
        session = self._require_session()
        result = await session.send("DOM.getQueryingDescendantsForContainer", {"nodeId": node_id})
        return list(result.get("nodeIds", [])) if result else []

    async def dom_get_relayout_boundary(self, node_id: int) -> dict[str, Any]:
        """Get the relayout boundary for a node by ID."""
        session = self._require_session()
        result = await session.send("DOM.getRelayoutBoundary", {"nodeId": node_id})
        return dict(result) if result else {}

    async def dom_get_top_layer_elements(self) -> list[dict[str, Any]]:
        """Get top layer elements."""
        session = self._require_session()
        result = await session.send("DOM.getTopLayerElements", {})
        return list(result.get("nodes", [])) if result else []

    async def dom_hide_highlight(self) -> None:
        """Hide any DOM highlight."""
        session = self._require_session()
        await session.send("DOM.hideHighlight", {})

    async def dom_highlight_node(self, node_id: int, highlight_config: dict[str, Any]) -> None:
        """Highlight a node by ID with the given highlight config."""
        session = self._require_session()
        await session.send(
            "DOM.highlightNode", {"highlightConfig": highlight_config, "nodeId": node_id}
        )

    async def dom_highlight_rect(
        self, x: int, y: int, width: int, height: int, highlight_config: dict[str, Any]
    ) -> None:
        """Highlight a rect with the given highlight config."""
        session = self._require_session()
        await session.send(
            "DOM.highlightRect",
            {
                "highlightConfig": highlight_config,
                "rect": {"x": x, "y": y, "width": width, "height": height},
            },
        )

    async def dom_mark_undoable_state(self) -> None:
        """Mark an undoable state in the DOM."""
        session = self._require_session()
        await session.send("DOM.markUndoableState", {})

    async def dom_move_to(
        self, node_id: int, target_node_id: int, insert_before_node_id: int | None = None
    ) -> None:
        """Move a node to a target node, optionally before another node."""
        session = self._require_session()
        params: dict[str, Any] = {"nodeId": node_id, "targetNodeId": target_node_id}
        if insert_before_node_id is not None:
            params["insertBeforeNodeId"] = insert_before_node_id
        await session.send("DOM.moveTo", params)

    async def dom_push_node_by_path_to_frontend(self, path: str) -> dict[str, Any]:
        """Push a node by path to frontend."""
        session = self._require_session()
        result = await session.send("DOM.pushNodeByPathToFrontend", {"path": path})
        return dict(result) if result else {}

    async def dom_push_nodes_by_backend_ids_to_frontend(
        self, backend_node_ids: list[int]
    ) -> dict[str, Any]:
        """Push nodes by backend IDs to frontend."""
        session = self._require_session()
        result = await session.send(
            "DOM.pushNodesByBackendIdsToFrontend", {"backendNodeIds": backend_node_ids}
        )
        return dict(result) if result else {}

    async def dom_query_selector(self, node_id: int, selector: str) -> dict[str, Any]:
        """Query a single selector within a node's subtree."""
        session = self._require_session()
        result = await session.send("DOM.querySelector", {"nodeId": node_id, "selector": selector})
        return dict(result) if result else {}

    async def dom_query_selector_all(self, node_id: int, selector: str) -> list[dict[str, Any]]:
        """Query all selectors within a node's subtree."""
        session = self._require_session()
        result = await session.send(
            "DOM.querySelectorAll", {"nodeId": node_id, "selector": selector}
        )
        return list(result.get("nodes", [])) if result else []

    async def dom_redo(self) -> None:
        """Redo the last DOM action."""
        session = self._require_session()
        await session.send("DOM.redo", {})

    async def dom_remove_node_by_id(self, node_id: int) -> None:
        """Remove a node from the DOM by ID."""
        session = self._require_session()
        await session.send("DOM.removeNode", {"nodeId": node_id})

    async def dom_set_attributes_as_text(self, node_id: int, text: str) -> None:
        """Set attributes on a node from a text string."""
        session = self._require_session()
        await session.send("DOM.setAttributesAsText", {"nodeId": node_id, "text": text})

    async def dom_set_file_input_files(self, node_id: int, files: list[str]) -> None:
        """Set files for a file input node by ID."""
        session = self._require_session()
        await session.send("DOM.setFileInputFiles", {"nodeId": node_id, "files": files})

    async def dom_set_inspected_node(self, node_id: int) -> None:
        """Set the inspected node by ID."""
        session = self._require_session()
        await session.send("DOM.setInspectedNode", {"nodeId": node_id})

    async def dom_set_node_name(self, node_id: int, name: str) -> dict[str, Any]:
        """Set the name of a node by ID."""
        session = self._require_session()
        result = await session.send("DOM.setNodeName", {"nodeId": node_id, "name": name})
        return dict(result) if result else {}

    async def dom_set_node_stack_traces_enabled(self, enable: bool) -> None:
        """Enable or disable node stack traces."""
        session = self._require_session()
        await session.send("DOM.setNodeStackTracesEnabled", {"enable": enable})

    async def dom_set_text_content(self, node_id: int, text: str) -> None:
        """Set the text content of a node by ID."""
        session = self._require_session()
        await session.send("DOM.setTextContent", {"nodeId": node_id, "text": text})

    async def dom_undo(self) -> None:
        """Undo the last DOM action."""
        session = self._require_session()
        await session.send("DOM.undo", {})

    async def suggest_locator(self, selector: str, all: bool = False) -> list[str] | str:
        """Suggest the best CSS selector for an element.

        Args:
            selector: CSS selector for the target element.
            all: If True, return multiple suggestions; otherwise just the best one.

        Returns:
            List of selector strings when all=True, single best selector when all=False.
        """
        session = self._require_session()
        escaped = json.dumps(selector)
        js = self._suggest_locator_js(escaped)
        result = await session.runtime.evaluate(js)
        raw = (result or {}).get("result", {}).get("value")
        if not raw:
            raise ElementNotFoundError(selector)
        suggestions = _safe_json_loads(raw, [])
        if not isinstance(suggestions, list) or not suggestions:
            raise ElementNotFoundError(selector)
        if all:
            return suggestions
        return suggestions[0]

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
        session = self._require_session()
        js = self._find_by_text_js(query)
        result = await session.runtime.evaluate(js)
        raw = (result or {}).get("result", {}).get("value")
        if not raw:
            raise ElementNotFoundError(query)
        selectors = _safe_json_loads(raw, [])
        if not isinstance(selectors, list) or not selectors:
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
                "headers": [{"name": k, "value": v} for k, v in request.get("headers", {}).items()],
                "queryString": [
                    {"name": k, "value": v} for k, v in request.get("queryString", {}).items()
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
                    {"name": k, "value": v} for k, v in response.get("headers", {}).items()
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

        try:
            await session.network.enable()
            await self.navigate(params.url, WaitStrategy(strategy="load"))
            await asyncio.sleep(params.timeout / 1000)
        finally:
            session.off("Network.requestWillBeSent", on_request)
            session.off("Network.responseReceived", on_response)
            session.off("Network.loadingFinished", on_loading_finished)

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
            entries.append(
                {
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
                }
            )

        return {
            "log": {
                "version": "1.2",
                "creator": {"name": "wavexis", "version": __version__},
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
        client = self._require_client()
        # Target.createBrowserContext is only supported on the browser target,
        # not on a page session (bug #11/#12: previously this called
        # session.target.create_browser_context() which raised
        # "[-32000] Not allowed").
        result = await client.send("Target.createBrowserContext", {})
        return str(result.get("browserContextId", ""))

    async def list_contexts(self) -> list[dict[str, Any]]:
        """List all browser contexts.

        Returns:
            List of context info dicts.
        """
        client = self._require_client()
        # Target.getBrowserContexts is only supported on the browser target.
        result = await client.send("Target.getBrowserContexts", {})
        contexts = result.get("browserContextIds", [])
        return [{"contextId": ctx} for ctx in contexts]

    async def close_context(self, context_id: str) -> None:
        """Close a browser context by ID.

        Args:
            context_id: The browser context ID to close.
        """
        client = self._require_client()
        await client.send("Target.disposeBrowserContext", {"browserContextId": context_id})

    async def new_user_context(self) -> str:
        """Create a new user context.

        CDP does not have a direct user-context concept, so a new browser
        context is created as the closest equivalent.

        Returns:
            The user/browser context ID string.
        """
        return await self.new_context()

    async def get_window_bounds(self) -> dict[str, Any]:
        """Get the current window bounds.

        Returns:
            Dict with width, height, left, top.
        """
        session = self._require_session()
        if self._client is None:
            raise NavigationError("", "Client not initialized.")
        result = await self._client.browser.get_window_for_target(target_id=session.target_id)
        bounds = result.get("bounds", {})
        return {
            "width": bounds.get("width", 0),
            "height": bounds.get("height", 0),
            "x": bounds.get("left", 0),
            "y": bounds.get("top", 0),
        }

    async def set_window_bounds(self, width: int, height: int, x: int = 0, y: int = 0) -> None:
        """Set the window bounds.

        Args:
            width: Window width in pixels.
            height: Window height in pixels.
            x: Window X position.
            y: Window Y position.
        """
        session = self._require_session()
        if self._client is None:
            raise NavigationError("", "Client not initialized.")
        result = await self._client.browser.get_window_for_target(target_id=session.target_id)
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
        )
        if preset.get("user_agent"):
            await session.emulation.set_user_agent_override(
                user_agent=str(preset["user_agent"]),
            )
        if preset.get("touch"):
            await session.emulation.set_touch_emulation_enabled(True)

    async def set_viewport(self, width: int, height: int, device_scale_factor: float = 1.0) -> None:
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
        escaped = json.dumps(selector)
        js = (
            f"(function(){{var el=document.querySelector({escaped});"
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
        escaped = json.dumps(selector)
        js = (
            f"(function(){{var el=document.querySelector({escaped});"
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
        for current_click in range(1, click_count + 1):
            await session.input.dispatch_mouse_event(
                **{"type": "mousePressed"}, x=x, y=y, button=btn, click_count=current_click
            )
            await session.input.dispatch_mouse_event(
                **{"type": "mouseReleased"}, x=x, y=y, button=btn, click_count=current_click
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
            await session.input.dispatch_key_event(**{"type": "char"}, text=char)
            if delay > 0:
                await asyncio.sleep(delay / 1000)

    async def fill(self, selector: str, value: str, auto_wait: bool = True) -> None:
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
        escaped = json.dumps(selector)
        escaped_val = json.dumps(value)
        js = (
            f"(function(){{var el=document.querySelector({escaped});"
            f"if(!el)return false;el.focus();el.value={escaped_val};"
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
        escaped = json.dumps(selector)
        escaped_val = json.dumps(value)
        js = (
            f"(function(){{var el=document.querySelector({escaped});"
            f"if(!el)return false;el.value={escaped_val};"
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
        await session.input.dispatch_mouse_event(**{"type": "mouseMoved"}, x=x, y=y)

    async def key_press(self, key: str) -> None:
        """Press a keyboard key.

        Args:
            key: Key name (e.g. 'Enter', 'Tab', 'Escape').
        """
        session = self._require_session()
        key_map = {
            "Enter": {"key": "Enter", "code": "Enter", "windows_virtual_key_code": 13},
            "Tab": {"key": "Tab", "code": "Tab", "windows_virtual_key_code": 9},
            "Escape": {"key": "Escape", "code": "Escape", "windows_virtual_key_code": 27},
            "Space": {"key": " ", "code": "Space", "windows_virtual_key_code": 32},
            "Backspace": {"key": "Backspace", "code": "Backspace", "windows_virtual_key_code": 8},
        }
        key_info = key_map.get(key, {"key": key, "code": key})
        await session.input.dispatch_key_event(**{"type": "keyDown"}, **key_info)
        await session.input.dispatch_key_event(**{"type": "keyUp"}, **key_info)

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
            **{"type": "mousePressed"}, x=sx, y=sy, button="left", click_count=1
        )
        await session.input.dispatch_mouse_event(**{"type": "mouseMoved"}, x=tx, y=ty)
        await session.input.dispatch_mouse_event(
            **{"type": "mouseReleased"}, x=tx, y=ty, button="left", click_count=1
        )

    async def tap(self, selector: str) -> None:
        """Tap an element (touch emulation click).

        Args:
            selector: CSS selector for the target element.
        """
        session = self._require_session()
        x, y = await self._get_box_center(selector)
        await session.input.dispatch_touch_event(
            **{"type": "touchStart"}, touch_points=[{"x": x, "y": y}]
        )
        await session.input.dispatch_touch_event(**{"type": "touchEnd"}, touch_points=[])

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

        Bug #26: previously the JS wrapper was
        ``(function(){<expr>}).call(f.contentDocument)`` which treats
        ``<expr>`` as a *statement* body, so e.g. ``document.title``
        evaluated to ``undefined`` and the CLI printed nothing. An earlier
        fix JSON-encoded the expression, which turned it into a string
        literal and made ``return ("document.title")`` return the literal
        string instead of the title. We now inject the expression as raw
        code (it is the user's responsibility to pass a valid JS
        expression) and serialize the result as JSON on the JS side so
        strings/objects survive the CDP ``RemoteObject`` round-trip.
        """
        session = self._require_session()
        escaped_iframe = json.dumps(iframe_selector)
        # NOTE: ``expression`` is injected as raw JavaScript source, NOT
        # as a JSON string. JSON-encoding it would turn
        # ``document.title`` into the literal string "document.title".
        js = (
            f"(function(){{var f=document.querySelector({escaped_iframe});"
            f"if(!f||!f.contentDocument)return null;"
            f"try{{var v=(function(){{return ({expression});}}).call(f.contentDocument);"
            f"if(v===undefined||v===null)return null;"
            f"return (typeof v==='object')?JSON.stringify(v):String(v);}}"
            f"catch(e){{return 'ERROR: '+e.message;}}}})()"
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
        session = self._require_session()
        pierce_js = self._build_shadow_pierce_js(selectors)
        escaped_expr = json.dumps(expression)
        js = (
            f"(function(){{var el=({pierce_js});"
            f"if(!el)return null;"
            f"return (new Function({escaped_expr})).call(el);}})()"
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

    async def shadow_click(self, selectors: list[str], auto_wait: bool = True) -> None:
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

    async def shadow_fill(self, selectors: list[str], value: str, auto_wait: bool = True) -> None:
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
        escaped_val = json.dumps(value)
        js = (
            f"(function(){{var el=({pierce_js});"
            f"if(!el)return false;"
            f"el.focus();el.value={escaped_val};"
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
        await session.send(
            "Network.setBlockedURLs",
            {"urls": patterns},
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
        try:
            await session.send(
                "Fetch.enable",
                {"patterns": [{"urlPattern": url, "requestStage": "Response"}]},
            )
        except Exception:
            session.off("Fetch.requestPaused", on_request_paused)
            raise

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
        except Exception as exc:
            if isinstance(exc, WavexisError):
                raise
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
        except Exception as exc:
            if isinstance(exc, WavexisError):
                raise
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
        try:
            await session.send("Fetch.enable", {"patterns": [pattern]})
        except Exception:
            session.off("Fetch.requestPaused", on_request_paused)
            raise

    async def modify_response(
        self,
        pattern: dict[str, Any],
        modifications: dict[str, Any],
    ) -> None:
        """Intercept responses matching a pattern and modify them in-flight.

        Uses CDP Fetch domain to pause responses and fulfill with modifications.

        Args:
            pattern: Pattern dict with optional keys: urlPattern, resourceType,
                requestStage (defaults to "Response").
            modifications: Dict with optional keys: status, headers, body.
        """
        session = self._require_session()

        response_pattern = dict(pattern)
        response_pattern.setdefault("requestStage", "Response")

        body = modifications.get("body", "")
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        body_b64 = base64.b64encode(body.encode("utf-8")).decode("ascii")

        async def on_request_paused(event_params: dict[str, Any]) -> None:
            """Handle Fetch.requestPaused and fulfill with modified response."""
            request_id = event_params.get("requestId", "")
            response_headers = modifications.get(
                "headers",
                [
                    {
                        "name": "Content-Type",
                        "value": modifications.get("content_type", "application/json"),
                    }
                ],
            )
            await session.send(
                "Fetch.fulfillRequest",
                {
                    "requestId": request_id,
                    "responseCode": modifications.get("status", 200),
                    "responseHeaders": response_headers,
                    "body": body_b64,
                },
            )

        session.on("Fetch.requestPaused", on_request_paused)
        try:
            await session.send("Fetch.enable", {"patterns": [response_pattern]})
        except Exception:
            session.off("Fetch.requestPaused", on_request_paused)
            raise

    async def replay_har(self, har_path: str, url_filter: str = "") -> None:
        """Replay network requests from a HAR file.

        Reads the HAR JSON, iterates entries, and replays each request using
        the browser's fetch API.

        Args:
            har_path: Path to the HAR file.
            url_filter: Optional URL pattern to filter which entries to replay.
        """
        session = self._require_session()

        try:
            content = await asyncio.to_thread(validate_path(har_path).read_text, encoding="utf-8")
        except OSError as e:
            raise WavexisError(f"Failed to read HAR file: {e}") from e
        har_data = _safe_json_loads(content, {})
        if not isinstance(har_data, dict):
            raise WavexisError("HAR file must contain a JSON object")

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

    async def handle_auth(
        self,
        url_pattern: str,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        """Handle HTTP authentication challenges for matching requests.

        Uses the CDP Fetch domain to intercept authRequired events and either
        provide credentials or cancel the challenge.

        Args:
            url_pattern: URL pattern to match auth challenges.
            username: Username to provide. If None, auth is canceled.
            password: Password to provide.
        """
        session = self._require_session()

        async def on_auth_required(event_params: dict[str, Any]) -> None:
            """Respond to Fetch.authRequired events."""
            request_url = event_params.get("request", {}).get("url", "")
            if url_pattern and url_pattern not in request_url:
                return
            request_id = event_params.get("requestId", "")
            if username and password:
                await session.send(
                    "Fetch.continueWithAuth",
                    {
                        "requestId": request_id,
                        "authChallengeResponse": {
                            "response": "ProvideCredentials",
                            "username": username,
                            "password": password,
                        },
                    },
                )
            else:
                await session.send(
                    "Fetch.continueWithAuth",
                    {
                        "requestId": request_id,
                        "authChallengeResponse": {"response": "CancelAuth"},
                    },
                )

        session.on("Fetch.authRequired", on_auth_required)
        try:
            await session.send(
                "Fetch.enable",
                {"patterns": [{"urlPattern": url_pattern}]},
            )
        except Exception:
            session.off("Fetch.authRequired", on_auth_required)
            raise

    async def network_clear_browser_cache(self) -> None:
        """Clear the browser cache."""
        session = self._require_session()
        await session.network.clear_browser_cache()

    async def network_clear_browser_cookies(self) -> None:
        """Clear all browser cookies."""
        session = self._require_session()
        await session.network.clear_browser_cookies()

    async def network_delete_cookies(self, name: str, domain: str = "") -> None:
        """Delete cookies by name and optional domain."""
        session = self._require_session()
        params: dict[str, Any] = {"name": name}
        if domain:
            params["domain"] = domain
        await session.network.delete_cookies(**params)

    async def network_set_blocked_urls(self, urls: list[str]) -> None:
        """Block requests to specific URLs."""
        session = self._require_session()
        await session.network.set_blocked_urls(urls=urls)

    async def network_set_bypass_service_worker(self, bypass: bool) -> None:
        """Bypass the service worker for all network requests."""
        session = self._require_session()
        await session.network.set_bypass_service_worker(bypass=bypass)

    async def network_set_cookie_controls(
        self, mode: str = "allow", third_party_mode: str = "allow"
    ) -> None:
        """Set cookie controls.

        Maps the legacy ``mode``/``third_party_mode`` string parameters to
        the boolean ``enable_third_party_cookie_restriction`` expected by
        cdpwave.  Any mode other than ``"allow"`` enables the restriction.
        """
        session = self._require_session()
        enable_restriction = mode != "allow" or third_party_mode != "allow"
        await session.network.set_cookie_controls(
            enable_third_party_cookie_restriction=enable_restriction
        )

    async def network_set_extra_request_headers(self, headers: dict[str, str]) -> None:
        """Set extra HTTP headers for all requests."""
        session = self._require_session()
        await session.network.set_extra_request_headers(headers=headers)

    async def network_set_user_agent_override(
        self, user_agent: str, accept_language: str = "", platform: str = ""
    ) -> None:
        """Override the User-Agent string with metadata."""
        session = self._require_session()
        params: dict[str, Any] = {"user_agent": user_agent}
        if accept_language:
            params["accept_language"] = accept_language
        if platform:
            params["platform"] = platform
        await session.network.set_user_agent_override(**params)

    async def network_replay_xhr(self, request_id: str) -> None:
        """Replay a previously captured XHR request by ID."""
        session = self._require_session()
        await session.network.replay_xhr(request_id=request_id)

    async def network_load_network_resource(
        self, frame_id: str, url: str, options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Load a network resource outside the context of a page."""
        session = self._require_session()
        params: dict[str, Any] = {"frameId": frame_id, "url": url}
        if options:
            params["options"] = options
        return dict(await session.network.load_network_resource(**params))

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
        self._trace_counter += 1
        trace_id = f"trace-{self._trace_counter}"

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
            await session.network.enable()

            def on_network_request(event_params: dict[str, Any]) -> None:
                state["network"].append(
                    {
                        "type": "request",
                        "url": event_params.get("request", {}).get("url", ""),
                        "method": event_params.get("request", {}).get("method", ""),
                        "requestId": event_params.get("requestId", ""),
                        "timestamp": event_params.get("timestamp"),
                    }
                )

            def on_network_response(event_params: dict[str, Any]) -> None:
                state["network"].append(
                    {
                        "type": "response",
                        "url": event_params.get("response", {}).get("url", ""),
                        "status": event_params.get("response", {}).get("status", 0),
                        "requestId": event_params.get("requestId", ""),
                        "timestamp": event_params.get("timestamp"),
                    }
                )

            session.on("Network.requestWillBeSent", on_network_request)
            session.on("Network.responseReceived", on_network_response)
            state["handlers"].append(("Network.requestWillBeSent", on_network_request))
            state["handlers"].append(("Network.responseReceived", on_network_response))

        if capture_console:
            await session.runtime.enable()

            def on_console_api(event_params: dict[str, Any]) -> None:
                state["console"].append(
                    {
                        "type": event_params.get("type", "log"),
                        "args": event_params.get("args", []),
                        "timestamp": event_params.get("timestamp"),
                    }
                )

            session.on("Runtime.consoleAPICalled", on_console_api)
            state["handlers"].append(("Runtime.consoleAPICalled", on_console_api))

        if capture_screenshots:
            screenshot = await session.page.capture_screenshot()
            if screenshot:
                state["screenshots"].append(
                    {
                        "timestamp": time.time(),
                        "data": screenshot,
                    }
                )

        await session.send("Tracing.start", {"traceType": "devtools-timeline"})

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
        traces = self._combined_traces
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
                    raw = await read_trace_stream(
                        lambda: session.send("IO.read", {"handle": stream_handle})
                    )
                    extracted = await asyncio.to_thread(extract_trace_events, raw)
                    trace_events.extend(extracted)
            finally:
                if stream_handle:
                    with contextlib.suppress(Exception):
                        await session.send("IO.close", {"handle": stream_handle})
                tracing_done.set()

        session.on("Tracing.tracingComplete", _on_tracing_complete)
        try:
            await session.send("Tracing.end", {})

            if state["capture_screenshots"]:
                screenshot = await session.page.capture_screenshot()
                if screenshot:
                    state["screenshots"].append(
                        {
                            "timestamp": time.time(),
                            "data": screenshot,
                        }
                    )

            # Wait for the tracingComplete handler to finish (max 10s).
            try:
                await asyncio.wait_for(tracing_done.wait(), timeout=10.0)
            except TimeoutError:
                logger.warning("tracingComplete handler did not fire within 10s")
        finally:
            session.off("Tracing.tracingComplete", _on_tracing_complete)

        result: dict[str, Any] = {
            "trace_events": trace_events,
            "screenshots": state["screenshots"],
            "network": state["network"],
            "console": state["console"],
        }
        for event_name, handler in state.get("handlers", []):
            session.off(event_name, handler)
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
        value = (result or {}).get("result", {}).get("value")
        if isinstance(value, dict):
            return value
        parsed = _safe_json_loads(value, {})
        if isinstance(parsed, dict) and parsed:
            return parsed
        return {"error": "axe-core audit failed", "raw": dict(result) if result else None}

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
        self._subscription_counter += 1
        sub_id = f"sub-{self._subscription_counter}"

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
                    await session.network.enable()
                elif evt_type == "console":
                    await session.runtime.enable()
                elif evt_type in ("dialog", "navigation"):
                    # Bug #27: Page events (Page.javascriptDialogOpening,
                    # Page.frameNavigated) are only delivered after
                    # Page.enable() is called. Without this, the
                    # subscription silently captured nothing.
                    await session.page.enable()

        self._subscriptions[sub_id] = handlers
        return sub_id

    async def unsubscribe_events(self, subscription_id: str) -> None:
        """Unsubscribe from events by subscription ID.

        Args:
            subscription_id: The ID returned by subscribe_events.
        """
        session = self._require_session()
        handlers = self._subscriptions.pop(subscription_id, {})
        for cdp_event, handler in handlers.items():
            off = getattr(session, "off", None)
            if off is not None:
                try:
                    off(cdp_event, handler)
                except Exception:
                    # The handler may have been removed already; keep going
                    # so the remaining subscriptions are cleaned up.
                    logger.warning(
                        "Failed to unsubscribe %s from %s; continuing cleanup",
                        subscription_id,
                        cdp_event,
                    )

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

        # Build a map of nodeId -> node for O(1) lookup
        node_map = {node.get("nodeId"): node for node in nodes}

        # Find the target node
        target = node_map.get(node_id)
        if not target:
            return []

        # Traverse up via parentId to find ancestors
        ancestors: list[dict[str, Any]] = []
        current_parent_id = target.get("parentId")
        while current_parent_id:
            parent = node_map.get(current_parent_id)
            if parent:
                ancestors.append(dict(parent))
                current_parent_id = parent.get("parentId")
            else:
                break

        return ancestors

    # ── Downloads ──────────────────────────────────────────

    async def intercept_download(self, pattern: str = ".*", timeout: float | None = None) -> bytes:
        """Intercept a file download matching a URL pattern and return bytes.

        Sets the download behavior to a temp directory, then polls for the
        first downloaded file to appear and finishes writing. Returns the
        file bytes, or empty bytes if no download appears within the timeout.

        Args:
            pattern: URL pattern to match downloads (regex, default matches all).
                Currently informational — all downloads in the temp dir are returned.
            timeout: Maximum seconds to wait for a download to appear (default 30s).

        Returns:
            Downloaded file bytes, or empty bytes if no file appears.

        Bug #13: previously the first file in the download directory was
        returned immediately. Chrome writes a ``.crdownload`` temp file
        while the download is in progress, which can be 0 bytes for a
        moment; the old code would pick that up and return 0 bytes. We
        now skip ``.crdownload`` files when looking for the final file,
        and wait for the in-progress temp file to be renamed to the
        final name (which signals completion) before reading.
        """
        session = self._require_session()
        import tempfile

        with tempfile.TemporaryDirectory() as download_dir:
            await session.send(
                "Page.setDownloadBehavior",
                {"behavior": "allow", "downloadPath": download_dir},
            )

            download_path = Path(download_dir)
            effective_timeout = timeout if timeout is not None else 30.0
            deadline = time.monotonic() + effective_timeout
            found: Path | None = None
            while time.monotonic() < deadline:

                def _list_completed_files() -> list[Path]:
                    # Skip Chrome's in-progress temp files (.crdownload)
                    # and any 0-byte files that haven't been written yet.
                    return [
                        p
                        for p in download_path.iterdir()
                        if p.is_file()
                        and not p.name.endswith(".crdownload")
                        and p.stat().st_size > 0
                    ]

                candidates = await asyncio.to_thread(_list_completed_files)
                if candidates:
                    found = candidates[0]
                    break
                await asyncio.sleep(0.25)

            if found is None:
                return b""

            # Wait for the download to finish writing (size stable for 0.5s).
            prev_size = -1
            stable_until = time.monotonic() + min(effective_timeout, 10.0)
            while time.monotonic() < stable_until:
                try:
                    size = await asyncio.to_thread(found.stat)
                except OSError:
                    # File was deleted or renamed mid-download.
                    return b""
                if size.st_size == prev_size and size.st_size > 0:
                    break
                prev_size = size.st_size
                await asyncio.sleep(0.5)

            try:
                return await asyncio.to_thread(found.read_bytes)
            except OSError:
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

    async def dialog_wait_for_opening(self, timeout: float = 30.0) -> dict[str, Any]:
        """Wait for a JavaScript dialog to open and return its event params.

        Args:
            timeout: Maximum seconds to wait for the dialog.

        Returns:
            The ``Page.javascriptDialogOpening`` event params.

        Raises:
            TimeoutError: If no dialog opens within ``timeout``.
        """
        session = self._require_session()
        await session.page.enable()
        return await session.wait_for_event("Page.javascriptDialogOpening", timeout=timeout)

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
        await session.send("Security.enable")
        # Listen for security state change event
        state = await session.send("Security.getVisibleSecurityState")
        return dict(state) if state else {}

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

    async def set_device_metrics_override(
        self,
        width: int,
        height: int,
        device_scale_factor: float = 1.0,
        mobile: bool = False,
    ) -> None:
        """Override device metrics."""
        session = self._require_session()
        await session.emulation.set_device_metrics_override(
            width=width,
            height=height,
            device_scale_factor=device_scale_factor,
            mobile=mobile,
        )

    async def clear_device_metrics_override(self) -> None:
        """Clear device metrics override."""
        session = self._require_session()
        await session.emulation.clear_device_metrics_override()

    async def set_emulated_media(self, media: str) -> None:
        """Set the emulated media type."""
        session = self._require_session()
        await session.emulation.set_emulated_media(media)

    async def clear_emulated_media(self) -> None:
        """Clear emulated media override."""
        session = self._require_session()
        await session.emulation.clear_emulated_media()

    async def set_emulated_vision_deficiency(self, deficiency: str) -> None:
        """Set emulated vision deficiency."""
        session = self._require_session()
        await session.emulation.set_emulated_vision_deficiency(deficiency)

    async def clear_emulated_vision_deficiency(self) -> None:
        """Clear emulated vision deficiency override."""
        session = self._require_session()
        await session.emulation.clear_emulated_vision_deficiency()

    async def set_idle_override(
        self, is_user_active: bool = True, is_screen_active: bool = True
    ) -> None:
        """Override the idle state.

        Note: ``is_screen_active`` is mapped to the CDP parameter
        ``is_screen_unlocked`` as expected by cdpwave.
        """
        session = self._require_session()
        await session.emulation.set_idle_override(
            is_user_active=is_user_active, is_screen_unlocked=is_screen_active
        )

    async def clear_idle_override(self) -> None:
        """Clear the idle state override."""
        session = self._require_session()
        await session.emulation.clear_idle_override()

    async def set_script_execution_disabled(self, disabled: bool = True) -> None:
        """Disable or enable JavaScript script execution."""
        session = self._require_session()
        await session.emulation.set_script_execution_disabled(disabled)

    async def set_visible_size(self, width: int, height: int) -> None:
        """Set the visible size of the page."""
        session = self._require_session()
        await session.emulation.set_visible_size(width, height)

    async def add_screen(self, screen: dict[str, Any]) -> None:
        """Add a virtual screen with the given configuration."""
        session = self._require_session()
        await session.send("Emulation.addScreen", {"screen": screen})

    async def can_emulate(self) -> bool:
        """Check whether the browser supports emulation."""
        session = self._require_session()
        result = await session.send("Emulation.canEmulate", {})
        return bool(result.get("result", False))

    async def clear_auto_dark_mode_override(self) -> None:
        """Clear the auto dark mode override."""
        session = self._require_session()
        await session.send("Emulation.clearAutoDarkModeOverride", {})

    async def clear_default_background_color_override(self) -> None:
        """Clear the default background color override."""
        session = self._require_session()
        await session.send("Emulation.clearDefaultBackgroundColorOverride", {})

    async def clear_device_posture_override(self) -> None:
        """Clear the device posture override."""
        session = self._require_session()
        await session.send("Emulation.clearDevicePostureOverride", {})

    async def clear_display_features_override(self) -> None:
        """Clear the display features override."""
        session = self._require_session()
        await session.send("Emulation.clearDisplayFeaturesOverride", {})

    async def clear_geolocation_override(self) -> None:
        """Clear the geolocation override."""
        session = self._require_session()
        await session.send("Emulation.clearGeolocationOverride", {})

    async def clear_timezone_override(self) -> None:
        """Clear the timezone override."""
        session = self._require_session()
        await session.send("Emulation.clearTimezoneOverride", {})

    async def get_overridden_sensor_information(self, sensor_type: str) -> dict[str, Any]:
        """Get information about overridden sensors of the given type."""
        session = self._require_session()
        result = await session.send(
            "Emulation.getOverriddenSensorInformation", {"type": sensor_type}
        )
        return dict(result) if result else {}

    async def get_screen_infos(self) -> dict[str, Any]:
        """Get information about all virtual screens."""
        session = self._require_session()
        result = await session.send("Emulation.getScreenInfos", {})
        return dict(result) if result else {}

    async def remove_screen(self, screen_id: str) -> None:
        """Remove a virtual screen by ID."""
        session = self._require_session()
        await session.send("Emulation.removeScreen", {"screenId": screen_id})

    async def reset_page_scale_factor(self) -> None:
        """Reset the page scale factor to its default."""
        session = self._require_session()
        await session.send("Emulation.resetPageScaleFactor", {})

    async def set_auto_dark_mode_override(self, enabled: bool) -> None:
        """Enable or disable auto dark mode override."""
        session = self._require_session()
        await session.send("Emulation.setAutoDarkModeOverride", {"enabled": enabled})

    async def set_automation_override(self, enabled: bool) -> None:
        """Enable or disable automation override."""
        session = self._require_session()
        await session.send("Emulation.setAutomationOverride", {"enabled": enabled})

    async def set_cpu_throttling_rate(self, rate: float) -> None:
        """Set CPU throttling rate as a multiplier."""
        session = self._require_session()
        await session.send("Emulation.setCPUThrottlingRate", {"rate": rate})

    async def set_data_saver_override(self, enabled: bool) -> None:
        """Enable or disable data saver override."""
        session = self._require_session()
        await session.send("Emulation.setDataSaverOverride", {"enabled": enabled})

    async def set_default_background_color_override(self, color: dict[str, Any]) -> None:
        """Override the default background color."""
        session = self._require_session()
        await session.send("Emulation.setDefaultBackgroundColorOverride", {"color": color})

    async def set_device_posture_override(self, posture: str) -> None:
        """Override the device posture."""
        session = self._require_session()
        await session.send("Emulation.setDevicePostureOverride", {"posture": posture})

    async def set_disabled_image_types(self, image_types: list[str]) -> None:
        """Disable the given image types from loading."""
        session = self._require_session()
        await session.send("Emulation.setDisabledImageTypes", {"imageTypes": image_types})

    async def set_display_features_override(self, features: list[dict[str, Any]]) -> None:
        """Override display features."""
        session = self._require_session()
        await session.send("Emulation.setDisplayFeaturesOverride", {"features": features})

    async def set_document_cookie_disabled(self, disabled: bool) -> None:
        """Disable or enable document cookies."""
        session = self._require_session()
        await session.send("Emulation.setDocumentCookieDisabled", {"disabled": disabled})

    async def set_emit_touch_events_for_mouse(
        self, enabled: bool, configuration: dict[str, Any] | None = None
    ) -> None:
        """Enable or disable touch event emulation for mouse input."""
        session = self._require_session()
        params: dict[str, Any] = {"enabled": enabled}
        if configuration is not None:
            params["configuration"] = configuration
        await session.send("Emulation.setEmitTouchEventsForMouse", params)

    async def set_emulated_media_feature(self, features: list[dict[str, str]]) -> None:
        """Set emulated media features."""
        session = self._require_session()
        await session.send("Emulation.setEmulatedMediaFeature", {"features": features})

    async def set_emulated_os_text_scale(self, scale: float) -> None:
        """Override the OS text scale factor."""
        session = self._require_session()
        await session.send("Emulation.setEmulatedOSTextScale", {"scale": scale})

    async def set_focus_emulation_enabled(self, enabled: bool) -> None:
        """Enable or disable focus emulation."""
        session = self._require_session()
        await session.send("Emulation.setFocusEmulationEnabled", {"enabled": enabled})

    async def set_geolocation_override(
        self, latitude: float, longitude: float, accuracy: float = 100.0
    ) -> None:
        """Override the geolocation position."""
        session = self._require_session()
        await session.send(
            "Emulation.setGeolocationOverride",
            {
                "latitude": latitude,
                "longitude": longitude,
                "accuracy": accuracy,
            },
        )

    async def set_hardware_concurrency_override(self, concurrency: int) -> None:
        """Override the hardware concurrency."""
        session = self._require_session()
        await session.send(
            "Emulation.setHardwareConcurrencyOverride", {"hardwareConcurrency": concurrency}
        )

    async def set_locale_override(self, locale: str) -> None:
        """Override the browser locale."""
        session = self._require_session()
        await session.send("Emulation.setLocaleOverride", {"locale": locale})

    async def set_navigator_overrides(self, navigator: dict[str, Any]) -> None:
        """Override navigator properties."""
        session = self._require_session()
        await session.send("Emulation.setNavigatorOverrides", {"navigator": navigator})

    async def set_page_scale_factor(self, factor: float) -> None:
        """Set the page scale factor."""
        session = self._require_session()
        await session.send("Emulation.setPageScaleFactor", {"pageScaleFactor": factor})

    async def set_pressure_source_override_enabled(self, source: str, enabled: bool) -> None:
        """Enable or disable pressure source override."""
        session = self._require_session()
        await session.send(
            "Emulation.setPressureSourceOverrideEnabled", {"source": source, "enabled": enabled}
        )

    async def set_pressure_state_override(self, source: str, state: str, value: float) -> None:
        """Override the pressure state."""
        session = self._require_session()
        await session.send(
            "Emulation.setPressureStateOverride", {"source": source, "state": state, "value": value}
        )

    async def set_primary_screen(self, screen_id: str) -> None:
        """Set the primary screen by ID."""
        session = self._require_session()
        await session.send("Emulation.setPrimaryScreen", {"screenId": screen_id})

    async def set_safe_area_insets_override(self, insets: dict[str, Any]) -> None:
        """Override the safe area insets."""
        session = self._require_session()
        await session.send("Emulation.setSafeAreaInsetsOverride", {"insets": insets})

    async def set_scrollbars_hidden(self, hidden: bool) -> None:
        """Hide or show scrollbars."""
        session = self._require_session()
        await session.send("Emulation.setScrollbarsHidden", {"hidden": hidden})

    async def set_sensor_override_enabled(self, type: str, enabled: bool) -> None:
        """Enable or disable sensor override."""
        session = self._require_session()
        await session.send("Emulation.setSensorOverrideEnabled", {"type": type, "enabled": enabled})

    async def set_sensor_override_readings(self, type: str, readings: list[dict[str, Any]]) -> None:
        """Override sensor readings."""
        session = self._require_session()
        await session.send(
            "Emulation.setSensorOverrideReadings", {"type": type, "readings": readings}
        )

    async def set_small_viewport_height_difference_override(self, difference: float) -> None:
        """Override the small viewport height difference."""
        session = self._require_session()
        await session.send(
            "Emulation.setSmallViewportHeightDifferenceOverride", {"difference": difference}
        )

    async def set_timezone_override(self, timezone_id: str) -> None:
        """Override the timezone."""
        session = self._require_session()
        await session.send("Emulation.setTimezoneOverride", {"timezoneId": timezone_id})

    async def set_touch_emulation_enabled(self, enabled: bool, max_touch_points: int = 5) -> None:
        """Enable or disable touch emulation."""
        session = self._require_session()
        await session.send(
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
        """Override the user agent string and related metadata."""
        session = self._require_session()
        params: dict[str, Any] = {"userAgent": user_agent}
        if accept_language:
            params["acceptLanguage"] = accept_language
        if platform:
            params["platform"] = platform
        if user_agent_metadata is not None:
            params["userAgentMetadata"] = user_agent_metadata
        await session.send("Emulation.setUserAgentOverride", params)

    async def set_virtual_time_policy(self, policy: str, budget: int = 0) -> None:
        """Set the virtual time policy."""
        session = self._require_session()
        await session.send("Emulation.setVirtualTimePolicy", {"policy": policy, "budget": budget})

    async def update_screen(self, screen_id: str, screen: dict[str, Any]) -> None:
        """Update a virtual screen by ID."""
        session = self._require_session()
        await session.send("Emulation.updateScreen", {"screenId": screen_id, "screen": screen})

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
        tracing_done = asyncio.Event()

        async def _on_tracing_complete(params: dict[str, Any]) -> None:
            """Handle Tracing.tracingComplete and extract trace events from the stream.

            Args:
                params: CDP event parameters containing the trace data stream handle.
            """
            try:
                stream_handle = params.get("stream")
                if stream_handle:
                    try:
                        raw = await read_trace_stream(
                            lambda: session.send("IO.read", {"handle": stream_handle})
                        )
                        extracted = await asyncio.to_thread(extract_trace_events, raw)
                        trace_events.extend(extracted)
                    finally:
                        with contextlib.suppress(Exception):
                            await session.send("IO.close", {"handle": stream_handle})
                else:
                    trace_events.append({"error": "No stream handle in tracingComplete"})
            finally:
                tracing_done.set()

        session.on("Tracing.tracingComplete", _on_tracing_complete)
        try:
            await session.send(
                "Tracing.start",
                {"traceType": "devtools-timeline"},
            )
            await asyncio.sleep(duration_ms / 1000)
            await session.send("Tracing.end", {})

            # Wait for the tracingComplete handler to finish (max 10s).
            try:
                await asyncio.wait_for(tracing_done.wait(), timeout=10.0)
            except TimeoutError:
                logger.warning("tracingComplete handler did not fire within 10s")
        finally:
            session.off("Tracing.tracingComplete", _on_tracing_complete)
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
        await session.dom.enable()
        await session.send("CSS.enable", {})
        await session.send("CSS.startRuleUsageTracking", {})
        await asyncio.sleep(1)
        result = await session.send("CSS.stopRuleUsageTracking", {})
        return dict(result) if result else {}

    async def performance_disable(self) -> None:
        """Disable the Performance domain."""
        session = self._require_session()
        await session.send("Performance.disable", {})

    async def performance_enable(self) -> None:
        """Enable the Performance domain."""
        session = self._require_session()
        await session.send("Performance.enable", {})

    async def performance_get_metrics(self) -> dict[str, Any]:
        """Get current values of run-time metrics."""
        session = self._require_session()
        result = await session.send("Performance.getMetrics", {})
        return dict(result) if result else {}

    async def performance_set_time_domain(self, time_domain: str) -> None:
        """Set the time domain for collecting and reporting durations."""
        session = self._require_session()
        await session.send("Performance.setTimeDomain", {"timeDomain": time_domain})

    # ── Tracing ───────────────────────────────────────────

    async def tracing_start(
        self,
        categories: str = "",
        options: str = "",
        transfer_mode: str = "ReturnAsStream",
    ) -> None:
        """Start trace event collection."""
        session = self._require_session()
        params: dict[str, Any] = {"transferMode": transfer_mode}
        if categories:
            params["traceConfig"] = {"includedCategories": categories.split(",")}
        if options:
            params["traceConfig"] = params.get("traceConfig", {})
            params["traceConfig"]["excludedCategories"] = options.split(",")
        await session.send("Tracing.start", params)

    async def tracing_end(self) -> None:
        """Stop trace event collection."""
        session = self._require_session()
        await session.send("Tracing.end", {})

    async def tracing_get_categories(self) -> list[str]:
        """Get supported tracing categories."""
        session = self._require_session()
        result = await session.send("Tracing.getCategories", {})
        return list(result.get("categories", [])) if result else []

    async def tracing_record_clock_sync_marker(self, sync_id: str) -> None:
        """Record a clock sync marker."""
        session = self._require_session()
        await session.send("Tracing.recordClockSyncMarker", {"syncId": sync_id})

    async def tracing_request_memory_dump(self) -> dict[str, Any]:
        """Request a memory dump."""
        session = self._require_session()
        result = await session.send("Tracing.requestMemoryDump", {})
        return dict(result) if result else {}

    async def tracing_get_track_event_descriptor(self, track_event: str) -> dict[str, Any]:
        """Get a track event descriptor."""
        session = self._require_session()
        result = await session.send("Tracing.getTrackEventDescriptor", {"trackEvent": track_event})
        return dict(result) if result else {}

    # ── PerformanceTimeline ───────────────────────────────

    async def performance_timeline_enable(self) -> None:
        """Enable the PerformanceTimeline domain."""
        session = self._require_session()
        await session.send("PerformanceTimeline.enable", {})

    # ── CSS ────────────────────────────────────────────────

    async def css_get_styles(self, selector: str) -> dict[str, Any]:
        """Get inline and computed styles for an element by CSS selector.

        Args:
            selector: CSS selector for the target element.

        Returns:
            Dict containing inlineStyles and computedStyles.
        """
        session = self._require_session()
        await session.dom.enable()
        await session.send("CSS.enable")
        node_id = await self._find_node(selector)
        try:
            inline = await session.send("CSS.getInlineStyles", {"nodeId": node_id})
        except Exception as exc:
            if isinstance(exc, WavexisError):
                raise
            escaped = json.dumps(selector)
            inline = await session.runtime.evaluate(
                expression=(
                    "(() => {const el = document.querySelector('"
                    + escaped
                    + "'); const s = getComputedStyle(el); "
                    + "const result = {}; for (let i = 0; i < s.length; i++) "
                    + "{result[s[i]] = s.getPropertyValue(s[i]);} return result;})()"
                ),
                return_by_value=True,
            )
            inline = inline.get("result", {}).get("value", {})
        try:
            computed = await session.send("CSS.getComputedStyleForNode", {"nodeId": node_id})
        except Exception as exc:
            if isinstance(exc, WavexisError):
                raise
            escaped = json.dumps(selector)
            computed = await session.runtime.evaluate(
                expression=(
                    "(() => {const el = document.querySelector('"
                    + escaped
                    + "'); const s = getComputedStyle(el); "
                    + "const result = []; for (let i = 0; i < s.length; i++) "
                    + "{result.push({name: s[i], value: s.getPropertyValue(s[i])});} "
                    + "return result;})()"
                ),
                return_by_value=True,
            )
            computed = computed.get("result", {}).get("value", {})
        return {"inlineStyles": inline, "computedStyles": computed}

    async def css_get_stylesheets(self) -> list[dict[str, Any]]:
        """List all stylesheets in the current page.

        Returns:
            List of stylesheet info dicts.
        """
        session = self._require_session()
        await session.dom.enable()
        await session.send("CSS.enable")
        try:
            result = await session.send("CSS.getLayoutTreeAndStyles", {})
            stylesheets = result.get("stylesheets", [])
            return [dict(s) for s in stylesheets] if stylesheets else []
        except Exception as exc:
            if isinstance(exc, WavexisError):
                raise
            js = (
                "Array.from(document.styleSheets).map((s, i) => ({"
                "styleSheetId: String(i), "
                "sourceURL: s.href || '', "
                "disabled: s.disabled, "
                "isInline: !s.href}))"
            )
            result = await session.runtime.evaluate(expression=js, return_by_value=True)
            value = result.get("result", {}).get("value", [])
            return [dict(v) for v in value] if value else []

    async def css_get_rules(self, stylesheet_id: str) -> list[dict[str, Any]]:
        """Get CSS rules from a specific stylesheet.

        Args:
            stylesheet_id: The styleSheetId from css_get_stylesheets.

        Returns:
            List of CSS rule dicts.
        """
        session = self._require_session()
        await session.send("CSS.enable", {})
        result = await session.send("CSS.getStyleSheetText", {"styleSheetId": stylesheet_id})
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
        resolved = await session.send("DOM.resolveNode", {"nodeId": node_id})
        object_id = resolved.get("object", {}).get("objectId", "")
        if not object_id:
            raise ElementNotFoundError(selector)
        result = await session.send("CSS.getComputedStyleForNode", {"nodeId": node_id})
        computed: dict[str, Any] = {}
        for prop in result.get("computedStyle", []):
            computed[prop.get("name", "")] = prop.get("value", "")
        return computed

    async def css_add_rule(self, stylesheet_id: str, rule_text: str, location: int = 0) -> str:
        """Add a new CSS rule to a stylesheet."""
        session = self._require_session()
        result = await session.css.add_rule(
            style_sheet_id=stylesheet_id,
            rule_text=rule_text,
            location={"lineNumber": location, "columnNumber": 0},
        )
        return str(result.get("ruleId", ""))

    async def css_create_style_sheet(self, frame_id: str) -> str:
        """Create a new stylesheet in the given frame."""
        session = self._require_session()
        result = await session.css.create_style_sheet(frame_id=frame_id)
        return str(result.get("styleSheetId", ""))

    async def css_get_media_queries(self) -> list[dict[str, Any]]:
        """Get all media queries in the current page."""
        session = self._require_session()
        result = await session.css.get_media_queries()
        return [dict(m) for m in result.get("medias", [])] if result else []

    async def css_get_style_sheet_text(self, stylesheet_id: str) -> str:
        """Get the text content of a stylesheet by ID."""
        session = self._require_session()
        result = await session.css.get_style_sheet_text(style_sheet_id=stylesheet_id)
        return str(result.get("text", ""))

    async def css_set_style_sheet_text(self, stylesheet_id: str, text: str) -> None:
        """Set the text content of a stylesheet by ID."""
        session = self._require_session()
        await session.css.set_style_sheet_text(style_sheet_id=stylesheet_id, text=text)

    async def css_set_rule_selector(
        self, stylesheet_id: str, range_: dict[str, Any], selector: str
    ) -> None:
        """Set the selector text of a CSS rule.

        Args:
            stylesheet_id: The stylesheet id.
            range_: Source range of the selector to edit
                (``{"startLine": int, "startColumn": int, "endLine": int, "endColumn": int}``).
            selector: The new selector text.
        """
        session = self._require_session()
        await session.css.set_rule_selector(
            style_sheet_id=stylesheet_id,
            range_=range_,
            selector=selector,
        )

    async def css_set_media_text(
        self, stylesheet_id: str, range_: dict[str, Any], text: str
    ) -> None:
        """Set the text of a media rule.

        Args:
            stylesheet_id: The stylesheet id.
            range_: Source range of the media rule to edit.
            text: The new media rule text.
        """
        session = self._require_session()
        await session.css.set_media_text(
            style_sheet_id=stylesheet_id,
            range_=range_,
            text=text,
        )

    async def css_force_pseudo_state(self, node_id: int, pseudo_state: list[str]) -> None:
        """Force a pseudo state on a node."""
        session = self._require_session()
        await session.css.force_pseudo_state(node_id=node_id, forced_pseudo_classes=pseudo_state)

    async def css_get_background_colors(self, node_id: int) -> dict[str, Any]:
        """Get background colors for a node."""
        session = self._require_session()
        return dict(await session.css.get_background_colors(node_id=node_id))

    async def css_start_rule_usage_tracking(self) -> None:
        """Start tracking CSS rule usage."""
        session = self._require_session()
        await session.css.start_rule_usage_tracking()

    async def css_stop_rule_usage_tracking(self) -> None:
        """Stop tracking CSS rule usage."""
        session = self._require_session()
        await session.css.stop_rule_usage_tracking()

    async def css_take_coverage_delta(self) -> dict[str, Any]:
        """Get the coverage delta since the last call."""
        session = self._require_session()
        return dict(await session.css.take_coverage_delta())

    async def css_collect_class_names(self, node_id: int) -> list[str]:
        """Collect class names from the subtree of a node by ID."""
        session = self._require_session()
        result = await session.send("CSS.collectClassNames", {"nodeId": node_id})
        return list(result.get("classNames", [])) if result else []

    async def css_disable(self) -> None:
        """Disable the CSS domain."""
        session = self._require_session()
        await session.send("CSS.disable", {})

    async def css_enable(self) -> None:
        """Enable the CSS domain."""
        session = self._require_session()
        await session.send("CSS.enable", {})

    async def css_force_starting_style(
        self, node_id: int, starting_style_id: dict[str, Any]
    ) -> None:
        """Force a starting style for a node."""
        session = self._require_session()
        await session.send(
            "CSS.forceStartingStyle", {"nodeId": node_id, "startingStyleId": starting_style_id}
        )

    async def css_get_animated_styles_for_node(self, node_id: int) -> dict[str, Any]:
        """Get animated styles for a node by ID."""
        session = self._require_session()
        result = await session.send("CSS.getAnimatedStylesForNode", {"nodeId": node_id})
        return dict(result) if result else {}

    async def css_get_computed_style_for_node(self, node_id: int) -> list[dict[str, Any]]:
        """Get computed style for a node by ID."""
        session = self._require_session()
        result = await session.send("CSS.getComputedStyleForNode", {"nodeId": node_id})
        return list(result.get("computedStyle", [])) if result else []

    async def css_get_environment_variables(self) -> list[dict[str, Any]]:
        """Get environment variables for the CSS domain."""
        session = self._require_session()
        result = await session.send("CSS.getEnvironmentVariables", {})
        return list(result.get("environmentVariables", [])) if result else []

    async def css_get_inline_styles(self, node_id: int) -> dict[str, Any]:
        """Get inline styles for a node by ID."""
        session = self._require_session()
        result = await session.send("CSS.getInlineStyles", {"nodeId": node_id})
        return dict(result) if result else {}

    async def css_get_inline_styles_for_node(self, node_id: int) -> dict[str, Any]:
        """Get inline styles for a node by ID (alias)."""
        session = self._require_session()
        result = await session.send("CSS.getInlineStylesForNode", {"nodeId": node_id})
        return dict(result) if result else {}

    async def css_get_layers_for_node(self, node_id: int) -> list[dict[str, Any]]:
        """Get CSS layers for a node by ID."""
        session = self._require_session()
        result = await session.send("CSS.getLayersForNode", {"nodeId": node_id})
        return list(result.get("layers", [])) if result else []

    async def css_get_location_for_selector(
        self, selector: str, stylesheet_id: str
    ) -> dict[str, Any]:
        """Get the location of a CSS selector in a stylesheet."""
        session = self._require_session()
        result = await session.send(
            "CSS.getLocationForSelector", {"selector": selector, "styleSheetId": stylesheet_id}
        )
        return dict(result) if result else {}

    async def css_get_longhand_properties(
        self, shorthand_id: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Get longhand properties for a shorthand property."""
        session = self._require_session()
        result = await session.send("CSS.getLonghandProperties", {"shorthandId": shorthand_id})
        return list(result.get("longhandProperties", [])) if result else []

    async def css_get_matched_styles_for_node(self, node_id: int) -> dict[str, Any]:
        """Get matched styles for a node by ID."""
        session = self._require_session()
        result = await session.send("CSS.getMatchedStylesForNode", {"nodeId": node_id})
        return dict(result) if result else {}

    async def css_get_platform_fonts_for_node(self, node_id: int) -> list[dict[str, Any]]:
        """Get platform fonts for a node by ID."""
        session = self._require_session()
        result = await session.send("CSS.getPlatformFontsForNode", {"nodeId": node_id})
        return list(result.get("fonts", [])) if result else []

    async def css_get_stylesheet_text(self, stylesheet_id: str) -> str:
        """Get the text content of a stylesheet by ID."""
        session = self._require_session()
        result = await session.send("CSS.getStyleSheetText", {"styleSheetId": stylesheet_id})
        return str(result.get("text", "")) if result else ""

    async def css_resolve_values(self, values: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Resolve CSS values."""
        session = self._require_session()
        result = await session.send("CSS.resolveValues", {"values": values})
        return list(result.get("resolvedValues", [])) if result else []

    async def css_set_container_query_condition_text(
        self, stylesheet_id: str, container_query_id: dict[str, Any], text: str
    ) -> None:
        """Set the condition text of a container query."""
        session = self._require_session()
        await session.send(
            "CSS.setContainerQueryConditionText",
            {"styleSheetId": stylesheet_id, "containerQueryId": container_query_id, "text": text},
        )

    async def css_set_effective_property_value_for_node(
        self, node_id: int, property_name: str, value: str
    ) -> None:
        """Set the effective property value for a node."""
        session = self._require_session()
        await session.send(
            "CSS.setEffectivePropertyValueForNode",
            {"nodeId": node_id, "propertyName": property_name, "value": value},
        )

    async def css_set_keyframe_key(
        self, stylesheet_id: str, keyframe_id: dict[str, Any], key_text: str
    ) -> None:
        """Set the key text of a keyframe rule."""
        session = self._require_session()
        await session.send(
            "CSS.setKeyframeKey",
            {"styleSheetId": stylesheet_id, "keyframeId": keyframe_id, "keyText": key_text},
        )

    async def css_set_local_fonts_enabled(self, enabled: bool) -> None:
        """Enable or disable local fonts."""
        session = self._require_session()
        await session.send("CSS.setLocalFontsEnabled", {"enabled": enabled})

    async def css_set_navigation_text(
        self, stylesheet_id: str, navigation_id: dict[str, Any], text: str
    ) -> None:
        """Set the text of a navigation rule."""
        session = self._require_session()
        await session.send(
            "CSS.setNavigationText",
            {"styleSheetId": stylesheet_id, "navigationId": navigation_id, "text": text},
        )

    async def css_set_property_rule_property_name(
        self, stylesheet_id: str, property_rule_id: dict[str, Any], name: str
    ) -> None:
        """Set the property name of a property rule."""
        session = self._require_session()
        await session.send(
            "CSS.setPropertyRulePropertyName",
            {"styleSheetId": stylesheet_id, "propertyRuleId": property_rule_id, "name": name},
        )

    async def css_set_rule_style(
        self, stylesheet_id: str, rule_id: dict[str, Any], style_text: str
    ) -> None:
        """Set the style text of a CSS rule."""
        session = self._require_session()
        await session.send(
            "CSS.setRuleStyle",
            {"styleSheetId": stylesheet_id, "ruleId": rule_id, "style": style_text},
        )

    async def css_set_scope_text(
        self, stylesheet_id: str, scope_id: dict[str, Any], text: str
    ) -> None:
        """Set the text of a scope rule."""
        session = self._require_session()
        await session.send(
            "CSS.setScopeText", {"styleSheetId": stylesheet_id, "scopeId": scope_id, "text": text}
        )

    async def css_set_style_text(self, edits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Set style texts for multiple edits."""
        session = self._require_session()
        result = await session.send("CSS.setStyleTexts", {"edits": edits})
        return list(result.get("styles", [])) if result else []

    async def css_set_style_texts(self, edits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Set style texts for multiple edits (batch)."""
        session = self._require_session()
        result = await session.send("CSS.setStyleTexts", {"edits": edits})
        return list(result.get("styles", [])) if result else []

    async def css_set_stylesheet_text(self, stylesheet_id: str, text: str) -> None:
        """Set the text content of a stylesheet by ID (alias)."""
        session = self._require_session()
        await session.send("CSS.setStyleSheetText", {"styleSheetId": stylesheet_id, "text": text})

    async def css_set_supports_text(
        self, stylesheet_id: str, supports_id: dict[str, Any], text: str
    ) -> None:
        """Set the text of a supports rule."""
        session = self._require_session()
        await session.send(
            "CSS.setSupportsText",
            {"styleSheetId": stylesheet_id, "supportsId": supports_id, "text": text},
        )

    async def css_take_computed_style_updates(self) -> list[dict[str, Any]]:
        """Take computed style updates."""
        session = self._require_session()
        result = await session.send("CSS.takeComputedStyleUpdates", {})
        return list(result.get("computedStyleUpdates", [])) if result else []

    async def css_track_computed_style_updates(self, track_properties: bool = True) -> None:
        """Track computed style updates."""
        session = self._require_session()
        await session.send("CSS.trackComputedStyleUpdates", {"trackProperties": track_properties})

    async def css_track_computed_style_updates_for_node(
        self, node_id: int, track_properties: bool = True
    ) -> None:
        """Track computed style updates for a specific node."""
        session = self._require_session()
        await session.send(
            "CSS.trackComputedStyleUpdatesForNode",
            {"nodeId": node_id, "trackProperties": track_properties},
        )

    # ── Debugging ──────────────────────────────────────────

    async def debug_set_breakpoint(self, url: str, line: int, condition: str | None = None) -> str:
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
        result = await session.send("Debugger.setBreakpointByUrl", params)
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
        await session.send("Debugger.removeBreakpoint", {"breakpointId": breakpoint_id})

    async def debug_step_over(self) -> None:
        """Step over the current statement in the debugger."""
        session = self._require_session()
        await session.debugger.enable()
        await session.debugger.step_over()

    async def debug_step_into(self) -> None:
        """Step into the current function call in the debugger."""
        session = self._require_session()
        await session.debugger.enable()
        await session.debugger.step_into()

    async def debug_step_out(self) -> None:
        """Step out of the current function in the debugger."""
        session = self._require_session()
        await session.debugger.enable()
        await session.debugger.step_out()

    async def debug_pause(self) -> None:
        """Pause JavaScript execution."""
        session = self._require_session()
        await session.debugger.enable()
        paused_event = asyncio.Event()
        handler = lambda _: paused_event.set()  # noqa: E731
        session.on("Debugger.paused", handler)
        try:
            await session.debugger.pause()
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(paused_event.wait(), timeout=5.0)
        finally:
            session.off("Debugger.paused", handler)

    async def debug_resume(self) -> None:
        """Resume JavaScript execution after a pause."""
        session = self._require_session()
        await session.debugger.enable()
        await session.debugger.resume()

    async def debug_get_listeners(self, selector: str) -> list[dict[str, Any]]:
        """Get event listeners attached to an element by CSS selector.

        Args:
            selector: CSS selector for the target element.

        Returns:
            List of listener dicts (type, useCapture, passive, etc.).
        """
        session = self._require_session()
        node_id = await self._find_node(selector)
        resolved = await session.send("DOM.resolveNode", {"nodeId": node_id})
        object_id = resolved.get("object", {}).get("objectId", "")
        if not object_id:
            raise ElementNotFoundError(selector)
        result = await session.send("DOMDebugger.getEventListeners", {"objectId": object_id})
        listeners: list[dict[str, Any]] = []
        for listener in result.get("listeners", []):
            listeners.append(dict(listener))
        return listeners

    async def debug_evaluate_on_call_frame(
        self, call_frame_id: str, expression: str
    ) -> dict[str, Any]:
        """Evaluate a JavaScript expression in the context of a paused call frame."""
        session = self._require_session()
        result = await session.debugger.evaluate_on_call_frame(
            call_frame_id=call_frame_id, expression=expression
        )
        return dict(result)

    async def debug_get_script_source(self, script_id: str) -> str:
        """Get the source code of a script by ID."""
        session = self._require_session()
        result = await session.debugger.get_script_source(script_id=script_id)
        return str(result.get("scriptSource", ""))

    async def debug_get_stack_trace(self) -> dict[str, Any]:
        """Get the current JavaScript stack trace."""
        session = self._require_session()
        result = await session.debugger.get_stack_trace()
        return dict(result)

    async def debug_get_possible_breakpoints(
        self, start: dict[str, Any], end: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Get possible breakpoint locations for a range in a script."""
        session = self._require_session()
        params: dict[str, Any] = {"start": start}
        if end:
            params["end"] = end
        result = await session.debugger.get_possible_breakpoints(**params)
        return [dict(b) for b in result.get("locations", [])] if result else []

    async def debug_search_in_content(
        self, script_id: str, query: str, case_sensitive: bool = False, is_regex: bool = False
    ) -> list[dict[str, Any]]:
        """Search for a string in script content."""
        session = self._require_session()
        params: dict[str, Any] = {"scriptId": script_id, "query": query}
        if case_sensitive:
            params["caseSensitive"] = True
        if is_regex:
            params["isRegex"] = True
        result = await session.debugger.search_in_content(**params)
        return [dict(r) for r in result.get("result", [])] if result else []

    async def debug_set_pause_on_exceptions(self, state: str) -> None:
        """Set pause on exceptions mode (none, uncaught, all)."""
        session = self._require_session()
        await session.debugger.set_pause_on_exceptions(state=state)

    async def debug_set_breakpoints_active(self, active: bool) -> None:
        """Enable or disable all breakpoints."""
        session = self._require_session()
        await session.debugger.set_breakpoints_active(active=active)

    async def debug_set_skip_all_pauses(self, skip: bool) -> None:
        """Skip all pauses for the duration of the current script."""
        session = self._require_session()
        await session.debugger.set_skip_all_pauses(skip=skip)

    async def debug_set_script_source(self, script_id: str, source: str) -> dict[str, Any]:
        """Edit the source code of a live script."""
        session = self._require_session()
        result = await session.debugger.set_script_source(script_id=script_id, source=source)
        return dict(result) if result else {}

    async def debug_continue_to_location(self, url: str, line: int, column: int = 0) -> None:
        """Continue execution until a specific location is reached."""
        session = self._require_session()
        await session.debugger.continue_to_location(
            location={"scriptId": url, "lineNumber": line, "columnNumber": column}
        )

    async def debug_disable(self) -> None:
        """Disable the Debugger domain."""
        session = self._require_session()
        await session.send("Debugger.disable", {})

    async def debug_disassemble_wasm_module(self, script_id: str) -> dict[str, Any]:
        """Disassemble a WASM module by script ID."""
        session = self._require_session()
        result = await session.send("Debugger.disassembleWasmModule", {"scriptId": script_id})
        return dict(result) if result else {}

    async def debug_enable(self) -> None:
        """Enable the Debugger domain."""
        session = self._require_session()
        await session.send("Debugger.enable", {})

    async def debug_get_wasm_bytecode(self, script_id: str, offset: int) -> dict[str, Any]:
        """Get WASM bytecode for a script by ID and offset."""
        session = self._require_session()
        result = await session.send(
            "Debugger.getWasmBytecode", {"scriptId": script_id, "offset": offset}
        )
        return dict(result) if result else {}

    async def debug_next_wasm_disassembly_chunk(self, disassembly_id: str) -> dict[str, Any]:
        """Get the next chunk of a WASM disassembly."""
        session = self._require_session()
        result = await session.send(
            "Debugger.nextWasmDisassemblyChunk", {"disassemblyId": disassembly_id}
        )
        return dict(result) if result else {}

    async def debug_pause_on_async_call(self, operation: str) -> None:
        """Pause on an async call operation."""
        session = self._require_session()
        await session.send("Debugger.pauseOnAsyncCall", {"operation": operation})

    async def debug_restart_frame(self, call_frame_id: str) -> None:
        """Restart a call frame by ID."""
        session = self._require_session()
        await session.send("Debugger.restartFrame", {"callFrameId": call_frame_id})

    async def debug_set_async_call_stack_depth(self, depth: int) -> None:
        """Set the async call stack depth."""
        session = self._require_session()
        await session.send("Debugger.setAsyncCallStackDepth", {"depth": depth})

    async def debug_set_blackbox_execution_contexts(self, unique_ids: list[str]) -> None:
        """Set blackboxed execution contexts by unique IDs."""
        session = self._require_session()
        await session.send("Debugger.setBlackboxExecutionContexts", {"uniqueIds": unique_ids})

    async def debug_set_blackbox_patterns(self, patterns: list[str]) -> None:
        """Set blackbox patterns for script URLs."""
        session = self._require_session()
        await session.send("Debugger.setBlackboxPatterns", {"patterns": patterns})

    async def debug_set_blackboxed_ranges(
        self, script_id: str, positions: list[dict[str, Any]]
    ) -> None:
        """Set blackboxed ranges for a script."""
        session = self._require_session()
        await session.send(
            "Debugger.setBlackboxedRanges", {"scriptId": script_id, "positions": positions}
        )

    async def debug_set_breakpoint_raw(
        self, location: dict[str, Any], condition: str | None = None
    ) -> dict[str, Any]:
        """Set a breakpoint at a raw location in a script."""
        session = self._require_session()
        params: dict[str, Any] = {"location": location}
        if condition is not None:
            params["condition"] = condition
        result = await session.send("Debugger.setBreakpoint", params)
        return dict(result) if result else {}

    async def debug_set_breakpoint_by_url(
        self, url: str, line_number: int, column_number: int = 0, condition: str | None = None
    ) -> dict[str, Any]:
        """Set a breakpoint by URL and line number."""
        session = self._require_session()
        params: dict[str, Any] = {
            "url": url,
            "lineNumber": line_number,
            "columnNumber": column_number,
        }
        if condition is not None:
            params["condition"] = condition
        result = await session.send("Debugger.setBreakpointByUrl", params)
        return dict(result) if result else {}

    async def debug_set_breakpoint_on_function_call(
        self, object_id: str, condition: str | None = None
    ) -> dict[str, Any]:
        """Set a breakpoint on a function call by object ID."""
        session = self._require_session()
        params: dict[str, Any] = {"objectId": object_id}
        if condition is not None:
            params["condition"] = condition
        result = await session.send("Debugger.setBreakpointOnFunctionCall", params)
        return dict(result) if result else {}

    async def debug_set_instrumentation_breakpoint(self, instrumentation: str) -> dict[str, Any]:
        """Set an instrumentation breakpoint."""
        session = self._require_session()
        result = await session.send(
            "Debugger.setInstrumentationBreakpoint", {"instrumentation": instrumentation}
        )
        return dict(result) if result else {}

    async def debug_set_return_value(self, new_value: dict[str, Any]) -> None:
        """Set the return value of the current call frame."""
        session = self._require_session()
        await session.send("Debugger.setReturnValue", {"newValue": new_value})

    async def debug_set_variable_value(
        self, call_frame_id: str, scope_number: int, variable_name: str, new_value: dict[str, Any]
    ) -> None:
        """Set a variable value in a scope of a call frame."""
        session = self._require_session()
        await session.send(
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
        """Get event listeners for an object by its remote object ID."""
        session = self._require_session()
        result = await session.send(
            "DOMDebugger.getEventListeners",
            {"objectId": object_id, "depth": depth, "pierce": pierce},
        )
        return list(result.get("listeners", [])) if result else []

    async def dom_debugger_remove_dom_breakpoint(self, node_id: int, type: str) -> None:
        """Remove a DOM breakpoint from a node by ID."""
        session = self._require_session()
        await session.send("DOMDebugger.removeDOMBreakpoint", {"nodeId": node_id, "type": type})

    async def dom_debugger_remove_event_listener_breakpoint(
        self, event_name: str, target_name: str | None = None
    ) -> None:
        """Remove an event listener breakpoint."""
        session = self._require_session()
        params: dict[str, Any] = {"eventName": event_name}
        if target_name is not None:
            params["targetName"] = target_name
        await session.send("DOMDebugger.removeEventListenerBreakpoint", params)

    async def dom_debugger_remove_instrumentation_breakpoint(self, event_name: str) -> None:
        """Remove an instrumentation breakpoint."""
        session = self._require_session()
        await session.send("DOMDebugger.removeInstrumentationBreakpoint", {"eventName": event_name})

    async def dom_debugger_remove_xhr_breakpoint(self, url: str) -> None:
        """Remove an XHR breakpoint for a URL substring."""
        session = self._require_session()
        await session.send("DOMDebugger.removeXHRBreakpoint", {"url": url})

    async def dom_debugger_set_break_on_csp_violation(self, enabled: bool) -> None:
        """Set whether to break on CSP violations."""
        session = self._require_session()
        await session.send("DOMDebugger.setBreakOnCSPViolation", {"enabled": enabled})

    async def dom_debugger_set_dom_breakpoint(self, node_id: int, type: str) -> None:
        """Set a DOM breakpoint on a node by ID."""
        session = self._require_session()
        await session.send("DOMDebugger.setDOMBreakpoint", {"nodeId": node_id, "type": type})

    async def dom_debugger_set_event_listener_breakpoint(
        self, event_name: str, target_name: str | None = None
    ) -> None:
        """Set an event listener breakpoint."""
        session = self._require_session()
        params: dict[str, Any] = {"eventName": event_name}
        if target_name is not None:
            params["targetName"] = target_name
        await session.send("DOMDebugger.setEventListenerBreakpoint", params)

    async def dom_debugger_set_instrumentation_breakpoint(self, event_name: str) -> None:
        """Set an instrumentation breakpoint."""
        session = self._require_session()
        await session.send("DOMDebugger.setInstrumentationBreakpoint", {"eventName": event_name})

    async def dom_debugger_set_xhr_breakpoint(self, url: str) -> None:
        """Set an XHR breakpoint for a URL substring."""
        session = self._require_session()
        await session.send("DOMDebugger.setXHRBreakpoint", {"url": url})

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

    async def overlay_highlight(self, selector: str, color: str = "rgba(255,0,0,0.5)") -> None:
        """Highlight an element with a colored overlay.

        Args:
            selector: CSS selector for the element to highlight.
            color: RGBA color string for the highlight overlay.
        """
        session = self._require_session()
        await session.dom.enable()
        await session.overlay.enable()
        node_id = await self._find_node(selector)
        highlight_config: dict[str, Any] = {
            "showInfo": True,
            "contentColor": {"r": 255, "g": 0, "b": 0, "a": 0.5},
            "contentOutlineColor": {"r": 0, "g": 0, "b": 0, "a": 0},
            "borderColor": {"r": 0, "g": 0, "b": 0, "a": 0},
            "paddingColor": {"r": 0, "g": 0, "b": 0, "a": 0},
            "marginColor": {"r": 0, "g": 0, "b": 0, "a": 0},
        }
        await session.overlay.highlight_node(
            highlight_config=highlight_config,
            node_id=node_id,
        )

    async def overlay_clear(self) -> None:
        """Clear all highlight overlays from the page."""
        session = self._require_session()
        await session.overlay.hide_highlight()

    async def overlay_enable(self) -> None:
        """Enable the overlay domain."""
        session = self._require_session()
        await session.overlay.enable()

    async def overlay_disable(self) -> None:
        """Disable the overlay domain."""
        session = self._require_session()
        await session.overlay.disable()

    async def overlay_highlight_node(self, node_id: int, color: str = "rgba(255,0,0,0.5)") -> None:
        """Highlight a DOM node by node ID."""
        session = self._require_session()
        highlight_config: dict[str, Any] = {
            "showStyle": False,
            "showRulers": False,
            "showExtensionLines": False,
            "contentColor": {"r": 255, "g": 0, "b": 0, "a": 0.5},
        }
        await session.overlay.highlight_node(
            highlight_config=highlight_config,
            node_id=node_id,
        )

    async def overlay_highlight_quad(
        self, quad: list[float], color: str = "rgba(255,0,0,0.5)"
    ) -> None:
        """Highlight a quad region on the page."""
        session = self._require_session()
        await session.overlay.highlight_quad(
            quad=quad,
            color={"r": 255, "g": 0, "b": 0, "a": 0.5},
        )

    async def overlay_highlight_rect(
        self, x: float, y: float, width: float, height: float, color: str = "rgba(255,0,0,0.5)"
    ) -> None:
        """Highlight a rectangular region on the page."""
        session = self._require_session()
        await session.overlay.highlight_rect(
            x=x,
            y=y,
            width=width,
            height=height,
            outline_color={"r": 255, "g": 0, "b": 0, "a": 0.5},
        )

    async def overlay_set_inspect_mode(self, mode: str = "searchForNode") -> None:
        """Set the inspect mode for element selection."""
        session = self._require_session()
        await session.overlay.set_inspect_mode(mode=mode, highlight_config={})

    async def overlay_set_show_fps_counter(self, show: bool) -> None:
        """Show or hide the FPS counter overlay."""
        session = self._require_session()
        await session.overlay.set_show_fps_counter(show=show)

    async def overlay_set_show_paint_rects(self, show: bool) -> None:
        """Show or hide paint rectangles overlay."""
        session = self._require_session()
        await session.send("Overlay.setShowPaintRects", {"result": show})

    async def overlay_set_show_debug_borders(self, show: bool) -> None:
        """Show or hide debug borders overlay."""
        session = self._require_session()
        await session.overlay.set_show_debug_borders(show=show)

    async def overlay_set_show_ad_highlights(self, show: bool) -> None:
        """Show or hide ad highlights overlay."""
        session = self._require_session()
        await session.overlay.set_show_ad_highlights(show=show)

    async def overlay_get_grid_highlight_objects_for_test(self, node_id: int) -> dict[str, Any]:
        """Get grid highlight objects for testing."""
        session = self._require_session()
        result = await session.send("Overlay.getGridHighlightObjectsForTest", {"nodeId": node_id})
        return dict(result) if result else {}

    async def overlay_get_highlight_object_for_test(
        self,
        node_id: int,
        include_distance: bool = False,
        include_style: bool = False,
        color_format: str = "hex",
    ) -> dict[str, Any]:
        """Get highlight object for testing."""
        session = self._require_session()
        params: dict[str, Any] = {
            "nodeId": node_id,
            "includeDistance": include_distance,
            "includeStyle": include_style,
            "colorFormat": color_format,
        }
        result = await session.send("Overlay.getHighlightObjectForTest", params)
        return dict(result) if result else {}

    async def overlay_get_source_order_highlight_object_for_test(
        self, node_id: int
    ) -> dict[str, Any]:
        """Get source order highlight object for testing."""
        session = self._require_session()
        result = await session.send(
            "Overlay.getSourceOrderHighlightObjectForTest", {"nodeId": node_id}
        )
        return dict(result) if result else {}

    async def overlay_hide_highlight(self) -> None:
        """Hide any highlight overlay."""
        session = self._require_session()
        await session.send("Overlay.hideHighlight", {})

    async def overlay_highlight_source_order(self, source_order_config: dict[str, Any]) -> None:
        """Highlight the source order of a node."""
        session = self._require_session()
        await session.send(
            "Overlay.highlightSourceOrder", {"sourceOrderConfig": source_order_config}
        )

    async def overlay_set_paused_in_debugger_message(self, message: str = "") -> None:
        """Set the message displayed when paused in the debugger."""
        session = self._require_session()
        params: dict[str, Any] = {}
        if message:
            params["message"] = message
        await session.send("Overlay.setPausedInDebuggerMessage", params)

    async def overlay_set_show_container_query_overlays(self, show: bool) -> None:
        """Show or hide container query overlays."""
        session = self._require_session()
        await session.send("Overlay.setShowContainerQueryOverlays", {"show": show})

    async def overlay_set_show_display_cutout(self, show: bool) -> None:
        """Show or hide display cutout overlay."""
        session = self._require_session()
        await session.send("Overlay.setShowDisplayCutout", {"show": show})

    async def overlay_set_show_flex_overlays(self, show: bool) -> None:
        """Show or hide flex overlays."""
        session = self._require_session()
        await session.send("Overlay.setShowFlexOverlays", {"show": show})

    async def overlay_set_show_grid_overlays(
        self, show_grid_overlays: list[dict[str, Any]]
    ) -> None:
        """Show grid overlays for the given configurations."""
        session = self._require_session()
        await session.send("Overlay.setShowGridOverlays", {"showGridOverlays": show_grid_overlays})

    async def overlay_set_show_hinge(self, hinge_config: dict[str, Any] | None = None) -> None:
        """Show or hide the hinge overlay."""
        session = self._require_session()
        params: dict[str, Any] = {}
        if hinge_config is not None:
            params["hingeConfig"] = hinge_config
        await session.send("Overlay.setShowHinge", params)

    async def overlay_set_show_inspected_element_anchor(self, show: bool) -> None:
        """Show or hide the inspected element anchor."""
        session = self._require_session()
        await session.send("Overlay.setShowInspectedElementAnchor", {"show": show})

    async def overlay_set_show_isolated_elements(
        self, isolated_element_highlight_configs: list[dict[str, Any]]
    ) -> None:
        """Show isolated elements with the given highlight configurations."""
        session = self._require_session()
        await session.send(
            "Overlay.setShowIsolatedElements",
            {"isolatedElementHighlightConfigs": isolated_element_highlight_configs},
        )

    async def overlay_set_show_layout_shift_regions(self, show: bool) -> None:
        """Show or hide layout shift regions."""
        session = self._require_session()
        await session.send("Overlay.setShowLayoutShiftRegions", {"result": show})

    async def overlay_set_show_scroll_bottleneck_rects(self, show: bool) -> None:
        """Show or hide scroll bottleneck rects."""
        session = self._require_session()
        await session.send("Overlay.setShowScrollBottleneckRects", {"show": show})

    async def overlay_set_show_scroll_snap_overlays(self, show: bool) -> None:
        """Show or hide scroll snap overlays."""
        session = self._require_session()
        await session.send("Overlay.setShowScrollSnapOverlays", {"show": show})

    async def overlay_set_show_viewport_size_on_resize(self, show: bool) -> None:
        """Show or hide viewport size on resize."""
        session = self._require_session()
        await session.send("Overlay.setShowViewportSizeOnResize", {"show": show})

    async def overlay_set_show_window_controls_overlay(self, show: bool) -> None:
        """Show or hide window controls overlay."""
        session = self._require_session()
        await session.send("Overlay.setShowWindowControlsOverlay", {"show": show})

    # ── Runtime ───────────────────────────────────────────

    async def runtime_evaluate(
        self,
        expression: str,
        await_promise: bool = False,
        return_by_value: bool = False,
    ) -> dict[str, Any]:
        """Evaluate a JavaScript expression."""
        session = self._require_session()
        result = await session.runtime.evaluate(
            expression,
            await_promise=await_promise,
            return_by_value=return_by_value,
        )
        return dict(result) if result else {}

    async def runtime_compile_script(
        self,
        expression: str,
        source_url: str = "",
        persist_script: bool = False,
    ) -> dict[str, Any]:
        """Compile a JavaScript expression without running it."""
        session = self._require_session()
        result = await session.runtime.compile_script(
            expression=expression,
            source_url=source_url,
            persist_script=persist_script,
        )
        return dict(result) if result else {}

    async def runtime_run_script(
        self, script_id: str, await_promise: bool = False
    ) -> dict[str, Any]:
        """Run a previously compiled script by ID."""
        session = self._require_session()
        result = await session.runtime.run_script(
            script_id=script_id,
            await_promise=await_promise,
        )
        return dict(result) if result else {}

    async def runtime_call_function_on(
        self,
        function_declaration: str,
        object_id: str = "",
        arguments: list[dict[str, Any]] | None = None,
        await_promise: bool = False,
        return_by_value: bool = False,
    ) -> dict[str, Any]:
        """Call a function on a remote object."""
        session = self._require_session()
        params: dict[str, Any] = {
            "function_declaration": function_declaration,
            "await_promise": await_promise,
            "return_by_value": return_by_value,
        }
        if object_id:
            params["object_id"] = object_id
        if arguments:
            params["arguments"] = arguments
        result = await session.runtime.call_function_on(**params)
        return dict(result) if result else {}

    async def runtime_get_properties(
        self, object_id: str, own_properties: bool = True
    ) -> dict[str, Any]:
        """Get properties of a remote object."""
        session = self._require_session()
        result = await session.runtime.get_properties(
            object_id=object_id,
            own_properties=own_properties,
        )
        return dict(result) if result else {}

    async def runtime_release_object(self, object_id: str) -> None:
        """Release a remote object."""
        session = self._require_session()
        await session.runtime.release_object(object_id=object_id)

    async def runtime_release_object_group(self, object_group: str) -> None:
        """Release all objects in a group."""
        session = self._require_session()
        await session.runtime.release_object_group(object_group=object_group)

    async def runtime_discard_console_entries(self) -> None:
        """Discard collected console entries."""
        session = self._require_session()
        await session.runtime.discard_console_entries()

    async def runtime_get_heap_usage(self) -> dict[str, Any]:
        """Get the current heap usage."""
        session = self._require_session()
        result = await session.runtime.get_heap_usage()
        return dict(result) if result else {}

    async def runtime_global_lexical_scope_names(
        self, execution_context_id: int | None = None
    ) -> dict[str, Any]:
        """Get global lexical scope names."""
        session = self._require_session()
        params: dict[str, Any] = {}
        if execution_context_id is not None:
            params["execution_context_id"] = execution_context_id
        result = await session.runtime.global_lexical_scope_names(**params)
        return dict(result) if result else {}

    async def runtime_add_binding(
        self, name: str, execution_context_name: str | None = None
    ) -> None:
        """Add a binding with the given name."""
        session = self._require_session()
        params: dict[str, Any] = {"name": name}
        if execution_context_name is not None:
            params["executionContextName"] = execution_context_name
        await session.send("Runtime.addBinding", params)

    async def runtime_await_promise(
        self, promise_object_id: str, return_by_value: bool = False
    ) -> dict[str, Any]:
        """Await a promise by its remote object ID."""
        session = self._require_session()
        result = await session.send(
            "Runtime.awaitPromise",
            {
                "promiseObjectId": promise_object_id,
                "returnByValue": return_by_value,
            },
        )
        return dict(result) if result else {}

    async def runtime_collect_garbage(self) -> None:
        """Collect garbage."""
        session = self._require_session()
        await session.send("Runtime.collectGarbage", {})

    async def runtime_disable(self) -> None:
        """Disable the Runtime domain."""
        session = self._require_session()
        await session.send("Runtime.disable", {})

    async def runtime_enable(self) -> None:
        """Enable the Runtime domain."""
        session = self._require_session()
        await session.send("Runtime.enable", {})

    async def runtime_get_exception_details(self, error_object_id: str) -> dict[str, Any]:
        """Get exception details for an error object."""
        session = self._require_session()
        result = await session.send(
            "Runtime.getExceptionDetails", {"errorObjectId": error_object_id}
        )
        return dict(result) if result else {}

    async def runtime_get_isolate_id(self) -> dict[str, Any]:
        """Get the isolate ID."""
        session = self._require_session()
        result = await session.send("Runtime.getIsolateId", {})
        return dict(result) if result else {}

    async def runtime_query_objects(self, prototype_object_id: str) -> dict[str, Any]:
        """Query objects by prototype."""
        session = self._require_session()
        result = await session.send(
            "Runtime.queryObjects", {"prototypeObjectId": prototype_object_id}
        )
        return dict(result) if result else {}

    async def runtime_remove_binding(self, name: str) -> None:
        """Remove a previously added binding."""
        session = self._require_session()
        await session.send("Runtime.removeBinding", {"name": name})

    async def runtime_run_if_waiting_for_debugger(self) -> None:
        """Run if waiting for debugger to pause."""
        session = self._require_session()
        await session.send("Runtime.runIfWaitingForDebugger", {})

    async def runtime_set_async_call_stack_depth(self, max_depth: int) -> None:
        """Set the async call stack depth."""
        session = self._require_session()
        await session.send("Runtime.setAsyncCallStackDepth", {"maxDepth": max_depth})

    async def runtime_set_custom_object_formatter_enabled(self, enabled: bool) -> None:
        """Enable or disable the custom object formatter."""
        session = self._require_session()
        await session.send("Runtime.setCustomObjectFormatterEnabled", {"enabled": enabled})

    async def runtime_set_max_call_stack_size_to_capture(self, size: int) -> None:
        """Set the max call stack size to capture."""
        session = self._require_session()
        await session.send("Runtime.setMaxCallStackSizeToCapture", {"size": size})

    async def runtime_terminate_execution(self) -> None:
        """Terminate the current execution."""
        session = self._require_session()
        await session.send("Runtime.terminateExecution", {})

    # ── Schema ─────────────────────────────────────────────

    async def schema_get_domains(self) -> dict[str, Any]:
        """Get all available CDP domains."""
        session = self._require_session()
        result = await session.send("Schema.getDomains", {})
        return dict(result) if result else {}

    # ── Security ──────────────────────────────────────────

    async def security_disable(self) -> None:
        """Disable the Security domain."""
        session = self._require_session()
        await session.send("Security.disable", {})

    async def security_enable(self) -> None:
        """Enable the Security domain."""
        session = self._require_session()
        await session.send("Security.enable", {})

    async def security_get_visible_security_state(self) -> dict[str, Any]:
        """Get the visible security state of the current page.

        Bug #16: ``Security.getVisibleSecurityState`` was removed from CDP
        (Chrome 137+, 2025). The supported replacement is to subscribe to
        ``Security.securityStateChanged`` events, but for a one-shot query
        we derive the visible security state from the current navigation
        entry and the page URL: HTTPS pages are reported as ``secure``,
        HTTP pages as ``insecure``, and certificate/SSL errors are surfaced
        via ``Security.certificateError`` events (handled separately).
        """
        session = self._require_session()
        # Enable Security so any future state-change events fire, and so
        # the call mirrors the old behavior as closely as possible.
        with contextlib.suppress(Exception):
            await session.send("Security.enable", {})
        # Pull the current URL from the navigation history.
        url = self._current_url
        if not url:
            try:
                history = await session.send("Page.getNavigationHistory", {})
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
        """Handle a certificate error event."""
        session = self._require_session()
        await session.send(
            "Security.handleCertificateError", {"eventId": event_id, "action": action}
        )

    async def security_set_ignore_certificate_errors(self, ignore: bool) -> None:
        """Set whether to ignore certificate errors."""
        session = self._require_session()
        await session.send("Security.setIgnoreCertificateErrors", {"ignore": ignore})

    async def security_set_override_certificate_errors(self, override: bool) -> None:
        """Set whether to override certificate errors."""
        session = self._require_session()
        await session.send("Security.setOverrideCertificateErrors", {"override": override})

    # ── Sensor ─────────────────────────────────────────────

    async def sensor_clear_sensor_override(self, sensor_type: str) -> None:
        """Clear a sensor override."""
        session = self._require_session()
        await session.send("Sensor.clearSensorOverride", {"type": sensor_type})

    async def sensor_disable(self) -> None:
        """Disable the Sensor domain."""
        session = self._require_session()
        await session.send("Sensor.disable", {})

    async def sensor_enable(self) -> None:
        """Enable the Sensor domain."""
        session = self._require_session()
        await session.send("Sensor.enable", {})

    async def sensor_set_sensor_override(
        self, sensor_type: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """Set a sensor override."""
        session = self._require_session()
        params: dict[str, Any] = {"type": sensor_type}
        if metadata is not None:
            params["metadata"] = metadata
        await session.send("Sensor.setSensorOverride", params)

    # ── Target ────────────────────────────────────────────

    async def target_get_targets(self) -> list[dict[str, Any]]:
        """Get all available targets."""
        session = self._require_session()
        result = await session.target.get_targets()
        return list(result.get("targetInfos", []))

    async def target_create_target(self, url: str) -> str:
        """Create a new target (tab) with the given URL."""
        session = self._require_session()
        result = await session.target.create_target(url)
        return str(result.get("targetId", ""))

    async def target_close_target(self, target_id: str) -> None:
        """Close a target by ID."""
        session = self._require_session()
        await session.target.close_target(target_id)

    async def target_activate_target(self, target_id: str) -> None:
        """Activate (focus) a target by ID."""
        session = self._require_session()
        await session.target.activate_target(target_id)

    async def target_attach_to_target(self, target_id: str, flatten: bool = True) -> str:
        """Attach to a target by ID."""
        session = self._require_session()
        result = await session.target.attach_to_target(
            target_id=target_id,
            flatten=flatten,
        )
        return str(result.get("sessionId", ""))

    async def target_detach_from_target(self, session_id: str) -> None:
        """Detach from a target by session ID."""
        session = self._require_session()
        await session.target.detach_from_target(session_id=session_id)

    async def target_set_auto_attach(
        self, auto_attach: bool, wait_for_debugger_on_start: bool = False
    ) -> None:
        """Set auto-attach for new targets."""
        session = self._require_session()
        await session.target.set_auto_attach(
            auto_attach=auto_attach,
            wait_for_debugger_on_start=wait_for_debugger_on_start,
        )

    async def target_set_discover_targets(self, discover: bool) -> None:
        """Enable or disable target discovery."""
        session = self._require_session()
        await session.target.set_discover_targets(discover=discover)

    async def target_get_target_info(self, target_id: str) -> dict[str, Any]:
        """Get info about a specific target."""
        session = self._require_session()
        result = await session.target.get_target_info(target_id=target_id)
        return dict(result) if result else {}

    async def target_create_browser_context(self) -> str:
        """Create a new browser context."""
        session = self._require_session()
        result = await session.target.create_browser_context()
        return str(result.get("browserContextId", ""))

    async def target_attach_to_browser_target(self) -> str:
        """Attach to the browser target."""
        session = self._require_session()
        result = await session.send("Target.attachToBrowserTarget", {})
        return str(result.get("sessionId", ""))

    async def target_auto_attach_related(
        self, target_id: str, wait_for_debugger_on_start: bool = False
    ) -> None:
        """Auto-attach to related targets of a given target."""
        session = self._require_session()
        await session.send(
            "Target.autoAttachRelated",
            {
                "targetId": target_id,
                "waitForDebuggerOnStart": wait_for_debugger_on_start,
            },
        )

    async def target_dispose_browser_context(self, browser_context_id: str) -> None:
        """Dispose a browser context by ID."""
        session = self._require_session()
        await session.send(
            "Target.disposeBrowserContext",
            {"browserContextId": browser_context_id},
        )

    async def target_expose_dev_tools_protocol(self, target_id: str, binding_name: str) -> None:
        """Expose DevTools protocol API to the target."""
        session = self._require_session()
        await session.send(
            "Target.exposeDevToolsProtocol",
            {"targetId": target_id, "bindingName": binding_name},
        )

    async def target_get_browser_contexts(self) -> list[str]:
        """Get all browser contexts."""
        session = self._require_session()
        result = await session.send("Target.getBrowserContexts", {})
        return list(result.get("browserContextIds", [])) if result else []

    async def target_get_dev_tools_target(self, target_id: str) -> str:
        """Get the DevTools target for a given target."""
        session = self._require_session()
        result = await session.send("Target.getDevToolsTarget", {"targetId": target_id})
        return str(result.get("targetId", ""))

    async def target_open_dev_tools(self, target_id: str) -> None:
        """Open DevTools for a target."""
        session = self._require_session()
        await session.send("Target.openDevTools", {"targetId": target_id})

    async def target_send_message_to_target(self, session_id: str, message: str) -> None:
        """Send a message to a target via session ID."""
        session = self._require_session()
        await session.send(
            "Target.sendMessageToTarget",
            {"sessionId": session_id, "message": message},
        )

    async def target_set_remote_locations(self, locations: list[dict[str, str]]) -> None:
        """Set remote locations for target discovery."""
        session = self._require_session()
        await session.send("Target.setRemoteLocations", {"locations": locations})

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

        Bug #14: previously this used ``DOMStorage.getDOMStorageItems`` with
        a ``storageId`` built from the page's security origin. On Chrome 150
        that call intermittently raised
        ``[-32000] Frame not found for the given storage id`` because the
        DOMStorage domain resolves the storage via the frame tree and the
        frame lookup can fail depending on timing. Reading via
        ``Runtime.evaluate`` against ``window.localStorage`` /
        ``window.sessionStorage`` is more reliable and avoids the frame
        resolution path entirely.
        """
        session = self._require_session()
        storage_obj = "localStorage" if storage_type == "local" else "sessionStorage"
        js = (
            f"(function(){{try{{return {storage_obj}.getItem({json.dumps(key)})||''}}"
            f"catch(e){{return ''}}}})()"
        )
        result = await session.runtime.evaluate(js, await_promise=False)
        value = result.get("result", {}).get("value")
        return str(value) if value is not None else ""

    async def storage_set(self, key: str, value: str, storage_type: str = "local") -> None:
        """Set a value in DOM storage (local or session).

        Args:
            key: The storage key.
            value: The value to store.
            storage_type: "local" or "session".
        """
        session = self._require_session()
        storage_obj = "localStorage" if storage_type == "local" else "sessionStorage"
        js = (
            f"(function(){{try{{{storage_obj}.setItem({json.dumps(key)},"
            f"{json.dumps(value)});return 'ok'}}catch(e){{return e.message}}}})()"
        )
        result = await session.runtime.evaluate(js, await_promise=False)
        msg = result.get("result", {}).get("value")
        if msg and msg != "ok":
            raise WavexisError(f"storage_set failed: {msg}")

    async def storage_clear(self, storage_type: str = "local") -> None:
        """Clear all entries in DOM storage.

        Args:
            storage_type: "local" or "session".
        """
        session = self._require_session()
        storage_obj = "localStorage" if storage_type == "local" else "sessionStorage"
        js = (
            f"(function(){{try{{{storage_obj}.clear();return 'ok'}}"
            f"catch(e){{return e.message}}}})()"
        )
        result = await session.runtime.evaluate(js, await_promise=False)
        msg = result.get("result", {}).get("value")
        if msg and msg != "ok":
            raise WavexisError(f"storage_clear failed: {msg}")

    async def storage_list(self, storage_type: str = "local") -> dict[str, str]:
        """List all key-value pairs in DOM storage.

        Args:
            storage_type: "local" or "session".

        Returns:
            Dict mapping keys to values.
        """
        session = self._require_session()
        storage_obj = "localStorage" if storage_type == "local" else "sessionStorage"
        js = (
            f"(function(){{try{{"
            f"var out={{}};"
            f"for(var i=0;i<{storage_obj}.length;i++){{"
            f"var k={storage_obj}.key(i);out[k]={storage_obj}.getItem(k);}}"
            f"return JSON.stringify(out);}}"
            f"catch(e){{return '{{}}'}}}})()"
        )
        result = await session.runtime.evaluate(js, await_promise=False)
        raw = result.get("result", {}).get("value") or "{}"
        try:
            loaded = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return {}
        if not isinstance(loaded, dict):
            return {}
        return {str(k): str(v) for k, v in loaded.items()}

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

        # First, get the actual cacheId for the given cache_name
        caches_result = await session.send(
            "CacheStorage.requestCacheNames",
            {"securityOrigin": self._get_origin()},
        )

        # Find the cacheId for the requested cache_name
        cache_id = None
        for cache in caches_result.get("caches", []):
            if cache.get("cacheName") == cache_name:
                cache_id = cache.get("cacheId")
                break

        if not cache_id:
            return []

        result = await session.send(
            "CacheStorage.requestEntries",
            {"cacheId": cache_id, "skipCount": 0, "pageSize": 1000},
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

        # First, get the actual cacheId for the given cache_name
        caches_result = await session.send(
            "CacheStorage.requestCacheNames",
            {"securityOrigin": self._get_origin()},
        )

        # Find the cacheId for the requested cache_name
        cache_id = None
        for cache in caches_result.get("caches", []):
            if cache.get("cacheName") == cache_name:
                cache_id = cache.get("cacheId")
                break

        if cache_id:
            await session.send(
                "CacheStorage.deleteCache",
                {"cacheId": cache_id},
            )

    async def cache_storage_delete_cache(self, cache_id: str) -> None:
        """Delete a cache by its CDP cache ID.

        Args:
            cache_id: The CDP cache identifier.
        """
        session = self._require_session()
        await session.send("CacheStorage.deleteCache", {"cacheId": cache_id})

    async def cache_storage_delete_entry(self, cache_id: str, request: str) -> None:
        """Delete a specific entry from a cache.

        Args:
            cache_id: The CDP cache identifier.
            request: The request URL of the entry to delete.
        """
        session = self._require_session()
        await session.send(
            "CacheStorage.deleteEntry",
            {"cacheId": cache_id, "request": request},
        )

    async def cache_storage_request_cache_names(
        self, security_origin: str | None = None
    ) -> list[dict[str, Any]]:
        """Request cache names for a security origin.

        Args:
            security_origin: Optional security origin. If None, uses the current page.

        Returns:
            List of cache info dicts with cacheId and cacheName.
        """
        session = self._require_session()
        params: dict[str, Any] = {}
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        else:
            params["securityOrigin"] = self._get_origin()
        result = await session.send("CacheStorage.requestCacheNames", params)
        return [dict(c) for c in result.get("caches", [])] if result else []

    async def cache_storage_request_cached_response(
        self, cache_id: str, request_url: str, request_headers: list[dict[str, str]] | None = None
    ) -> dict[str, Any]:
        """Request a cached response for a specific request.

        Args:
            cache_id: The CDP cache identifier.
            request_url: The request URL.
            request_headers: Optional list of request header dicts.

        Returns:
            The cached response dict.
        """
        session = self._require_session()
        params: dict[str, Any] = {"cacheId": cache_id, "requestURL": request_url}
        if request_headers is not None:
            params["requestHeaders"] = request_headers
        return dict(await session.send("CacheStorage.requestCachedResponse", params))

    async def cache_storage_request_entries(
        self, cache_id: str, skip_count: int = 0, page_size: int = 100
    ) -> list[dict[str, Any]]:
        """Request entries from a cache.

        Args:
            cache_id: The CDP cache identifier.
            skip_count: Number of entries to skip.
            page_size: Maximum number of entries to return.

        Returns:
            List of cache entry dicts.
        """
        session = self._require_session()
        result = await session.send(
            "CacheStorage.requestEntries",
            {
                "cacheId": cache_id,
                "skipCount": skip_count,
                "pageSize": page_size,
            },
        )
        return [dict(e) for e in result.get("cacheDataEntries", [])] if result else []

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

    async def indexeddb_get_data(self, database: str, store: str, key: str = "") -> Any:
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

    async def storage_clear_data_for_origin(self, origin: str, storage_types: str = "all") -> None:
        """Clear storage data for a given origin."""
        session = self._require_session()
        await session.storage.clear_data_for_origin(origin=origin, storage_types=storage_types)

    async def storage_get_usage_and_quota(self, origin: str) -> dict[str, Any]:
        """Get usage and quota for a given origin."""
        session = self._require_session()
        return dict(await session.storage.get_usage_and_quota(origin=origin))

    async def storage_get_trust_tokens(self) -> list[dict[str, Any]]:
        """Get all trust tokens for the current origin."""
        session = self._require_session()
        result = await session.storage.get_trust_tokens()
        return [dict(t) for t in result.get("tokens", [])] if result else []

    async def storage_clear_trust_tokens(self, origin: str) -> None:
        """Clear trust tokens for a given origin."""
        session = self._require_session()
        await session.storage.clear_trust_tokens(issuer_origin=origin)

    async def storage_get_shared_storage_entries(self, owner_origin: str) -> list[dict[str, Any]]:
        """Get shared storage entries for an owner origin."""
        session = self._require_session()
        result = await session.storage.get_shared_storage_entries(owner_origin=owner_origin)
        return [dict(e) for e in result.get("entries", [])] if result else []

    async def storage_set_shared_storage_entry(
        self, owner_origin: str, key: str, value: str
    ) -> None:
        """Set a shared storage entry."""
        session = self._require_session()
        await session.storage.set_shared_storage_entry(
            owner_origin=owner_origin, key=key, value=value
        )

    async def storage_delete_shared_storage_entry(self, owner_origin: str, key: str) -> None:
        """Delete a shared storage entry."""
        session = self._require_session()
        await session.storage.delete_shared_storage_entry(owner_origin=owner_origin, key=key)

    async def storage_clear_shared_storage_entries(self, owner_origin: str) -> None:
        """Clear all shared storage entries for an owner origin."""
        session = self._require_session()
        await session.storage.clear_shared_storage_entries(owner_origin=owner_origin)

    async def storage_get_interest_group_details(
        self, owner_origin: str, name: str
    ) -> dict[str, Any]:
        """Get interest group details."""
        session = self._require_session()
        return dict(
            await session.storage.get_interest_group_details(owner_origin=owner_origin, name=name)
        )

    async def storage_override_quota_for_origin(
        self, origin: str, quota_size: float | None = None
    ) -> None:
        """Override quota for a given origin."""
        session = self._require_session()
        params: dict[str, Any] = {"origin": origin}
        if quota_size is not None:
            params["quotaSize"] = quota_size
        await session.storage.override_quota_for_origin(**params)

    async def storage_clear_data_for_storage_key(
        self, storage_key: str, storage_types: str = "all"
    ) -> None:
        """Clear storage data for a given storage key."""
        session = self._require_session()
        await session.send(
            "Storage.clearDataForStorageKey",
            {"storageKey": storage_key, "storageTypes": storage_types},
        )

    async def storage_delete_storage_bucket(self, storage_key: str, bucket_name: str) -> None:
        """Delete a storage bucket."""
        session = self._require_session()
        await session.send(
            "Storage.deleteStorageBucket",
            {"storageKey": storage_key, "bucketName": bucket_name},
        )

    async def storage_get_related_website_sets(self) -> list[dict[str, Any]]:
        """Get related website sets."""
        session = self._require_session()
        result = await session.send("Storage.getRelatedWebsiteSets", {})
        return [dict(s) for s in result.get("sets", [])] if result else []

    async def storage_get_shared_storage_metadata(self, owner_origin: str) -> dict[str, Any]:
        """Get shared storage metadata for an owner origin."""
        session = self._require_session()
        return dict(
            await session.send(
                "Storage.getSharedStorageMetadata",
                {"ownerOrigin": owner_origin},
            )
        )

    async def storage_get_storage_key(self, frame_id: str) -> str:
        """Get storage key for a frame."""
        session = self._require_session()
        result = await session.send("Storage.getStorageKey", {"frameId": frame_id})
        return result.get("storageKey", "")

    async def storage_get_storage_key_for_frame(self, frame_id: str) -> str:
        """Get storage key for a frame (alternative endpoint)."""
        session = self._require_session()
        result = await session.send("Storage.getStorageKeyForFrame", {"frameId": frame_id})
        return result.get("storageKey", "")

    async def storage_reset_shared_storage_budget(self, owner_origin: str) -> None:
        """Reset shared storage budget for an owner origin."""
        session = self._require_session()
        await session.send(
            "Storage.resetSharedStorageBudget",
            {"ownerOrigin": owner_origin},
        )

    async def storage_run_bounce_tracking_mitigations(self) -> None:
        """Run bounce tracking mitigations."""
        session = self._require_session()
        await session.send("Storage.runBounceTrackingMitigations", {})

    async def storage_set_cookies(self, cookies: list[dict[str, Any]]) -> None:
        """Set cookies."""
        session = self._require_session()
        await session.send("Storage.setCookies", {"cookies": cookies})

    async def storage_set_interest_group_auction_tracking(
        self, enable: bool, context_id: int | None = None
    ) -> None:
        """Set interest group auction tracking."""
        session = self._require_session()
        params: dict[str, Any] = {"enable": enable}
        if context_id is not None:
            params["contextId"] = context_id
        await session.send("Storage.setInterestGroupAuctionTracking", params)

    async def storage_set_interest_group_tracking(self, enable: bool) -> None:
        """Set interest group tracking."""
        session = self._require_session()
        await session.send("Storage.setInterestGroupTracking", {"enable": enable})

    async def storage_set_protected_audience_k_anonymity(
        self, storage_key: str, hashed_mac_key: str
    ) -> None:
        """Set protected audience k-anonymity."""
        session = self._require_session()
        await session.send(
            "Storage.setProtectedAudienceKAnonymity",
            {"storageKey": storage_key, "hashedMacKey": hashed_mac_key},
        )

    async def storage_set_shared_storage_tracking(self, enable: bool) -> None:
        """Set shared storage tracking."""
        session = self._require_session()
        await session.send("Storage.setSharedStorageTracking", {"enable": enable})

    async def storage_set_storage_bucket_tracking(
        self, storage_key: str, bucket_name: str, enable: bool
    ) -> None:
        """Set storage bucket tracking."""
        session = self._require_session()
        await session.send(
            "Storage.setStorageBucketTracking",
            {
                "storageKey": storage_key,
                "bucketName": bucket_name,
                "enable": enable,
            },
        )

    async def storage_track_cache_storage_for_origin(self, origin: str) -> None:
        """Track cache storage for an origin."""
        session = self._require_session()
        await session.send("Storage.trackCacheStorageForOrigin", {"origin": origin})

    async def storage_track_cache_storage_for_storage_key(self, storage_key: str) -> None:
        """Track cache storage for a storage key."""
        session = self._require_session()
        await session.send("Storage.trackCacheStorageForStorageKey", {"storageKey": storage_key})

    async def storage_track_indexed_db_for_origin(self, origin: str) -> None:
        """Track IndexedDB for an origin."""
        session = self._require_session()
        await session.send("Storage.trackIndexedDBForOrigin", {"origin": origin})

    async def storage_track_indexed_db_for_storage_key(self, storage_key: str) -> None:
        """Track IndexedDB for a storage key."""
        session = self._require_session()
        await session.send("Storage.trackIndexedDBForStorageKey", {"storageKey": storage_key})

    async def storage_untrack_cache_storage_for_origin(self, origin: str) -> None:
        """Untrack cache storage for an origin."""
        session = self._require_session()
        await session.send("Storage.untrackCacheStorageForOrigin", {"origin": origin})

    async def storage_untrack_cache_storage_for_storage_key(self, storage_key: str) -> None:
        """Untrack cache storage for a storage key."""
        session = self._require_session()
        await session.send("Storage.untrackCacheStorageForStorageKey", {"storageKey": storage_key})

    async def storage_untrack_indexed_db_for_origin(self, origin: str) -> None:
        """Untrack IndexedDB for an origin."""
        session = self._require_session()
        await session.send("Storage.untrackIndexedDBForOrigin", {"origin": origin})

    async def storage_untrack_indexed_db_for_storage_key(self, storage_key: str) -> None:
        """Untrack IndexedDB for a storage key."""
        session = self._require_session()
        await session.send("Storage.untrackIndexedDBForStorageKey", {"storageKey": storage_key})

    # ── Service Workers ────────────────────────────────────

    async def sw_list(self) -> list[dict[str, Any]]:
        """List registered service workers.

        Returns:
            List of service worker target dicts.
        """
        session = self._require_session()
        await session.send("ServiceWorker.enable", {})
        result = await session.send("Target.getTargets", {})
        registrations: list[dict[str, Any]] = []
        for target in result.get("targetInfos", []):
            if target.get("type") == "service_worker":
                registrations.append(dict(target))
        return registrations

    async def sw_unregister(self, registration_id: str) -> None:
        """Unregister a service worker by registration ID.

        Args:
            registration_id: The service worker registration ID.
        """
        session = self._require_session()
        await session.send("ServiceWorker.enable", {})
        await session.send("ServiceWorker.unregister", {"registrationId": registration_id})

    async def sw_update(self, registration_id: str) -> None:
        """Trigger an update for a service worker registration.

        Args:
            registration_id: The service worker registration ID.
        """
        session = self._require_session()
        await session.send("ServiceWorker.enable", {})
        await session.send("ServiceWorker.updateRegistration", {"registrationId": registration_id})

    async def sw_enable(self) -> None:
        """Enable the ServiceWorker domain."""
        session = self._require_session()
        await session.send("ServiceWorker.enable", {})

    async def sw_disable(self) -> None:
        """Disable the ServiceWorker domain."""
        session = self._require_session()
        await session.send("ServiceWorker.disable", {})

    async def sw_deliver_push_message(self, origin: str, registration_id: str, data: str) -> None:
        """Deliver a push message to a service worker.

        Args:
            origin: Origin of the service worker.
            registration_id: Service worker registration ID.
            data: Push message data.
        """
        session = self._require_session()
        await session.send(
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
        """Dispatch a sync event to a service worker.

        Args:
            origin: Origin of the service worker.
            registration_id: Service worker registration ID.
            tag: Sync tag.
            last_chance: Whether this is the last chance to run the sync.
        """
        session = self._require_session()
        await session.send(
            "ServiceWorker.dispatchSyncEvent",
            {
                "origin": origin,
                "registrationId": registration_id,
                "tag": tag,
                "lastChance": last_chance,
            },
        )

    async def sw_get_messages(self, worker_id: str) -> list[dict[str, Any]]:
        """Get messages from a service worker.

        Args:
            worker_id: Service worker target ID.

        Returns:
            List of message dicts.
        """
        session = self._require_session()
        result = await session.send("ServiceWorker.getMessages", {"workerId": worker_id})
        return result.get("messages", [])

    async def sw_inspect_worker(self, worker_id: str) -> None:
        """Inspect a service worker by opening a DevTools window.

        Args:
            worker_id: Service worker target ID.
        """
        session = self._require_session()
        await session.send("ServiceWorker.inspectWorker", {"workerId": worker_id})

    async def sw_skip_waiting(self, scope_url: str) -> None:
        """Skip waiting for a service worker to become active.

        Args:
            scope_url: Scope URL of the service worker.
        """
        session = self._require_session()
        await session.send("ServiceWorker.skipWaiting", {"scopeURL": scope_url})

    async def sw_start_worker(self, scope_url: str) -> None:
        """Start a service worker by scope URL.

        Args:
            scope_url: Scope URL of the service worker.
        """
        session = self._require_session()
        await session.send("ServiceWorker.startWorker", {"scopeURL": scope_url})

    async def sw_stop_worker(self, worker_id: str) -> None:
        """Stop a running service worker.

        Args:
            worker_id: Service worker target ID.
        """
        session = self._require_session()
        await session.send("ServiceWorker.stopWorker", {"workerId": worker_id})

    # ── Animations ─────────────────────────────────────────

    async def animation_list(self) -> list[dict[str, Any]]:
        """List all active animations on the page.

        Returns:
            List of animation dicts (id, name, state, etc.).
        """
        session = self._require_session()
        await session.animation.enable()
        result = await session.runtime.evaluate(
            expression=(
                "Array.from(document.getAnimations()).map(a => "
                "({id: a.id, name: a.animationName, "
                "playState: a.playState, duration: a.effect?.timing?.duration || 0}))"
            ),
            return_by_value=True,
        )
        value = result.get("result", {}).get("value", [])
        return [dict(a) for a in value] if isinstance(value, list) else []

    async def animation_pause(self, animation_id: str) -> None:
        """Pause an animation by ID.

        Args:
            animation_id: The animation ID to pause.
        """
        session = self._require_session()
        await session.send("Animation.enable", {})
        await session.send("Animation.setPaused", {"animations": [animation_id], "paused": True})

    async def animation_play(self, animation_id: str) -> None:
        """Play/resume an animation by ID.

        Args:
            animation_id: The animation ID to play.
        """
        session = self._require_session()
        await session.send("Animation.enable", {})
        await session.send("Animation.setPaused", {"animations": [animation_id], "paused": False})

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

    async def webauthn_add_virtual_authenticator(self, protocol: str, transport: str) -> str:
        """Add a virtual authenticator via CDP WebAuthn domain."""
        session = self._require_session()
        await session.web_authn.enable()
        result = await session.web_authn.add_virtual_authenticator(
            protocol=protocol,
            transport=transport,
        )
        return str(result.get("authenticatorId", ""))

    async def webauthn_remove_authenticator(self, authenticator_id: str) -> None:
        """Remove a virtual authenticator via CDP WebAuthn domain."""
        session = self._require_session()
        await session.web_authn.enable()
        await session.web_authn.remove_virtual_authenticator(
            authenticator_id=authenticator_id,
        )

    async def webauthn_add_credential(
        self, authenticator_id: str, credential: dict[str, Any]
    ) -> None:
        """Add a credential to a virtual authenticator via CDP WebAuthn domain."""
        session = self._require_session()
        await session.web_authn.enable()
        await session.web_authn.add_credential(
            authenticator_id=authenticator_id,
            credential=credential,
        )

    async def webauthn_get_credentials(self, authenticator_id: str) -> list[dict[str, Any]]:
        """Get credentials from a virtual authenticator via CDP WebAuthn domain."""
        session = self._require_session()
        await session.web_authn.enable()
        result = await session.web_authn.get_credentials(
            authenticator_id=authenticator_id,
        )
        return list(result.get("credentials", []))

    async def webauthn_enable(self) -> None:
        """Enable the WebAuthn domain."""
        session = self._require_session()
        await session.send("WebAuthn.enable", {})

    async def webauthn_disable(self) -> None:
        """Disable the WebAuthn domain."""
        session = self._require_session()
        await session.send("WebAuthn.disable", {})

    async def webauthn_get_credential(
        self, authenticator_id: str, credential_id: str
    ) -> dict[str, Any]:
        """Get a specific credential from a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID.
            credential_id: The credential ID.

        Returns:
            Credential dict.
        """
        session = self._require_session()
        result = await session.send(
            "WebAuthn.getCredential",
            {"authenticatorId": authenticator_id, "credentialId": credential_id},
        )
        return dict(result) if result else {}

    async def webauthn_remove_credential(self, authenticator_id: str, credential_id: str) -> None:
        """Remove a credential from a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID.
            credential_id: The credential ID.
        """
        session = self._require_session()
        await session.send(
            "WebAuthn.removeCredential",
            {"authenticatorId": authenticator_id, "credentialId": credential_id},
        )

    async def webauthn_clear_credentials(self, authenticator_id: str) -> None:
        """Clear all credentials from a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID.
        """
        session = self._require_session()
        await session.send(
            "WebAuthn.clearCredentials",
            {"authenticatorId": authenticator_id},
        )

    async def webauthn_set_user_verified(
        self, authenticator_id: str, is_user_verified: bool
    ) -> None:
        """Set the user-verified flag on a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID.
            is_user_verified: Whether the user is verified.
        """
        session = self._require_session()
        await session.send(
            "WebAuthn.setUserVerified",
            {"authenticatorId": authenticator_id, "isUserVerified": is_user_verified},
        )

    async def webauthn_set_automatic_presence_simulation(
        self, authenticator_id: str, enabled: bool
    ) -> None:
        """Set automatic presence simulation on a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID.
            enabled: Whether to enable presence simulation.
        """
        session = self._require_session()
        await session.send(
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
        """Set credential properties on a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID.
            credential_id: The credential ID.
            backup_state: The backup state.
            backup_eligibility: The backup eligibility.
        """
        session = self._require_session()
        await session.send(
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
        """Set response override bits on a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID.
            is_bogus_signature: Whether to return bogus signatures.
            is_bad_uv: Whether to return bad UV responses.
            is_bad_up: Whether to return bad UP responses.
        """
        session = self._require_session()
        await session.send(
            "WebAuthn.setResponseOverrideBits",
            {
                "authenticatorId": authenticator_id,
                "isBogusSignature": is_bogus_signature,
                "isBadUV": is_bad_uv,
                "isBadUP": is_bad_up,
            },
        )

    # ── WebAudio (experimental) ────────────────────────────

    async def webaudio_get_contexts(self) -> list[dict[str, Any]]:
        """Get all WebAudio contexts via CDP WebAudio domain.

        Enables the WebAudio domain and collects all contextCreated events
        emitted within a short window. Returns the list of contexts.

        Returns:
            List of WebAudio context dicts.
        """
        session = self._require_session()
        events: list[dict[str, Any]] = []

        def on_context_created(event: dict[str, Any]) -> None:
            events.append(event)

        session.on("WebAudio.contextCreated", on_context_created)
        try:
            await session.send("WebAudio.enable", {})
            await asyncio.sleep(1.0)
        finally:
            session.off("WebAudio.contextCreated", on_context_created)
        return [dict(ev.get("context", ev)) for ev in events]

    async def webaudio_get_context(self, context_id: str) -> dict[str, Any]:
        """Get a specific WebAudio context by ID via CDP WebAudio domain."""
        contexts = await self.webaudio_get_contexts()
        for ctx in contexts:
            if ctx.get("contextId") == context_id:
                return dict(ctx)
        return {}

    async def webaudio_enable(self) -> None:
        """Enable the WebAudio domain."""
        session = self._require_session()
        await session.send("WebAudio.enable", {})

    async def webaudio_disable(self) -> None:
        """Disable the WebAudio domain."""
        session = self._require_session()
        await session.send("WebAudio.disable", {})

    async def webaudio_get_realtime_data(self, context_id: str) -> dict[str, Any]:
        """Get realtime data for a WebAudio context.

        Args:
            context_id: The audio context ID.

        Returns:
            Dict with realtime audio data.
        """
        session = self._require_session()
        result = await session.send("WebAudio.getRealtimeData", {"contextId": context_id})
        return dict(result) if result else {}

    # ── Media (experimental) ───────────────────────────────

    async def media_get_players(self) -> list[dict[str, Any]]:
        """Get all media players via CDP Media domain."""
        session = self._require_session()
        await session.send("Media.enable", {})
        result = await session.runtime.evaluate(
            expression=(
                "Array.from(document.querySelectorAll('video, audio')).map(el => "
                "({id: el.id || '', tagName: el.tagName, "
                "src: el.src || '', currentTime: el.currentTime, "
                "duration: el.duration, paused: el.paused}))"
            ),
            return_by_value=True,
        )
        value = result.get("result", {}).get("value", [])
        return [dict(p) for p in value] if isinstance(value, list) else []

    async def media_get_messages(self, player_id: str) -> list[dict[str, Any]]:
        """Get messages for a specific media player via CDP Media domain."""
        session = self._require_session()
        result = await session.send("Media.getPlayerMessages", {"playerId": player_id})
        return list(result.get("messages", []))

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

    async def cast_enable(self) -> None:
        """Enable the Cast domain via CDP."""
        session = self._require_session()
        await session.send("Cast.enable", {})

    async def cast_disable(self) -> None:
        """Disable the Cast domain via CDP."""
        session = self._require_session()
        await session.send("Cast.disable", {})

    async def cast_set_sink_to_use(self, sink_name: str) -> None:
        """Set a sink to use for cast via CDP."""
        session = self._require_session()
        await session.send("Cast.setSinkToUse", {"sinkName": sink_name})

    async def cast_start_desktop_mirroring(self, sink_name: str) -> None:
        """Start desktop mirroring to a cast sink via CDP."""
        session = self._require_session()
        await session.send("Cast.startDesktopMirroring", {"sinkName": sink_name})

    async def cast_start_tab_mirroring(self, sink_name: str) -> None:
        """Start tab mirroring to a cast sink via CDP."""
        session = self._require_session()
        await session.send("Cast.startTabMirroring", {"sinkName": sink_name})

    async def cast_stop_casting(self, sink_name: str) -> None:
        """Stop casting to a specific sink via CDP."""
        session = self._require_session()
        await session.send("Cast.stopCasting", {"sinkName": sink_name})

    # ── Bluetooth (experimental) ───────────────────────────

    async def bluetooth_emulate(self, name: str, address: str = "00:00:00:00:00:01") -> None:
        """Emulate a Bluetooth Low Energy device via CDP BluetoothEmulation domain.

        Bug #23: uses _send_cdp to translate method-not-found/timeout errors
        into a friendly WavexisError.
        """
        session = self._require_session()
        await self._send_cdp(session, "BluetoothEmulation.enable", {})
        await self._send_cdp(
            session,
            "BluetoothEmulation.simulatePreconnected",
            {"name": name, "address": address},
        )

    async def bluetooth_stop(self) -> None:
        """Stop Bluetooth emulation via CDP BluetoothEmulation domain."""
        session = self._require_session()
        await self._send_cdp(session, "BluetoothEmulation.disable", {})

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
        valid_path = validate_path(path)
        is_dir = await asyncio.to_thread(os.path.isdir, valid_path)
        if is_dir:
            abs_path = await asyncio.to_thread(os.path.abspath, valid_path)
            ext_id = hashlib.sha256(abs_path.encode()).hexdigest()[:32]
            await session.send(
                "Extensions.loadUnpacked",
                {"path": abs_path},
            )
        else:
            ext_id = hashlib.sha256(str(valid_path).encode()).hexdigest()[:32]
            try:
                data = await asyncio.to_thread(lambda: valid_path.read_bytes())
            except OSError as e:
                raise WavexisError(f"Failed to read extension file: {e}") from e
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
        result = await self._send_cdp(session, "Extensions.getInfo", {})
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
        result = await self._send_cdp(session, "Browser.getPreference", {"name": key})
        return result.get("value")

    async def set_pref(self, key: str, value: Any) -> None:
        """Set a browser preference value.

        Args:
            key: The preference key.
            value: The value to set.
        """
        session = self._require_session()
        await self._send_cdp(session, "Browser.setPreference", {"name": key, "value": value})

    # ── Tethering ─────────────────────────────────────────

    async def tethering_bind(self, port: int) -> None:
        """Bind a port for tethering (accept incoming connections).

        Args:
            port: The port number to bind.
        """
        session = self._require_session()
        await self._send_cdp(session, "Tethering.bind", {"port": port})

    async def tethering_unbind(self, port: int) -> None:
        """Unbind a port from tethering.

        Args:
            port: The port number to unbind.
        """
        session = self._require_session()
        await self._send_cdp(session, "Tethering.unbind", {"port": port})

    # ── WebMcp ────────────────────────────────────────────

    async def web_mcp_enable(self) -> None:
        """Enable the WebMcp domain."""
        session = self._require_session()
        await self._send_cdp(session, "WebMcp.enable", {})

    async def web_mcp_disable(self) -> None:
        """Disable the WebMcp domain."""
        session = self._require_session()
        await self._send_cdp(session, "WebMcp.disable", {})

    # ── DeviceAccess ────────────────────────────────────────

    async def device_access_cancel_prompt(self, id: str) -> None:
        """Cancel a device access prompt by ID."""
        session = self._require_session()
        await session.send("DeviceAccess.cancelPrompt", {"id": id})

    async def device_access_disable(self) -> None:
        """Disable the DeviceAccess domain."""
        session = self._require_session()
        await session.send("DeviceAccess.disable", {})

    async def device_access_enable(self) -> None:
        """Enable the DeviceAccess domain."""
        session = self._require_session()
        await session.send("DeviceAccess.enable", {})

    async def device_access_select_prompt(self, id: str, device_id: str) -> None:
        """Select a device in a device access prompt."""
        session = self._require_session()
        await session.send("DeviceAccess.selectPrompt", {"id": id, "deviceId": device_id})

    # ── DeviceOrientation ───────────────────────────────────

    async def device_orientation_clear_override(self) -> None:
        """Clear device orientation override."""
        session = self._require_session()
        await session.send("DeviceOrientation.clearDeviceOrientationOverride", {})

    async def device_orientation_set_override(
        self, alpha: float, beta: float, gamma: float
    ) -> None:
        """Set device orientation override."""
        session = self._require_session()
        await session.send(
            "DeviceOrientation.setDeviceOrientationOverride",
            {"alpha": alpha, "beta": beta, "gamma": gamma},
        )

    # ── DigitalCredentials ──────────────────────────────────

    async def digital_credentials_set_virtual_wallet_behavior(
        self, behavior: dict[str, Any]
    ) -> None:
        """Set the virtual wallet behavior for digital credentials."""
        session = self._require_session()
        await session.send("DigitalCredentials.setVirtualWalletBehavior", {"behavior": behavior})

    # ── DOMSnapshot ─────────────────────────────────────────

    async def dom_snapshot_capture_snapshot(
        self,
        computed_styles: list[str] | None = None,
        include_paint_order: bool = False,
        include_dom_rects: bool = False,
        include_blended_background_colors: bool = False,
        include_text_color_opacity: bool = False,
    ) -> dict[str, Any]:
        """Capture a DOM snapshot of the current page.

        Bug #7: ``DOMSnapshot.captureSnapshot`` requires ``computedStyles``
        to be present as an array (even empty). Previously we omitted the
        key when ``computed_styles`` was None, which caused
        ``[-32602] Invalid parameters``. We now default to an empty list.
        """
        session = self._require_session()
        params: dict[str, Any] = {"computedStyles": computed_styles or []}
        if include_paint_order:
            params["includePaintOrder"] = True
        if include_dom_rects:
            params["includeDOMRects"] = True
        if include_blended_background_colors:
            params["includeBlendedBackgroundColor"] = True
        if include_text_color_opacity:
            params["includeTextColorOpacity"] = True
        result = await session.send("DOMSnapshot.captureSnapshot", params)
        return dict(result) if result else {}

    async def dom_snapshot_disable(self) -> None:
        """Disable the DOMSnapshot domain."""
        session = self._require_session()
        await session.send("DOMSnapshot.disable", {})

    async def dom_snapshot_enable(self) -> None:
        """Enable the DOMSnapshot domain."""
        session = self._require_session()
        await session.send("DOMSnapshot.enable", {})

    async def dom_snapshot_get_snapshot(
        self,
        computed_styles: list[str] | None = None,
        include_paint_order: bool = False,
        include_dom_rects: bool = False,
        include_blended_background_colors: bool = False,
        include_text_color_opacity: bool = False,
    ) -> dict[str, Any]:
        """Get a DOM snapshot of the current page.

        Bug #8: ``DOMSnapshot.getSnapshot`` requires ``computedStyles``
        as an array (even empty). Previously we omitted the key when
        ``computed_styles`` was None, causing
        ``[-32602] Invalid parameters``. We now default to an empty list.
        """
        session = self._require_session()
        params: dict[str, Any] = {"computedStyles": computed_styles or []}
        if include_paint_order:
            params["includePaintOrder"] = True
        if include_dom_rects:
            params["includeDOMRects"] = True
        if include_blended_background_colors:
            params["includeBlendedBackgroundColor"] = True
        if include_text_color_opacity:
            params["includeTextColorOpacity"] = True
        result = await session.send("DOMSnapshot.getSnapshot", params)
        return dict(result) if result else {}

    # ── DOMStorage ──────────────────────────────────────────

    async def dom_storage_clear(self, storage_id: dict[str, Any]) -> None:
        """Clear all entries in a DOM storage."""
        session = self._require_session()
        await session.send("DOMStorage.clear", {"storageId": storage_id})

    async def dom_storage_clear_items(self, storage_id: dict[str, Any]) -> None:
        """Clear all items in a DOM storage (alias)."""
        session = self._require_session()
        await session.send("DOMStorage.clear", {"storageId": storage_id})

    async def dom_storage_disable(self) -> None:
        """Disable the DOMStorage domain."""
        session = self._require_session()
        await session.send("DOMStorage.disable", {})

    async def dom_storage_enable(self) -> None:
        """Enable the DOMStorage domain."""
        session = self._require_session()
        await session.send("DOMStorage.enable", {})

    async def dom_storage_get_items(self, storage_id: dict[str, Any]) -> list[dict[str, Any]]:
        """Get all items in a DOM storage."""
        session = self._require_session()
        result = await session.send("DOMStorage.getDOMStorageItems", {"storageId": storage_id})
        return list(result.get("items", [])) if result else []

    async def dom_storage_remove_item(self, storage_id: dict[str, Any], key: str) -> None:
        """Remove an item from a DOM storage."""
        session = self._require_session()
        await session.send("DOMStorage.removeDOMStorageItem", {"storageId": storage_id, "key": key})

    async def dom_storage_set_item(self, storage_id: dict[str, Any], key: str, value: str) -> None:
        """Set an item in a DOM storage."""
        session = self._require_session()
        await session.send(
            "DOMStorage.setDOMStorageItem", {"storageId": storage_id, "key": key, "value": value}
        )

    # ── EventBreakpoints ────────────────────────────────────

    async def event_breakpoints_clear_instrumentation_breakpoint(
        self, instrumentation_name: str
    ) -> None:
        """Clear an instrumentation breakpoint for events."""
        session = self._require_session()
        await session.send(
            "EventBreakpoints.clearInstrumentationBreakpoint",
            {"instrumentationName": instrumentation_name},
        )

    async def event_breakpoints_disable(self) -> None:
        """Disable the EventBreakpoints domain."""
        session = self._require_session()
        await session.send("EventBreakpoints.disable", {})

    async def event_breakpoints_remove_instrumentation_breakpoint(
        self, instrumentation_name: str
    ) -> None:
        """Remove an instrumentation breakpoint for events."""
        session = self._require_session()
        await session.send(
            "EventBreakpoints.removeInstrumentationBreakpoint",
            {"instrumentationName": instrumentation_name},
        )

    async def event_breakpoints_set_instrumentation_breakpoint(
        self, instrumentation_name: str
    ) -> None:
        """Set an instrumentation breakpoint for events."""
        session = self._require_session()
        await session.send(
            "EventBreakpoints.setInstrumentationBreakpoint",
            {"instrumentationName": instrumentation_name},
        )

    # ── Extensions ──────────────────────────────────────────

    async def extensions_clear_storage_items(self, id: str, storage_type: str) -> None:
        """Clear storage items for an extension."""
        session = self._require_session()
        await session.send("Extensions.clearStorageItems", {"id": id, "storageType": storage_type})

    async def extensions_get_storage_items(self, id: str, storage_type: str) -> dict[str, Any]:
        """Get storage items for an extension."""
        session = self._require_session()
        result = await session.send(
            "Extensions.getStorageItems", {"id": id, "storageType": storage_type}
        )
        return dict(result) if result else {}

    async def extensions_remove_storage_items(
        self, id: str, storage_type: str, keys: list[str]
    ) -> None:
        """Remove storage items from an extension."""
        session = self._require_session()
        await session.send(
            "Extensions.removeStorageItems", {"id": id, "storageType": storage_type, "keys": keys}
        )

    async def extensions_set_storage_items(
        self, id: str, storage_type: str, values: list[dict[str, Any]]
    ) -> None:
        """Set storage items for an extension."""
        session = self._require_session()
        await session.send(
            "Extensions.setStorageItems", {"id": id, "storageType": storage_type, "values": values}
        )

    async def extensions_trigger_action(self, id: str, action: str) -> None:
        """Trigger an action on an extension."""
        session = self._require_session()
        await session.send("Extensions.triggerAction", {"id": id, "action": action})

    # ── FedCm ───────────────────────────────────────────────

    async def fed_cm_click_dialog_button(self, dialog_id: str, button_index: int) -> None:
        """Click a button in a FedCm dialog."""
        session = self._require_session()
        await session.send(
            "FedCm.clickDialogButton", {"dialogId": dialog_id, "buttonIndex": button_index}
        )

    async def fed_cm_disable(self) -> None:
        """Disable the FedCm domain."""
        session = self._require_session()
        await session.send("FedCm.disable", {})

    async def fed_cm_dismiss_dialog(self, dialog_id: str) -> None:
        """Dismiss a FedCm dialog."""
        session = self._require_session()
        await session.send("FedCm.dismissDialog", {"dialogId": dialog_id})

    async def fed_cm_enable(self) -> None:
        """Enable the FedCm domain."""
        session = self._require_session()
        await session.send("FedCm.enable", {})

    async def fed_cm_open_url(self, dialog_id: str, account_index: int, url: str) -> None:
        """Open a URL from a FedCm dialog."""
        session = self._require_session()
        await session.send(
            "FedCm.openUrl", {"dialogId": dialog_id, "accountIndex": account_index, "url": url}
        )

    async def fed_cm_reset_cooldown(self) -> None:
        """Reset the FedCm cooldown."""
        session = self._require_session()
        await session.send("FedCm.resetCooldown", {})

    async def fed_cm_select_account(self, dialog_id: str, account_index: int) -> None:
        """Select an account in a FedCm dialog."""
        session = self._require_session()
        await session.send(
            "FedCm.selectAccount", {"dialogId": dialog_id, "accountIndex": account_index}
        )

    # ── Fetch ───────────────────────────────────────────────

    async def fetch_continue_request(
        self,
        request_id: str,
        url: str | None = None,
        method: str | None = None,
        post_data: str | None = None,
        headers: list[dict[str, Any]] | None = None,
    ) -> None:
        """Continue a paused request with optional modifications."""
        session = self._require_session()
        params: dict[str, Any] = {"requestId": request_id}
        if url is not None:
            params["url"] = url
        if method is not None:
            params["method"] = method
        if post_data is not None:
            params["postData"] = post_data
        if headers is not None:
            params["headers"] = headers
        await session.send("Fetch.continueRequest", params)

    async def fetch_continue_request_with_auth(
        self, request_id: str, auth_challenge_response: dict[str, Any]
    ) -> None:
        """Continue a paused request with authentication."""
        session = self._require_session()
        await session.send(
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
        """Continue a paused response."""
        session = self._require_session()
        params: dict[str, Any] = {"requestId": request_id, "responseCode": response_code}
        if response_headers is not None:
            params["responseHeaders"] = response_headers
        if binary_response_headers is not None:
            params["binaryResponseHeaders"] = binary_response_headers
        await session.send("Fetch.continueResponse", params)

    async def fetch_continue_with_auth(
        self, request_id: str, auth_challenge_response: dict[str, Any]
    ) -> None:
        """Continue a paused request with auth challenge response."""
        session = self._require_session()
        await session.send(
            "Fetch.continueWithAuth",
            {"requestId": request_id, "authChallengeResponse": auth_challenge_response},
        )

    async def fetch_disable(self) -> None:
        """Disable the Fetch domain."""
        session = self._require_session()
        await session.send("Fetch.disable", {})

    async def fetch_enable(
        self, patterns: list[dict[str, Any]] | None = None, handle_auth_requests: bool = False
    ) -> None:
        """Enable the Fetch domain with optional patterns."""
        session = self._require_session()
        params: dict[str, Any] = {}
        if patterns is not None:
            params["patterns"] = patterns
        if handle_auth_requests:
            params["handleAuthRequests"] = True
        await session.send("Fetch.enable", params)

    async def fetch_fail_request(self, request_id: str, error_reason: str) -> None:
        """Fail a paused request with an error."""
        session = self._require_session()
        await session.send(
            "Fetch.failRequest", {"requestId": request_id, "errorReason": error_reason}
        )

    async def fetch_fulfill_request(
        self,
        request_id: str,
        response_code: int = 200,
        response_headers: list[dict[str, Any]] | None = None,
        body: str | None = None,
    ) -> None:
        """Fulfill a paused request with a response."""
        session = self._require_session()
        params: dict[str, Any] = {"requestId": request_id, "responseCode": response_code}
        if response_headers is not None:
            params["responseHeaders"] = response_headers
        if body is not None:
            params["body"] = body
        await session.send("Fetch.fulfillRequest", params)

    async def fetch_get_request_post_data(self, request_id: str) -> str:
        """Get the POST data of a paused request."""
        session = self._require_session()
        result = await session.send("Fetch.getRequestPostData", {"requestId": request_id})
        return str(result.get("postData", "")) if result else ""

    async def fetch_take_response_body_as_stream(self, request_id: str) -> dict[str, Any]:
        """Take the response body of a paused request as a stream."""
        session = self._require_session()
        result = await session.send("Fetch.takeResponseBodyAsStream", {"requestId": request_id})
        return dict(result) if result else {}

    # ── FileSystem ──────────────────────────────────────────

    async def file_system_get_directory(self, origin: str, type: str) -> dict[str, Any]:
        """Get a file system directory by origin and type."""
        session = self._require_session()
        result = await session.send("FileSystem.getDirectory", {"origin": origin, "type": type})
        return dict(result) if result else {}

    # ── HeadlessExperimental ────────────────────────────────

    async def headless_experimental_begin_frame(
        self,
        frame_time_ticks: float | None = None,
        interval: float | None = None,
        no_display_updates: bool = False,
        screenshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Begin a new frame in headless mode."""
        session = self._require_session()
        params: dict[str, Any] = {}
        if frame_time_ticks is not None:
            params["frameTimeTicks"] = frame_time_ticks
        if interval is not None:
            params["interval"] = interval
        if no_display_updates:
            params["noDisplayUpdates"] = True
        if screenshot is not None:
            params["screenshot"] = screenshot
        result = await self._send_cdp(session, "HeadlessExperimental.beginFrame", params)
        return dict(result) if result else {}

    async def headless_experimental_disable(self) -> None:
        """Disable the HeadlessExperimental domain."""
        session = self._require_session()
        await self._send_cdp(session, "HeadlessExperimental.disable", {})

    async def headless_experimental_enable(self) -> None:
        """Enable the HeadlessExperimental domain."""
        session = self._require_session()
        await self._send_cdp(session, "HeadlessExperimental.enable", {})

    # ── Inspector ───────────────────────────────────────────

    async def inspector_disable(self) -> None:
        """Disable the Inspector domain."""
        session = self._require_session()
        await session.send("Inspector.disable", {})

    async def inspector_enable(self) -> None:
        """Enable the Inspector domain."""
        session = self._require_session()
        await session.send("Inspector.enable", {})

    # ── Preload ────────────────────────────────────────────

    async def preload_disable(self) -> None:
        """Disable the Preload domain."""
        session = self._require_session()
        await session.send("Preload.disable", {})

    async def preload_enable(self) -> None:
        """Enable the Preload domain."""
        session = self._require_session()
        await session.send("Preload.enable", {})

    async def preload_get_preload_policy(self) -> dict[str, Any]:
        """Get the current preload policy."""
        session = self._require_session()
        result = await session.send("Preload.getPreloadPolicy", {})
        return dict(result) if result else {}

    async def preload_set_preload_policy(self, policy: dict[str, Any]) -> None:
        """Set the preload policy."""
        session = self._require_session()
        await session.send("Preload.setPreloadPolicy", {"policy": policy})

    # ── Profiler ───────────────────────────────────────────

    async def profiler_disable(self) -> None:
        """Disable the Profiler domain."""
        session = self._require_session()
        await session.send("Profiler.disable", {})

    async def profiler_enable(self) -> None:
        """Enable the Profiler domain."""
        session = self._require_session()
        await session.send("Profiler.enable", {})

    async def profiler_get_best_effort_coverage(self) -> dict[str, Any]:
        """Get best effort coverage data."""
        session = self._require_session()
        result = await session.send("Profiler.getBestEffortCoverage", {})
        return dict(result) if result else {}

    async def profiler_set_sampling_interval(self, interval: int) -> None:
        """Set the CPU sampling interval in microseconds."""
        session = self._require_session()
        await session.send("Profiler.setSamplingInterval", {"interval": interval})

    async def profiler_start(self) -> None:
        """Start CPU profiling."""
        session = self._require_session()
        await session.send("Profiler.start", {})

    async def profiler_start_precise_coverage(
        self, call_count: bool = False, detailed: bool = False
    ) -> dict[str, Any]:
        """Start precise code coverage tracking."""
        session = self._require_session()
        result = await session.send(
            "Profiler.startPreciseCoverage",
            {"callCount": call_count, "detailed": detailed},
        )
        return dict(result) if result else {}

    async def profiler_stop(self) -> dict[str, Any]:
        """Stop CPU profiling and return the profile data."""
        session = self._require_session()
        result = await session.send("Profiler.stop", {})
        return dict(result) if result else {}

    async def profiler_stop_precise_coverage(self) -> None:
        """Stop precise code coverage tracking."""
        session = self._require_session()
        await session.send("Profiler.stopPreciseCoverage", {})

    async def profiler_take_precise_coverage(self) -> dict[str, Any]:
        """Take a snapshot of precise code coverage data."""
        session = self._require_session()
        result = await session.send("Profiler.takePreciseCoverage", {})
        return dict(result) if result else {}

    # ── PWA ────────────────────────────────────────────────

    async def pwa_change_app_user_settings(
        self, app_id: str, user_settings: dict[str, Any]
    ) -> None:
        """Change PWA user settings."""
        session = self._require_session()
        await session.send(
            "PWA.changeAppUserSettings", {"appId": app_id, "userSettings": user_settings}
        )

    async def pwa_get_os_app_state(self, app_id: str) -> dict[str, Any]:
        """Get the OS-level state of a PWA."""
        session = self._require_session()
        result = await session.send("PWA.getOsAppState", {"appId": app_id})
        return dict(result) if result else {}

    async def pwa_install(self, manifest_id: str, install_url: str | None = None) -> None:
        """Install a PWA."""
        session = self._require_session()
        params: dict[str, Any] = {"manifestId": manifest_id}
        if install_url is not None:
            params["installUrlOrBundleUrl"] = install_url
        await session.send("PWA.install", params)

    async def pwa_launch_files_in_app(self, app_id: str, files: list[str]) -> dict[str, Any]:
        """Launch files in a PWA."""
        session = self._require_session()
        result = await session.send("PWA.launchFilesInApp", {"appId": app_id, "files": files})
        return dict(result) if result else {}

    async def pwa_open_current_page_in_app(self, app_id: str) -> dict[str, Any]:
        """Open the current page in a PWA."""
        session = self._require_session()
        result = await session.send("PWA.openCurrentPageInApp", {"appId": app_id})
        return dict(result) if result else {}

    async def pwa_uninstall(self, app_id: str) -> None:
        """Uninstall a PWA."""
        session = self._require_session()
        await session.send("PWA.uninstall", {"appId": app_id})

    # ── IO ──────────────────────────────────────────────────

    async def io_read(
        self, handle: str, offset: int = 0, size: int | None = None
    ) -> dict[str, Any]:
        """Read data from a blob handle."""
        session = self._require_session()
        params: dict[str, Any] = {"handle": handle, "offset": offset}
        if size is not None:
            params["size"] = size
        result = await session.send("IO.read", params)
        return dict(result) if result else {}

    async def io_resolve_blob(self, object_id: str) -> str:
        """Resolve a blob object ID to a UUID handle."""
        session = self._require_session()
        result = await session.send("IO.resolveBlob", {"objectId": object_id})
        return str(result.get("uuid", "")) if result else ""

    # ── HeapProfiler ───────────────────────────────────────

    async def heap_profiler_add_inspected_heap_object(self, heap_object_id: str) -> None:
        """Add an inspected heap object."""
        session = self._require_session()
        await session.send("HeapProfiler.addInspectedHeapObject", {"heapObjectId": heap_object_id})

    async def heap_profiler_collect_garbage(self) -> None:
        """Collect garbage."""
        session = self._require_session()
        await session.send("HeapProfiler.collectGarbage", {})

    async def heap_profiler_disable(self) -> None:
        """Disable the HeapProfiler domain."""
        session = self._require_session()
        await session.send("HeapProfiler.disable", {})

    async def heap_profiler_enable(self) -> None:
        """Enable the HeapProfiler domain."""
        session = self._require_session()
        await session.send("HeapProfiler.enable", {})

    async def heap_profiler_get_heap_object_id(self, object_id: str) -> str:
        """Get the heap object ID for a remote object."""
        session = self._require_session()
        result = await session.send("HeapProfiler.getHeapObjectId", {"objectId": object_id})
        return str(result.get("heapSnapshotObjectId", "")) if result else ""

    async def heap_profiler_get_object_by_heap_object_id(
        self, object_id: str, object_group: str = ""
    ) -> dict[str, Any]:
        """Get an object by heap object ID."""
        session = self._require_session()
        params: dict[str, Any] = {"objectId": object_id}
        if object_group:
            params["objectGroup"] = object_group
        result = await session.send("HeapProfiler.getObjectByHeapObjectId", params)
        return dict(result) if result else {}

    async def heap_profiler_get_sampling_profile(self) -> dict[str, Any]:
        """Get the current sampling profile."""
        session = self._require_session()
        result = await session.send("HeapProfiler.getSamplingProfile", {})
        return dict(result) if result else {}

    async def heap_profiler_start_sampling(self, sampling_interval: int = 0) -> None:
        """Start heap sampling."""
        session = self._require_session()
        params: dict[str, Any] = {}
        if sampling_interval:
            params["samplingInterval"] = sampling_interval
        await session.send("HeapProfiler.startSampling", params)

    async def heap_profiler_start_tracking_heap_objects(
        self, track_allocations: bool = False
    ) -> None:
        """Start tracking heap objects."""
        session = self._require_session()
        await session.send(
            "HeapProfiler.startTrackingHeapObjects", {"trackAllocations": track_allocations}
        )

    async def heap_profiler_stop_sampling(self) -> dict[str, Any]:
        """Stop heap sampling and return the profile."""
        session = self._require_session()
        result = await session.send("HeapProfiler.stopSampling", {})
        return dict(result) if result else {}

    async def heap_profiler_stop_tracking_heap_objects(self, report_progress: bool = False) -> None:
        """Stop tracking heap objects."""
        session = self._require_session()
        await session.send(
            "HeapProfiler.stopTrackingHeapObjects", {"reportProgress": report_progress}
        )

    async def heap_profiler_take_heap_snapshot(self, report_progress: bool = False) -> None:
        """Take a heap snapshot."""
        session = self._require_session()
        await session.send("HeapProfiler.takeHeapSnapshot", {"reportProgress": report_progress})

    # ── IndexedDB ──────────────────────────────────────────

    async def indexed_db_clear_object_store(
        self, security_origin: str, database_name: str, object_store_name: str
    ) -> None:
        """Clear all entries in an IndexedDB object store."""
        session = self._require_session()
        await session.send(
            "IndexedDB.clearObjectStore",
            {
                "securityOrigin": security_origin,
                "databaseName": database_name,
                "objectStoreName": object_store_name,
            },
        )

    async def indexed_db_delete_database(self, security_origin: str, database_name: str) -> None:
        """Delete an IndexedDB database."""
        session = self._require_session()
        await session.send(
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
        """Delete entries in an IndexedDB object store."""
        session = self._require_session()
        await session.send(
            "IndexedDB.deleteObjectStoreEntries",
            {
                "securityOrigin": security_origin,
                "databaseName": database_name,
                "objectStoreName": object_store_name,
                "keyRange": key_range,
            },
        )

    async def indexed_db_disable(self) -> None:
        """Disable the IndexedDB domain."""
        session = self._require_session()
        await session.send("IndexedDB.disable", {})

    async def indexed_db_enable(self) -> None:
        """Enable the IndexedDB domain."""
        session = self._require_session()
        await session.send("IndexedDB.enable", {})

    async def indexed_db_get_metadata(
        self, security_origin: str, database_name: str, object_store_name: str
    ) -> dict[str, Any]:
        """Get metadata for an IndexedDB object store."""
        session = self._require_session()
        result = await session.send(
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
        """Request data from an IndexedDB object store."""
        session = self._require_session()
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
        result = await session.send("IndexedDB.requestData", params)
        return dict(result) if result else {}

    async def indexed_db_request_database(
        self, security_origin: str, database_name: str
    ) -> dict[str, Any]:
        """Request an IndexedDB database with its object stores."""
        session = self._require_session()
        result = await session.send(
            "IndexedDB.requestDatabase",
            {"securityOrigin": security_origin, "databaseName": database_name},
        )
        return dict(result) if result else {}

    async def indexed_db_request_database_names(self, security_origin: str) -> dict[str, Any]:
        """Request the names of all IndexedDB databases for an origin."""
        session = self._require_session()
        result = await session.send(
            "IndexedDB.requestDatabaseNames", {"securityOrigin": security_origin}
        )
        return dict(result) if result else {}

    # ── LayerTree ──────────────────────────────────────────

    async def layer_tree_compositing_reasons(self, layer_id: str) -> dict[str, Any]:
        """Get compositing reasons for a layer."""
        session = self._require_session()
        result = await session.send("LayerTree.compositingReasons", {"layerId": layer_id})
        return dict(result) if result else {}

    async def layer_tree_disable(self) -> None:
        """Disable the LayerTree domain."""
        session = self._require_session()
        await session.send("LayerTree.disable", {})

    async def layer_tree_enable(self) -> None:
        """Enable the LayerTree domain."""
        session = self._require_session()
        await session.send("LayerTree.enable", {})

    async def layer_tree_load_snapshot(self, snapshots: list[dict[str, Any]]) -> dict[str, Any]:
        """Load a layer tree snapshot."""
        session = self._require_session()
        result = await session.send("LayerTree.loadSnapshot", {"snapshots": snapshots})
        return dict(result) if result else {}

    async def layer_tree_make_snapshot(self, layer_id: str) -> dict[str, Any]:
        """Make a snapshot of a layer."""
        session = self._require_session()
        result = await session.send("LayerTree.makeSnapshot", {"layerId": layer_id})
        return dict(result) if result else {}

    async def layer_tree_profile_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        """Profile a layer snapshot."""
        session = self._require_session()
        result = await session.send("LayerTree.profileSnapshot", {"snapshotId": snapshot_id})
        return dict(result) if result else {}

    async def layer_tree_release_snapshot(self, snapshot_id: str) -> None:
        """Release a layer snapshot."""
        session = self._require_session()
        await session.send("LayerTree.releaseSnapshot", {"snapshotId": snapshot_id})

    async def layer_tree_replay_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        """Replay a layer snapshot."""
        session = self._require_session()
        result = await session.send("LayerTree.replaySnapshot", {"snapshotId": snapshot_id})
        return dict(result) if result else {}

    async def layer_tree_snapshot_command_log(self, snapshot_id: str) -> dict[str, Any]:
        """Get the command log for a layer snapshot."""
        session = self._require_session()
        result = await session.send("LayerTree.snapshotCommandLog", {"snapshotId": snapshot_id})
        return dict(result) if result else {}

    # ── Log ─────────────────────────────────────────────────

    async def log_clear(self) -> None:
        """Clear the log."""
        session = self._require_session()
        await session.send("Log.clear", {})

    async def log_disable(self) -> None:
        """Disable the Log domain."""
        session = self._require_session()
        await session.send("Log.disable", {})

    async def log_enable(self) -> None:
        """Enable the Log domain."""
        session = self._require_session()
        await session.send("Log.enable", {})

    async def log_start_violations_report(self, config: list[dict[str, Any]]) -> None:
        """Start reporting violations."""
        session = self._require_session()
        await session.send("Log.startViolationsReport", {"config": config})

    async def log_stop_violations_report(self) -> None:
        """Stop reporting violations."""
        session = self._require_session()
        await session.send("Log.stopViolationsReport", {})

    # ── Media ───────────────────────────────────────────────

    async def media_disable(self) -> None:
        """Disable the Media domain."""
        session = self._require_session()
        await session.send("Media.disable", {})

    async def media_enable(self) -> None:
        """Enable the Media domain."""
        session = self._require_session()
        await session.send("Media.enable", {})

    # ── Memory ──────────────────────────────────────────────

    async def memory_forcibly_purge_javascript_memory(self) -> None:
        """Forcibly purge JavaScript memory."""
        session = self._require_session()
        await session.send("Memory.forciblyPurgeJavaScriptMemory", {})

    async def memory_get_all_time_sampling_profile(self) -> dict[str, Any]:
        """Get the all-time sampling profile."""
        session = self._require_session()
        result = await session.send("Memory.getAllTimeSamplingProfile", {})
        return dict(result) if result else {}

    async def memory_get_browser_sampling_profile(self) -> dict[str, Any]:
        """Get the browser sampling profile."""
        session = self._require_session()
        result = await session.send("Memory.getBrowserSamplingProfile", {})
        return dict(result) if result else {}

    async def memory_get_dom_counters(self) -> dict[str, Any]:
        """Get DOM counters."""
        session = self._require_session()
        result = await session.send("Memory.getDOMCounters", {})
        return dict(result) if result else {}

    async def memory_get_dom_counters_for_leak_detection(self) -> dict[str, Any]:
        """Get DOM counters for leak detection."""
        session = self._require_session()
        result = await session.send("Memory.getDOMCountersForLeakDetection", {})
        return dict(result) if result else {}

    async def memory_get_sampling_profile(self) -> dict[str, Any]:
        """Get the current sampling profile."""
        session = self._require_session()
        result = await session.send("Memory.getSamplingProfile", {})
        return dict(result) if result else {}

    async def memory_prepare_for_leak_detection(self) -> None:
        """Prepare for leak detection."""
        session = self._require_session()
        await session.send("Memory.prepareForLeakDetection", {})

    async def memory_set_pressure_notifications_suppressed(self, suppressed: bool) -> None:
        """Set pressure notifications suppressed state."""
        session = self._require_session()
        await session.send("Memory.setPressureNotificationsSuppressed", {"suppressed": suppressed})

    async def memory_simulate_pressure_notification(self, level: str) -> None:
        """Simulate a memory pressure notification."""
        session = self._require_session()
        await session.send("Memory.simulatePressureNotification", {"level": level})

    async def memory_start_sampling(self, sampling_interval: int = 0) -> None:
        """Start memory sampling."""
        session = self._require_session()
        params: dict[str, Any] = {}
        if sampling_interval:
            params["samplingInterval"] = sampling_interval
        await session.send("Memory.startSampling", params)

    async def memory_stop_sampling(self) -> None:
        """Stop memory sampling."""
        session = self._require_session()
        await session.send("Memory.stopSampling", {})

    # ── Console ─────────────────────────────────────────────

    async def console_clear_messages(self) -> None:
        """Clear all console messages."""
        session = self._require_session()
        await session.send("Console.clearMessages", {})

    async def console_disable(self) -> None:
        """Disable the Console domain."""
        session = self._require_session()
        await session.send("Console.disable", {})

    async def console_enable(self) -> None:
        """Enable the Console domain."""
        session = self._require_session()
        await session.send("Console.enable", {})

    # ── CrashReportContext ──────────────────────────────────

    async def crash_report_context_get_entries(self) -> list[dict[str, Any]]:
        """Get crash report entries."""
        session = self._require_session()
        return await session.send("CrashReportContext.getEntries", {})

    # ── Input (low-level CDP) ───────────────────────────────

    async def input_cancel_dragging(self) -> None:
        """Cancel any ongoing drag operation."""
        session = self._require_session()
        await session.send("Input.cancelDragging", {})

    async def input_dispatch_drag_event(
        self, type: str, x: float, y: float, data: dict[str, Any] | None = None
    ) -> None:
        """Dispatch a drag event to the page."""
        session = self._require_session()
        params: dict[str, Any] = {"type": type, "x": x, "y": y}
        if data is not None:
            params["data"] = data
        await session.send("Input.dispatchDragEvent", params)

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
        """Dispatch a key event to the page."""
        session = self._require_session()
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
        await session.send("Input.dispatchKeyEvent", params)

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
        """Dispatch a mouse event to the page."""
        session = self._require_session()
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
        await session.send("Input.dispatchMouseEvent", params)

    async def input_dispatch_touch_event(
        self,
        type: str,
        touch_points: list[dict[str, Any]],
        modifiers: int = 0,
        timestamp: float = 0,
    ) -> None:
        """Dispatch a touch event to the page."""
        session = self._require_session()
        params: dict[str, Any] = {"type": type, "touchPoints": touch_points}
        if modifiers:
            params["modifiers"] = modifiers
        if timestamp:
            params["timestamp"] = timestamp
        await session.send("Input.dispatchTouchEvent", params)

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
        """Emulate a touch event from a mouse event."""
        session = self._require_session()
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
        await session.send("Input.emulateTouchFromMouseEvent", params)

    async def input_ime_set_composition(
        self,
        text: str,
        selection_start: int,
        selection_end: int,
        replacement_start: int = 0,
        replacement_end: int = 0,
    ) -> None:
        """Set the IME composition."""
        session = self._require_session()
        params: dict[str, Any] = {
            "text": text,
            "selectionStart": selection_start,
            "selectionEnd": selection_end,
        }
        if replacement_start:
            params["replacementStart"] = replacement_start
        if replacement_end:
            params["replacementEnd"] = replacement_end
        await session.send("Input.imeSetComposition", params)

    async def input_insert_text(self, text: str) -> None:
        """Insert text into the focused element."""
        session = self._require_session()
        await session.send("Input.insertText", {"text": text})

    async def input_set_ignore_input_events(self, ignore: bool) -> None:
        """Set whether to ignore input events."""
        session = self._require_session()
        await session.send("Input.setIgnoreInputEvents", {"ignore": ignore})

    async def input_set_intercept_drags(self, enabled: bool) -> None:
        """Set whether to intercept drag operations."""
        session = self._require_session()
        await session.send("Input.setInterceptDrags", {"enabled": enabled})

    async def input_synthesize_pinch_gesture(
        self, x: float, y: float, scale_factor: float, relative_pointer_speed: int = 0
    ) -> None:
        """Synthesize a pinch gesture."""
        session = self._require_session()
        params: dict[str, Any] = {"x": x, "y": y, "scaleFactor": scale_factor}
        if relative_pointer_speed:
            params["relativePointerSpeed"] = relative_pointer_speed
        await session.send("Input.synthesizePinchGesture", params)

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
        """Synthesize a scroll gesture."""
        session = self._require_session()
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
        await session.send("Input.synthesizeScrollGesture", params)

    async def input_synthesize_tap_gesture(
        self, x: float, y: float, duration: int = 0, tap_count: int = 1
    ) -> None:
        """Synthesize a tap gesture."""
        session = self._require_session()
        params: dict[str, Any] = {"x": x, "y": y}
        if duration:
            params["duration"] = duration
        if tap_count != 1:
            params["tapCount"] = tap_count
        await session.send("Input.synthesizeTapGesture", params)

    # ── Network (additional CDP methods) ────────────────────

    async def network_clear_accepted_encodings_override(self) -> None:
        """Clear the accepted encodings override."""
        session = self._require_session()
        await session.send("Network.clearAcceptedEncodingsOverride", {})

    async def network_configure_durable_messages(self, options: dict[str, Any]) -> None:
        """Configure durable messages."""
        session = self._require_session()
        await session.send("Network.configureDurableMessages", {"options": options})

    async def network_delete_device_bound_session(self, session_id: str) -> None:
        """Delete a device-bound session."""
        session = self._require_session()
        await session.send("Network.deleteDeviceBoundSession", {"sessionId": session_id})

    async def network_disable(self) -> None:
        """Disable the Network domain."""
        session = self._require_session()
        await session.send("Network.disable", {})

    async def network_emulate_network_conditions_by_rule(
        self,
        download_throughput: float = 0,
        upload_throughput: float = 0,
        offline: bool = False,
        latency: float = 0,
        connection_type: str = "",
    ) -> None:
        """Emulate network conditions by rule."""
        session = self._require_session()
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
        await session.send("Network.emulateNetworkConditionsByRule", params)

    async def network_enable(
        self, max_total_buffer_size: int = 0, max_resource_buffer_size: int = 0
    ) -> None:
        """Enable the Network domain."""
        session = self._require_session()
        params: dict[str, Any] = {}
        if max_total_buffer_size:
            params["maxTotalBufferSize"] = max_total_buffer_size
        if max_resource_buffer_size:
            params["maxResourceBufferSize"] = max_resource_buffer_size
        await session.send("Network.enable", params)

    async def network_enable_device_bound_sessions(self) -> None:
        """Enable device-bound sessions."""
        session = self._require_session()
        await session.send("Network.enableDeviceBoundSessions", {})

    async def network_enable_reporting_api(self, enable: bool) -> None:
        """Enable or disable the Reporting API."""
        session = self._require_session()
        await session.send("Network.enableReportingApi", {"enable": enable})

    async def network_fetch_schemeful_site(self, request_id: str) -> dict[str, Any]:
        """Fetch the schemeful site for a request."""
        session = self._require_session()
        return await session.send("Network.fetchSchemefulSite", {"requestId": request_id})

    async def network_get_certificate(self, origin: str) -> dict[str, Any]:
        """Get the certificate for an origin."""
        session = self._require_session()
        return await session.send("Network.getCertificate", {"origin": origin})

    async def network_get_request_post_data(self, request_id: str) -> str:
        """Get the POST data for a request."""
        session = self._require_session()
        result = await session.send("Network.getRequestPostData", {"requestId": request_id})
        return result.get("postData", "")

    async def network_get_response_body_for_interception(self, interception_id: str) -> str:
        """Get the response body for an interception."""
        session = self._require_session()
        result = await session.send(
            "Network.getResponseBodyForInterception", {"interceptionId": interception_id}
        )
        return result.get("body", "")

    async def network_get_security_isolation_status(self, frame_id: str = "") -> dict[str, Any]:
        """Get the security isolation status."""
        session = self._require_session()
        params: dict[str, Any] = {}
        if frame_id:
            params["frameId"] = frame_id
        return await session.send("Network.getSecurityIsolationStatus", params)

    async def network_override_network_state(self, state: dict[str, Any]) -> None:
        """Override the network state."""
        session = self._require_session()
        await session.send("Network.overrideNetworkState", state)

    async def network_search_in_response_body(
        self, request_id: str, query: str, case_sensitive: bool = False, is_regex: bool = False
    ) -> dict[str, Any]:
        """Search in a response body."""
        session = self._require_session()
        params: dict[str, Any] = {"requestId": request_id, "query": query}
        if case_sensitive:
            params["caseSensitive"] = case_sensitive
        if is_regex:
            params["isRegex"] = is_regex
        return await session.send("Network.searchInResponseBody", params)

    async def network_set_accepted_encodings(self, encodings: list[str]) -> None:
        """Set accepted encodings."""
        session = self._require_session()
        await session.send("Network.setAcceptedEncodings", {"encodings": encodings})

    async def network_set_attach_debug_stack(self, enabled: bool) -> None:
        """Set whether to attach debug stack to network requests."""
        session = self._require_session()
        await session.send("Network.setAttachDebugStack", {"enabled": enabled})

    async def network_set_cookies(self, cookies: list[dict[str, Any]]) -> None:
        """Set cookies."""
        session = self._require_session()
        await session.send("Network.setCookies", {"cookies": cookies})

    async def network_stream_resource_content(self, request_id: str) -> dict[str, Any]:
        """Stream resource content for a request."""
        session = self._require_session()
        return await session.send("Network.streamResourceContent", {"requestId": request_id})

    async def network_take_response_body_for_interception_as_stream(
        self, interception_id: str
    ) -> dict[str, Any]:
        """Take the response body for an interception as a stream."""
        session = self._require_session()
        return await session.send(
            "Network.takeResponseBodyForInterceptionAsStream",
            {"interceptionId": interception_id},
        )

    # ── SmartCardEmulation ────────────────────────────────

    async def smart_card_enable(self) -> None:
        """Enable the SmartCardEmulation domain.

        Bug #24: uses _send_cdp to translate method-not-found/timeout errors.
        """
        session = self._require_session()
        await self._send_cdp(session, "SmartCardEmulation.enable", {})

    async def smart_card_disable(self) -> None:
        """Disable the SmartCardEmulation domain."""
        session = self._require_session()
        await self._send_cdp(session, "SmartCardEmulation.disable", {})

    async def smart_card_report_error(self, request_id: str, error: str) -> None:
        """Report an error for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            error: Error code string.
        """
        session = self._require_session()
        await session.send(
            "SmartCardEmulation.reportError",
            {"requestId": request_id, "error": error},
        )

    async def smart_card_report_plain_result(self, request_id: str, result_code: int) -> None:
        """Report a plain result for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
        """
        session = self._require_session()
        await session.send(
            "SmartCardEmulation.reportPlainResult",
            {"requestId": request_id, "resultCode": result_code},
        )

    async def smart_card_report_connect_result(
        self, request_id: str, result_code: int, connection_id: str
    ) -> None:
        """Report a connect result for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
            connection_id: Established connection identifier.
        """
        session = self._require_session()
        await session.send(
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
        """Report a data result for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
            data: Response data (hex-encoded).
        """
        session = self._require_session()
        await session.send(
            "SmartCardEmulation.reportDataResult",
            {
                "requestId": request_id,
                "resultCode": result_code,
                "data": data,
            },
        )

    async def smart_card_report_status_result(self, request_id: str, status: str) -> None:
        """Report a status result for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            status: Status string.
        """
        session = self._require_session()
        await session.send(
            "SmartCardEmulation.reportStatusResult",
            {"requestId": request_id, "status": status},
        )

    async def smart_card_report_begin_transaction_result(
        self, request_id: str, result_code: int
    ) -> None:
        """Report a begin-transaction result for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
        """
        session = self._require_session()
        await session.send(
            "SmartCardEmulation.reportBeginTransactionResult",
            {"requestId": request_id, "resultCode": result_code},
        )

    async def smart_card_report_establish_context_result(
        self, request_id: str, result_code: int, context_id: str
    ) -> None:
        """Report an establish-context result for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
            context_id: Established context identifier.
        """
        session = self._require_session()
        await session.send(
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
        """Report a release-context result for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
        """
        session = self._require_session()
        await session.send(
            "SmartCardEmulation.reportReleaseContextResult",
            {"requestId": request_id, "resultCode": result_code},
        )

    async def smart_card_report_list_readers_result(
        self, request_id: str, result_code: int, readers: list[dict[str, Any]]
    ) -> None:
        """Report a list-readers result for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
            readers: List of reader dicts.
        """
        session = self._require_session()
        await session.send(
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
        """Report a get-status-change result for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
            readers: List of reader status dicts.
        """
        session = self._require_session()
        await session.send(
            "SmartCardEmulation.reportGetStatusChangeResult",
            {
                "requestId": request_id,
                "resultCode": result_code,
                "readers": readers,
            },
        )

    # ── System Info ───────────────────────────────────────

    async def system_info_get_info(self) -> dict[str, Any]:
        """Get system info (OS, GPU, model, etc.) via CDP.

        Bug #18: ``SystemInfo.getInfo`` is only supported on the browser
        target, not on a page session. Previously this called
        ``session.send(...)`` which raised
        ``[-32000] SystemInfo.getInfo is only supported on the browser target``.
        We now send the command via the browser-level CDPClient.
        """
        client = self._require_client()
        return dict(await client.send("SystemInfo.getInfo", {}))

    async def system_info_get_process_info(self) -> list[dict[str, Any]]:
        """Get process info for the browser via CDP."""
        client = self._require_client()
        result = await client.send("SystemInfo.getProcessInfo", {})
        return [dict(p) for p in result.get("processInfo", [])] if result else []

    async def system_info_get_feature_state(self, feature_name: str) -> dict[str, Any]:
        """Get the state of a specific feature via CDP.

        Args:
            feature_name: The feature name to query.

        Returns:
            Dict with feature state information.
        """
        session = self._require_session()
        return dict(await session.send("SystemInfo.getFeatureState", {"featureName": feature_name}))

    async def __aenter__(self) -> CDPBackend:
        """Enter async context manager, returning self.

        Returns:
            The CDPBackend instance.
        """
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Exit async context manager, closing the backend.

        Args:
            exc_type: Exception type if raised, else None.
            exc_val: Exception value if raised, else None.
            exc_tb: Traceback if raised, else None.
        """
        await self.close()

    # ── Accessibility (extended) ──────────────────────────

    async def a11y_disable(self) -> None:
        """Disable the accessibility domain."""
        session = self._require_session()
        await session.send("Accessibility.disable")

    async def a11y_enable(self) -> None:
        """Enable the accessibility domain."""
        session = self._require_session()
        await session.send("Accessibility.enable")

    async def a11y_get_ax_node_and_ancestors(
        self,
        node_id: int | None = None,
        backend_node_id: int | None = None,
        object_id: str | None = None,
    ) -> dict[str, Any]:
        """Fetch a node and all ancestors up to and including the root.

        Args:
            node_id: DOM node ID.
            backend_node_id: Backend DOM node ID.
            object_id: JavaScript object ID.

        Returns:
            Dict with ``nodes`` list.
        """
        session = self._require_session()
        params: dict[str, Any] = {}
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        return dict(await session.send("Accessibility.getAXNodeAndAncestors", params))

    async def a11y_get_child_ax_nodes(
        self, node_id: str, frame_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Fetch children of an accessibility node by AXNodeId.

        Args:
            node_id: Accessibility node ID.
            frame_id: Optional frame ID.

        Returns:
            List of child node dicts.
        """
        session = self._require_session()
        params: dict[str, Any] = {"id": node_id}
        if frame_id is not None:
            params["frameId"] = frame_id
        result = await session.send("Accessibility.getChildAXNodes", params)
        return list(result.get("nodes", []))

    async def a11y_get_full_ax_tree(
        self, depth: int | None = None, frame_id: str | None = None
    ) -> dict[str, Any]:
        """Fetch the entire accessibility tree for the root document.

        Args:
            depth: Maximum depth to fetch.
            frame_id: Optional frame ID.

        Returns:
            Dict with ``nodes`` list.
        """
        session = self._require_session()
        params: dict[str, Any] = {}
        if depth is not None:
            params["depth"] = depth
        if frame_id is not None:
            params["frameId"] = frame_id
        return dict(await session.send("Accessibility.getFullAXTree", params))

    async def a11y_get_partial_ax_tree(
        self,
        node_id: int | None = None,
        backend_node_id: int | None = None,
        object_id: str | None = None,
        fetch_relatives: bool = True,
    ) -> dict[str, Any]:
        """Fetch a partial accessibility tree for a DOM node.

        Args:
            node_id: DOM node ID.
            backend_node_id: Backend DOM node ID.
            object_id: JavaScript object ID.
            fetch_relatives: Whether to fetch relatives.

        Returns:
            Dict with ``nodes`` list.
        """
        session = self._require_session()
        params: dict[str, Any] = {"fetchRelatives": fetch_relatives}
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        return dict(await session.send("Accessibility.getPartialAXTree", params))

    async def a11y_get_root_ax_node(self, frame_id: str | None = None) -> dict[str, Any]:
        """Fetch the root accessibility node.

        Args:
            frame_id: Optional frame ID.

        Returns:
            Dict with the root node.
        """
        session = self._require_session()
        params: dict[str, Any] = {}
        if frame_id is not None:
            params["frameId"] = frame_id
        return dict(await session.send("Accessibility.getRootAXNode", params))

    async def a11y_query_ax_tree(
        self,
        node_id: int | None = None,
        backend_node_id: int | None = None,
        object_id: str | None = None,
        accessible_name: str | None = None,
        role: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query a DOM node's accessibility subtree.

        Args:
            node_id: DOM node ID.
            backend_node_id: Backend DOM node ID.
            object_id: JavaScript object ID.
            accessible_name: Filter by accessible name.
            role: Filter by role.

        Returns:
            List of matching node dicts.
        """
        session = self._require_session()
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
        result = await session.send("Accessibility.queryAXTree", params)
        return list(result.get("nodes", []))

    # ── Ads ────────────────────────────────────────────────

    async def ads_get_ad_metrics(self) -> dict[str, Any]:
        """Get ad metrics for the current page."""
        session = self._require_session()
        return dict(await session.send("Ads.getAdMetrics"))

    # ── Animation (extended) ──────────────────────────────

    async def animation_disable(self) -> None:
        """Disable the Animation domain."""
        session = self._require_session()
        await session.send("Animation.disable")

    async def animation_enable(self) -> None:
        """Enable the Animation domain."""
        session = self._require_session()
        await session.send("Animation.enable")

    async def animation_get_current_time(self, animation_id: str) -> float:
        """Get the current time of an animation.

        Args:
            animation_id: The animation ID.

        Returns:
            Current time in milliseconds.
        """
        session = self._require_session()
        result = await session.send("Animation.getCurrentTime", {"id": animation_id})
        return float(result.get("currentTime", 0))

    async def animation_get_playback_rate(self) -> float:
        """Get the playback rate of the document timeline.

        Returns:
            Playback rate (1.0 = normal).
        """
        session = self._require_session()
        result = await session.send("Animation.getPlaybackRate")
        return float(result.get("playbackRate", 1.0))

    async def animation_release_animations(self, animations: list[str]) -> None:
        """Release animations to free resources.

        Args:
            animations: List of animation IDs to release.
        """
        session = self._require_session()
        await session.send("Animation.releaseAnimations", {"animations": animations})

    async def animation_replay(self, animations: list[str]) -> None:
        """Replay animations from the beginning.

        Args:
            animations: List of animation IDs to replay.
        """
        session = self._require_session()
        await session.send("Animation.replay", {"animations": animations})

    async def animation_resolve_animation(self, animation_id: str) -> dict[str, Any]:
        """Get the remote object of an Animation.

        Args:
            animation_id: The animation ID.

        Returns:
            Dict with remote object info.
        """
        session = self._require_session()
        return dict(await session.send("Animation.resolveAnimation", {"animationId": animation_id}))

    async def animation_seek_animations(self, animations: list[str], current_time: int) -> None:
        """Seek a set of animations to a particular time.

        Args:
            animations: List of animation IDs.
            current_time: Target time in milliseconds.
        """
        session = self._require_session()
        await session.send(
            "Animation.seekAnimations",
            {"animations": animations, "currentTime": current_time},
        )

    async def animation_seek_to(self, animations: list[str], current_time: int) -> None:
        """Seek animations to a specific time.

        Args:
            animations: List of animation IDs.
            current_time: Target time in milliseconds.
        """
        session = self._require_session()
        await session.send(
            "Animation.seekTo",
            {"animations": animations, "currentTime": current_time},
        )

    async def animation_set_paused(self, animations: list[str], paused: bool) -> None:
        """Pause or resume animations.

        Args:
            animations: List of animation IDs.
            paused: True to pause, False to resume.
        """
        session = self._require_session()
        await session.send(
            "Animation.setPaused",
            {"animations": animations, "paused": paused},
        )

    async def animation_set_playback_rate(self, playback_rate: float) -> None:
        """Set the global animation playback rate.

        Args:
            playback_rate: Playback rate (1.0 = normal).
        """
        session = self._require_session()
        await session.send("Animation.setPlaybackRate", {"playbackRate": playback_rate})

    async def animation_set_timing(self, animation_id: str, duration: int, delay: int) -> None:
        """Set the timing of an animation.

        Args:
            animation_id: The animation ID.
            duration: Duration in milliseconds.
            delay: Delay in milliseconds.
        """
        session = self._require_session()
        await session.send(
            "Animation.setTiming",
            {"animationId": animation_id, "duration": duration, "delay": delay},
        )

    # ── Audits ─────────────────────────────────────────────

    async def audits_check_contrast(self) -> dict[str, Any]:
        """Check contrast issues on the current page."""
        session = self._require_session()
        return dict(await session.send("Audits.checkContrast"))

    async def audits_check_forms_issues(self) -> dict[str, Any]:
        """Run the form issues check for the target page."""
        session = self._require_session()
        return dict(await session.send("Audits.checkFormsIssues"))

    async def audits_disable(self) -> None:
        """Disable the Audits domain."""
        session = self._require_session()
        await session.send("Audits.disable")

    async def audits_enable(self) -> None:
        """Enable the Audits domain."""
        session = self._require_session()
        await session.send("Audits.enable")

    async def audits_get_encoded_response(
        self,
        request_id: str,
        encoding: str,
        quality: float | None = None,
        size_only: bool | None = None,
    ) -> dict[str, Any]:
        """Get the encoded response body for a request.

        Args:
            request_id: The network request ID.
            encoding: Encoding format ("webp", "jpeg", "png").
            quality: Optional quality (0-1) for jpeg.
            size_only: If True, only return size info.

        Returns:
            Dict with encoded body, body size, and encoding.
        """
        session = self._require_session()
        params: dict[str, Any] = {"requestId": request_id, "encoding": encoding}
        if quality is not None:
            params["quality"] = quality
        if size_only is not None:
            params["sizeOnly"] = size_only
        return dict(await session.send("Audits.getEncodedResponse", params))

    # ── Autofill ───────────────────────────────────────────

    async def autofill_disable(self) -> None:
        """Disable the Autofill domain."""
        session = self._require_session()
        await session.send("Autofill.disable")

    async def autofill_enable(self) -> None:
        """Enable the Autofill domain."""
        session = self._require_session()
        await session.send("Autofill.enable")

    async def autofill_set_addresses(self, addresses: list[dict[str, Any]]) -> None:
        """Set autofill addresses for testing.

        Args:
            addresses: List of address dicts.
        """
        session = self._require_session()
        await session.send("Autofill.setAddresses", {"addresses": addresses})

    async def autofill_trigger(
        self,
        field_id: int,
        frame_id: str | None = None,
        card: dict[str, Any] | None = None,
        address: dict[str, Any] | None = None,
    ) -> None:
        """Trigger autofill on a form identified by the fieldId.

        Args:
            field_id: The field ID to trigger autofill on.
            frame_id: Optional frame ID.
            card: Optional card data.
            address: Optional address data.
        """
        session = self._require_session()
        params: dict[str, Any] = {"fieldId": field_id}
        if frame_id is not None:
            params["frameId"] = frame_id
        if card is not None:
            params["card"] = card
        if address is not None:
            params["address"] = address
        await session.send("Autofill.trigger", params)

    async def autofill_trigger_fill(
        self,
        field_id: int,
        frame_id: str | None = None,
        card: dict[str, Any] | None = None,
        address: dict[str, Any] | None = None,
    ) -> None:
        """Trigger autofill on a form field.

        Args:
            field_id: The field ID.
            frame_id: Optional frame ID.
            card: Optional card data.
            address: Optional address data.
        """
        session = self._require_session()
        params: dict[str, Any] = {"fieldId": field_id}
        if frame_id is not None:
            params["frameId"] = frame_id
        if card is not None:
            params["card"] = card
        if address is not None:
            params["address"] = address
        await session.send("Autofill.triggerFill", params)

    async def autofill_trigger_fill_after_save(
        self, field_id: int, frame_id: str | None = None
    ) -> None:
        """Trigger autofill using saved data after a user save action.

        Args:
            field_id: The field ID.
            frame_id: Optional frame ID.
        """
        session = self._require_session()
        params: dict[str, Any] = {"fieldId": field_id}
        if frame_id is not None:
            params["frameId"] = frame_id
        await session.send("Autofill.triggerFillAfterSave", params)

    # ── Background Service ─────────────────────────────────

    async def background_service_clear_events(self, service: str) -> None:
        """Clear all stored events for a background service.

        Args:
            service: The background service name.
        """
        session = self._require_session()
        await session.send("BackgroundService.clearEvents", {"service": service})

    async def background_service_set_recording(self, should_record: bool, service: str) -> None:
        """Set recording state for a background service.

        Args:
            should_record: Whether to record events.
            service: The background service name.
        """
        session = self._require_session()
        await session.send(
            "BackgroundService.setRecording",
            {"shouldRecord": should_record, "service": service},
        )

    async def background_service_start_observing(self, service: str) -> None:
        """Start observing events for a background service.

        Args:
            service: The background service name.
        """
        session = self._require_session()
        await session.send("BackgroundService.startObserving", {"service": service})

    async def background_service_stop_observing(self, service: str) -> None:
        """Stop observing events for a background service.

        Args:
            service: The background service name.
        """
        session = self._require_session()
        await session.send("BackgroundService.stopObserving", {"service": service})

    # ── Bluetooth Emulation ────────────────────────────────

    async def bluetooth_emulation_add_characteristic(
        self, service_id: str, characteristic_uuid: str, properties: dict[str, Any]
    ) -> str:
        """Add a characteristic to a service.

        Args:
            service_id: The service ID.
            characteristic_uuid: The characteristic UUID.
            properties: Characteristic properties dict.

        Returns:
            The characteristic ID.
        """
        session = self._require_session()
        result = await session.send(
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
        """Add a descriptor to a characteristic.

        Args:
            characteristic_id: The characteristic ID.
            descriptor_uuid: The descriptor UUID.

        Returns:
            The descriptor ID.
        """
        session = self._require_session()
        result = await session.send(
            "BluetoothEmulation.addDescriptor",
            {
                "characteristicId": characteristic_id,
                "descriptorUuid": descriptor_uuid,
            },
        )
        return str(result.get("descriptorId", ""))

    async def bluetooth_emulation_add_service(self, address: str, service_uuid: str) -> str:
        """Add a service to a peripheral.

        Args:
            address: The peripheral address.
            service_uuid: The service UUID.

        Returns:
            The service ID.
        """
        session = self._require_session()
        result = await session.send(
            "BluetoothEmulation.addService",
            {"address": address, "serviceUuid": service_uuid},
        )
        return str(result.get("serviceId", ""))

    async def bluetooth_emulation_disable(self) -> None:
        """Disable the Bluetooth emulation domain."""
        session = self._require_session()
        await self._send_cdp(session, "BluetoothEmulation.disable", {})

    async def bluetooth_emulation_enable(self, state: str, le_supported: bool) -> None:
        """Enable the Bluetooth emulation domain.

        Args:
            state: The central state ("powered-on", "powered-off").
            le_supported: Whether LE is supported.
        """
        session = self._require_session()
        await self._send_cdp(
            session,
            "BluetoothEmulation.enable",
            {"state": state, "leSupported": le_supported},
        )

    async def bluetooth_emulation_remove_characteristic(self, characteristic_id: str) -> None:
        """Remove a characteristic from the simulated central.

        Args:
            characteristic_id: The characteristic ID.
        """
        session = self._require_session()
        await session.send(
            "BluetoothEmulation.removeCharacteristic",
            {"characteristicId": characteristic_id},
        )

    async def bluetooth_emulation_remove_descriptor(self, descriptor_id: str) -> None:
        """Remove a descriptor from the simulated central.

        Args:
            descriptor_id: The descriptor ID.
        """
        session = self._require_session()
        await session.send(
            "BluetoothEmulation.removeDescriptor",
            {"descriptorId": descriptor_id},
        )

    async def bluetooth_emulation_remove_service(self, service_id: str) -> None:
        """Remove a service from the simulated central.

        Args:
            service_id: The service ID.
        """
        session = self._require_session()
        await session.send("BluetoothEmulation.removeService", {"serviceId": service_id})

    async def bluetooth_emulation_set_simulated_central_state(self, state: str) -> None:
        """Set the simulated central state.

        Args:
            state: The central state ("powered-on", "powered-off").
        """
        session = self._require_session()
        await session.send("BluetoothEmulation.setSimulatedCentralState", {"state": state})

    async def bluetooth_emulation_simulate_advertisement(self, entry: dict[str, Any]) -> None:
        """Simulate a Bluetooth advertisement.

        Args:
            entry: Advertisement entry dict.
        """
        session = self._require_session()
        await session.send("BluetoothEmulation.simulateAdvertisement", {"entry": entry})

    async def bluetooth_emulation_simulate_characteristic_operation_response(
        self, characteristic_id: str, op_type: str, code: int, data: str | None = None
    ) -> None:
        """Simulate a characteristic operation response.

        Args:
            characteristic_id: The characteristic ID.
            op_type: Operation type ("read", "write").
            code: Response code.
            data: Optional response data.
        """
        session = self._require_session()
        params: dict[str, Any] = {
            "characteristicId": characteristic_id,
            "opType": op_type,
            "code": code,
        }
        if data is not None:
            params["data"] = data
        await session.send("BluetoothEmulation.simulateCharacteristicOperationResponse", params)

    async def bluetooth_emulation_simulate_descriptor_operation_response(
        self, descriptor_id: str, op_type: str, code: int, data: str | None = None
    ) -> None:
        """Simulate a descriptor operation response.

        Args:
            descriptor_id: The descriptor ID.
            op_type: Operation type ("read", "write").
            code: Response code.
            data: Optional response data.
        """
        session = self._require_session()
        params: dict[str, Any] = {
            "descriptorId": descriptor_id,
            "opType": op_type,
            "code": code,
        }
        if data is not None:
            params["data"] = data
        await session.send("BluetoothEmulation.simulateDescriptorOperationResponse", params)

    async def bluetooth_emulation_simulate_gatt_disconnection(self, address: str) -> None:
        """Simulate a GATT disconnection.

        Args:
            address: The peripheral address.
        """
        session = self._require_session()
        await session.send("BluetoothEmulation.simulateGATTDisconnection", {"address": address})

    async def bluetooth_emulation_simulate_gatt_operation_response(
        self, address: str, op_type: str, code: int
    ) -> None:
        """Simulate a GATT operation response.

        Args:
            address: The peripheral address.
            op_type: Operation type.
            code: Response code.
        """
        session = self._require_session()
        await session.send(
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
        """Simulate a preconnected peripheral.

        Args:
            address: The peripheral address.
            name: The peripheral name.
            manufacturer_data: List of manufacturer data dicts.
            known_service_uuids: List of known service UUIDs.
        """
        session = self._require_session()
        await session.send(
            "BluetoothEmulation.simulatePreconnectedPeripheral",
            {
                "address": address,
                "name": name,
                "manufacturerData": manufacturer_data,
                "knownServiceUuids": known_service_uuids,
            },
        )

    # ── Browser (extended) ─────────────────────────────────

    async def browser_add_privacy_sandbox_coordinator_key_config(
        self,
        api: str,
        coordinator_origin: str,
        key_config: str,
        browser_context_id: str | None = None,
    ) -> None:
        """Configure encryption keys for a privacy sandbox API.

        Args:
            api: The privacy sandbox API name.
            coordinator_origin: The coordinator origin.
            key_config: The key configuration.
            browser_context_id: Optional browser context ID.
        """
        session = self._require_session()
        params: dict[str, Any] = {
            "api": api,
            "coordinatorOrigin": coordinator_origin,
            "keyConfig": key_config,
        }
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        await session.send("Browser.addPrivacySandboxCoordinatorKeyConfig", params)

    async def browser_add_privacy_sandbox_enrollment_override(self, url: str) -> None:
        """Allow a site to use privacy sandbox features that require enrollment.

        Args:
            url: The URL to enroll.
        """
        session = self._require_session()
        await session.send("Browser.addPrivacySandboxEnrollmentOverride", {"url": url})

    async def browser_cancel_download(
        self, guid: str, browser_context_id: str | None = None
    ) -> None:
        """Cancel a download if in progress.

        Args:
            guid: The download GUID.
            browser_context_id: Optional browser context ID.
        """
        session = self._require_session()
        params: dict[str, Any] = {"guid": guid}
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        await session.send("Browser.cancelDownload", params)

    async def browser_crash(self) -> None:
        """Crashes browser on the main thread."""
        session = self._require_session()
        await session.send("Browser.crash")

    async def browser_crash_gpu_process(self) -> None:
        """Crashes GPU process."""
        session = self._require_session()
        await session.send("Browser.crashGpuProcess")

    async def browser_execute_browser_command(self, command_id: str) -> None:
        """Invoke custom browser commands used by telemetry.

        Args:
            command_id: The command ID.
        """
        session = self._require_session()
        await session.send("Browser.executeBrowserCommand", {"commandId": command_id})

    async def browser_get_browser_command_line(self) -> str:
        """Returns the command line switches for the browser process.

        Returns:
            The command line string.
        """
        session = self._require_session()
        result = await session.send("Browser.getBrowserCommandLine")
        return str(result.get("commandLine", ""))

    async def browser_get_command_line(self) -> str:
        """Returns the command line switches for the browser process.

        Returns:
            The command line string.
        """
        session = self._require_session()
        result = await session.send("Browser.getCommandLine")
        return str(result.get("commandLine", ""))

    async def browser_get_histogram(self, name: str, delta: bool = False) -> dict[str, Any]:
        """Get a Chrome histogram by name.

        Args:
            name: Histogram name.
            delta: If True, return delta since last call.

        Returns:
            Dict with histogram data.
        """
        session = self._require_session()
        return dict(await session.send("Browser.getHistogram", {"name": name, "delta": delta}))

    async def browser_get_histograms(
        self, query: str | None = None, delta: bool = False
    ) -> list[dict[str, Any]]:
        """Get Chrome histograms.

        Args:
            query: Optional query string to filter.
            delta: If True, return deltas since last call.

        Returns:
            List of histogram dicts.
        """
        session = self._require_session()
        params: dict[str, Any] = {"delta": delta}
        if query is not None:
            params["query"] = query
        result = await session.send("Browser.getHistograms", params)
        return list(result.get("histograms", []))

    async def browser_get_version(self) -> dict[str, Any]:
        """Returns version information.

        Returns:
            Dict with protocolVersion, product, revision, etc.
        """
        session = self._require_session()
        return dict(await session.send("Browser.getVersion"))

    async def browser_get_window_for_target(self, target_id: str | None = None) -> dict[str, Any]:
        """Get the browser window that contains the devtools target.

        Args:
            target_id: Optional target ID.

        Returns:
            Dict with windowId and bounds.
        """
        session = self._require_session()
        params: dict[str, Any] = {}
        if target_id is not None:
            params["targetId"] = target_id
        return dict(await session.send("Browser.getWindowForTarget", params))

    async def browser_grant_permissions(
        self,
        origin: str,
        permissions: list[str],
        browser_context_id: str | None = None,
    ) -> None:
        """Grant specific permissions to the given origin.

        Args:
            origin: The origin to grant permissions to.
            permissions: List of permission names.
            browser_context_id: Optional browser context ID.
        """
        session = self._require_session()
        params: dict[str, Any] = {"origin": origin, "permissions": permissions}
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        await session.send("Browser.grantPermissions", params)

    async def browser_set_contents_size(
        self, window_id: int, width: int | None = None, height: int | None = None
    ) -> None:
        """Set size of the browser contents.

        Args:
            window_id: The window ID.
            width: Optional width.
            height: Optional height.
        """
        session = self._require_session()
        params: dict[str, Any] = {"windowId": window_id}
        if width is not None:
            params["width"] = width
        if height is not None:
            params["height"] = height
        await session.send("Browser.setContentsSize", params)

    async def browser_set_dock_tile(
        self, badge_label: str | None = None, image: str | None = None
    ) -> None:
        """Set dock tile details (platform-specific).

        Args:
            badge_label: Optional badge label.
            image: Optional base64-encoded image.
        """
        session = self._require_session()
        params: dict[str, Any] = {}
        if badge_label is not None:
            params["badgeLabel"] = badge_label
        if image is not None:
            params["image"] = image
        await session.send("Browser.setDockTile", params)

    async def browser_set_download_behavior(
        self,
        behavior: str,
        browser_context_id: str | None = None,
        download_path: str | None = None,
        events_enabled: bool = False,
    ) -> None:
        """Set the behavior when downloading a file.

        Args:
            behavior: "allow", "deny", or "default".
            browser_context_id: Optional browser context ID.
            download_path: Optional download path.
            events_enabled: Whether to emit download events.
        """
        session = self._require_session()
        params: dict[str, Any] = {
            "behavior": behavior,
            "eventsEnabled": events_enabled,
        }
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        if download_path is not None:
            params["downloadPath"] = download_path
        await session.send("Browser.setDownloadBehavior", params)

    async def browser_set_permission(
        self,
        permission: dict[str, Any],
        setting: str,
        origin: str | None = None,
        embedded_origin: str | None = None,
        browser_context_id: str | None = None,
    ) -> None:
        """Set permission settings for given embedding and embedded origins.

        Args:
            permission: Permission descriptor dict.
            setting: "grant", "deny", or "prompt".
            origin: Optional origin.
            embedded_origin: Optional embedded origin.
            browser_context_id: Optional browser context ID.
        """
        session = self._require_session()
        params: dict[str, Any] = {"permission": permission, "setting": setting}
        if origin is not None:
            params["origin"] = origin
        if embedded_origin is not None:
            params["embeddedOrigin"] = embedded_origin
        if browser_context_id is not None:
            params["browserContextId"] = browser_context_id
        await session.send("Browser.setPermission", params)

    # ── Debugger ──────────────────────────────────────────

    async def debugger_continue_to_location(
        self, location: dict[str, Any], target_call_frames: str | None = None
    ) -> None:
        """Continue execution until a specific location."""
        session = self._require_session()
        params: dict[str, Any] = {"location": location}
        if target_call_frames is not None:
            params["targetCallFrames"] = target_call_frames
        await session.send("Debugger.continueToLocation", params)

    async def debugger_disable(self) -> None:
        """Disable the Debugger domain."""
        session = self._require_session()
        await session.send("Debugger.disable", {})

    async def debugger_disassemble_wasm_module(self, script_id: str) -> dict[str, Any]:
        """Disassemble a Wasm module and return the first chunk."""
        session = self._require_session()
        return dict(await session.send("Debugger.disassembleWasmModule", {"scriptId": script_id}))

    async def debugger_enable(self, max_scripts_cache_size: int | None = None) -> None:
        """Enable the Debugger domain."""
        session = self._require_session()
        params: dict[str, Any] = {}
        if max_scripts_cache_size is not None:
            params["maxScriptsCacheSize"] = max_scripts_cache_size
        await session.send("Debugger.enable", params)

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
        """Evaluate an expression in the context of a call frame."""
        session = self._require_session()
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
        return dict(await session.send("Debugger.evaluateOnCallFrame", params))

    async def debugger_get_possible_breakpoints(
        self,
        start: dict[str, Any],
        end: dict[str, Any] | None = None,
        restrict_to_function: bool | None = None,
    ) -> list[dict[str, Any]]:
        """Get possible breakpoint locations for a range."""
        session = self._require_session()
        params: dict[str, Any] = {"start": start}
        if end is not None:
            params["end"] = end
        if restrict_to_function is not None:
            params["restrictToFunction"] = restrict_to_function
        result = await session.send("Debugger.getPossibleBreakpoints", params)
        return list(result.get("locations", []))

    async def debugger_get_script_source(self, script_id: str) -> str:
        """Get the source code of a script."""
        session = self._require_session()
        result = await session.send("Debugger.getScriptSource", {"scriptId": script_id})
        return str(result.get("scriptSource", ""))

    async def debugger_get_stack_trace(self, stack_trace_id: dict[str, Any]) -> dict[str, Any]:
        """Get stack trace with a given stack trace ID."""
        session = self._require_session()
        return dict(await session.send("Debugger.getStackTrace", {"stackTraceId": stack_trace_id}))

    async def debugger_get_wasm_bytecode(self, script_id: str) -> dict[str, Any]:
        """Get Wasm bytecode for a script."""
        session = self._require_session()
        return dict(await session.send("Debugger.getWasmBytecode", {"scriptId": script_id}))

    async def debugger_next_wasm_disassembly_chunk(self, stream_id: str) -> dict[str, Any]:
        """Get the next chunk of Wasm disassembly."""
        session = self._require_session()
        return dict(
            await session.send("Debugger.nextWasmDisassemblyChunk", {"streamId": stream_id})
        )

    async def debugger_pause(self) -> None:
        """Pause script execution."""
        session = self._require_session()
        await session.send("Debugger.pause", {})

    async def debugger_pause_on_async_call(self, parent_stack_trace_id: dict[str, Any]) -> None:
        """Pause on the next async call."""
        session = self._require_session()
        await session.send(
            "Debugger.pauseOnAsyncCall", {"parentStackTraceId": parent_stack_trace_id}
        )

    async def debugger_remove_breakpoint(self, breakpoint_id: str) -> None:
        """Remove a breakpoint by ID."""
        session = self._require_session()
        await session.send("Debugger.removeBreakpoint", {"breakpointId": breakpoint_id})

    async def debugger_restart_frame(self, call_frame_id: str, mode: str) -> None:
        """Restart a particular call frame."""
        session = self._require_session()
        await session.send("Debugger.restartFrame", {"callFrameId": call_frame_id, "mode": mode})

    async def debugger_resume(self, terminate_on_resume: bool | None = None) -> None:
        """Resume script execution after a pause."""
        session = self._require_session()
        params: dict[str, Any] = {}
        if terminate_on_resume is not None:
            params["terminateOnResume"] = terminate_on_resume
        await session.send("Debugger.resume", params)

    async def debugger_search_in_content(
        self,
        script_id: str,
        query: str,
        case_sensitive: bool | None = None,
        is_regex: bool | None = None,
    ) -> list[dict[str, Any]]:
        """Search for a string in a script's content."""
        session = self._require_session()
        params: dict[str, Any] = {"scriptId": script_id, "query": query}
        if case_sensitive is not None:
            params["caseSensitive"] = case_sensitive
        if is_regex is not None:
            params["isRegex"] = is_regex
        result = await session.send("Debugger.searchInContent", params)
        return list(result.get("result", []))

    async def debugger_set_async_call_stack_depth(self, max_depth: int) -> None:
        """Enable or disable async call stack tracking."""
        session = self._require_session()
        await session.send("Debugger.setAsyncCallStackDepth", {"maxDepth": max_depth})

    async def debugger_set_blackbox_execution_contexts(
        self, execution_context_ids: list[int]
    ) -> None:
        """Replace blackbox execution contexts."""
        session = self._require_session()
        await session.send(
            "Debugger.setBlackboxExecutionContexts", {"executionContextIds": execution_context_ids}
        )

    async def debugger_set_blackbox_patterns(
        self, patterns: list[str], skip_anonymous: bool | None = None
    ) -> None:
        """Set patterns to blackbox scripts."""
        session = self._require_session()
        params: dict[str, Any] = {"patterns": patterns}
        if skip_anonymous is not None:
            params["skipAnonymous"] = skip_anonymous
        await session.send("Debugger.setBlackboxPatterns", params)

    async def debugger_set_blackboxed_ranges(
        self, script_id: str, positions: list[dict[str, Any]]
    ) -> None:
        """Set blackboxed ranges for a script."""
        session = self._require_session()
        await session.send(
            "Debugger.setBlackboxedRanges", {"scriptId": script_id, "positions": positions}
        )

    async def debugger_set_breakpoint(
        self, location: dict[str, Any], condition: str | None = None
    ) -> dict[str, Any]:
        """Set a breakpoint at a script location."""
        session = self._require_session()
        params: dict[str, Any] = {"location": location}
        if condition is not None:
            params["condition"] = condition
        return dict(await session.send("Debugger.setBreakpoint", params))

    async def debugger_set_breakpoint_by_url(
        self,
        line_number: int,
        url: str | None = None,
        url_regex: str | None = None,
        script_hash: str | None = None,
        column_number: int | None = None,
        condition: str | None = None,
    ) -> dict[str, Any]:
        """Set a breakpoint by script URL, regex, or hash."""
        session = self._require_session()
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
        return dict(await session.send("Debugger.setBreakpointByUrl", params))

    async def debugger_set_breakpoint_on_function_call(
        self, object_id: str, condition: str | None = None
    ) -> None:
        """Set a breakpoint before each call to the given function."""
        session = self._require_session()
        params: dict[str, Any] = {"objectId": object_id}
        if condition is not None:
            params["condition"] = condition
        await session.send("Debugger.setBreakpointOnFunctionCall", params)

    async def debugger_set_breakpoints_active(self, active: bool) -> None:
        """Enable or disable all breakpoints."""
        session = self._require_session()
        await session.send("Debugger.setBreakpointsActive", {"active": active})

    async def debugger_set_instrumentation_breakpoint(self, instrumentation: str) -> None:
        """Set instrumentation breakpoint."""
        session = self._require_session()
        await session.send(
            "Debugger.setInstrumentationBreakpoint", {"instrumentation": instrumentation}
        )

    async def debugger_set_pause_on_exceptions(self, state: str) -> None:
        """Set pause on exceptions mode."""
        session = self._require_session()
        await session.send("Debugger.setPauseOnExceptions", {"state": state})

    async def debugger_set_return_value(self, new_value: dict[str, Any]) -> None:
        """Set the return value of the current function."""
        session = self._require_session()
        await session.send("Debugger.setReturnValue", {"newValue": new_value})

    async def debugger_set_script_source(
        self,
        script_id: str,
        source: str,
        dry_run: bool | None = None,
        allow_top_frame_editing: bool | None = None,
    ) -> dict[str, Any]:
        """Set the source code of a script."""
        session = self._require_session()
        params: dict[str, Any] = {"scriptId": script_id, "source": source}
        if dry_run is not None:
            params["dryRun"] = dry_run
        if allow_top_frame_editing is not None:
            params["allowTopFrameEditing"] = allow_top_frame_editing
        return dict(await session.send("Debugger.setScriptSource", params))

    async def debugger_set_skip_all_pauses(self, skip: bool) -> None:
        """Skip all pauses."""
        session = self._require_session()
        await session.send("Debugger.setSkipAllPauses", {"skip": skip})

    async def debugger_set_variable_value(
        self,
        call_frame_id: str,
        scope_number: int,
        variable_name: str,
        new_value: dict[str, Any],
    ) -> None:
        """Set the value of a variable in a call frame."""
        session = self._require_session()
        await session.send(
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
        """Step into the next function call."""
        session = self._require_session()
        params: dict[str, Any] = {}
        if break_on_async_call is not None:
            params["breakOnAsyncCall"] = break_on_async_call
        if skip_list is not None:
            params["skipList"] = skip_list
        await session.send("Debugger.stepInto", params)

    async def debugger_step_out(self) -> None:
        """Step out of the current function."""
        session = self._require_session()
        await session.send("Debugger.stepOut", {})

    async def debugger_step_over(self, skip_list: list[dict[str, Any]] | None = None) -> None:
        """Step over the next function call."""
        session = self._require_session()
        params: dict[str, Any] = {}
        if skip_list is not None:
            params["skipList"] = skip_list
        await session.send("Debugger.stepOver", params)

    # ── HeapProfiler ──────────────────────────────────────

    async def heap_profiler_add_inspected_heap_object(self, heap_object_id: str) -> None:
        """Enable console to refer to the node with given id via $x."""
        session = self._require_session()
        await session.send("HeapProfiler.addInspectedHeapObject", {"heapObjectId": heap_object_id})

    async def heap_profiler_collect_garbage(self) -> None:
        """Force garbage collection."""
        session = self._require_session()
        await session.send("HeapProfiler.collectGarbage", {})

    async def heap_profiler_disable(self) -> None:
        """Disable the HeapProfiler domain."""
        session = self._require_session()
        await session.send("HeapProfiler.disable", {})

    async def heap_profiler_enable(self) -> None:
        """Enable the HeapProfiler domain."""
        session = self._require_session()
        await session.send("HeapProfiler.enable", {})

    async def heap_profiler_get_heap_object_id(self, object_id: str) -> str:
        """Get the heap object ID for a remote object."""
        session = self._require_session()
        result = await session.send("HeapProfiler.getHeapObjectId", {"objectId": object_id})
        return str(result.get("heapObjectId", ""))

    async def heap_profiler_get_object_by_heap_object_id(
        self, heap_object_id: str, object_group: str | None = None
    ) -> dict[str, Any]:
        """Get a remote object by heap object ID."""
        session = self._require_session()
        params: dict[str, Any] = {"heapObjectId": heap_object_id}
        if object_group is not None:
            params["objectGroup"] = object_group
        return dict(await session.send("HeapProfiler.getObjectByHeapObjectId", params))

    async def heap_profiler_get_sampling_profile(self) -> dict[str, Any]:
        """Get the sampling heap profile."""
        session = self._require_session()
        return dict(await session.send("HeapProfiler.getSamplingProfile", {}))

    async def heap_profiler_start_sampling(
        self,
        sampling_interval: float | None = None,
        stack_depth: float | None = None,
        include_objects_collected_by_major_gc: bool = False,
        include_objects_collected_by_minor_gc: bool = False,
    ) -> None:
        """Start sampling heap allocations."""
        session = self._require_session()
        params: dict[str, Any] = {
            "includeObjectsCollectedByMajorGC": include_objects_collected_by_major_gc,
            "includeObjectsCollectedByMinorGC": include_objects_collected_by_minor_gc,
        }
        if sampling_interval is not None:
            params["samplingInterval"] = sampling_interval
        if stack_depth is not None:
            params["stackDepth"] = stack_depth
        await session.send("HeapProfiler.startSampling", params)

    async def heap_profiler_start_tracking_heap_objects(
        self, track_allocations: bool = False
    ) -> None:
        """Start tracking heap object allocation."""
        session = self._require_session()
        await session.send(
            "HeapProfiler.startTrackingHeapObjects", {"trackAllocations": track_allocations}
        )

    async def heap_profiler_stop_sampling(self) -> dict[str, Any]:
        """Stop sampling heap allocations and return the profile."""
        session = self._require_session()
        return dict(await session.send("HeapProfiler.stopSampling", {}))

    async def heap_profiler_stop_tracking_heap_objects(
        self,
        report_progress: bool = False,
        capture_numeric_value: bool = False,
        expose_internals: bool = False,
    ) -> dict[str, Any]:
        """Stop tracking heap object allocation."""
        session = self._require_session()
        return dict(
            await session.send(
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
        """Take a heap snapshot."""
        session = self._require_session()
        await session.send(
            "HeapProfiler.takeHeapSnapshot",
            {
                "reportProgress": report_progress,
                "captureNumericValue": capture_numeric_value,
                "exposeInternals": expose_internals,
            },
        )

    # ── SmartCardEmulation ────────────────────────────────

    async def smart_card_emulation_disable(self) -> None:
        """Disable the SmartCardEmulation domain."""
        session = self._require_session()
        await self._send_cdp(session, "SmartCardEmulation.disable", {})

    async def smart_card_emulation_enable(self) -> None:
        """Enable the SmartCardEmulation domain."""
        session = self._require_session()
        await self._send_cdp(session, "SmartCardEmulation.enable", {})

    async def smart_card_emulation_report_begin_transaction_result(
        self, request_id: str, handle: int
    ) -> None:
        """Report the result of beginning a transaction."""
        session = self._require_session()
        await session.send(
            "SmartCardEmulation.reportBeginTransactionResult",
            {"requestId": request_id, "handle": handle},
        )

    async def smart_card_emulation_report_connect_result(
        self, request_id: str, handle: int, active_protocol: str | None = None
    ) -> None:
        """Report the result of connecting to a card."""
        session = self._require_session()
        params: dict[str, Any] = {"requestId": request_id, "handle": handle}
        if active_protocol is not None:
            params["activeProtocol"] = active_protocol
        await session.send("SmartCardEmulation.reportConnectResult", params)

    async def smart_card_emulation_report_data_result(self, request_id: str, data: str) -> None:
        """Report the result of a data transfer."""
        session = self._require_session()
        await session.send(
            "SmartCardEmulation.reportDataResult", {"requestId": request_id, "data": data}
        )

    async def smart_card_emulation_report_error(self, request_id: str, result_code: str) -> None:
        """Report an error result for a request."""
        session = self._require_session()
        await session.send(
            "SmartCardEmulation.reportError", {"requestId": request_id, "resultCode": result_code}
        )

    async def smart_card_emulation_report_establish_context_result(
        self, request_id: str, context_id: int
    ) -> None:
        """Report the result of establishing a context."""
        session = self._require_session()
        await session.send(
            "SmartCardEmulation.reportEstablishContextResult",
            {"requestId": request_id, "contextId": context_id},
        )

    async def smart_card_emulation_report_get_status_change_result(
        self, request_id: str, reader_states: list[dict[str, Any]]
    ) -> None:
        """Report the result of getting status changes."""
        session = self._require_session()
        await session.send(
            "SmartCardEmulation.reportGetStatusChangeResult",
            {"requestId": request_id, "readerStates": reader_states},
        )

    async def smart_card_emulation_report_list_readers_result(
        self, request_id: str, readers: list[str]
    ) -> None:
        """Report the result of listing readers."""
        session = self._require_session()
        await session.send(
            "SmartCardEmulation.reportListReadersResult",
            {"requestId": request_id, "readers": readers},
        )

    async def smart_card_emulation_report_plain_result(self, request_id: str) -> None:
        """Report a plain result."""
        session = self._require_session()
        await session.send("SmartCardEmulation.reportPlainResult", {"requestId": request_id})

    async def smart_card_emulation_report_release_context_result(self, request_id: str) -> None:
        """Report the result of releasing a context."""
        session = self._require_session()
        await session.send(
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
        """Report the status of a card."""
        session = self._require_session()
        params: dict[str, Any] = {
            "requestId": request_id,
            "readerName": reader_name,
            "state": state,
            "atr": atr,
        }
        if protocol is not None:
            params["protocol"] = protocol
        await session.send("SmartCardEmulation.reportStatusResult", params)

    # ── IndexedDB ─────────────────────────────────────────

    async def indexed_db_clear_object_store(
        self,
        database_name: str,
        object_store_name: str,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: dict[str, Any] | None = None,
    ) -> None:
        """Clears all entries from an object store."""
        session = self._require_session()
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
        await session.send("IndexedDB.clearObjectStore", params)

    async def indexed_db_delete_database(
        self,
        database_name: str,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: dict[str, Any] | None = None,
    ) -> None:
        """Deletes a database."""
        session = self._require_session()
        params: dict[str, Any] = {"databaseName": database_name}
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        await session.send("IndexedDB.deleteDatabase", params)

    async def indexed_db_delete_object_store_entries(
        self,
        database_name: str,
        object_store_name: str,
        key_range: dict[str, Any],
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: dict[str, Any] | None = None,
    ) -> None:
        """Delete a range of entries from an object store."""
        session = self._require_session()
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
        await session.send("IndexedDB.deleteObjectStoreEntries", params)

    async def indexed_db_disable(self) -> None:
        """Disables events from backend."""
        session = self._require_session()
        await session.send("IndexedDB.disable", {})

    async def indexed_db_enable(self) -> None:
        """Enables events from backend."""
        session = self._require_session()
        await session.send("IndexedDB.enable", {})

    async def indexed_db_get_metadata(
        self,
        database_name: str,
        object_store_name: str,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Gets metadata of an object store."""
        session = self._require_session()
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
        return dict(await session.send("IndexedDB.getMetadata", params))

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
        """Requests data from object store or index."""
        session = self._require_session()
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
        return dict(await session.send("IndexedDB.requestData", params))

    async def indexed_db_request_database(
        self,
        database_name: str,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Requests database with given name."""
        session = self._require_session()
        params: dict[str, Any] = {"databaseName": database_name}
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        return dict(await session.send("IndexedDB.requestDatabase", params))

    async def indexed_db_request_database_names(
        self,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Requests database names."""
        session = self._require_session()
        params: dict[str, Any] = {}
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        return dict(await session.send("IndexedDB.requestDatabaseNames", params))

    # ── LayerTree ─────────────────────────────────────────

    async def layer_tree_compositing_reasons(self, layer_id: str) -> dict[str, Any]:
        """Provides the reasons why the given layer was composited."""
        session = self._require_session()
        return dict(await session.send("LayerTree.compositingReasons", {"layerId": layer_id}))

    async def layer_tree_disable(self) -> None:
        """Disables compositing tree inspection."""
        session = self._require_session()
        await session.send("LayerTree.disable", {})

    async def layer_tree_enable(self) -> None:
        """Enables compositing tree inspection."""
        session = self._require_session()
        await session.send("LayerTree.enable", {})

    async def layer_tree_load_snapshot(self, tiles: list[dict[str, Any]]) -> str:
        """Returns the snapshot identifier."""
        session = self._require_session()
        result = await session.send("LayerTree.loadSnapshot", {"tiles": tiles})
        return str(result.get("snapshotId", ""))

    async def layer_tree_make_snapshot(self, layer_id: str) -> str:
        """Returns the layer snapshot identifier."""
        session = self._require_session()
        result = await session.send("LayerTree.makeSnapshot", {"layerId": layer_id})
        return str(result.get("snapshotId", ""))

    async def layer_tree_profile_snapshot(
        self,
        snapshot_id: str,
        min_repeat_count: int | None = None,
        min_duration: float | None = None,
        clip_rect: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Profile a layer snapshot."""
        session = self._require_session()
        params: dict[str, Any] = {"snapshotId": snapshot_id}
        if min_repeat_count is not None:
            params["minRepeatCount"] = min_repeat_count
        if min_duration is not None:
            params["minDuration"] = min_duration
        if clip_rect is not None:
            params["clipRect"] = clip_rect
        return dict(await session.send("LayerTree.profileSnapshot", params))

    async def layer_tree_release_snapshot(self, snapshot_id: str) -> None:
        """Releases layer snapshot."""
        session = self._require_session()
        await session.send("LayerTree.releaseSnapshot", {"snapshotId": snapshot_id})

    async def layer_tree_replay_snapshot(
        self,
        snapshot_id: str,
        from_step: int | None = None,
        to_step: int | None = None,
        scale: float | None = None,
    ) -> dict[str, Any]:
        """Replays the layer snapshot."""
        session = self._require_session()
        params: dict[str, Any] = {"snapshotId": snapshot_id}
        if from_step is not None:
            params["fromStep"] = from_step
        if to_step is not None:
            params["toStep"] = to_step
        if scale is not None:
            params["scale"] = scale
        return dict(await session.send("LayerTree.replaySnapshot", params))

    async def layer_tree_snapshot_command_log(self, snapshot_id: str) -> dict[str, Any]:
        """Replays the layer snapshot and returns canvas log."""
        session = self._require_session()
        return dict(await session.send("LayerTree.snapshotCommandLog", {"snapshotId": snapshot_id}))

    # ── FedCM ─────────────────────────────────────────────

    async def fed_cm_click_dialog_button(self, dialog_id: str, dialog_button: str) -> None:
        """Click a FedCM dialog button."""
        session = self._require_session()
        await session.send(
            "FedCM.clickDialogButton", {"dialogId": dialog_id, "dialogButton": dialog_button}
        )

    async def fed_cm_disable(self) -> None:
        """Disable the FedCM domain."""
        session = self._require_session()
        await session.send("FedCM.disable", {})

    async def fed_cm_dismiss_dialog(self, dialog_id: str, trigger_cooldown: bool = False) -> None:
        """Dismiss a FedCM dialog."""
        session = self._require_session()
        await session.send(
            "FedCM.dismissDialog", {"dialogId": dialog_id, "triggerCooldown": trigger_cooldown}
        )

    async def fed_cm_enable(self, disable_rejection_delay: bool = False) -> None:
        """Enable the FedCM domain."""
        session = self._require_session()
        await session.send("FedCM.enable", {"disableRejectionDelay": disable_rejection_delay})

    async def fed_cm_open_url(
        self, dialog_id: str, account_index: int, account_url_type: str
    ) -> None:
        """Open a URL in a FedCM dialog."""
        session = self._require_session()
        await session.send(
            "FedCM.openURL",
            {
                "dialogId": dialog_id,
                "accountIndex": account_index,
                "accountUrlType": account_url_type,
            },
        )

    async def fed_cm_reset_cooldown(self) -> None:
        """Reset the FedCM cooldown."""
        session = self._require_session()
        await session.send("FedCM.resetCooldown", {})

    async def fed_cm_select_account(self, dialog_id: str, account_index: int) -> None:
        """Select an account in a FedCM dialog."""
        session = self._require_session()
        await session.send(
            "FedCM.selectAccount", {"dialogId": dialog_id, "accountIndex": account_index}
        )

    # ── CacheStorage ──────────────────────────────────────

    async def cache_storage_delete_cache(self, cache_id: str) -> None:
        """Deletes a cache."""
        session = self._require_session()
        await session.send("CacheStorage.deleteCache", {"cacheId": cache_id})

    async def cache_storage_delete_entry(self, cache_id: str, request: str) -> None:
        """Deletes a cache entry."""
        session = self._require_session()
        await session.send("CacheStorage.deleteEntry", {"cacheId": cache_id, "request": request})

    async def cache_storage_request_cache_names(
        self,
        security_origin: str | None = None,
        storage_key: str | None = None,
        storage_bucket: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Requests cache names."""
        session = self._require_session()
        params: dict[str, Any] = {}
        if security_origin is not None:
            params["securityOrigin"] = security_origin
        if storage_key is not None:
            params["storageKey"] = storage_key
        if storage_bucket is not None:
            params["storageBucket"] = storage_bucket
        result = await session.send("CacheStorage.requestCacheNames", params)
        return list(result.get("caches", []))

    async def cache_storage_request_cached_response(
        self, cache_id: str, request_url: str, request_headers: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Fetches cache entry."""
        session = self._require_session()
        return dict(
            await session.send(
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
        """Requests data from cache."""
        session = self._require_session()
        params: dict[str, Any] = {"cacheId": cache_id}
        if skip_count is not None:
            params["skipCount"] = skip_count
        if page_size is not None:
            params["pageSize"] = page_size
        if path_filter is not None:
            params["pathFilter"] = path_filter
        return dict(await session.send("CacheStorage.requestEntries", params))

    # ── DOMStorage ────────────────────────────────────────

    async def dom_storage_clear(self, storage_id: dict[str, Any]) -> None:
        """Clear all DOM storage items."""
        session = self._require_session()
        await session.send("DOMStorage.clear", {"storageId": storage_id})

    async def dom_storage_clear_dom_storage_items(self, storage_id: dict[str, Any]) -> None:
        """Alias for clear."""
        session = self._require_session()
        await session.send("DOMStorage.clear", {"storageId": storage_id})

    async def dom_storage_disable(self) -> None:
        """Disable storage tracking."""
        session = self._require_session()
        await session.send("DOMStorage.disable", {})

    async def dom_storage_enable(self) -> None:
        """Enable storage tracking."""
        session = self._require_session()
        await session.send("DOMStorage.enable", {})

    async def dom_storage_get_dom_storage_items(
        self, storage_id: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Get DOM storage items."""
        session = self._require_session()
        result = await session.send("DOMStorage.getDOMStorageItems", {"storageId": storage_id})
        return list(result.get("items", []))

    async def dom_storage_remove_dom_storage_item(
        self, storage_id: dict[str, Any], key: str
    ) -> None:
        """Remove a DOM storage item."""
        session = self._require_session()
        await session.send("DOMStorage.removeDOMStorageItem", {"storageId": storage_id, "key": key})

    async def dom_storage_set_dom_storage_item(
        self, storage_id: dict[str, Any], key: str, value: str
    ) -> None:
        """Set a DOM storage item."""
        session = self._require_session()
        await session.send(
            "DOMStorage.setDOMStorageItem", {"storageId": storage_id, "key": key, "value": value}
        )

    # ── EventBreakpoints ──────────────────────────────────

    async def event_breakpoints_clear_instrumentation_breakpoint(self, event_name: str) -> None:
        """Remove a breakpoint on a particular native event."""
        session = self._require_session()
        await session.send(
            "EventBreakpoints.clearInstrumentationBreakpoint", {"eventName": event_name}
        )

    async def event_breakpoints_disable(self) -> None:
        """Remove all breakpoints."""
        session = self._require_session()
        await session.send("EventBreakpoints.disable", {})

    async def event_breakpoints_remove_instrumentation_breakpoint(self, event_name: str) -> None:
        """Remove a breakpoint on a particular native event."""
        session = self._require_session()
        await session.send(
            "EventBreakpoints.removeInstrumentationBreakpoint", {"eventName": event_name}
        )

    async def event_breakpoints_set_instrumentation_breakpoint(self, event_name: str) -> None:
        """Set a breakpoint on a particular native event."""
        session = self._require_session()
        await session.send(
            "EventBreakpoints.setInstrumentationBreakpoint", {"eventName": event_name}
        )

    # ── Extensions ────────────────────────────────────────

    async def extensions_get_extensions(self) -> list[dict[str, Any]]:
        """Gets a list of all unpacked extensions."""
        session = self._require_session()
        result = await session.send("Extensions.getExtensions", {})
        return list(result.get("extensions", []))

    async def extensions_load_unpacked(
        self, path: str, enable_in_incognito: bool = False
    ) -> dict[str, Any]:
        """Installs an unpacked extension from the filesystem."""
        session = self._require_session()
        valid_path = validate_path(path)
        return dict(
            await session.send(
                "Extensions.loadUnpacked",
                {"path": str(valid_path), "enableInIncognito": enable_in_incognito},
            )
        )

    async def extensions_uninstall(self, extension_id: str) -> None:
        """Uninstalls an unpacked extension."""
        session = self._require_session()
        await session.send("Extensions.uninstall", {"id": extension_id})

    # ── HeadlessExperimental ──────────────────────────────

    async def headless_experimental_begin_frame(
        self,
        frame_time_ticks: float | None = None,
        interval: float | None = None,
        no_display_updates: bool | None = None,
        screenshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a BeginFrame to the target.

        Bug #21: uses _send_cdp to translate method-not-found errors.
        """
        session = self._require_session()
        params: dict[str, Any] = {}
        if frame_time_ticks is not None:
            params["frameTimeTicks"] = frame_time_ticks
        if interval is not None:
            params["interval"] = interval
        if no_display_updates is not None:
            params["noDisplayUpdates"] = no_display_updates
        if screenshot is not None:
            params["screenshot"] = screenshot
        return dict(await self._send_cdp(session, "HeadlessExperimental.beginFrame", params))

    async def headless_experimental_disable(self) -> None:
        """Disable the HeadlessExperimental domain."""
        session = self._require_session()
        await self._send_cdp(session, "HeadlessExperimental.disable", {})

    async def headless_experimental_enable(self) -> None:
        """Enable the HeadlessExperimental domain."""
        session = self._require_session()
        await session.send("HeadlessExperimental.enable", {})

    # ── SystemInfo ────────────────────────────────────────

    async def system_info_get_feature_state(self, feature_state: str) -> dict[str, Any]:
        """Returns information about the feature state."""
        session = self._require_session()
        return dict(
            await session.send("SystemInfo.getFeatureState", {"featureState": feature_state})
        )

    async def system_info_get_info(self) -> dict[str, Any]:
        """Returns information about the system.

        Bug #18: ``SystemInfo.getInfo`` is only supported on the browser
        target. ``TabHandle`` inherits from ``CDPBackend`` but does not
        have a browser-level client, so we delegate to the parent
        backend's client when available; otherwise we raise a clear error.
        """
        client = self._client
        if client is None:
            raise WavexisError(
                "SystemInfo.getInfo is only supported on the browser target, "
                "but this TabHandle has no browser-level client. "
                "Call this command from the main wavexis backend, not from a tab."
            )
        return dict(await client.send("SystemInfo.getInfo", {}))

    async def system_info_get_process_info(self) -> dict[str, Any]:
        """Returns information about all running processes."""
        client = self._client
        if client is None:
            raise WavexisError(
                "SystemInfo.getProcessInfo is only supported on the browser "
                "target, but this TabHandle has no browser-level client."
            )
        return dict(await client.send("SystemInfo.getProcessInfo", {}))

    # ── DeviceOrientation ─────────────────────────────────

    async def device_orientation_clear_device_orientation_override(self) -> None:
        """Clear the device orientation override."""
        session = self._require_session()
        await session.send("DeviceOrientation.clearDeviceOrientationOverride", {})

    async def device_orientation_set_device_orientation_override(
        self, alpha: float, beta: float, gamma: float
    ) -> None:
        """Set a device orientation override."""
        session = self._require_session()
        await session.send(
            "DeviceOrientation.setDeviceOrientationOverride",
            {"alpha": alpha, "beta": beta, "gamma": gamma},
        )

    # ── DOMDebugger ───────────────────────────────────────

    async def dom_debugger_get_event_listeners(
        self, object_id: str, depth: int | None = None, pierce: bool | None = None
    ) -> list[dict[str, Any]]:
        """Get event listeners for a DOM node."""
        session = self._require_session()
        params: dict[str, Any] = {"objectId": object_id}
        if depth is not None:
            params["depth"] = depth
        if pierce is not None:
            params["pierce"] = pierce
        result = await session.send("DOMDebugger.getEventListeners", params)
        return list(result.get("listeners", []))

    async def dom_debugger_remove_dom_breakpoint(self, node_id: int, type: str) -> None:
        """Remove a DOM breakpoint from a node."""
        session = self._require_session()
        await session.send("DOMDebugger.removeDOMBreakpoint", {"nodeId": node_id, "type": type})

    async def dom_debugger_remove_event_listener_breakpoint(
        self, event_name: str, target_name: str | None = None
    ) -> None:
        """Remove an event listener breakpoint."""
        session = self._require_session()
        params: dict[str, Any] = {"eventName": event_name}
        if target_name is not None:
            params["targetName"] = target_name
        await session.send("DOMDebugger.removeEventListenerBreakpoint", params)

    async def dom_debugger_remove_instrumentation_breakpoint(self, event_name: str) -> None:
        """Remove an instrumentation breakpoint."""
        session = self._require_session()
        await session.send("DOMDebugger.removeInstrumentationBreakpoint", {"eventName": event_name})

    async def dom_debugger_remove_xhr_breakpoint(self, url: str) -> None:
        """Remove an XHR breakpoint."""
        session = self._require_session()
        await session.send("DOMDebugger.removeXHRBreakpoint", {"url": url})

    async def dom_debugger_set_break_on_csp_violation(self, violation_types: list[str]) -> None:
        """Set breakpoints on CSP violations."""
        session = self._require_session()
        await session.send(
            "DOMDebugger.setBreakOnCSPViolation", {"violationTypes": violation_types}
        )

    async def dom_debugger_set_dom_breakpoint(self, node_id: int, type: str) -> None:
        """Set a DOM breakpoint on a node."""
        session = self._require_session()
        await session.send("DOMDebugger.setDOMBreakpoint", {"nodeId": node_id, "type": type})

    async def dom_debugger_set_event_listener_breakpoint(
        self, event_name: str, target_name: str | None = None
    ) -> None:
        """Set an event listener breakpoint."""
        session = self._require_session()
        params: dict[str, Any] = {"eventName": event_name}
        if target_name is not None:
            params["targetName"] = target_name
        await session.send("DOMDebugger.setEventListenerBreakpoint", params)

    async def dom_debugger_set_instrumentation_breakpoint(self, event_name: str) -> None:
        """Set an instrumentation breakpoint."""
        session = self._require_session()
        await session.send("DOMDebugger.setInstrumentationBreakpoint", {"eventName": event_name})

    async def dom_debugger_set_xhr_breakpoint(self, url: str) -> None:
        """Set an XHR breakpoint."""
        session = self._require_session()
        await session.send("DOMDebugger.setXHRBreakpoint", {"url": url})

    # ── DOMSnapshot ───────────────────────────────────────

    async def dom_snapshot_capture_snapshot(
        self,
        computed_styles: list[str] | None = None,
        include_paint_order: bool = False,
        include_dom_rects: bool = False,
        include_blended_background_colors: bool = False,
        include_text_color_opacities: bool = False,
    ) -> dict[str, Any]:
        """Capture a document snapshot.

        Bug #7: ``computedStyles`` must be an array (even empty).
        """
        session = self._require_session()
        params: dict[str, Any] = {
            "computedStyles": computed_styles or [],
            "includePaintOrder": include_paint_order,
            "includeDOMRects": include_dom_rects,
            "includeBlendedBackgroundColors": include_blended_background_colors,
            "includeTextColorOpacities": include_text_color_opacities,
        }
        return dict(await session.send("DOMSnapshot.captureSnapshot", params))

    async def dom_snapshot_disable(self) -> None:
        """Disable the DOM snapshot agent."""
        session = self._require_session()
        await session.send("DOMSnapshot.disable", {})

    async def dom_snapshot_enable(self) -> None:
        """Enable the DOM snapshot agent."""
        session = self._require_session()
        await session.send("DOMSnapshot.enable", {})

    async def dom_snapshot_get_snapshot(
        self,
        computed_styles: list[str] | None = None,
        computed_style_whitelist: list[str] | None = None,
        include_event_listeners: bool | None = None,
        include_paint_order: bool | None = None,
        include_user_agent_shadow_tree: bool | None = None,
    ) -> dict[str, Any]:
        """Get a DOM snapshot.

        Bug #8: ``DOMSnapshot.getSnapshot`` is the older variant that
        expects ``computedStyleWhitelist`` (not ``computedStyles``). We
        accept both kwargs for compatibility but default to an empty
        whitelist so the call doesn't fail with ``Invalid parameters``.
        """
        session = self._require_session()
        # Prefer computed_styles if provided; fall back to whitelist.
        styles = computed_styles if computed_styles is not None else computed_style_whitelist
        params: dict[str, Any] = {"computedStyleWhitelist": styles or []}
        if include_event_listeners is not None:
            params["includeEventListeners"] = include_event_listeners
        if include_paint_order is not None:
            params["includePaintOrder"] = include_paint_order
        if include_user_agent_shadow_tree is not None:
            params["includeUserAgentShadowTree"] = include_user_agent_shadow_tree
        return dict(await session.send("DOMSnapshot.getSnapshot", params))

    # ── DeviceAccess ──────────────────────────────────────

    async def device_access_cancel_prompt(self, request_id: str) -> None:
        """Cancel a prompt."""
        session = self._require_session()
        await session.send("DeviceAccess.cancelPrompt", {"id": request_id})

    async def device_access_disable(self) -> None:
        """Disable events in this domain."""
        session = self._require_session()
        await session.send("DeviceAccess.disable", {})

    async def device_access_enable(self) -> None:
        """Enable events in this domain."""
        session = self._require_session()
        await session.send("DeviceAccess.enable", {})

    async def device_access_select_prompt(self, request_id: str, device_id: str) -> None:
        """Select a device in response to a prompt."""
        session = self._require_session()
        await session.send("DeviceAccess.selectPrompt", {"id": request_id, "deviceId": device_id})

    # ── Remaining single methods ──────────────────────────

    async def dom_get_attribute(self, node_id: int, name: str | None = None) -> dict[str, Any]:
        """Get attributes of a node."""
        session = self._require_session()
        params: dict[str, Any] = {"nodeId": node_id}
        if name is not None:
            params["name"] = name
        return dict(await session.send("DOM.getAttributes", params))

    async def webauthn_remove_virtual_authenticator(self, authenticator_id: str) -> None:
        """Remove a virtual authenticator."""
        session = self._require_session()
        await session.send(
            "WebAuthn.removeVirtualAuthenticator", {"authenticatorId": authenticator_id}
        )

    async def crash_report_context_get_entries(self) -> list[dict[str, Any]]:
        """Return all entries in the CrashReportContext."""
        session = self._require_session()
        result = await session.send("CrashReportContext.getEntries", {})
        return list(result.get("entries", []))

    async def digital_credentials_set_virtual_wallet_behavior(
        self,
        action: str,
        protocol: str | None = None,
        response: dict[str, Any] | None = None,
        frame_id: str | None = None,
    ) -> None:
        """Set the behavior of the virtual wallet."""
        session = self._require_session()
        params: dict[str, Any] = {"action": action}
        if protocol is not None:
            params["protocol"] = protocol
        if response is not None:
            params["response"] = response
        if frame_id is not None:
            params["frameId"] = frame_id
        await session.send("DigitalCredentials.setVirtualWalletBehavior", params)

    async def file_system_get_directory(
        self, storage_key: str, path_components: list[str], bucket_name: str = ""
    ) -> dict[str, Any]:
        """Get a file system directory."""
        session = self._require_session()
        return dict(
            await session.send(
                "FileSystem.getDirectory",
                {
                    "storageKey": storage_key,
                    "pathComponents": path_components,
                    "bucketName": bucket_name,
                },
            )
        )


class TabHandle(CDPBackend):
    """A handle to a browser tab sharing the same Chrome process.

    Created via ``CDPBackend.new_tab_handle()``. Shares the WebSocket
    connection (``_client``) with the parent backend but has its own
    CDP session (``_session``) for a specific tab.

    All CDPBackend methods work as-is because they use ``_require_session()``
    which returns this tab's session. Call ``close()`` to close the tab
    (not the browser).
    """

    def __init__(self, client: Any, session: Any) -> None:
        """Initialize the tab handle with a shared client and own session.

        Args:
            client: The CDPClient instance shared with the parent backend.
            session: The CDPSession for this specific tab.
        """
        self._client = client
        self._session = session
        self._console_entries: list[dict[str, Any]] = []
        self._log_entries: list[dict[str, Any]] = []
        self._current_url: str = ""
        self._subscriptions: dict[str, dict[str, Any]] = {}
        self._combined_traces: dict[str, dict[str, Any]] = {}

    async def close(self) -> None:
        """Close the tab session without closing the browser."""
        if self._session is not None:
            for handlers in self._subscriptions.values():
                for cdp_event, handler in handlers.items():
                    with contextlib.suppress(Exception):
                        self._session.off(cdp_event, handler)
            self._subscriptions.clear()
            await self._session.close()
            self._session = None
        self._client = None
        # Drop any in-progress combined traces so their captured frames
        # and events are released before the backend is reused or GC'd.
        self._combined_traces.clear()
