"""Typer CLI application for wavexis."""

from __future__ import annotations

import asyncio
import contextvars
import json
from dataclasses import dataclass
from typing import Any

import typer

from wavexis.backend.manager import get_manager
from wavexis.cleanup import register_backend, unregister_backend
from wavexis.config import (
    DEVICE_PRESETS,
    BrowserOptions,
    WaitStrategy,
)
from wavexis.exceptions import (
    BackendNotAvailableError,
    ElementNotFoundError,
    MultiConfigError,
    NavigationError,
    SessionNotInitializedError,
    WaitTimeoutError,
    WavexisError,
)
from wavexis.output import Output

__all__ = [
    "BackendNotAvailableError",
    "BrowserOptions",
    "CLIContext",
    "DEVICE_PRESETS",
    "ElementNotFoundError",
    "EXIT_BACKEND_ERROR",
    "EXIT_BROWSER_ERROR",
    "EXIT_CONFIG_ERROR",
    "EXIT_SUCCESS",
    "MultiConfigError",
    "NavigationError",
    "Output",
    "SessionNotInitializedError",
    "WaitTimeoutError",
    "WavexisError",
    "_browser_options",
    "_close_backend",
    "_ctx",
    "_echo",
    "_get_backend",
    "_get_ctx",
    "_handle_error",
    "_load_global_config",
    "_progress",
    "_run_async",
    "_wait_strategy",
    "_write_json_output",
    "app",
    "get_manager",
    "unregister_backend",
]

EXIT_SUCCESS = 0
EXIT_BROWSER_ERROR = 1
EXIT_CONFIG_ERROR = 2
EXIT_BACKEND_ERROR = 3

app = typer.Typer(
    name="wavexis",
    help="Browser automation CLI — wraps cdpwave and bidiwave. No Node.js, no Chromium download.",
    no_args_is_help=True,
    invoke_without_command=True,
)


@dataclass
class CLIContext:
    """Mutable CLI context holding global flags and settings."""

    preferred_backend: str | None = None
    verbose: bool = False
    quiet: bool = False
    headless: bool = True
    timeout: int = 30000
    wait_strategy: str = "load"
    proxy: str | None = None
    user_data_dir: str | None = None
    browser_url: str | None = None
    remote_url: str | None = None
    stealth: bool = False


_ctx: contextvars.ContextVar[CLIContext | None] = contextvars.ContextVar(
    "wavexis_cli_ctx", default=None
)


def _get_ctx() -> CLIContext:
    """Get the current CLI context, initializing if needed."""
    ctx = _ctx.get()
    if ctx is None:
        ctx = CLIContext()
        _ctx.set(ctx)
    return ctx


def _load_global_config() -> None:
    """Load defaults from ~/.wavexis/config.yml if it exists."""
    from pathlib import Path

    ctx = _get_ctx()
    config_path = Path.home() / ".wavexis" / "config.yml"
    if not config_path.exists():
        return
    try:
        import yaml

        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return
        if "backend" in raw and ctx.preferred_backend is None:
            ctx.preferred_backend = str(raw["backend"])
        if "headless" in raw:
            ctx.headless = bool(raw["headless"])
        if "timeout" in raw:
            ctx.timeout = int(raw["timeout"])
        if "wait_strategy" in raw:
            ctx.wait_strategy = str(raw["wait_strategy"])
        if "proxy" in raw:
            ctx.proxy = str(raw["proxy"])
        if "user_data_dir" in raw:
            ctx.user_data_dir = str(raw["user_data_dir"])
        if "browser_url" in raw:
            ctx.browser_url = str(raw["browser_url"])
        if "remote_url" in raw:
            ctx.remote_url = str(raw["remote_url"])
        if "stealth" in raw:
            ctx.stealth = bool(raw["stealth"])
    except ImportError:
        if ctx.verbose:
            _echo(f"Warning: failed to load config from {config_path}: PyYAML not installed")
    except (OSError, ValueError, TypeError) as exc:
        if ctx.verbose:
            _echo(f"Warning: failed to load config from {config_path}: {exc}")
    except Exception as exc:
        if ctx.verbose:
            _echo(f"Warning: failed to load config from {config_path}: {exc}")


