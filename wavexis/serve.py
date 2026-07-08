"""HTTP server mode for wavexis using aiohttp.

aiohttp is an optional dependency under the [serve] extra.
All imports are lazy — ``WavexisError`` is raised if aiohttp is not installed.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import dataclasses
import hmac
import json
import logging
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from wavexis import __version__
from wavexis.backend.base import AbstractBackend
from wavexis.backend.manager import get_manager
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

logger = logging.getLogger(__name__)

__all__ = [
    "BackendPool",
    "TokenBucket",
    "create_app",
    "serve",
    "set_allowed_base_dir",
    "set_ws_max_connections",
]


def _safe_params(cls: type, data: dict[str, Any]) -> Any:
    """Construct a dataclass from a dict, ignoring unknown keys.

    Args:
        cls: A dataclass type to construct.
        data: Raw dict from the request JSON body.

    Returns:
        An instance of cls with only valid fields populated.
    """
    valid = {f.name for f in dataclasses.fields(cls)}
    filtered = {k: v for k, v in data.items() if k in valid}
    return cls(**filtered)


class TokenBucket:
    """Token bucket rate limiter for the HTTP API.

    Allows up to `capacity` requests per `refill_period` seconds.
    Tokens refill continuously at a rate of capacity/refill_period per second.
    """

    def __init__(self, capacity: int, refill_period: float) -> None:
        """Initialize the token bucket.

        Args:
            capacity: Maximum number of tokens (burst size).
            refill_period: Seconds to fully refill from empty.
        """
        self._capacity = capacity
        self._tokens = float(capacity)
        self._refill_rate = capacity / refill_period if refill_period > 0 else 0
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """Try to acquire a token.

        Returns:
            True if a token was acquired, False if rate limited.
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(
                self._capacity, self._tokens + elapsed * self._refill_rate
            )
            self._last_refill = now
            if self._tokens >= 1:
                self._tokens -= 1
                return True
            return False

    async def retry_after(self) -> float:
        """Return seconds until the next token is available."""
        async with self._lock:
            if self._tokens >= 1:
                return 0.0
            if self._refill_rate <= 0:
                return 1.0
            return (1 - self._tokens) / self._refill_rate


async def _request_logging_middleware(request: Any, handler: Any) -> Any:
    """Middleware that assigns a request ID and logs structured request info.

    Each request gets a unique ``X-Request-ID`` header. Response time and
    status are logged as JSON-structured fields for production correlation.
    """
    request_id = request.headers.get("X-Request-ID", "") or uuid.uuid4().hex[:12]
    request["request_id"] = request_id
    start = time.monotonic()
    try:
        response = await handler(request)
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        logger.info(
            json.dumps({
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status": getattr(response, "status", 200),
                "elapsed_ms": elapsed_ms,
            })
        )
        if hasattr(response, "headers"):
            response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        logger.error(
            json.dumps({
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status": 500,
                "elapsed_ms": elapsed_ms,
                "error": "unhandled exception",
            })
        )
        raise


async def _json_error_middleware(request: Any, handler: Any) -> Any:
    """Middleware that catches JSON decode errors and returns 400.

    Catches json.JSONDecodeError and aiohttp.ContentTypeError raised when
    request.json() fails, returning a consistent 400 response.
    """
    web = _import_aiohttp()
    try:
        return await handler(request)
    except (json.JSONDecodeError, ValueError):
        return web.Response(
            status=400,
            text='{"error": "invalid JSON body"}',
            content_type="application/json",
        )
    except Exception as exc:
        web = _import_aiohttp()
        if isinstance(exc, web.ContentTypeError):
            return web.Response(
                status=400,
                text='{"error": "invalid or missing JSON content-type"}',
                content_type="application/json",
            )
        raise


