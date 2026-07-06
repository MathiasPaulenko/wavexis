"""HTTP server mode for wavexis using aiohttp.

aiohttp is an optional dependency under the [serve] extra.
All imports are lazy — ``WavexisError`` is raised if aiohttp is not installed.
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from typing import Any

from wavexis.backend.base import AbstractBackend
from wavexis.backend.manager import BackendManager
from wavexis.config import (
    BrowserOptions,
    CookieParams,
    DOMParams,
    EvalParams,
    HarParams,
    InputParams,
    PDFParams,
    ScrapeParams,
    ScreenshotParams,
    WaitStrategy,
)
from wavexis.exceptions import WavexisError

__version__ = "1.11.2"


def _import_aiohttp() -> Any:
    """Lazily import aiohttp and raise WavexisError if not installed."""
    try:
        from aiohttp import web  # type: ignore[import-not-found,unused-ignore]

        return web
    except ImportError as exc:
        raise WavexisError(
            "aiohttp is not installed. Run: pip install wavexis[serve]"
        ) from exc


# ── Handlers ───────────────────────────────────────────────


async def _get_backend(request: Any) -> AbstractBackend:
    """Create a fresh backend instance for this request.

    Actions call launch() and close() internally, so we cannot share
    a single backend across requests.
    """
    preferred = request.app.get("backend_name")
    manager = BackendManager()
    return manager.select(preferred=preferred)


async def _run_action(request: Any, action: Any) -> Any:
    """Launch backend, execute action, and close backend.

    Args:
        request: The aiohttp request.
        action: An action instance with an execute(backend) method.

    Returns:
        The result of action.execute().
    """
    backend = await _get_backend(request)
    await backend.launch(BrowserOptions())
    try:
        return await action.execute(backend)
    finally:
        await backend.close()


async def handle_screenshot(request: Any) -> Any:
    """Handle POST /screenshot — return PNG bytes."""
    web = _import_aiohttp()
    data = await request.json()
    params = ScreenshotParams(**data)
    from wavexis.actions.screenshot import ScreenshotAction

    action = ScreenshotAction(params)
    image_bytes = await _run_action(request, action)
    return web.Response(body=image_bytes, content_type="image/png")


async def handle_pdf(request: Any) -> Any:
    """Handle POST /pdf — return PDF bytes."""
    web = _import_aiohttp()
    data = await request.json()
    params = PDFParams(**data)
    from wavexis.actions.pdf import PDFAction

    action = PDFAction(params)
    pdf_bytes = await _run_action(request, action)
    return web.Response(body=pdf_bytes, content_type="application/pdf")


async def handle_eval(request: Any) -> Any:
    """Handle POST /eval — return JSON result."""
    web = _import_aiohttp()
    data = await request.json()
    params = EvalParams(**data)
    from wavexis.actions.eval import EvalAction

    action = EvalAction(params)
    result = await _run_action(request, action)
    return web.json_response({"result": result})


async def handle_scrape(request: Any) -> Any:
    """Handle POST /scrape — return JSON or CSV."""
    web = _import_aiohttp()
    data = await request.json()
    params = ScrapeParams(**data)
    from wavexis.actions.scrape import ScrapeAction

    action = ScrapeAction(params)
    result = await _run_action(request, action)
    if params.output_format == "csv":
        return web.Response(body=result, content_type="text/csv")
    return web.json_response({"result": result})


async def handle_dom_get(request: Any) -> Any:
    """Handle POST /dom/get — return HTML as JSON."""
    web = _import_aiohttp()
    data = await request.json()
    params = DOMParams(**data)
    from wavexis.actions.dom import DOMAction

    action = DOMAction(params)
    result = await _run_action(request, action)
    return web.json_response({"result": result})


async def handle_dom_query(request: Any) -> Any:
    """Handle POST /dom/query — return elements as JSON."""
    web = _import_aiohttp()
    data = await request.json()
    params = DOMParams(**data)
    from wavexis.actions.dom import DOMAction

    action = DOMAction(params)
    result = await _run_action(request, action)
    return web.json_response({"result": result})


async def handle_navigate(request: Any) -> Any:
    """Handle POST /navigate — navigate and return status."""
    web = _import_aiohttp()
    data = await request.json()
    url = data.get("url", "")
    wait_for = data.get("wait_for")
    strategy = WaitStrategy(
        strategy="selector", selector=wait_for
    ) if wait_for else WaitStrategy(strategy="load")
    backend = await _get_backend(request)
    await backend.launch(BrowserOptions())
    try:
        await backend.navigate(url, strategy)
    finally:
        await backend.close()
    return web.json_response({"status": "ok", "url": url})


async def handle_har(request: Any) -> Any:
    """Handle POST /har — return HAR data as JSON."""
    web = _import_aiohttp()
    data = await request.json()
    params = HarParams(**data)
    from wavexis.actions.har import HARAction

    action = HARAction(params)
    result = await _run_action(request, action)
    return web.json_response(result)


async def handle_cookies_get(request: Any) -> Any:
    """Handle POST /cookies/get — return cookies as JSON."""
    web = _import_aiohttp()
    data = await request.json()
    url = data.get("url", "")
    backend = await _get_backend(request)
    await backend.launch(BrowserOptions())
    try:
        await backend.navigate(url, WaitStrategy(strategy="load"))
        cookies = await backend.get_cookies()
    finally:
        await backend.close()
    return web.json_response({"cookies": cookies})


async def handle_cookies_set(request: Any) -> Any:
    """Handle POST /cookies/set — set a cookie and return status."""
    web = _import_aiohttp()
    data = await request.json()
    cookie_data = data.get("cookie", data)
    params = CookieParams(**cookie_data)
    backend = await _get_backend(request)
    await backend.launch(BrowserOptions())
    try:
        await backend.set_cookie(params)
    finally:
        await backend.close()
    return web.json_response({"status": "ok"})


async def handle_input_click(request: Any) -> Any:
    """Handle POST /input/click — click an element."""
    web = _import_aiohttp()
    data = await request.json()
    params = InputParams(**data, action="click")
    from wavexis.actions.input import InputAction

    action = InputAction(params)
    await _run_action(request, action)
    return web.json_response({"status": "ok"})


async def handle_input_type(request: Any) -> Any:
    """Handle POST /input/type — type text into an element."""
    web = _import_aiohttp()
    data = await request.json()
    params = InputParams(**data, action="type")
    from wavexis.actions.input import InputAction

    action = InputAction(params)
    await _run_action(request, action)
    return web.json_response({"status": "ok"})


async def handle_perf_metrics(request: Any) -> Any:
    """Handle POST /perf/metrics — return performance metrics."""
    web = _import_aiohttp()
    data = await request.json()
    url = data.get("url", "")
    from wavexis.actions.performance import PerformanceAction, PerformanceParams

    params = PerformanceParams(url=url, action="metrics")
    action = PerformanceAction(params)
    result = await _run_action(request, action)
    return web.json_response(result)


async def handle_perf_trace(request: Any) -> Any:
    """Handle POST /perf/trace — return performance trace."""
    web = _import_aiohttp()
    data = await request.json()
    url = data.get("url", "")
    duration_ms = data.get("duration_ms", 3000)
    from wavexis.actions.performance import PerformanceAction, PerformanceParams

    params = PerformanceParams(url=url, action="trace", duration_ms=duration_ms)
    action = PerformanceAction(params)
    result = await _run_action(request, action)
    return web.json_response(result)


async def handle_health(request: Any) -> Any:
    """Handle GET /health — return health status."""
    web = _import_aiohttp()
    return web.json_response({"status": "ok"})


async def handle_backends(request: Any) -> Any:
    """Handle GET /backends — return available backends."""
    web = _import_aiohttp()
    manager = BackendManager()
    available = manager.list_available()
    return web.json_response({
        "cdp": "cdp" in available,
        "bidi": "bidi" in available,
    })


async def handle_version(request: Any) -> Any:
    """Handle GET /version — return wavexis version."""
    web = _import_aiohttp()
    return web.json_response({"version": __version__})


async def handle_auth(request: Any) -> Any:
    """Handle POST /auth — apply auth context and navigate."""
    web = _import_aiohttp()
    from wavexis.auth import load_auth_context
    from wavexis.config import CookieParams

    data = await request.json()
    context_path = data.get("context", "")
    url = data.get("url", "")
    ctx = load_auth_context(context_path)
    backend = await _get_backend(request)
    await backend.launch(BrowserOptions())
    try:
        if ctx.headers:
            await backend.set_headers(ctx.headers)
        if ctx.username and ctx.password:
            import base64

            cred = base64.b64encode(
                f"{ctx.username}:{ctx.password}".encode()
            ).decode()
            await backend.set_headers({"Authorization": f"Basic {cred}"})
        await backend.navigate(url, WaitStrategy(strategy="load"))
        for cookie in ctx.cookies:
            cp = CookieParams(
                name=cookie.get("name", ""),
                value=cookie.get("value", ""),
                domain=cookie.get("domain", ""),
                path=cookie.get("path", "/"),
            )
            await backend.set_cookie(cp)
        await backend.navigate(url, WaitStrategy(strategy="load"))
    finally:
        await backend.close()
    return web.json_response({"status": "ok", "url": url})


async def handle_user_agent(request: Any) -> Any:
    """Handle POST /user-agent — set custom user agent."""
    web = _import_aiohttp()
    data = await request.json()
    ua = data.get("user_agent", "")
    url = data.get("url", "")
    backend = await _get_backend(request)
    await backend.launch(BrowserOptions())
    try:
        await backend.set_user_agent(ua)
        await backend.navigate(url, WaitStrategy(strategy="load"))
    finally:
        await backend.close()
    return web.json_response({"status": "ok", "user_agent": ua})


async def handle_headers(request: Any) -> Any:
    """Handle POST /headers — set custom HTTP headers."""
    web = _import_aiohttp()
    data = await request.json()
    headers = data.get("headers", {})
    url = data.get("url", "")
    backend = await _get_backend(request)
    await backend.launch(BrowserOptions())
    try:
        await backend.set_headers(headers)
        await backend.navigate(url, WaitStrategy(strategy="load"))
    finally:
        await backend.close()
    return web.json_response({"status": "ok", "headers": headers})


async def handle_device(request: Any) -> Any:
    """Handle POST /device — emulate a device preset."""
    web = _import_aiohttp()
    data = await request.json()
    device = data.get("device", "")
    url = data.get("url", "")
    backend = await _get_backend(request)
    await backend.launch(BrowserOptions())
    try:
        await backend.emulate_device(device)
        await backend.navigate(url, WaitStrategy(strategy="load"))
    finally:
        await backend.close()
    return web.json_response({"status": "ok", "device": device})


async def handle_multi(request: Any) -> Any:
    """Handle POST /multi — execute multiple actions from YAML."""
    web = _import_aiohttp()
    from pathlib import Path

    from wavexis.record import replay_from_yaml

    data = await request.json()
    yaml_path = data.get("config", "")
    backend = await _get_backend(request)
    await backend.launch(BrowserOptions(headless=True))
    try:
        results = await replay_from_yaml(Path(yaml_path), backend)
    finally:
        await backend.close()
    return web.json_response({
        "status": "ok",
        "actions": len(results),
        "results": [
            len(r) if isinstance(r, bytes) else str(r)[:200]
            for r in results
        ],
    })


# ── WebSocket handler ──────────────────────────────────────


async def _stream_screenshots(
    ws: Any, backend: AbstractBackend, interval: float, fmt: str, quality: int,
) -> None:
    """Periodically capture and stream screenshots."""
    while True:
        try:
            params = ScreenshotParams(url="", format=fmt, quality=quality)
            img = await backend.screenshot(params)
            b64 = base64.b64encode(img).decode("ascii")
            await ws.send_json({
                "type": "screenshot",
                "data": b64,
                "timestamp": time.time(),
            })
        except Exception as exc:
            await ws.send_json({
                "type": "error",
                "source": "screenshot",
                "message": str(exc),
            })
        await asyncio.sleep(interval)


async def _stream_console(
    ws: Any, backend: AbstractBackend, interval: float,
) -> None:
    """Poll console messages and stream new ones."""
    seen: set[int] = set()
    while True:
        try:
            messages = await backend.capture_console()
            for msg in messages:
                key = hash(json.dumps(msg, sort_keys=True))
                if key not in seen:
                    seen.add(key)
                    await ws.send_json({
                        "type": "console",
                        "data": msg,
                        "timestamp": time.time(),
                    })
        except Exception as exc:
            await ws.send_json({
                "type": "error",
                "source": "console",
                "message": str(exc),
            })
        await asyncio.sleep(interval)


async def _stream_navigation(
    ws: Any, backend: AbstractBackend, interval: float,
) -> None:
    """Poll URL changes and stream navigation events."""
    last_url: str = ""
    while True:
        try:
            result = await backend.eval("window.location.href")
            current_url = str(result) if result else ""
            if current_url != last_url:
                last_url = current_url
                await ws.send_json({
                    "type": "navigation",
                    "url": current_url,
                    "timestamp": time.time(),
                })
        except Exception as exc:
            await ws.send_json({
                "type": "error",
                "source": "navigation",
                "message": str(exc),
            })
        await asyncio.sleep(interval)


async def handle_websocket(request: Any) -> Any:
    """Handle GET /ws — WebSocket endpoint for real-time streaming.

    Client sends a JSON subscribe message:
        {
            "url": "https://example.com",
            "events": ["screenshot", "console", "navigation"],
            "interval": 1.0,
            "format": "png",
            "quality": 80
        }

    Server streams events as JSON messages until the client disconnects.
    """
    web = _import_aiohttp()
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    try:
        msg = await ws.receive()
        if msg.type == web.WSMsgType.TEXT:
            config = json.loads(msg.data)
        else:
            await ws.close()
            return ws
    except Exception:
        await ws.close()
        return ws

    url = config.get("url", "about:blank")
    events = config.get("events", ["screenshot"])
    interval = float(config.get("interval", 1.0))
    fmt = config.get("format", "png")
    quality = int(config.get("quality", 80))

    backend = await _get_backend(request)
    await backend.launch(BrowserOptions())
    await backend.navigate(url, WaitStrategy(strategy="load"))

    await ws.send_json({
        "type": "ready",
        "url": url,
        "events": events,
        "timestamp": time.time(),
    })

    tasks: list[asyncio.Task[None]] = []
    if "screenshot" in events:
        tasks.append(asyncio.create_task(
            _stream_screenshots(ws, backend, interval, fmt, quality),
        ))
    if "console" in events:
        tasks.append(asyncio.create_task(
            _stream_console(ws, backend, max(interval, 0.5)),
        ))
    if "navigation" in events:
        tasks.append(asyncio.create_task(
            _stream_navigation(ws, backend, max(interval, 0.5)),
        ))

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    cmd = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue
                action = cmd.get("action")
                if action == "navigate":
                    new_url = cmd.get("url", "")
                    await backend.navigate(new_url, WaitStrategy(strategy="load"))
                    await ws.send_json({
                        "type": "navigated",
                        "url": new_url,
                        "timestamp": time.time(),
                    })
                elif action == "eval":
                    expr = cmd.get("expression", "")
                    result = await backend.eval(expr)
                    await ws.send_json({
                        "type": "eval_result",
                        "result": result,
                        "timestamp": time.time(),
                    })
                elif action == "screenshot":
                    params = ScreenshotParams(url="", format=fmt, quality=quality)
                    img = await backend.screenshot(params)
                    b64 = base64.b64encode(img).decode("ascii")
                    await ws.send_json({
                        "type": "screenshot",
                        "data": b64,
                        "timestamp": time.time(),
                    })
                elif action == "close":
                    break
            elif msg.type in (web.WSMsgType.CLOSE, web.WSMsgType.CLOSING,
                               web.WSMsgType.CLOSED, web.WSMsgType.ERROR):
                break
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await backend.close()
        await ws.close()

    return ws


async def handle_plugins(request: Any) -> Any:
    """Handle GET /plugins — list discovered plugins."""
    from wavexis.plugins import get_registry

    registry = get_registry()
    return request.app["web"].json_response({
        "actions": registry.list_actions(),
        "backends": registry.list_backends(),
        "middleware": registry.list_middleware(),
    })


# ── App factory ─────────────────────────────────────────────


def create_app(backend_name: str | None = None) -> Any:
    """Create and configure the aiohttp web application.

    Args:
        backend_name: Preferred backend name (e.g. "cdp", "bidi").
            If None, auto-detects the first available backend.

    Returns:
        aiohttp.web.Application with all routes registered.

    Raises:
        WavexisError: If aiohttp is not installed.
        BackendNotAvailableError: If no backend is available.
    """
    web = _import_aiohttp()
    from wavexis.plugins import get_registry

    registry = get_registry()
    middlewares = [m.factory(web) for m in registry.middleware]
    app = web.Application(middlewares=middlewares)
    manager = BackendManager()
    app["backend_name"] = backend_name
    app["backends"] = manager.list_available()

    app.router.add_post("/screenshot", handle_screenshot)
    app.router.add_post("/pdf", handle_pdf)
    app.router.add_post("/eval", handle_eval)
    app.router.add_post("/scrape", handle_scrape)
    app.router.add_post("/dom/get", handle_dom_get)
    app.router.add_post("/dom/query", handle_dom_query)
    app.router.add_post("/navigate", handle_navigate)
    app.router.add_post("/har", handle_har)
    app.router.add_post("/cookies/get", handle_cookies_get)
    app.router.add_post("/cookies/set", handle_cookies_set)
    app.router.add_post("/input/click", handle_input_click)
    app.router.add_post("/input/type", handle_input_type)
    app.router.add_post("/perf/metrics", handle_perf_metrics)
    app.router.add_post("/perf/trace", handle_perf_trace)
    app.router.add_post("/auth", handle_auth)
    app.router.add_post("/user-agent", handle_user_agent)
    app.router.add_post("/headers", handle_headers)
    app.router.add_post("/device", handle_device)
    app.router.add_post("/multi", handle_multi)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/backends", handle_backends)
    app.router.add_get("/version", handle_version)
    app.router.add_get("/ws", handle_websocket)
    app.router.add_get("/plugins", handle_plugins)
    return app


def serve(
    port: int = 8080,
    host: str = "localhost",
    backend: str | None = None,
) -> None:
    """Start the wavexis HTTP server.

    Args:
        port: Port to listen on (default 8080).
        host: Host to bind to (default "localhost").
        backend: Preferred backend name (default auto-detect).

    Raises:
        WavexisError: If aiohttp is not installed.
        BackendNotAvailableError: If no backend is available.
    """
    web = _import_aiohttp()
    app = create_app(backend)
    web.run_app(app, host=host, port=port)