@app.callback()
def main_callback(
    backend: str | None = typer.Option(None, "--backend", help="Preferred backend: cdp or bidi"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show backend logs and timing info"
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress all output except errors"),
    headed: bool = typer.Option(
        False, "--headed", help="Run browser in headed mode (visible window)"
    ),
    timeout: int = typer.Option(
        30000, "--timeout", help="Navigation timeout in milliseconds"
    ),
    wait_strategy: str = typer.Option(
        "load",
        "--wait-strategy",
        help="Default navigation wait strategy: load, domcontentloaded, or networkidle",
    ),
    proxy: str | None = typer.Option(
        None, "--proxy", help="Proxy server URL (e.g. http://proxy:8080)"
    ),
    user_data_dir: str | None = typer.Option(
        None, "--user-data-dir", help="Path to persistent browser profile directory"
    ),
    browser_url: str | None = typer.Option(
        None, "--browser-url", help="Connect to existing browser (e.g. ws://localhost:9222)"
    ),
    remote_url: str | None = typer.Option(
        None,
        "--remote-url",
        help="Cloud browser WebSocket URL (e.g. wss://chrome.browserless.io?token=XXX)",
    ),
    stealth: bool = typer.Option(
        False,
        "--stealth",
        help="Enable anti-bot stealth mode (hides navigator.webdriver, fakes plugins, etc.)",
    ),
    version: bool = typer.Option(False, "--version", help="Print wavexis version and exit"),
) -> None:
    """wavexis — browser automation CLI."""
    _load_global_config()
    ctx = _get_ctx()
    ctx.preferred_backend = backend
    ctx.verbose = verbose
    ctx.quiet = quiet
    if headed:
        ctx.headless = False
    # --timeout now defaults to 30000 at the Typer layer; honour any explicit
    # value the user passes (including 0 to disable the navigation timeout).
    ctx.timeout = timeout
    if wait_strategy:
        ctx.wait_strategy = wait_strategy
    if proxy:
        ctx.proxy = proxy
    if user_data_dir:
        ctx.user_data_dir = user_data_dir
    if browser_url:
        ctx.browser_url = browser_url
    if remote_url:
        ctx.remote_url = remote_url
    if stealth:
        ctx.stealth = True
    if version:
        from wavexis import __version__

        typer.echo(f"wavexis v{__version__}")
        raise typer.Exit(EXIT_SUCCESS)


def _echo(msg: str) -> None:
    """Print a message unless quiet mode is active."""
    if not _get_ctx().quiet:
        typer.echo(msg)


def _progress(current: int, total: int, label: str = "") -> None:
    """Print a progress indicator unless quiet mode is active.

    Args:
        current: Current item index (1-based).
        total: Total number of items.
        label: Optional label to prepend (e.g. URL or action name).
    """
    ctx = _get_ctx()
    if ctx.quiet:
        return
    suffix = f" — {label}" if label else ""
    typer.echo(f"[{current}/{total}]{suffix}")


def _progress_stderr(current: int, total: int, label: str = "") -> None:
    """Print a progress indicator to stderr unless quiet mode is active.

    Args:
        current: Current item index (1-based).
        total: Total number of items.
        label: Optional label to prepend (e.g. URL or action name).
    """
    ctx = _get_ctx()
    if ctx.quiet:
        return
    suffix = f" — {label}" if label else ""
    typer.echo(f"[{current}/{total}]{suffix}", err=True)


_ERROR_EXIT_CODES: dict[type[Exception], int] = {
    BackendNotAvailableError: EXIT_BACKEND_ERROR,
    SessionNotInitializedError: EXIT_BROWSER_ERROR,
    NavigationError: EXIT_BROWSER_ERROR,
    WaitTimeoutError: EXIT_BROWSER_ERROR,
    ElementNotFoundError: EXIT_BROWSER_ERROR,
    MultiConfigError: EXIT_CONFIG_ERROR,
    WavexisError: EXIT_BROWSER_ERROR,
}

_ERROR_MESSAGES: dict[type[Exception], str] = {
    BackendNotAvailableError: (
        "No backend available.\n"
        "Hint: Install cdpwave with `pip install wavexis[cdp]`, "
        "or bidiwave with `pip install wavexis[bidi]`."
    ),
    MultiConfigError: (
        "Invalid multi config: {e}\n"
        "Hint: Run `wavexis multi <config> --dry-run` to validate the config."
    ),
}


def _handle_error(e: Exception) -> None:
    """Handle a WavexisError with the correct exit code and message.

    Args:
        e: The exception to handle.
    """
    for exc_type, exit_code in _ERROR_EXIT_CODES.items():
        if isinstance(e, exc_type):
            template = _ERROR_MESSAGES.get(type(e))
            message = template.format(e=e) if template else str(e)
            Output.error(message)
            raise typer.Exit(exit_code) from e
    raise e


def _run_async(coro: Any) -> Any:
    """Run an async coroutine synchronously, handling WavexisError.

    Args:
        coro: The coroutine to run.

    Returns:
        The coroutine result, or None if an error was handled.
    """
    try:
        return asyncio.run(_run_with_cleanup(coro))
    except WavexisError as e:
        _handle_error(e)
        return None


async def _run_with_cleanup(coro: Any) -> Any:
    """Run a coroutine and perform async cleanup before returning.

    On Windows, the ProactorEventLoop can emit ``ResourceWarning`` /
    ``ValueError: I/O operation on closed pipe`` during interpreter
    shutdown if async generators and pending transports are not given
    a chance to close. This wrapper ensures ``asyncio`` runs its
    shutdown sequence before the event loop is closed.

    Bug #9: lighthouse (and other long-running commands) left a
    traceback on exit even though the operation succeeded.
    """
    try:
        return await coro
    finally:
        # Close async generators so their resources are released cleanly.
        # Note: ``asyncio.shutdown_asyncgens`` is a method on the running
        # event loop, not a module-level function in some Python builds.
        try:
            loop = asyncio.get_running_loop()
            await loop.shutdown_asyncgens()
        except (AttributeError, RuntimeError):
            # Loop already closed or shutdown_asyncgens not available.
            pass
        # Yield control to let pending transport callbacks drain.
        await asyncio.sleep(0)


def _get_backend() -> Any:
    """Select a backend using the preferred backend if set.

    Registers the backend for automatic cleanup on crash or signal.
    Falls back to another backend if the preferred one fails to launch.
    """
    manager = get_manager()
    preferred = _get_ctx().preferred_backend
    backend = manager.select_with_fallback_sync(preferred, _browser_options())
    register_backend(backend)
    return backend


async def _close_backend(backend: Any) -> None:
    """Close a backend and unregister it from cleanup tracking.

    Args:
        backend: The backend instance to close and unregister.
    """
    await backend.close()
    unregister_backend(backend)


def _browser_options() -> BrowserOptions:
    """Build BrowserOptions from CLI context.

    Applies --headed, --timeout, and --proxy global flags.
    """
    ctx = _get_ctx()
    return BrowserOptions(
        headless=ctx.headless,
        timeout=ctx.timeout,
        proxy=ctx.proxy,
        user_data_dir=ctx.user_data_dir,
        browser_url=ctx.browser_url,
        remote_url=ctx.remote_url,
        stealth=ctx.stealth,
    )


def _wait_strategy(
    strategy: str | None = None,
    *,
    selector: str | None = None,
    url_pattern: str | None = None,
    timeout: int | None = None,
) -> WaitStrategy:
    """Build a WaitStrategy that honours the global ``--timeout`` and ``--wait-strategy`` flags.

    Bug #3: previously CLI commands hardcoded ``WaitStrategy(strategy="load")``
    which always used the 30000ms default, ignoring ``--timeout`` and the
    config file. This helper applies ``ctx.timeout`` unless an explicit
    ``timeout`` is provided.

    Bug #4: callers can pass ``strategy=None`` to fall back to the global
    ``--wait-strategy`` flag (default ``"load"``). Pass an explicit string to
    override (e.g. ``"selector"`` with a ``selector`` argument).
    """
    ctx = _get_ctx()
    return WaitStrategy(
        strategy=ctx.wait_strategy if strategy is None else strategy,
        selector=selector,
        url_pattern=url_pattern,
        timeout=ctx.timeout if timeout is None else timeout,
    )


def _write_json_output(
    result: dict[str, Any] | list[dict[str, Any]], output: str, label: str
) -> None:
    """Write JSON result to file or stdout."""
    if output == "-":
        typer.echo(json.dumps(result, indent=2, default=str))
    else:
        Output.write_json(result, output)
        typer.echo(f"{label.capitalize()} saved to {output}")