def _rate_limit_middleware(bucket: TokenBucket) -> Any:
    """Create an aiohttp middleware for rate limiting.

    Args:
        bucket: The TokenBucket to use for rate limiting.

    Returns:
        A middleware factory function for aiohttp.
    """
    async def middleware(request: Any, handler: Any) -> Any:
        allowed = await bucket.acquire()
        if not allowed:
            web = _import_aiohttp()
            retry_after = await bucket.retry_after()
            return web.Response(
                status=429,
                headers={"Retry-After": f"{retry_after:.1f}"},
                text='{"error": "rate limited", "retry_after": '
                     f'"{retry_after:.1f}s"}}',
                content_type="application/json",
            )
        return await handler(request)

    return middleware


_ALLOWED_BASE_DIR: Path | None = None


def set_allowed_base_dir(path: str | None) -> None:
    """Set the base directory that serve-mode file paths must be inside of.

    Args:
        path: Absolute path to the allowed base directory, or None to allow
            any path (default, not recommended for production).
    """
    global _ALLOWED_BASE_DIR
    _ALLOWED_BASE_DIR = Path(path).resolve() if path else None


def _validate_path(raw_path: str) -> Path:
    """Validate that a user-supplied path is inside the allowed base directory.

    Args:
        raw_path: Raw path string from the request body.

    Returns:
        The resolved Path object.

    Raises:
        WavexisError: If the path is outside the allowed base directory or
            if no base directory is configured.
    """
    if _ALLOWED_BASE_DIR is None:
        raise WavexisError(
            "File path access is disabled. Configure --base-dir when starting "
            "the server to allow file path references."
        )
    resolved = Path(raw_path).resolve()
    try:
        resolved.relative_to(_ALLOWED_BASE_DIR)
    except ValueError:
        raise WavexisError(
            f"Path '{raw_path}' is outside the allowed base directory."
        ) from None
    return resolved


def _auth_middleware(api_key: str) -> Any:
    """Create an aiohttp middleware that validates an API key.

    The key may be provided as a Bearer token in the Authorization header
    or as an ``api_key`` query parameter.

    Args:
        api_key: The expected API key.

    Returns:
        A middleware factory function for aiohttp.
    """
    async def middleware(request: Any, handler: Any) -> Any:
        web = _import_aiohttp()

        if request.path == "/health":
            return await handler(request)

        token = (
            request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            or request.headers.get("X-API-Key", "")
            or request.query.get("api_key", "")
        )
        if not hmac.compare_digest(token.encode(), api_key.encode()):
            return web.Response(
                status=401,
                text='{"error": "unauthorized"}',
                content_type="application/json",
            )
        return await handler(request)

    return middleware


def _cors_middleware(allowed_origins: list[str]) -> Any:
    """Create an aiohttp middleware that adds CORS headers.

    Args:
        allowed_origins: List of allowed origin patterns. Use ["*"] to allow all.

    Returns:
        A middleware factory function for aiohttp.
    """
    allow_all = "*" in allowed_origins

    async def middleware(request: Any, handler: Any) -> Any:
        web = _import_aiohttp()
        origin = request.headers.get("Origin", "")

        if request.method == "OPTIONS":
            resp = web.Response(status=204)
        else:
            resp = await handler(request)

        if origin and (allow_all or origin in allowed_origins):
            resp.headers["Access-Control-Allow-Origin"] = origin if not allow_all else "*"
            resp.headers["Access-Control-Allow-Methods"] = (
                "GET, POST, PUT, DELETE, OPTIONS"
            )
            resp.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization, X-API-Key"
            )
            resp.headers["Access-Control-Max-Age"] = "3600"
        return resp

    return middleware


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


