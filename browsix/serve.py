"""HTTP server mode for browsix using aiohttp.

aiohttp is an optional dependency under the [serve] extra.
All imports are lazy — ``BrowsixError`` is raised if aiohttp is not installed.
"""

from __future__ import annotations

from typing import Any

from browsix.backend.base import AbstractBackend
from browsix.backend.manager import BackendManager
from browsix.config import (
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
from browsix.exceptions import BrowsixError

__version__ = "1.2.0"


def _import_aiohttp() -> Any:
    """Lazily import aiohttp and raise BrowsixError if not installed."""
    try:
        from aiohttp import web  # type: ignore[import-not-found,unused-ignore]

        return web
    except ImportError as exc:
        raise BrowsixError(
            "aiohttp is not installed. Run: pip install browsix[serve]"
        ) from exc


# ── Handlers ───────────────────────────────────────────────


async def _get_backend(request: Any) -> AbstractBackend:
    """Retrieve the shared backend from the app context."""
    backend: AbstractBackend = request.app["backend"]
    return backend


async def handle_screenshot(request: Any) -> Any:
    """Handle POST /screenshot — return PNG bytes."""
    web = _import_aiohttp()
    data = await request.json()
    params = ScreenshotParams(**data)
    from browsix.actions.screenshot import ScreenshotAction

    backend = await _get_backend(request)
    action = ScreenshotAction(params)
    image_bytes = await action.execute(backend)
    return web.Response(body=image_bytes, content_type="image/png")


async def handle_pdf(request: Any) -> Any:
    """Handle POST /pdf — return PDF bytes."""
    web = _import_aiohttp()
    data = await request.json()
    params = PDFParams(**data)
    from browsix.actions.pdf import PDFAction

    backend = await _get_backend(request)
    action = PDFAction(params)
    pdf_bytes = await action.execute(backend)
    return web.Response(body=pdf_bytes, content_type="application/pdf")


async def handle_eval(request: Any) -> Any:
    """Handle POST /eval — return JSON result."""
    web = _import_aiohttp()
    data = await request.json()
    params = EvalParams(**data)
    from browsix.actions.eval import EvalAction

    backend = await _get_backend(request)
    action = EvalAction(params)
    result = await action.execute(backend)
    return web.json_response({"result": result})


async def handle_scrape(request: Any) -> Any:
    """Handle POST /scrape — return JSON or CSV."""
    web = _import_aiohttp()
    data = await request.json()
    params = ScrapeParams(**data)
    from browsix.actions.scrape import ScrapeAction

    backend = await _get_backend(request)
    action = ScrapeAction(params)
    result = await action.execute(backend)
    if params.output_format == "csv":
        return web.Response(body=result, content_type="text/csv")
    return web.json_response({"result": result})


async def handle_dom_get(request: Any) -> Any:
    """Handle POST /dom/get — return HTML as JSON."""
    web = _import_aiohttp()
    data = await request.json()
    params = DOMParams(**data)
    from browsix.actions.dom import DOMAction

    backend = await _get_backend(request)
    action = DOMAction(params)
    result = await action.execute(backend)
    return web.json_response({"result": result})


async def handle_dom_query(request: Any) -> Any:
    """Handle POST /dom/query — return elements as JSON."""
    web = _import_aiohttp()
    data = await request.json()
    params = DOMParams(**data)
    from browsix.actions.dom import DOMAction

    backend = await _get_backend(request)
    action = DOMAction(params)
    result = await action.execute(backend)
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
    from browsix.actions.har import HARAction

    backend = await _get_backend(request)
    action = HARAction(params)
    result = await action.execute(backend)
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
    from browsix.actions.input import InputAction

    backend = await _get_backend(request)
    action = InputAction(params)
    await action.execute(backend)
    return web.json_response({"status": "ok"})


async def handle_input_type(request: Any) -> Any:
    """Handle POST /input/type — type text into an element."""
    web = _import_aiohttp()
    data = await request.json()
    params = InputParams(**data, action="type")
    from browsix.actions.input import InputAction

    backend = await _get_backend(request)
    action = InputAction(params)
    await action.execute(backend)
    return web.json_response({"status": "ok"})


async def handle_perf_metrics(request: Any) -> Any:
    """Handle POST /perf/metrics — return performance metrics."""
    web = _import_aiohttp()
    data = await request.json()
    url = data.get("url", "")
    from browsix.actions.performance import PerformanceAction, PerformanceParams

    params = PerformanceParams(url=url, action="metrics")
    backend = await _get_backend(request)
    action = PerformanceAction(params)
    result = await action.execute(backend)
    return web.json_response(result)


async def handle_perf_trace(request: Any) -> Any:
    """Handle POST /perf/trace — return performance trace."""
    web = _import_aiohttp()
    data = await request.json()
    url = data.get("url", "")
    duration_ms = data.get("duration_ms", 3000)
    from browsix.actions.performance import PerformanceAction, PerformanceParams

    params = PerformanceParams(url=url, action="trace", duration_ms=duration_ms)
    backend = await _get_backend(request)
    action = PerformanceAction(params)
    result = await action.execute(backend)
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
    """Handle GET /version — return browsix version."""
    web = _import_aiohttp()
    return web.json_response({"version": __version__})


# ── App factory ─────────────────────────────────────────────


def create_app(backend_name: str | None = None) -> Any:
    """Create and configure the aiohttp web application.

    Args:
        backend_name: Preferred backend name (e.g. "cdp", "bidi").
            If None, auto-detects the first available backend.

    Returns:
        aiohttp.web.Application with all routes registered.

    Raises:
        BrowsixError: If aiohttp is not installed.
        BackendNotAvailableError: If no backend is available.
    """
    web = _import_aiohttp()
    app = web.Application()
    manager = BackendManager()
    app["backend"] = manager.select(preferred=backend_name)

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
    app.router.add_get("/health", handle_health)
    app.router.add_get("/backends", handle_backends)
    app.router.add_get("/version", handle_version)
    return app


def serve(
    port: int = 8080,
    host: str = "localhost",
    backend: str | None = None,
) -> None:
    """Start the browsix HTTP server.

    Args:
        port: Port to listen on (default 8080).
        host: Host to bind to (default "localhost").
        backend: Preferred backend name (default auto-detect).

    Raises:
        BrowsixError: If aiohttp is not installed.
        BackendNotAvailableError: If no backend is available.
    """
    web = _import_aiohttp()
    app = create_app(backend)
    web.run_app(app, host=host, port=port)
