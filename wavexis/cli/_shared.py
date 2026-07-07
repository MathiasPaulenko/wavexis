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
    "_ctx",
    "_echo",
    "_get_backend",
    "_get_ctx",
    "_handle_error",
    "_load_global_config",
    "_progress",
    "_run_async",
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
    except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
        if ctx.verbose:
            _echo(f"Warning: failed to load config from {config_path}: {exc}")


@app.callback()
def main_callback(
    backend: str | None = typer.Option(
        None, "--backend", help="Preferred backend: cdp or bidi"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show backend logs and timing info"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
    headed: bool = typer.Option(
        False, "--headed", help="Run browser in headed mode (visible window)"
    ),
    timeout: int = typer.Option(
        0, "--timeout", help="Navigation timeout in milliseconds (default: 30000)"
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
    version: bool = typer.Option(
        False, "--version", help="Print wavexis version and exit"
    ),
) -> None:
    """wavexis — browser automation CLI."""
    _load_global_config()
    ctx = _get_ctx()
    ctx.preferred_backend = backend
    ctx.verbose = verbose
    ctx.quiet = quiet
    if headed:
        ctx.headless = False
    if timeout > 0:
        ctx.timeout = timeout
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


def _handle_error(e: Exception) -> None:
    """Handle a WavexisError with the correct exit code and message.

    Args:
        e: The exception to handle.
    """
    if isinstance(e, BackendNotAvailableError):
        Output.error(
            "No backend available.\n"
            "Hint: Install cdpwave with `pip install wavexis[cdp]`, "
            "or bidiwave with `pip install wavexis[bidi]`."
        )
        raise typer.Exit(EXIT_BACKEND_ERROR) from e
    if isinstance(e, SessionNotInitializedError):
        Output.error(str(e))
        raise typer.Exit(EXIT_BROWSER_ERROR) from e
    if isinstance(e, NavigationError):
        Output.error(str(e))
        raise typer.Exit(EXIT_BROWSER_ERROR) from e
    if isinstance(e, WaitTimeoutError):
        Output.error(str(e))
        raise typer.Exit(EXIT_BROWSER_ERROR) from e
    if isinstance(e, ElementNotFoundError):
        Output.error(str(e))
        raise typer.Exit(EXIT_BROWSER_ERROR) from e
    if isinstance(e, MultiConfigError):
        Output.error(
            f"Invalid multi config: {e}\n"
            "Hint: Run `wavexis multi <config> --dry-run` to validate the config."
        )
        raise typer.Exit(EXIT_CONFIG_ERROR) from e
    if isinstance(e, WavexisError):
        Output.error(str(e))
        raise typer.Exit(EXIT_BROWSER_ERROR) from e
    raise e


def _run_async(coro: Any) -> Any:
    """Run an async coroutine synchronously, handling WavexisError.

    Args:
        coro: The coroutine to run.

    Returns:
        The coroutine result, or None if an error was handled.
    """
    try:
        return asyncio.run(coro)
    except WavexisError as e:
        _handle_error(e)
        return None


def _get_backend() -> Any:
    """Select a backend using the preferred backend if set.

    Registers the backend for automatic cleanup on crash or signal.
    Falls back to another backend if the preferred one fails to launch.
    """
    import asyncio

    manager = get_manager()
    preferred = _get_ctx().preferred_backend
    try:
        asyncio.get_running_loop()
        backend = asyncio.get_event_loop().run_until_complete(
            manager.select_with_fallback(preferred, _browser_options())
        )
    except RuntimeError:
        backend = asyncio.run(
            manager.select_with_fallback(preferred, _browser_options())
        )
    register_backend(backend)
    return backend


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


def _write_json_output(
    result: dict[str, Any] | list[dict[str, Any]], output: str, label: str
) -> None:
    """Write JSON result to file or stdout."""
    if output == "-":
        typer.echo(json.dumps(result, indent=2, default=str))
    else:
        Output.write_json(result, output)
        typer.echo(f"{label.capitalize()} saved to {output}")