class BackendPool:
    """Concurrency limiter and connection pool for browser backends.

    Uses a semaphore to cap the number of simultaneous browser instances.
    Maintains a pool of reusable backend instances to avoid launching a
    new browser per request.
    """

    def __init__(self, max_concurrent: int = 5) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._pool: asyncio.Queue[AbstractBackend] = asyncio.Queue()
        self._created: int = 0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire a slot, blocking if the pool is full."""
        await self._semaphore.acquire()

    def release(self) -> None:
        """Release a slot back to the pool."""
        self._semaphore.release()

    async def get_backend(
        self,
        preferred: str | None = None,
    ) -> AbstractBackend:
        """Get a backend from the pool or create a new one.

        Reuses an idle backend if available, otherwise creates a new one.

        Args:
            preferred: Preferred backend name for new instances.

        Returns:
            A backend instance (may or may not be launched yet).
        """
        async with self._lock:
            if not self._pool.empty():
                return self._pool.get_nowait()
            self._created += 1
        return await get_manager().select_with_fallback(preferred)

    async def return_backend(self, backend: AbstractBackend) -> None:
        """Return a backend to the pool for reuse.

        Args:
            backend: The backend instance to return.
        """
        with contextlib.suppress(Exception):
            await backend.close()
        await self._pool.put(backend)

    async def close_all(self) -> None:
        """Close all pooled backends and clear the pool."""
        while not self._pool.empty():
            backend = self._pool.get_nowait()
            with contextlib.suppress(Exception):
                await backend.close()
        async with self._lock:
            self._created = 0


_backend_pool: BackendPool | None = None


def _get_pool(request: Any) -> BackendPool:
    """Get the backend pool from the app, or return a default."""
    pool: BackendPool | None = request.app.get("backend_pool")
    if pool is not None:
        return pool
    global _backend_pool
    if _backend_pool is None:
        _backend_pool = BackendPool()
    return _backend_pool


async def _get_backend(request: Any) -> AbstractBackend:
    """Acquire a backend from the pool for this request.

    Reuses an idle backend if available, otherwise creates a new one.
    The caller is responsible for calling ``_release_backend`` after use.
    """
    pool = _get_pool(request)
    await pool.acquire()
    preferred = request.app.get("backend_name")
    return await pool.get_backend(preferred)


async def _run_action(request: Any, action: Any) -> Any:
    """Launch backend, execute action, and return backend to pool.

    Args:
        request: The aiohttp request.
        action: An action instance with an execute(backend) method.

    Returns:
        The result of action.execute().
    """
    pool = _get_pool(request)
    backend = await _get_backend(request)
    try:
        await backend.launch(BrowserOptions())
        return await action.execute(backend)
    finally:
        await pool.return_backend(backend)
        pool.release()


async def _release_backend(request: Any, backend: AbstractBackend) -> None:
    """Return a backend to the pool and release its slot.

    Args:
        request: The aiohttp request.
        backend: The backend instance to return.
    """
    pool = _get_pool(request)
    await pool.return_backend(backend)
    pool.release()


def with_backend(
    launch_options: BrowserOptions | None = None,
) -> Callable[[Callable[..., Any]], Callable[[Any], Any]]:
    """Decorator that manages backend lifecycle for serve handlers.

    Acquires a backend from the pool, launches it, calls the handler
    with the backend, and ensures cleanup in a finally block.

    Args:
        launch_options: BrowserOptions to pass to launch(). Defaults to
            a plain BrowserOptions().

    Returns:
        A decorator function.
    """
    def decorator(handler: Any) -> Any:
        async def wrapper(request: Any) -> Any:
            web = _import_aiohttp()
            opts = launch_options or BrowserOptions()
            backend = await _get_backend(request)
            await backend.launch(opts)
            try:
                return await handler(request, backend)
            except WavexisError as exc:
                return web.json_response(
                    {"error": str(exc)}, status=500,
                )
            except Exception as exc:
                logger.exception("Unhandled error in %s: %s", handler.__name__, exc)
                return web.json_response(
                    {"error": "internal server error"}, status=500,
                )
            finally:
                await _release_backend(request, backend)
        return wrapper
    return decorator


async def handle_screenshot(request: Any) -> Any:
    """Handle POST /screenshot — return PNG bytes."""
    web = _import_aiohttp()
    data = await request.json()
    params = _safe_params(ScreenshotParams, data)
    from wavexis.actions.screenshot import ScreenshotAction

    action = ScreenshotAction(params)
    image_bytes = await _run_action(request, action)
    return web.Response(body=image_bytes, content_type="image/png")


async def handle_pdf(request: Any) -> Any:
    """Handle POST /pdf — return PDF bytes."""
    web = _import_aiohttp()
    data = await request.json()
    params = _safe_params(PDFParams, data)
    from wavexis.actions.pdf import PDFAction

    action = PDFAction(params)
    pdf_bytes = await _run_action(request, action)
    return web.Response(body=pdf_bytes, content_type="application/pdf")


async def handle_eval(request: Any) -> Any:
    """Handle POST /eval — return JSON result."""
    web = _import_aiohttp()
    data = await request.json()
    params = _safe_params(EvalParams, data)
    from wavexis.actions.eval import EvalAction

    action = EvalAction(params)
    result = await _run_action(request, action)
    return web.json_response({"result": result})


async def handle_scrape(request: Any) -> Any:
    """Handle POST /scrape — return JSON or CSV."""
    web = _import_aiohttp()
    data = await request.json()
    params = _safe_params(ScrapeParams, data)
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
    params = _safe_params(DOMParams, data)
    from wavexis.actions.dom import DOMAction

    action = DOMAction(params)
    result = await _run_action(request, action)
    return web.json_response({"result": result})


async def handle_dom_query(request: Any) -> Any:
    """Handle POST /dom/query — return elements as JSON."""
    web = _import_aiohttp()
    data = await request.json()
    params = _safe_params(DOMParams, data)
    from wavexis.actions.dom import DOMAction

    action = DOMAction(params)
    result = await _run_action(request, action)
    return web.json_response({"result": result})


@with_backend()
async def handle_navigate(request: Any, backend: AbstractBackend) -> Any:
    """Handle POST /navigate — navigate and return status."""
    web = _import_aiohttp()
    data = await request.json()
    url = data.get("url", "")
    wait_for = data.get("wait_for")
    strategy = WaitStrategy(
        strategy="selector", selector=wait_for
    ) if wait_for else WaitStrategy(strategy="load")
    await backend.navigate(url, strategy)
    return web.json_response({"status": "ok", "url": url})


async def handle_har(request: Any) -> Any:
    """Handle POST /har — return HAR data as JSON."""
    web = _import_aiohttp()
    data = await request.json()
    params = _safe_params(HarParams, data)
    from wavexis.actions.har import HARAction

    action = HARAction(params)
    result = await _run_action(request, action)
    return web.json_response(result)


@with_backend()
async def handle_cookies_get(request: Any, backend: AbstractBackend) -> Any:
    """Handle POST /cookies/get — return cookies as JSON."""
    web = _import_aiohttp()
    data = await request.json()
    url = data.get("url", "")
    await backend.navigate(url, WaitStrategy(strategy="load"))
    cookies = await backend.get_cookies()
    return web.json_response({"cookies": cookies})


@with_backend()
async def handle_cookies_set(request: Any, backend: AbstractBackend) -> Any:
    """Handle POST /cookies/set — set a cookie and return status."""
    web = _import_aiohttp()
    data = await request.json()
    cookie_data = data.get("cookie", data)
    params = _safe_params(CookieParams, cookie_data)
    await backend.set_cookie(params)
    return web.json_response({"status": "ok"})


async def handle_input_click(request: Any) -> Any:
    """Handle POST /input/click — click an element."""
    web = _import_aiohttp()
    data = await request.json()
    params = _safe_params(InputParams, data)
    params.action = "click"
    from wavexis.actions.input import InputAction

    action = InputAction(params)
    await _run_action(request, action)
    return web.json_response({"status": "ok"})


async def handle_input_type(request: Any) -> Any:
    """Handle POST /input/type — type text into an element."""
    web = _import_aiohttp()
    data = await request.json()
    params = _safe_params(InputParams, data)
    params.action = "type"
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
    manager = get_manager()
    available = manager.list_available()
    return web.json_response({
        "cdp": "cdp" in available,
        "bidi": "bidi" in available,
    })


async def handle_version(request: Any) -> Any:
    """Handle GET /version — return wavexis version."""
    web = _import_aiohttp()
    return web.json_response({"version": __version__})


async def handle_cwv(request: Any) -> Any:
    """Handle POST /cwv — measure Core Web Vitals with scoring.

    Body: {"url": "...", "observe_ms": 5000, "budgets": {"lcp_ms": 2500}}
    """
    web = _import_aiohttp()
    from wavexis.actions.core_web_vitals import (
        CoreWebVitalsAction,
        CoreWebVitalsParams,
    )

    data = await request.json()
    url = data.get("url", "")
    observe_ms = int(data.get("observe_ms", 5000))
    budgets = data.get("budgets", {})
    params = CoreWebVitalsParams(
        url=url,
        wait=WaitStrategy(strategy="load"),
        budgets=budgets,
        observe_ms=observe_ms,
    )
    action = CoreWebVitalsAction(params)
    result = await _run_action(request, action)
    return web.json_response(result)


@with_backend()
async def handle_auth(request: Any, backend: AbstractBackend) -> Any:
    """Handle POST /auth — apply auth context and navigate."""
    web = _import_aiohttp()
    from wavexis.auth import apply_auth_context, load_auth_context

    data = await request.json()
    context_path = _validate_path(data.get("context", ""))
    url = data.get("url", "")
    ctx = load_auth_context(str(context_path))
    await apply_auth_context(backend, ctx, url)
    return web.json_response({"status": "ok", "url": url})


@with_backend()
async def handle_user_agent(request: Any, backend: AbstractBackend) -> Any:
    """Handle POST /user-agent — set custom user agent."""
    web = _import_aiohttp()
    data = await request.json()
    ua = data.get("user_agent", "")
    url = data.get("url", "")
    await backend.set_user_agent(ua)
    await backend.navigate(url, WaitStrategy(strategy="load"))
    return web.json_response({"status": "ok", "user_agent": ua})


@with_backend()
async def handle_headers(request: Any, backend: AbstractBackend) -> Any:
    """Handle POST /headers — set custom HTTP headers."""
    web = _import_aiohttp()
    data = await request.json()
    headers = data.get("headers", {})
    url = data.get("url", "")
    await backend.set_headers(headers)
    await backend.navigate(url, WaitStrategy(strategy="load"))
    return web.json_response({"status": "ok", "headers": headers})


@with_backend()
async def handle_device(request: Any, backend: AbstractBackend) -> Any:
    """Handle POST /device — emulate a device preset."""
    web = _import_aiohttp()
    data = await request.json()
    device = data.get("device", "")
    url = data.get("url", "")
    await backend.emulate_device(device)
    await backend.navigate(url, WaitStrategy(strategy="load"))
    return web.json_response({"status": "ok", "device": device})


@with_backend()
async def handle_modify_request(request: Any, backend: AbstractBackend) -> Any:
    """Handle POST /modify-request — intercept and modify requests in-flight.

    Body: {"url": "...", "pattern": "*/api/*",
        "modifications": {"headers": [...], "method": "...", "post_data": "..."}}
    """
    web = _import_aiohttp()
    data = await request.json()
    url = data.get("url", "")
    pattern_input = data.get("pattern", "*")
    modifications = data.get("modifications", {})
    
    # Build pattern dict - accept either string or dict
    if isinstance(pattern_input, str):
        pattern = {"urlPattern": pattern_input}
    else:
        pattern = pattern_input
    
    await backend.modify_request(pattern, modifications)
    if url:
        await backend.navigate(url, WaitStrategy(strategy="load"))
    return web.json_response({"status": "ok", "pattern": pattern})


@with_backend()
async def handle_modify_response(request: Any, backend: AbstractBackend) -> Any:
    """Handle POST /modify-response — intercept and modify responses in-flight.

    Body: {"url": "...", "pattern": "*/api/*",
        "modifications": {"status": 200, "body": "...", "content_type": "application/json"}}
    """
    web = _import_aiohttp()
    data = await request.json()
    url = data.get("url", "")
    pattern = data.get("pattern", "*")
    modifications = data.get("modifications", {})
    await backend.modify_response({"urlPattern": pattern}, modifications)
    if url:
        await backend.navigate(url, WaitStrategy(strategy="load"))
    return web.json_response({"status": "ok", "pattern": pattern})


@with_backend(launch_options=BrowserOptions(headless=True))
async def handle_multi(request: Any, backend: AbstractBackend) -> Any:
    """Handle POST /multi — execute multiple actions from YAML."""
    web = _import_aiohttp()
    from wavexis.record import replay_from_yaml

    data = await request.json()
    yaml_path = _validate_path(data.get("config", ""))
    results = await replay_from_yaml(yaml_path, backend)
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
        except WavexisError as exc:
            await ws.send_json({
                "type": "error",
                "source": "screenshot",
                "message": str(exc),
            })
        except (ConnectionError, OSError):
            break
        await asyncio.sleep(interval)


async def _stream_console(
    ws: Any, backend: AbstractBackend, interval: float,
) -> None:
    """Poll console messages and stream new ones."""
    seen: set[str] = set()
    while True:
        try:
            messages = await backend.capture_console()
            for msg in messages:
                key = json.dumps(msg, sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    await ws.send_json({
                        "type": "console",
                        "data": msg,
                        "timestamp": time.time(),
                    })
        except WavexisError as exc:
            await ws.send_json({
                "type": "error",
                "source": "console",
                "message": str(exc),
            })
        except (ConnectionError, OSError):
            break
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
        except WavexisError as exc:
            await ws.send_json({
                "type": "error",
                "source": "navigation",
                "message": str(exc),
            })
        except (ConnectionError, OSError):
            break
        await asyncio.sleep(interval)


async def _stream_dom_mutations(
    ws: Any, backend: AbstractBackend, interval: float,
) -> None:
    """Stream DOM mutations using a MutationObserver.

    Injects a MutationObserver on first call, then polls the accumulated
    mutation queue on each interval. Much lighter than scanning all elements.
    """
    installed = False
    while True:
        try:
            if not installed:
                await backend.eval(
                    "window.__wavexisMutations = [];"
                    "window.__wavexisObserver = new MutationObserver(muts => {"
                    "  for (const m of muts) {"
                    "    if (m.type === 'childList') {"
                    "      for (const n of m.addedNodes) {"
                    "        window.__wavexisMutations.push("
                    "          {type:'added', tag:n.tagName, "
                    "           html:(n.outerHTML||'').slice(0,200)});"
                    "      }"
                    "      for (const n of m.removedNodes) {"
                    "        window.__wavexisMutations.push("
                    "          {type:'removed', tag:n.tagName, "
                    "           html:(n.outerHTML||'').slice(0,200)});"
                    "      }"
                    "    } else if (m.type === 'attributes') {"
                    "      window.__wavexisMutations.push("
                    "        {type:'attr', target:m.target.tagName, "
                    "         attr:m.attributeName});"
                    "    }"
                    "  }"
                    "});"
                    "window.__wavexisObserver.observe(document.body || "
                    "  document.documentElement,"
                    "  {childList:true, subtree:true, attributes:true});"
                )
                installed = True

            mutations = await backend.eval(
                "window.__wavexisMutations.splice(0, 50)"
            )
            if mutations:
                await ws.send_json({
                    "type": "dom_mutation",
                    "data": {"mutations": mutations[:50]},
                    "timestamp": time.time(),
                })
        except WavexisError as exc:
            await ws.send_json({
                "type": "error",
                "source": "dom_mutation",
                "message": str(exc),
            })
        except (ConnectionError, OSError):
            break
        await asyncio.sleep(interval)


async def _stream_perf_metrics(
    ws: Any, backend: AbstractBackend, interval: float,
) -> None:
    """Poll performance metrics and stream them."""
    while True:
        try:
            metrics = await backend.perf_metrics()
            await ws.send_json({
                "type": "perf_metrics",
                "data": metrics,
                "timestamp": time.time(),
            })
        except WavexisError as exc:
            await ws.send_json({
                "type": "error",
                "source": "perf_metrics",
                "message": str(exc),
            })
        except (ConnectionError, OSError) as exc:
            await ws.send_json({
                "type": "error",
                "source": "perf_metrics",
                "message": str(exc),
            })
        await asyncio.sleep(interval)


_ws_connections: int = 0
_ws_max_connections: int = 20
_ws_lock: asyncio.Lock = asyncio.Lock()
_ws_max_messages_per_minute: int = 120


def set_ws_max_connections(max_conn: int) -> None:
    """Set the maximum number of concurrent WebSocket connections.

    Args:
        max_conn: Maximum concurrent WebSocket connections allowed.
    """
    global _ws_max_connections
    _ws_max_connections = max_conn


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

    global _ws_connections
    async with _ws_lock:
        if _ws_connections >= _ws_max_connections:
            return web.Response(
                status=503,
                text='{"error": "too many websocket connections"}',
                content_type="application/json",
            )
        _ws_connections += 1

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    try:
        try:
            msg = await ws.receive()
            if msg.type == web.WSMsgType.TEXT:
                config = json.loads(msg.data)
            else:
                await ws.close()
                return ws
        except (json.JSONDecodeError, KeyError, TypeError):
            await ws.close()
            return ws

        url = config.get("url", "about:blank")
        events = config.get("events", ["screenshot"])
        interval = float(config.get("interval", 1.0))
        fmt = config.get("format", "png")
        quality = int(config.get("quality", 80))

        backend = await _get_backend(request)
        try:
            await backend.launch(BrowserOptions())
            await backend.navigate(url, WaitStrategy(strategy="load"))
        except Exception:
            await _release_backend(request, backend)
            raise

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
        if "dom_mutation" in events:
            tasks.append(asyncio.create_task(
                _stream_dom_mutations(ws, backend, max(interval, 0.5)),
            ))
        if "perf_metrics" in events:
            tasks.append(asyncio.create_task(
                _stream_perf_metrics(ws, backend, max(interval, 1.0)),
            ))

        subscribe_types = [
            e for e in events if e in ("network_request", "network_response", "dialog")
        ]
        if subscribe_types:
            async def _on_event(event: dict[str, Any]) -> None:
                await ws.send_json({
                    "type": event.get("type", "event"),
                    "data": event.get("data", {}),
                    "timestamp": time.time(),
                })

            await backend.subscribe_events(subscribe_types, _on_event)

        ws_bucket = TokenBucket(
            capacity=_ws_max_messages_per_minute, refill_period=60.0
        )

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    allowed = await ws_bucket.acquire()
                    if not allowed:
                        await ws.send_json({
                            "type": "error",
                            "message": "rate limited: too many messages",
                            "timestamp": time.time(),
                        })
                        continue
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
            await _release_backend(request, backend)
            await ws.close()
    finally:
        async with _ws_lock:
            _ws_connections -= 1

    return ws


async def handle_plugins(request: Any) -> Any:
    """Handle GET /plugins — list discovered plugins."""
    from wavexis.plugins import get_registry

    registry = get_registry()
    web = _import_aiohttp()
    return web.json_response({
        "actions": registry.list_actions(),
        "backends": registry.list_backends(),
        "middleware": registry.list_middleware(),
    })


# ── App factory ─────────────────────────────────────────────


def create_app(
    backend_name: str | None = None,
    rate_limit: int | None = None,
    base_dir: str | None = None,
    api_key: str | None = None,
    cors_origins: list[str] | None = None,
    max_concurrent: int = 5,
) -> Any:
    """Create and configure the aiohttp web application.

    Args:
        backend_name: Preferred backend name (e.g. "cdp", "bidi").
            If None, auto-detects the first available backend.
        rate_limit: Max requests per minute (0 or None = no limit).
        base_dir: Base directory for validating file paths in requests.
            If None, file path access is disabled.
        api_key: If set, all requests must include this key as a Bearer
            token or ``api_key`` query parameter.
        cors_origins: List of allowed CORS origins. Use ["*"] for all.
        max_concurrent: Max number of concurrent browser backends.

    Returns:
        aiohttp.web.Application with all routes registered.

    Raises:
        WavexisError: If aiohttp is not installed.
        BackendNotAvailableError: If no backend is available.
    """
    web = _import_aiohttp()
    from wavexis.plugins import get_registry

    set_allowed_base_dir(base_dir)

    registry = get_registry()
    middlewares: list[Any] = [m.factory(web) for m in registry.middleware]
    middlewares.append(web.middleware(_request_logging_middleware))
    middlewares.append(web.middleware(_json_error_middleware))

    if cors_origins:
        if "*" in cors_origins and api_key:
            logger.warning(
                "CORS is configured to allow all origins ('*') while API key "
                "authentication is enabled. This allows any website to make "
                "authenticated requests. Consider restricting --cors-origins "
                "to specific domains."
            )
        middlewares.append(_cors_middleware(cors_origins))

    if api_key:
        middlewares.append(_auth_middleware(api_key))

    if rate_limit and rate_limit > 0:
        bucket = TokenBucket(capacity=rate_limit, refill_period=60.0)
        middlewares.append(_rate_limit_middleware(bucket))

    app = web.Application(middlewares=middlewares)
    manager = get_manager()
    app["backend_name"] = backend_name
    app["backends"] = manager.list_available()
    app["backend_pool"] = BackendPool(max_concurrent=max_concurrent)

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
    app.router.add_post("/cwv", handle_cwv)
    app.router.add_post("/auth", handle_auth)
    app.router.add_post("/user-agent", handle_user_agent)
    app.router.add_post("/headers", handle_headers)
    app.router.add_post("/device", handle_device)
    app.router.add_post("/modify-request", handle_modify_request)
    app.router.add_post("/modify-response", handle_modify_response)
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
    rate_limit: int | None = None,
    base_dir: str | None = None,
    api_key: str | None = None,
    cors_origins: list[str] | None = None,
    max_concurrent: int = 5,
) -> None:
    """Start the wavexis HTTP server.

    Args:
        port: Port to listen on (default 8080).
        host: Host to bind to (default "localhost").
        backend: Preferred backend name (default auto-detect).
        rate_limit: Max requests per minute (0 or None = no limit).
        base_dir: Base directory for validating file paths in requests.
        api_key: If set, all requests must include this key.
        cors_origins: List of allowed CORS origins. Use ["*"] for all.
        max_concurrent: Max concurrent browser backends (default 5).

    Raises:
        WavexisError: If aiohttp is not installed.
        BackendNotAvailableError: If no backend is available.
    """
    web = _import_aiohttp()
    logging.basicConfig(
        level=logging.INFO,
        format='{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":%(message)s}',
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    app = create_app(
        backend,
        rate_limit=rate_limit,
        base_dir=base_dir,
        api_key=api_key,
        cors_origins=cors_origins,
        max_concurrent=max_concurrent,
    )
    web.run_app(app, host=host, port=port)
