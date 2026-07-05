"""Typer CLI application for browsix."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

import typer

from browsix.actions.animation import AnimationAction
from browsix.actions.bluetooth import BluetoothAction, BluetoothParams
from browsix.actions.browser import BrowserAction
from browsix.actions.cast import CastAction, CastParams
from browsix.actions.console import ConsoleAction, ConsoleParams
from browsix.actions.dom import DOMAction
from browsix.actions.eval import EvalAction
from browsix.actions.har import HARAction
from browsix.actions.media import MediaAction, MediaParams
from browsix.actions.navigate import (
    BackAction,
    ForwardAction,
    NavigateAction,
    NavigateParams,
    ReloadAction,
    StopAction,
)
from browsix.actions.pdf import PDFAction
from browsix.actions.scrape import ScrapeAction
from browsix.actions.screenshot import ScreenshotAction
from browsix.actions.service_worker import ServiceWorkerAction, ServiceWorkerParams
from browsix.actions.storage import StorageAction
from browsix.actions.tabs import TabsAction, TabsParams
from browsix.actions.webaudio import WebAudioAction, WebAudioParams
from browsix.actions.webauthn import WebAuthnAction, WebAuthnParams
from browsix.backend.manager import BackendManager
from browsix.config import (
    DEVICE_PRESETS,
    AnimationParams,
    BrowserOptions,
    CookieParams,
    DOMParams,
    EvalParams,
    HarParams,
    InputParams,
    PDFParams,
    ScrapeParams,
    ScreencastParams,
    ScreenshotParams,
    StorageParams,
    ThrottleParams,
    WaitStrategy,
)
from browsix.exceptions import (
    BackendNotAvailableError,
    BrowsixError,
    ElementNotFoundError,
    MultiConfigError,
    NavigationError,
    WaitTimeoutError,
)
from browsix.output import Output

EXIT_SUCCESS = 0
EXIT_BROWSER_ERROR = 1
EXIT_CONFIG_ERROR = 2
EXIT_BACKEND_ERROR = 3

app = typer.Typer(
    name="browsix",
    help="Browser automation CLI — wraps cdpwave and bidiwave. No Node.js, no Chromium download.",
    no_args_is_help=True,
    invoke_without_command=True,
)

_preferred_backend: str | None = None
_verbose: bool = False
_quiet: bool = False


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
    version: bool = typer.Option(
        False, "--version", help="Print browsix version and exit"
    ),
) -> None:
    """Browsix — browser automation CLI."""
    global _preferred_backend, _verbose, _quiet
    _preferred_backend = backend
    _verbose = verbose
    _quiet = quiet
    if version:
        from browsix import __version__

        typer.echo(f"browsix v{__version__}")
        raise typer.Exit(EXIT_SUCCESS)


def _echo(msg: str) -> None:
    """Print a message unless quiet mode is active."""
    if not _quiet:
        typer.echo(msg)


def _handle_error(e: Exception) -> None:
    """Handle a BrowsixError with the correct exit code and message.

    Args:
        e: The exception to handle.
    """
    if isinstance(e, BackendNotAvailableError):
        Output.error(
            "No backend available. Install cdpwave: pip install browsix[cdp]"
        )
        raise typer.Exit(EXIT_BACKEND_ERROR) from e
    if isinstance(e, NavigationError):
        Output.error(f"Navigation failed: {e}")
        raise typer.Exit(EXIT_BROWSER_ERROR) from e
    if isinstance(e, WaitTimeoutError):
        Output.error(f"Timeout waiting: {e}")
        raise typer.Exit(EXIT_BROWSER_ERROR) from e
    if isinstance(e, ElementNotFoundError):
        Output.error(f"Element not found: {e}")
        raise typer.Exit(EXIT_BROWSER_ERROR) from e
    if isinstance(e, MultiConfigError):
        Output.error(f"Invalid multi config: {e}")
        raise typer.Exit(EXIT_CONFIG_ERROR) from e
    if isinstance(e, BrowsixError):
        Output.error(str(e))
        raise typer.Exit(EXIT_BROWSER_ERROR) from e
    raise e


def _get_backend() -> Any:
    """Select a backend using the global preferred backend if set."""
    manager = BackendManager()
    return manager.select(_preferred_backend)


@app.command()
def screenshot(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("screenshot.png", "--output", "-o", help="Output file path"),
    full_page: bool = typer.Option(False, "--full-page", help="Capture full page"),
    selector: str | None = typer.Option(
        None, "--selector", help="CSS selector to capture"
    ),
    device: str | None = typer.Option(None, "--device", help="Device preset name"),
    format: str = typer.Option("png", "--format", help="Image format (png or jpeg)"),
    js: str | None = typer.Option(
        None, "--js", help="JavaScript to execute before screenshot"
    ),
    wait_for: str | None = typer.Option(
        None, "--wait-for", help="CSS selector to wait for"
    ),
) -> None:
    """Take a screenshot of a web page."""
    wait = (
        WaitStrategy(strategy="selector", selector=wait_for)
        if wait_for
        else WaitStrategy(strategy="load")
    )
    try:
        image_bytes = asyncio.run(
            _take_screenshot(url, full_page, selector, device, format, js, wait)
        )
    except BrowsixError as e:
        _handle_error(e)

    Output.write_bytes(image_bytes, output)
    typer.echo(f"Screenshot saved to {output}")


async def _take_screenshot(
    url: str,
    full_page: bool,
    selector: str | None,
    device: str | None,
    format: str,
    js: str | None,
    wait: WaitStrategy,
) -> bytes:
    """Async helper to take a screenshot via backend."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        params = ScreenshotParams(
            url=url,
            full_page=full_page,
            selector=selector,
            device=device,
            format=format,
            js=js,
            wait=wait,
        )
        action = ScreenshotAction(params)
        return await action.execute(backend)
    finally:
        await backend.close()


@app.command()
def pdf(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("output.pdf", "--output", "-o", help="Output file path"),
    paper: str = typer.Option(
        "letter", "--paper", help="Paper size (a4, letter, legal, a3, a5)"
    ),
    landscape: bool = typer.Option(False, "--landscape", help="Use landscape orientation"),
    margins: str = typer.Option(
        "0.4in", "--margins", help="Margin size (e.g. 0.4in)"
    ),
    media: str = typer.Option(
        "print", "--media", help="CSS media type (print or screen)"
    ),
    no_header_footer: bool = typer.Option(
        False, "--no-header-footer", help="Omit header and footer"
    ),
) -> None:
    """Generate a PDF of a web page."""
    try:
        pdf_bytes = asyncio.run(
            _generate_pdf(url, paper, landscape, margins, media, no_header_footer)
        )
    except BrowsixError as e:
        _handle_error(e)

    Output.write_bytes(pdf_bytes, output)
    typer.echo(f"PDF saved to {output}")


async def _generate_pdf(
    url: str,
    paper: str,
    landscape: bool,
    margins: str,
    media: str,
    no_header_footer: bool,
) -> bytes:
    """Async helper to generate a PDF via backend."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        params = PDFParams(
            url=url,
            paper=paper,
            landscape=landscape,
            margin=margins,
            media=media,
            no_header_footer=no_header_footer,
            wait=WaitStrategy(strategy="load"),
        )
        action = PDFAction(params)
        return await action.execute(backend)
    finally:
        await backend.close()


@app.command()
def eval(
    url: str = typer.Argument(..., help="URL to navigate to"),
    expression: str = typer.Option(
        "", "--expression", "-e", help="JavaScript expression to evaluate"
    ),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path (JSON)"
    ),
    await_promise: bool = typer.Option(
        False, "--await-promise", help="Await a returned Promise"
    ),
    file: str | None = typer.Option(None, "--file", help="Read expression from file"),
) -> None:
    """Evaluate a JavaScript expression on a web page."""
    if file and not expression:
        expression = f"@{file}"
    elif file:
        from pathlib import Path
        expression = Path(file).read_text(encoding="utf-8")

    try:
        result = asyncio.run(_eval(url, expression, await_promise, file))
    except BrowsixError as e:
        _handle_error(e)

    if output:
        Output.write_json(result, output)
        typer.echo(f"Result saved to {output}")
    else:
        typer.echo(json.dumps(result, indent=2, default=str))


async def _eval(url: str, expression: str, await_promise: bool, file: str | None) -> Any:
    """Async helper to evaluate JS via backend."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        params = EvalParams(
            url=url,
            expression=expression,
            await_promise=await_promise,
            file=file,
            wait=WaitStrategy(strategy="load"),
        )
        action = EvalAction(params)
        return await action.execute(backend)
    finally:
        await backend.close()


@app.command()
def navigate(
    url: str = typer.Argument(..., help="URL to navigate to"),
    wait_for: str | None = typer.Option(None, "--wait-for", help="CSS selector to wait for"),
) -> None:
    """Navigate to a URL and optionally wait for an element."""
    wait = (
        WaitStrategy(strategy="selector", selector=wait_for)
        if wait_for
        else WaitStrategy(strategy="load")
    )
    try:
        asyncio.run(_navigate(url, wait))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo(f"Navigated to {url}")


async def _navigate(url: str, wait: WaitStrategy) -> None:
    """Async helper for navigation."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        action = NavigateAction(NavigateParams(url=url, wait=wait))
        await action.execute(backend)
    finally:
        await backend.close()


@app.command()
def back() -> None:
    """Navigate back in browser history."""
    try:
        asyncio.run(_nav_simple(lambda b: BackAction(None).execute(b)))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo("Navigated back")


@app.command()
def forward() -> None:
    """Navigate forward in browser history."""
    try:
        asyncio.run(_nav_simple(lambda b: ForwardAction(None).execute(b)))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo("Navigated forward")


@app.command()
def reload(
    ignore_cache: bool = typer.Option(False, "--ignore-cache", help="Bypass browser cache"),
) -> None:
    """Reload the current page."""
    try:
        asyncio.run(_nav_simple(lambda b: ReloadAction(ignore_cache).execute(b)))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo("Page reloaded")


@app.command()
def stop() -> None:
    """Stop all pending navigations and resource loads."""
    try:
        asyncio.run(_nav_simple(lambda b: StopAction(None).execute(b)))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo("Stopped loading")


async def _nav_simple(action_fn: Any) -> None:
    """Async helper for simple navigation actions (back, forward, reload, stop)."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        await action_fn(backend)
    finally:
        await backend.close()


@app.command()
def tabs(
    action: str = typer.Argument("list", help="Tab action: list, new, close, activate"),
    url: str = typer.Option("about:blank", "--url", help="URL for new tab"),
    tab_id: str = typer.Option("", "--tab-id", help="Target ID for close/activate"),
) -> None:
    """Manage browser tabs (list, new, close, activate)."""
    try:
        result = asyncio.run(_tabs(action, url, tab_id))
    except BrowsixError as e:
        _handle_error(e)

    if action == "list":
        typer.echo(json.dumps(result, indent=2, default=str))
    elif action == "new":
        typer.echo(f"New tab created: {result}")
    elif action == "close":
        typer.echo(f"Tab closed: {tab_id}")
    elif action == "activate":
        typer.echo(f"Tab activated: {tab_id}")


async def _tabs(action: str, url: str, tab_id: str) -> Any:
    """Async helper for tab operations."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        params = TabsParams(action=action, url=url, tab_id=tab_id)
        return await TabsAction(params).execute(backend)
    finally:
        await backend.close()


@app.command()
def console(
    url: str = typer.Argument(..., help="URL to navigate to"),
    level: str = typer.Option(
        "all", "--level", help="Minimum log level (all, error, warning, info)"
    ),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path (JSON)"
    ),
) -> None:
    """Capture console messages from a web page."""
    try:
        result = asyncio.run(_console(url, level))
    except BrowsixError as e:
        _handle_error(e)

    if output:
        Output.write_json(result, output)
        typer.echo(f"Console output saved to {output}")
    else:
        typer.echo(json.dumps(result, indent=2, default=str))


async def _console(url: str, level: str) -> Any:
    """Async helper for console capture."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        params = ConsoleParams(
            url=url,
            level=level,
            wait=WaitStrategy(strategy="load"),
            capture="console",
        )
        return await ConsoleAction(params).execute(backend)
    finally:
        await backend.close()


@app.command()
def logs(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path (JSON)"
    ),
) -> None:
    """Capture browser log entries from a web page."""
    try:
        result = asyncio.run(_logs(url))
    except BrowsixError as e:
        _handle_error(e)

    if output:
        Output.write_json(result, output)
        typer.echo(f"Logs saved to {output}")
    else:
        typer.echo(json.dumps(result, indent=2, default=str))


async def _logs(url: str) -> Any:
    """Async helper for log capture."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        params = ConsoleParams(
            url=url,
            wait=WaitStrategy(strategy="load"),
            capture="logs",
        )
        return await ConsoleAction(params).execute(backend)
    finally:
        await backend.close()


@app.command()
def devices() -> None:
    """List available device presets."""
    for name, preset in DEVICE_PRESETS.items():
        typer.echo(
            f"  {name}: {preset['width']}x{preset['height']} "
            f"(scale={preset['device_scale_factor']}, "
            f"mobile={preset['mobile']}, touch={preset['touch']})"
        )


# ── Phase 2 commands ─────────────────────────────────────────────


@app.command()
def dom(
    url: str = typer.Argument(..., help="URL to navigate to"),
    action: str = typer.Option(
        "get",
        "--action",
        "-a",
        help="DOM action: get, query, attr, remove_attr, remove, focus, scroll",
    ),
    selector: str = typer.Option("", "--selector", "-s", help="CSS selector"),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path"
    ),
    outer: bool = typer.Option(True, "--outer/--inner", help="Outer or inner HTML"),
    all: bool = typer.Option(False, "--all", help="Query all matching elements"),
    attribute: str | None = typer.Option(
        None, "--attribute", help="Attribute name for get/set/remove"
    ),
    value: str | None = typer.Option(
        None, "--value", help="Attribute value for set"
    ),
) -> None:
    """DOM operations on a web page."""
    try:
        result = asyncio.run(
            _dom(url, action, selector, outer, all, attribute, value)
        )
    except BrowsixError as e:
        _handle_error(e)

    if isinstance(result, str):
        if output:
            Output.write_text(result, output)
            typer.echo(f"Output saved to {output}")
        else:
            typer.echo(result)
    elif result is not None:
        if output:
            Output.write_json(result, output)
            typer.echo(f"Output saved to {output}")
        else:
            typer.echo(json.dumps(result, indent=2, default=str))
    else:
        typer.echo("Done")


async def _dom(
    url: str,
    action: str,
    selector: str,
    outer: bool,
    all: bool,
    attribute: str | None,
    value: str | None,
) -> Any:
    """Async helper for DOM operations."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        params = DOMParams(
            url=url,
            action=action,
            selector=selector,
            outer=outer,
            all=all,
            attribute=attribute,
            value=value,
            wait=WaitStrategy(strategy="load"),
        )
        return await DOMAction(params).execute(backend)
    finally:
        await backend.close()


@app.command()
def scrape(
    urls: list[str] = typer.Argument(..., help="URLs to scrape"),  # noqa: B008
    expression: str = typer.Option(
        "document.title", "--expression", "-e", help="JavaScript expression"
    ),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path"
    ),
    csv_out: bool = typer.Option(False, "--csv", help="Output as CSV"),
    file: str | None = typer.Option(
        None, "--file", help="Read expression from file (prefix with @)"
    ),
    selector: str | None = typer.Option(
        None, "--selector", "-s", help="CSS selector to wait for"
    ),
) -> None:
    """Scrape multiple URLs by evaluating a JS expression on each."""
    expr = expression
    if file:
        expr = f"@{file}"

    try:
        results = asyncio.run(_scrape(urls, expr, file, selector))
    except BrowsixError as e:
        _handle_error(e)

    if csv_out:
        Output.write_csv(results, output)
        if output:
            typer.echo(f"CSV saved to {output}")
    elif output:
        Output.write_json(results, output)
        typer.echo(f"Results saved to {output}")
    else:
        typer.echo(json.dumps(results, indent=2, default=str))


async def _scrape(
    urls: list[str],
    expression: str,
    file: str | None,
    selector: str | None,
) -> list[dict[str, Any]]:
    """Async helper for scraping."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        params = ScrapeParams(
            urls=urls,
            expression=expression,
            file=file,
            output_format="json",
            selector=selector,
            wait=WaitStrategy(strategy="load"),
        )
        return await ScrapeAction(params).execute(backend)
    finally:
        await backend.close()


@app.command()
def har(
    url: str = typer.Argument(..., help="URL to capture HAR for"),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path (.har)"
    ),
    wait: int = typer.Option(
        3000, "--wait", help="Wait time after navigation (ms)"
    ),
    filter: str | None = typer.Option(
        None, "--filter", help="URL filter pattern"
    ),
) -> None:
    """Capture network traffic as HAR 1.2."""
    try:
        result = asyncio.run(_har(url, wait, filter))
    except BrowsixError as e:
        _handle_error(e)

    if output:
        Output.write_json(result, output)
        typer.echo(f"HAR saved to {output}")
    else:
        typer.echo(json.dumps(result, indent=2, default=str))


async def _har(url: str, wait: int, filter: str | None) -> Any:
    """Async helper for HAR capture."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        params = HarParams(url=url, wait=wait, filter=filter)
        return await HARAction(params).execute(backend)
    finally:
        await backend.close()


@app.command()
def cookies(
    action: str = typer.Argument(
        "get", help="Cookie action: get, set, delete, clear"
    ),
    url: str = typer.Option("", "--url", help="URL for cookie context"),
    name: str = typer.Option("", "--name", help="Cookie name"),
    value: str = typer.Option("", "--value", help="Cookie value"),
    domain: str = typer.Option("", "--domain", help="Cookie domain"),
    path: str = typer.Option("/", "--path", help="Cookie path"),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path (JSON)"
    ),
) -> None:
    """Manage browser cookies (get, set, delete, clear)."""
    try:
        result = asyncio.run(
            _cookies(action, url, name, value, domain, path)
        )
    except BrowsixError as e:
        _handle_error(e)

    if action == "get":
        if output:
            Output.write_json(result, output)
            typer.echo(f"Cookies saved to {output}")
        else:
            typer.echo(json.dumps(result, indent=2, default=str))
    else:
        typer.echo(f"Cookies {action} done")


async def _cookies(
    action: str,
    url: str,
    name: str,
    value: str,
    domain: str,
    path: str,
) -> Any:
    """Async helper for cookie operations."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        if url:
            await backend.navigate(url, WaitStrategy(strategy="load"))

        if action == "get":
            return await backend.get_cookies()
        if action == "set":
            cookie = CookieParams(
                name=name, value=value, domain=domain, path=path
            )
            await backend.set_cookie(cookie)
        elif action == "delete":
            await backend.delete_cookie(name, domain)
        elif action == "clear":
            await backend.clear_cookies()
        return None
    finally:
        await backend.close()


@app.command()
def headers(
    headers_json: str = typer.Argument(
        ..., help='JSON dict of headers, or @path to read from file'
    ),
) -> None:
    """Set extra HTTP headers for all requests."""
    if headers_json.startswith("@"):
        from pathlib import Path
        data = json.loads(Path(headers_json[1:]).read_text(encoding="utf-8"))
    else:
        data = json.loads(headers_json)

    try:
        asyncio.run(_headers(data))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo("Headers set")


async def _headers(headers: dict[str, str]) -> None:
    """Async helper for setting headers."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        await backend.set_headers(headers)
    finally:
        await backend.close()


@app.command()
def user_agent(
    ua: str = typer.Argument(..., help="User-Agent string to set"),
) -> None:
    """Override the browser's User-Agent string."""
    try:
        asyncio.run(_user_agent(ua))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo("User-Agent set")


async def _user_agent(ua: str) -> None:
    """Async helper for setting user agent."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        await backend.set_user_agent(ua)
    finally:
        await backend.close()


@app.command()
def browser(
    action: str = typer.Argument(
        "version", help="Browser action: version, new_context, list_contexts"
    ),
) -> None:
    """Browser management commands (version, contexts)."""
    try:
        result = asyncio.run(_browser(action))
    except BrowsixError as e:
        _handle_error(e)

    if isinstance(result, str):
        typer.echo(result)
    elif isinstance(result, list):
        typer.echo(json.dumps(result, indent=2, default=str))
    else:
        typer.echo("Done")


async def _browser(action: str) -> Any:
    """Async helper for browser management."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        return await BrowserAction(action).execute(backend)
    finally:
        await backend.close()


# ── Phase 3 commands ─────────────────────────────────────────────


@app.command()
def multi(
    config: str = typer.Argument(..., help="Path to YAML config file"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validate config and show planned actions without launching browser",
    ),
) -> None:
    """Execute multiple actions from a YAML config file."""
    from pathlib import Path

    config_path = Path(config)

    if dry_run:
        try:
            actions = _parse_and_describe(config_path)
        except BrowsixError as e:
            _handle_error(e)
            return
        typer.echo(f"Plan: {len(actions)} action(s)")
        for i, desc in enumerate(actions):
            typer.echo(f"  {i + 1}. {desc}")
        return

    try:
        results = asyncio.run(_multi(config_path))
    except BrowsixError as e:
        _handle_error(e)
        return

    typer.echo(f"Completed {len(results)} actions")
    for i, result in enumerate(results):
        if isinstance(result, bytes):
            typer.echo(f"  Action {i + 1}: {len(result)} bytes")
        elif isinstance(result, str):
            typer.echo(f"  Action {i + 1}: {result[:100]}")
        else:
            typer.echo(f"  Action {i + 1}: {type(result).__name__}")


async def _multi(config_path: Any) -> list[Any]:
    """Async helper for multi-action execution."""
    from browsix.actions.multi import MultiAction

    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        action = MultiAction(config_path)
        return await action.execute(backend)
    finally:
        await backend.close()


def _parse_and_describe(config_path: Any) -> list[str]:
    """Parse YAML config and return human-readable action descriptions.

    Args:
        config_path: Path to the YAML config file.

    Returns:
        List of description strings, one per action.
    """
    from browsix.multi import parse_yaml

    actions = parse_yaml(config_path)
    descriptions: list[str] = []
    for item in actions:
        action_type = next(iter(item))
        params = item[action_type]
        url = params.get("url", "")
        if url:
            descriptions.append(f"{action_type}({url})")
        else:
            descriptions.append(f"{action_type}()")
    return descriptions


@app.command()
def batch(
    urls_file: str = typer.Argument(..., help="Path to file with one URL per line"),
    action: str = typer.Argument(..., help="Action to run: screenshot, pdf, scrape, eval"),
    output_dir: str = typer.Option(
        "output", "--output-dir", "-o", help="Directory for output files"
    ),
    expression: str = typer.Option(
        "document.title",
        "--expression",
        "-e",
        help="JS expression for scrape/eval",
    ),
    parallel: int = typer.Option(
        4, "--parallel", "-p", help="Number of parallel browser instances"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show plan without launching browser"),
) -> None:
    """Run a single action against multiple URLs in parallel."""
    from pathlib import Path

    urls_path = Path(urls_file)
    if not urls_path.exists():
        typer.echo(f"Error: URLs file not found: {urls_path}")
        raise typer.Exit(1)

    urls = [line.strip() for line in urls_path.read_text().splitlines() if line.strip()]
    if not urls:
        typer.echo("Error: No URLs found in file")
        raise typer.Exit(1)

    if dry_run:
        typer.echo(f"Plan: {len(urls)} URL(s) x {action}")
        for u in urls:
            typer.echo(f"  {action}({u})")
        return

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        results = asyncio.run(_batch(urls, action, out_dir, expression, parallel))
    except BrowsixError as e:
        _handle_error(e)
        return

    typer.echo(f"Completed {len(results)} / {len(urls)} actions")
    for i, (url, result) in enumerate(zip(urls, results, strict=False)):
        if isinstance(result, Exception):
            typer.echo(f"  {i + 1}. {url}: ERROR — {result}")
        elif isinstance(result, bytes):
            typer.echo(f"  {i + 1}. {url}: {len(result)} bytes")
        elif isinstance(result, str):
            typer.echo(f"  {i + 1}. {url}: {result[:100]}")
        else:
            typer.echo(f"  {i + 1}. {url}: {type(result).__name__}")


async def _batch(
    urls: list[str],
    action: str,
    out_dir: Any,
    expression: str,
    parallel: int,
) -> list[Any]:
    """Run an action against multiple URLs with limited concurrency.

    Args:
        urls: List of URLs to process.
        action: Action type — screenshot, pdf, scrape, or eval.
        out_dir: Output directory for saved files.
        expression: JS expression for scrape/eval.
        parallel: Maximum number of concurrent browser instances.

    Returns:
        List of results (or exceptions) in the same order as urls.
    """
    import asyncio as _asyncio

    semaphore = _asyncio.Semaphore(parallel)

    async def _run_one(url: str) -> Any:
        async with semaphore:
            try:
                return await _batch_single(url, action, out_dir, expression)
            except Exception as exc:
                return exc

    tasks = [_run_one(u) for u in urls]
    return await _asyncio.gather(*tasks)


async def _batch_single(
    url: str,
    action: str,
    out_dir: Any,
    expression: str,
) -> Any:
    """Execute a single action for one URL in batch mode.

    Args:
        url: URL to process.
        action: Action type — screenshot, pdf, scrape, or eval.
        out_dir: Output directory for saved files.
        expression: JS expression for scrape/eval.

    Returns:
        Result of the action.

    Raises:
        ValueError: If the action type is unknown.
    """
    from browsix.actions.eval import EvalAction
    from browsix.actions.pdf import PDFAction
    from browsix.actions.scrape import ScrapeAction
    from browsix.actions.screenshot import ScreenshotAction
    from browsix.config import (
        EvalParams,
        PDFParams,
        ScrapeParams,
        ScreenshotParams,
        WaitStrategy,
    )

    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions(headless=True))

        if action == "screenshot":
            sp = ScreenshotParams(url=url, full_page=True, wait=WaitStrategy(strategy="load"))
            result = await ScreenshotAction(sp).execute(backend)
            safe_url = url.replace("://", "_").replace("/", "_")[:80]
            (out_dir / f"{safe_url}.png").write_bytes(result)
            return result

        if action == "pdf":
            pp = PDFParams(url=url, wait=WaitStrategy(strategy="load"))
            result = await PDFAction(pp).execute(backend)
            safe_url = url.replace("://", "_").replace("/", "_")[:80]
            (out_dir / f"{safe_url}.pdf").write_bytes(result)
            return result

        if action == "scrape":
            scp = ScrapeParams(
                urls=[url],
                expression=expression,
                wait=WaitStrategy(strategy="load"),
            )
            return await ScrapeAction(scp).execute(backend)

        if action == "eval":
            ep = EvalParams(url=url, expression=expression, wait=WaitStrategy(strategy="load"))
            return await EvalAction(ep).execute(backend)

        raise ValueError(f"Unknown batch action: {action}")
    finally:
        await backend.close()


@app.command()
def backends() -> None:
    """List available backends."""
    manager = BackendManager()
    available = manager.list_available()
    if not available:
        typer.echo("No backends available. Install cdpwave or bidiwave.")
        return
    for name in available:
        typer.echo(f"  {name}")


@app.command()
def install_check() -> None:
    """Check which backends are installed and their versions."""
    manager = BackendManager()
    status = manager.install_check()
    for name, version in status.items():
        typer.echo(f"  {name}: {version}")


emulation_app = typer.Typer(
    help="Emulation commands (device, viewport, geolocation, timezone, dark_mode)"
)
app.add_typer(emulation_app, name="emulation")


@emulation_app.command("device")
def emulation_device(
    url: str = typer.Argument(..., help="URL to navigate to"),
    device: str = typer.Option(..., "--device", help="Device preset name"),
    output: str = typer.Option("screenshot.png", "--output", "-o", help="Output file path"),
) -> None:
    """Emulate a device and take a screenshot."""
    try:
        image_bytes = asyncio.run(_emulation_device(url, device))
    except BrowsixError as e:
        _handle_error(e)

    Output.write_bytes(image_bytes, output)
    typer.echo(f"Screenshot saved to {output}")


async def _emulation_device(url: str, device: str) -> bytes:
    """Async helper for device emulation + screenshot."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        await backend.emulate_device(device)
        from browsix.config import ScreenshotParams

        params = ScreenshotParams(url=url, full_page=True)
        return bytes(await backend.screenshot(params))
    finally:
        await backend.close()


@emulation_app.command("viewport")
def emulation_viewport(
    url: str = typer.Argument(..., help="URL to navigate to"),
    width: int = typer.Option(..., "--width", help="Viewport width in pixels"),
    height: int = typer.Option(..., "--height", help="Viewport height in pixels"),
    output: str = typer.Option("screenshot.png", "--output", "-o", help="Output file path"),
) -> None:
    """Set a custom viewport and take a screenshot."""
    try:
        image_bytes = asyncio.run(_emulation_viewport(url, width, height))
    except BrowsixError as e:
        _handle_error(e)

    Output.write_bytes(image_bytes, output)
    typer.echo(f"Screenshot saved to {output}")


async def _emulation_viewport(url: str, width: int, height: int) -> bytes:
    """Async helper for viewport emulation + screenshot."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        await backend.set_viewport(width, height)
        await backend.navigate(url, WaitStrategy(strategy="load"))
        from browsix.config import ScreenshotParams

        params = ScreenshotParams(url=url, full_page=True)
        return bytes(await backend.screenshot(params))
    finally:
        await backend.close()


@emulation_app.command("geolocation")
def emulation_geolocation(
    url: str = typer.Argument(..., help="URL to navigate to"),
    lat: float = typer.Option(..., "--lat", help="Latitude in degrees"),
    lon: float = typer.Option(..., "--lon", help="Longitude in degrees"),
    output: str = typer.Option("screenshot.png", "--output", "-o", help="Output file path"),
) -> None:
    """Override geolocation and take a screenshot."""
    try:
        image_bytes = asyncio.run(_emulation_geolocation(url, lat, lon))
    except BrowsixError as e:
        _handle_error(e)

    Output.write_bytes(image_bytes, output)
    typer.echo(f"Screenshot saved to {output}")


async def _emulation_geolocation(url: str, lat: float, lon: float) -> bytes:
    """Async helper for geolocation override + screenshot."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        await backend.set_geolocation(lat, lon)
        from browsix.config import ScreenshotParams

        params = ScreenshotParams(url=url, full_page=True)
        return bytes(await backend.screenshot(params))
    finally:
        await backend.close()


@emulation_app.command("timezone")
def emulation_timezone(
    url: str = typer.Argument(..., help="URL to navigate to"),
    tz: str = typer.Option(..., "--tz", help="IANA timezone ID"),
    output: str = typer.Option("screenshot.png", "--output", "-o", help="Output file path"),
) -> None:
    """Override timezone and take a screenshot."""
    try:
        image_bytes = asyncio.run(_emulation_timezone(url, tz))
    except BrowsixError as e:
        _handle_error(e)

    Output.write_bytes(image_bytes, output)
    typer.echo(f"Screenshot saved to {output}")


async def _emulation_timezone(url: str, tz: str) -> bytes:
    """Async helper for timezone override + screenshot."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        await backend.set_timezone(tz)
        from browsix.config import ScreenshotParams

        params = ScreenshotParams(url=url, full_page=True)
        return bytes(await backend.screenshot(params))
    finally:
        await backend.close()


@emulation_app.command("dark_mode")
def emulation_dark_mode(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("screenshot.png", "--output", "-o", help="Output file path"),
) -> None:
    """Enable dark mode and take a screenshot."""
    try:
        image_bytes = asyncio.run(_emulation_dark_mode(url))
    except BrowsixError as e:
        _handle_error(e)

    Output.write_bytes(image_bytes, output)
    typer.echo(f"Screenshot saved to {output}")


async def _emulation_dark_mode(url: str) -> bytes:
    """Async helper for dark mode + screenshot."""
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        await backend.set_dark_mode(True)
        from browsix.config import ScreenshotParams

        params = ScreenshotParams(url=url, full_page=True)
        return bytes(await backend.screenshot(params))
    finally:
        await backend.close()


# ── Phase 5 commands ─────────────────────────────────────────────

input_app = typer.Typer(help="Input commands (click, type, fill, select, hover, key, drag, tap)")
app.add_typer(input_app, name="input")


@input_app.command("click")
def input_click(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Argument(..., help="CSS selector for element to click"),
    button: str = typer.Option("left", "--button", help="Mouse button (left, right, middle)"),
    click_count: int = typer.Option(1, "--count", help="Number of clicks"),
) -> None:
    """Click an element on a web page."""
    try:
        asyncio.run(_input_action(
            url, "click", selector=selector, button=button, click_count=click_count
        ))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo(f"Clicked '{selector}' on {url}")


@input_app.command("type")
def input_type(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Argument(..., help="CSS selector for input element"),
    text: str = typer.Argument(..., help="Text to type"),
    delay: int = typer.Option(0, "--delay", help="Delay between keystrokes (ms)"),
) -> None:
    """Type text into an element on a web page."""
    try:
        asyncio.run(_input_action(url, "type", selector=selector, text=text, delay=delay))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo(f"Typed text into '{selector}' on {url}")


@input_app.command("fill")
def input_fill(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Argument(..., help="CSS selector for input element"),
    value: str = typer.Argument(..., help="Value to fill"),
) -> None:
    """Fill an input element with a value."""
    try:
        asyncio.run(_input_action(url, "fill", selector=selector, value=value))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo(f"Filled '{selector}' with value on {url}")


@input_app.command("select")
def input_select(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Argument(..., help="CSS selector for select element"),
    value: str = typer.Argument(..., help="Option value to select"),
) -> None:
    """Select an option in a <select> element."""
    try:
        asyncio.run(_input_action(url, "select", selector=selector, value=value))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo(f"Selected '{value}' in '{selector}' on {url}")


@input_app.command("hover")
def input_hover(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Argument(..., help="CSS selector for element to hover"),
) -> None:
    """Hover over an element on a web page."""
    try:
        asyncio.run(_input_action(url, "hover", selector=selector))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo(f"Hovered over '{selector}' on {url}")


@input_app.command("key")
def input_key(
    url: str = typer.Argument(..., help="URL to navigate to"),
    key: str = typer.Argument(..., help="Key to press (e.g. Enter, Tab, Escape)"),
) -> None:
    """Press a keyboard key on a web page."""
    try:
        asyncio.run(_input_action(url, "key", key=key))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo(f"Pressed key '{key}' on {url}")


@input_app.command("drag")
def input_drag(
    url: str = typer.Argument(..., help="URL to navigate to"),
    source: str = typer.Argument(..., help="CSS selector for element to drag"),
    target: str = typer.Argument(..., help="CSS selector for drop target"),
) -> None:
    """Drag an element to a target on a web page."""
    try:
        asyncio.run(_input_action(url, "drag", source=source, target=target))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo(f"Dragged '{source}' to '{target}' on {url}")


@input_app.command("tap")
def input_tap(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Argument(..., help="CSS selector for element to tap"),
) -> None:
    """Tap an element on a web page (touch emulation)."""
    try:
        asyncio.run(_input_action(url, "tap", selector=selector))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo(f"Tapped '{selector}' on {url}")


async def _input_action(
    url: str,
    action: str,
    selector: str = "",
    text: str | None = None,
    value: str | None = None,
    key: str | None = None,
    button: str = "left",
    click_count: int = 1,
    delay: int = 0,
    source: str | None = None,
    target: str | None = None,
) -> None:
    """Async helper for input actions."""
    from browsix.actions.input import InputAction

    backend = _get_backend()
    params = InputParams(
        url=url,
        action=action,
        selector=selector,
        text=text,
        value=value,
        key=key,
        button=button,
        click_count=click_count,
        delay=delay,
        source=source,
        target=target,
        wait=WaitStrategy(strategy="load"),
    )
    await InputAction(params).execute(backend)


# ── Network advanced ────────────────────────────────────────────

network_app = typer.Typer(help="Network commands (block, throttle, cache, intercept, mock)")
app.add_typer(network_app, name="network")


@network_app.command("block")
def network_block(
    patterns: list[str] = typer.Argument(..., help="URL patterns to block (glob-style)"),  # noqa: B008
) -> None:
    """Block requests matching URL patterns."""
    try:
        asyncio.run(_network_block(patterns))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo(f"Blocked {len(patterns)} URL pattern(s)")


async def _network_block(patterns: list[str]) -> None:
    """Block network requests matching the given patterns.

    Args:
        patterns: List of URL patterns to block.
    """
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        await backend.block_requests(patterns)
    finally:
        await backend.close()


@network_app.command("throttle")
def network_throttle(
    offline: bool = typer.Option(False, "--offline", help="Emulate offline state"),
    latency: int = typer.Option(0, "--latency", help="Latency in milliseconds"),
    download: int = typer.Option(-1, "--download", help="Download bps (-1=unlimited)"),
    upload: int = typer.Option(-1, "--upload", help="Upload bps (-1=unlimited)"),
) -> None:
    """Throttle network conditions."""
    params = ThrottleParams(
        offline=offline, latency_ms=latency, download_bps=download, upload_bps=upload
    )
    try:
        asyncio.run(_network_throttle(params))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo("Network throttling set")


async def _network_throttle(params: ThrottleParams) -> None:
    """Apply network throttling conditions.

    Args:
        params: Throttle parameters with offline, latency, and bandwidth settings.
    """
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        await backend.throttle_network(params)
    finally:
        await backend.close()


@network_app.command("cache")
def network_cache(
    disabled: bool = typer.Option(True, "--disabled/--enabled", help="Disable or enable cache"),
) -> None:
    """Disable or enable the browser cache."""
    try:
        asyncio.run(_network_cache(disabled))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo(f"Cache {'disabled' if disabled else 'enabled'}")


async def _network_cache(disabled: bool) -> None:
    """Enable or disable the browser cache.

    Args:
        disabled: True to disable cache, False to enable.
    """
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        await backend.set_cache_disabled(disabled)
    finally:
        await backend.close()


@network_app.command("intercept")
def network_intercept(
    url_pattern: str = typer.Argument(..., help="URL pattern to intercept"),
    resource_type: str = typer.Option("", "--resource-type", help="Resource type filter"),
) -> None:
    """Intercept requests matching a URL pattern."""
    pattern: dict[str, Any] = {"urlPattern": url_pattern}
    if resource_type:
        pattern["resourceType"] = resource_type
    try:
        asyncio.run(_network_intercept(pattern))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo(f"Intercepting requests matching '{url_pattern}'")


async def _network_intercept(pattern: dict[str, Any]) -> None:
    """Intercept network requests matching a pattern.

    Args:
        pattern: Fetch.enable pattern dict with urlPattern and optional resourceType.
    """
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        await backend.intercept_requests(pattern)
    finally:
        await backend.close()


@network_app.command("mock")
def network_mock(
    url: str = typer.Argument(..., help="URL pattern to mock"),
    body: str = typer.Argument(..., help="Response body (or JSON string)"),
    status: int = typer.Option(200, "--status", help="HTTP status code"),
    content_type: str = typer.Option(
        "application/json", "--content-type", help="Content-Type header"
    ),
) -> None:
    """Mock a response for requests matching a URL pattern."""
    response: dict[str, Any] = {"status": status, "body": body, "content_type": content_type}
    try:
        asyncio.run(_network_mock(url, response))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo(f"Mocking responses for '{url}'")


async def _network_mock(url: str, response: dict[str, Any]) -> None:
    """Mock a response for requests matching a URL pattern.

    Args:
        url: URL pattern to mock.
        response: Response dict with status, body, and content_type.
    """
    backend = _get_backend()
    try:
        await backend.launch(BrowserOptions())
        await backend.mock_response(url, response)
    finally:
        await backend.close()


# ── Accessibility ───────────────────────────────────────────────


@app.command()
def a11y(
    url: str = typer.Argument(..., help="URL to navigate to"),
    action: str = typer.Option("tree", "--action", "-a", help="A11y action: tree, node, ancestors"),
    node_id: str = typer.Option("", "--node-id", help="Node ID for node/ancestors actions"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Get accessibility tree, node, or ancestors from a web page."""
    try:
        result = asyncio.run(_a11y(url, action, node_id))
    except BrowsixError as e:
        _handle_error(e)

    if output:
        Output.write_json(result, output)
        typer.echo(f"A11y data saved to {output}")
    else:
        typer.echo(json.dumps(result, indent=2, default=str))


async def _a11y(url: str, action: str, node_id: str) -> Any:
    """Execute an accessibility action on a web page.

    Args:
        url: URL to navigate to.
        action: Accessibility action ("tree", "node", or "ancestors").
        node_id: Node ID for node-specific actions.

    Returns:
        Accessibility tree or node data.
    """
    from browsix.actions.accessibility import AccessibilityAction

    backend = _get_backend()
    act = AccessibilityAction(
        params=None,
        action=action,
        node_id=node_id,
        url=url,
        wait=WaitStrategy(strategy="load"),
    )
    return await act.execute(backend)


# ── Download ────────────────────────────────────────────────────


@app.command()
def download(
    url: str = typer.Argument(..., help="URL to navigate to (must trigger a download)"),
    pattern: str = typer.Option(".*", "--pattern", help="URL pattern to match downloads"),
    output: str = typer.Option("download.bin", "--output", "-o", help="Output file path"),
) -> None:
    """Intercept a file download from a web page."""
    try:
        data = asyncio.run(_download(url, pattern))
    except BrowsixError as e:
        _handle_error(e)

    Output.write_bytes(data, output)
    typer.echo(f"Download saved to {output} ({len(data)} bytes)")


async def _download(url: str, pattern: str) -> bytes:
    """Intercept a file download from a web page.

    Args:
        url: URL to navigate to that triggers a download.
        pattern: URL pattern to match download requests.

    Returns:
        Downloaded file bytes.
    """
    from browsix.actions.download import DownloadAction

    backend = _get_backend()
    act = DownloadAction(
        params=pattern,
        url=url,
        wait=WaitStrategy(strategy="load"),
    )
    return await act.execute(backend)


# ── Dialog ──────────────────────────────────────────────────────


@app.command()
def dialog(
    url: str = typer.Argument(..., help="URL to navigate to"),
    action: str = typer.Option("accept", "--action", "-a", help="Dialog action: accept, dismiss"),
    prompt_text: str = typer.Option("", "--text", help="Text for prompt dialogs"),
) -> None:
    """Accept or dismiss a JavaScript dialog on a web page."""
    try:
        asyncio.run(_dialog(url, action, prompt_text or None))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo(f"Dialog {action}ed on {url}")


async def _dialog(url: str, action: str, prompt_text: str | None) -> None:
    """Accept or dismiss a JavaScript dialog on a web page.

    Args:
        url: URL to navigate to.
        action: Dialog action ("accept" or "dismiss").
        prompt_text: Text to enter in prompt dialogs, if applicable.
    """
    from browsix.actions.dialog import DialogAction

    backend = _get_backend()
    act = DialogAction(
        params="",
        action=action,
        prompt_text=prompt_text,
        url=url,
        wait=WaitStrategy(strategy="load"),
    )
    await act.execute(backend)


# ── Permissions ─────────────────────────────────────────────────


@app.command()
def permissions(
    action: str = typer.Argument("grant", help="Permissions action: grant, reset"),
    permission: str = typer.Option(
        "geolocation", "--permission",
        help="Permission name (e.g. geolocation, notifications)",
    ),
    url: str = typer.Option("", "--url", help="URL to navigate to (optional)"),
) -> None:
    """Grant or reset browser permissions."""
    try:
        asyncio.run(_permissions(action, permission, url))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo(f"Permissions {action} for '{permission}'")


async def _permissions(action: str, permission: str, url: str) -> None:
    """Grant or reset browser permissions.

    Args:
        action: Permission action ("grant", "deny", "reset", or "query").
        permission: Permission name (e.g. "geolocation").
        url: URL to navigate to (optional).
    """
    from browsix.actions.permissions import PermissionsAction

    backend = _get_backend()
    act = PermissionsAction(
        params="",
        action=action,
        permission=permission,
        url=url,
        wait=WaitStrategy(strategy="load") if url else None,
    )
    await act.execute(backend)


# ── Security ────────────────────────────────────────────────────


@app.command()
def security(
    url: str = typer.Argument(..., help="URL to navigate to"),
    action: str = typer.Option(
        "state", "--action", "-a", help="Security action: state, ignore_cert"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Get security state or ignore certificate errors."""
    try:
        result = asyncio.run(_security(url, action))
    except BrowsixError as e:
        _handle_error(e)

    if action == "state":
        if output:
            Output.write_json(result, output)
            typer.echo(f"Security state saved to {output}")
        else:
            typer.echo(json.dumps(result, indent=2, default=str))
    else:
        typer.echo(f"Certificate errors ignored on {url}")


async def _security(url: str, action: str) -> Any:
    """Execute a security action on a web page.

    Args:
        url: URL to navigate to.
        action: Security action ("state" or "ignore-cert-errors").

    Returns:
        Security state data if action is "state".
    """
    from browsix.actions.security import SecurityAction

    backend = _get_backend()
    act = SecurityAction(
        params="",
        action=action,
        url=url,
        wait=WaitStrategy(strategy="load"),
    )
    return await act.execute(backend)


# ── Screencast ──────────────────────────────────────────────────


@app.command()
def screencast(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output_dir: str = typer.Option(
        "screencast", "--output", "-o", help="Output directory for frames"
    ),
    duration: float = typer.Option(5.0, "--duration", help="Capture duration in seconds"),
    fps: int = typer.Option(10, "--fps", help="Frames per second (approximate)"),
    quality: int = typer.Option(80, "--quality", help="JPEG quality (0-100)"),
    format: str = typer.Option("png", "--format", help="Image format (png or jpeg)"),
) -> None:
    """Capture a screencast from a web page and save frames as PNGs."""
    params = ScreencastParams(
        url=url,
        format=format,
        quality=quality,
        duration=duration,
        wait=WaitStrategy(strategy="load"),
    )
    try:
        frames = asyncio.run(_screencast(params, output_dir))
    except BrowsixError as e:
        _handle_error(e)
    typer.echo(f"Saved {len(frames)} frames to {output_dir}/")


async def _screencast(params: ScreencastParams, output_dir: str) -> list[str]:
    """Capture screencast frames and save them to a directory.

    Args:
        params: Screencast parameters including URL, format, and duration.
        output_dir: Directory to save captured frames.

    Returns:
        List of saved frame file paths.
    """
    from browsix.actions.screencast import ScreencastAction

    backend = _get_backend()
    action = ScreencastAction(params, output_dir=output_dir)
    return await action.execute(backend)


# ── Phase 6: Performance ─────────────────────────────────────────


perf_app = typer.Typer(help="Performance commands (metrics, trace, profile, heap, coverage)")
app.add_typer(perf_app, name="perf")


@perf_app.command("metrics")
def perf_metrics(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get performance metrics from a web page."""
    try:
        result = asyncio.run(_perf_action(url, "metrics"))
    except BrowsixError as e:
        _handle_error(e)
    _write_perf_output(result, output, "metrics")


@perf_app.command("trace")
def perf_trace(
    url: str = typer.Argument(..., help="URL to navigate to"),
    duration: int = typer.Option(3000, "--duration", help="Trace duration in ms"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Capture a performance trace from a web page."""
    try:
        result = asyncio.run(_perf_action(url, "trace", duration_ms=duration))
    except BrowsixError as e:
        _handle_error(e)
    _write_perf_output(result, output, "trace")


@perf_app.command("profile")
def perf_profile(
    url: str = typer.Argument(..., help="URL to navigate to"),
    duration: int = typer.Option(3000, "--duration", help="Profile duration in ms"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Capture a CPU profile from a web page."""
    try:
        result = asyncio.run(_perf_action(url, "profile", duration_ms=duration))
    except BrowsixError as e:
        _handle_error(e)
    _write_perf_output(result, output, "profile")


@perf_app.command("heap")
def perf_heap(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Capture a heap snapshot from a web page."""
    try:
        result = asyncio.run(_perf_action(url, "heap"))
    except BrowsixError as e:
        _handle_error(e)
    _write_perf_output(result, output, "heap snapshot")


@perf_app.command("coverage")
def perf_coverage(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get JavaScript code coverage from a web page."""
    try:
        result = asyncio.run(_perf_action(url, "coverage"))
    except BrowsixError as e:
        _handle_error(e)
    _write_perf_output(result, output, "JS coverage")


@perf_app.command("css-coverage")
def perf_css_coverage(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get CSS rule usage coverage from a web page."""
    try:
        result = asyncio.run(_perf_action(url, "css-coverage"))
    except BrowsixError as e:
        _handle_error(e)
    _write_perf_output(result, output, "CSS coverage")


async def _perf_action(
    url: str, action: str, duration_ms: int = 3000
) -> dict[str, Any]:
    """Execute a performance action on a web page.

    Args:
        url: URL to navigate to.
        action: Performance action ("metrics", "trace", "profile",
            "heap", "coverage", "css-coverage").
        duration_ms: Duration in milliseconds for trace/profile actions.

    Returns:
        Performance data as a dictionary.
    """
    from browsix.actions.performance import PerformanceAction, PerformanceParams

    params = PerformanceParams(
        url=url, action=action, duration_ms=duration_ms,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    act = PerformanceAction(params)
    return await act.execute(backend)


def _write_perf_output(result: dict[str, Any], output: str, label: str) -> None:
    """Write performance result to file or stdout as JSON."""
    if output == "-":
        typer.echo(json.dumps(result, indent=2, default=str))
    else:
        with open(output, "w") as f:  # noqa: ASYNC230
            json.dump(result, f, indent=2, default=str)
        _echo(f"Saved {label} to {output}")


# ── Phase 6: Serve mode ──────────────────────────────────────────


@app.command()
def serve(
    port: int = typer.Option(8080, "--port", "-p", help="Port to listen on"),
    host: str = typer.Option("localhost", "--host", help="Host to bind to"),
    backend: str = typer.Option(
        None, "--backend", help="Preferred backend (cdp or bidi)"
    ),
) -> None:
    """Start the browsix HTTP server."""
    from browsix.serve import serve as _serve

    try:
        _serve(port=port, host=host, backend=backend or _preferred_backend)
    except BrowsixError as e:
        _handle_error(e)


@app.command()
def plugins() -> None:
    """List discovered plugins (actions, backends, middleware)."""
    from browsix.plugins import get_registry

    registry = get_registry()
    actions = registry.list_actions()
    backends = registry.list_backends()
    middleware = registry.list_middleware()

    if not actions and not backends and not middleware:
        typer.echo("No plugins discovered.")
        typer.echo(
            "\nInstall a plugin package with entry point group "
            "'browsix.plugins' to extend browsix."
        )
        return

    if actions:
        typer.echo("Actions:")
        for name in actions:
            plugin = registry.get_action(name)
            desc = plugin.description if plugin else ""
            typer.echo(f"  {name}: {desc}" if desc else f"  {name}")

    if backends:
        typer.echo("Backends:")
        for name in backends:
            typer.echo(f"  {name}")

    if middleware:
        typer.echo("Middleware:")
        for name in middleware:
            typer.echo(f"  {name}")


@app.command()
def completions(
    shell: str = typer.Argument(..., help="Shell: bash, zsh, fish, powershell"),
) -> None:
    """Install shell completions for browsix."""
    import subprocess

    shells = {"bash", "zsh", "fish", "powershell"}
    if shell not in shells:
        Output.error(f"Unsupported shell: {shell}. Choose from: {', '.join(sorted(shells))}")
        raise typer.Exit(EXIT_CONFIG_ERROR)

    try:
        subprocess.run(
            [sys.executable, "-m", "browsix", "completion", shell],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        Output.error(f"Failed to install completions: {e}")
        raise typer.Exit(EXIT_BROWSER_ERROR) from e

    Output.success(f"Completions installed for {shell}")


# ── Phase 7: CSS ─────────────────────────────────────────────────


css_app = typer.Typer(help="CSS inspection commands (styles, stylesheets, rules, computed)")
app.add_typer(css_app, name="css")


@css_app.command("styles")
def css_styles(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get inline and matched styles for an element."""
    try:
        result = asyncio.run(_css_action(url, "styles", selector=selector))
    except BrowsixError as e:
        _handle_error(e)
    _write_json_output(result, output, "styles")


@css_app.command("stylesheets")
def css_stylesheets(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """List all stylesheets in the page."""
    try:
        result = asyncio.run(_css_action(url, "stylesheets"))
    except BrowsixError as e:
        _handle_error(e)
    _write_json_output(result, output, "stylesheets")


@css_app.command("rules")
def css_rules(
    url: str = typer.Argument(..., help="URL to navigate to"),
    stylesheet_id: str = typer.Option(..., "--stylesheet-id", help="Stylesheet ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get CSS rules from a specific stylesheet."""
    try:
        result = asyncio.run(_css_action(url, "rules", stylesheet_id=stylesheet_id))
    except BrowsixError as e:
        _handle_error(e)
    _write_json_output(result, output, "rules")


@css_app.command("computed")
def css_computed(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get computed styles for an element."""
    try:
        result = asyncio.run(_css_action(url, "computed", selector=selector))
    except BrowsixError as e:
        _handle_error(e)
    _write_json_output(result, output, "computed styles")


async def _css_action(
    url: str,
    action: str,
    selector: str | None = None,
    stylesheet_id: str | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    """Execute a CSS action on a web page.

    Args:
        url: URL to navigate to.
        action: CSS action ("styles", "stylesheets", "rules", "computed").
        selector: CSS selector for styles/computed actions.
        stylesheet_id: Stylesheet ID for rules action.

    Returns:
        CSS data as a dict or list of dicts depending on the action.
    """
    from browsix.actions.css import CSSAction, CSSActionParams

    params = CSSActionParams(
        url=url,
        action=action,
        selector=selector,
        stylesheet_id=stylesheet_id,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    act = CSSAction(params)
    return await act.execute(backend)


# ── Phase 7: Debug ───────────────────────────────────────────────


debug_app = typer.Typer(help="Debugging commands (breakpoint, step, pause, resume, listeners)")
app.add_typer(debug_app, name="debug")


@debug_app.command("breakpoint")
def debug_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    script_url: str = typer.Option(..., "--url", help="Script URL for breakpoint"),
    line: int = typer.Option(..., "--line", help="Line number (0-based)"),
    condition: str | None = typer.Option(None, "--condition", help="Condition expression"),
) -> None:
    """Set a breakpoint by URL and line number."""
    try:
        result = asyncio.run(
            _debug_action(url, "breakpoint", script_url=script_url, line=line, condition=condition)
        )
    except BrowsixError as e:
        _handle_error(e)
    _echo(f"Breakpoint set: {result}")


@debug_app.command("function-breakpoint")
def debug_function_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    function_name: str = typer.Option(..., "--function-name", help="Function name"),
) -> None:
    """Set a breakpoint by function name."""
    try:
        result = asyncio.run(
            _debug_action(url, "function_breakpoint", function_name=function_name)
        )
    except BrowsixError as e:
        _handle_error(e)
    _echo(f"Breakpoint set: {result}")


@debug_app.command("remove-breakpoint")
def debug_remove_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    breakpoint_id: str = typer.Option(..., "--breakpoint-id", help="Breakpoint ID"),
) -> None:
    """Remove a breakpoint by ID."""
    try:
        asyncio.run(_debug_action(url, "remove_breakpoint", breakpoint_id=breakpoint_id))
    except BrowsixError as e:
        _handle_error(e)
    _echo(f"Breakpoint removed: {breakpoint_id}")


@debug_app.command("step-over")
def debug_step_over(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Step over the current statement."""
    try:
        asyncio.run(_debug_action(url, "step_over"))
    except BrowsixError as e:
        _handle_error(e)
    _echo("Stepped over")


@debug_app.command("step-into")
def debug_step_into(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Step into the current function call."""
    try:
        asyncio.run(_debug_action(url, "step_into"))
    except BrowsixError as e:
        _handle_error(e)
    _echo("Stepped into")


@debug_app.command("step-out")
def debug_step_out(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Step out of the current function."""
    try:
        asyncio.run(_debug_action(url, "step_out"))
    except BrowsixError as e:
        _handle_error(e)
    _echo("Stepped out")


@debug_app.command("pause")
def debug_pause(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Pause JavaScript execution."""
    try:
        asyncio.run(_debug_action(url, "pause"))
    except BrowsixError as e:
        _handle_error(e)
    _echo("Paused")


@debug_app.command("resume")
def debug_resume(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Resume JavaScript execution."""
    try:
        asyncio.run(_debug_action(url, "resume"))
    except BrowsixError as e:
        _handle_error(e)
    _echo("Resumed")


@debug_app.command("listeners")
def debug_listeners(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get event listeners attached to an element."""
    try:
        result = asyncio.run(_debug_action(url, "listeners", selector=selector))
    except BrowsixError as e:
        _handle_error(e)
    _write_json_output(result, output, "listeners")


async def _debug_action(
    url: str,
    action: str,
    script_url: str | None = None,
    line: int | None = None,
    condition: str | None = None,
    function_name: str | None = None,
    breakpoint_id: str | None = None,
    selector: str | None = None,
) -> Any:
    """Execute a debug action on a web page.

    Args:
        url: URL to navigate to.
        action: Debug action ("breakpoint", "function_breakpoint", "remove_breakpoint",
            "step_over", "step_into", "step_out", "pause", "resume", "listeners").
        script_url: Script URL for breakpoint action.
        line: Line number for breakpoint action.
        condition: Condition expression for conditional breakpoints.
        function_name: Function name for function_breakpoint action.
        breakpoint_id: Breakpoint ID for remove_breakpoint action.
        selector: CSS selector for listeners action.

    Returns:
        Result of the debug operation.
    """
    from browsix.actions.debug import DebugAction, DebugActionParams

    params = DebugActionParams(
        url=url,
        action=action,
        script_url=script_url,
        line=line,
        condition=condition,
        function_name=function_name,
        breakpoint_id=breakpoint_id,
        selector=selector,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    act = DebugAction(params)
    return await act.execute(backend)


# ── Phase 7: DOM Snapshot ────────────────────────────────────────


@app.command("dom-snapshot")
def dom_snapshot(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Capture a DOM snapshot of a web page."""
    try:
        result = asyncio.run(_dom_snapshot_action(url))
    except BrowsixError as e:
        _handle_error(e)
    _write_json_output(result, output, "DOM snapshot")


async def _dom_snapshot_action(url: str) -> dict[str, Any]:
    """Capture a DOM snapshot of a web page.

    Args:
        url: URL to navigate to.

    Returns:
        DOM snapshot data as a dictionary.
    """
    from browsix.actions.dom_snapshot import DOMSnapshotAction, DOMSnapshotParams

    params = DOMSnapshotParams(
        url=url,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    act = DOMSnapshotAction(params)
    return await act.execute(backend)


# ── Phase 7: Overlay ─────────────────────────────────────────────


overlay_app = typer.Typer(help="Overlay commands (highlight, clear)")
app.add_typer(overlay_app, name="overlay")


@overlay_app.command("highlight")
def overlay_highlight(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector"),
    color: str = typer.Option("rgba(255,0,0,0.5)", "--color", help="RGBA color"),
) -> None:
    """Highlight an element with a colored overlay."""
    try:
        asyncio.run(_overlay_action(url, "highlight", selector=selector, color=color))
    except BrowsixError as e:
        _handle_error(e)
    _echo(f"Highlighted: {selector}")


@overlay_app.command("clear")
def overlay_clear(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Clear all highlight overlays."""
    try:
        asyncio.run(_overlay_action(url, "clear"))
    except BrowsixError as e:
        _handle_error(e)
    _echo("Overlay cleared")


async def _overlay_action(
    url: str,
    action: str,
    selector: str | None = None,
    color: str = "rgba(255,0,0,0.5)",
) -> None:
    """Execute an overlay action on a web page.

    Args:
        url: URL to navigate to.
        action: Overlay action ("highlight" or "clear").
        selector: CSS selector for highlight action.
        color: RGBA color for highlight overlay.
    """
    from browsix.actions.overlay import OverlayAction, OverlayParams

    params = OverlayParams(
        url=url,
        action=action,
        selector=selector,
        color=color,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    act = OverlayAction(params)
    await act.execute(backend)


# ── Phase 8 commands ─────────────────────────────────────────────


@app.command()
def storage(
    action: str = typer.Argument(
        ...,
        help="Storage action: get, set, clear, list, cache-list, "
             "cache-entries, cache-delete, indexeddb-list, indexeddb-get, indexeddb-clear",
    ),
    url: str = typer.Argument(..., help="URL to navigate to"),
    key: str = typer.Option("", "--key", help="Storage key"),
    value: str = typer.Option("", "--value", help="Storage value"),
    storage_type: str = typer.Option("local", "--type", help="Storage type: local or session"),
    cache_name: str = typer.Option("", "--cache-name", help="Cache storage name"),
    database: str = typer.Option("", "--database", help="IndexedDB database name"),
    store: str = typer.Option("", "--store", help="IndexedDB object store name"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Storage operations: DOM storage, Cache Storage, IndexedDB."""
    params = StorageParams(
        url=url,
        action=action,
        key=key or None,
        value=value or None,
        storage_type=storage_type,
        cache_name=cache_name or None,
        database=database or None,
        store=store or None,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    try:
        result = asyncio.run(StorageAction(params).execute(backend))
    except BrowsixError as e:
        _handle_error(e)
        return

    if result is None:
        _echo("OK")
    elif isinstance(result, str):
        if output == "-":
            typer.echo(result)
        else:
            with open(output, "w") as f:  # noqa: ASYNC230
                f.write(result)
            _echo(f"Saved to {output}")
    else:
        _write_json_output(result, output, "storage result")


@app.command()
def sw(
    action: str = typer.Argument(..., help="SW action: list, unregister, update"),
    url: str = typer.Argument(..., help="URL to navigate to"),
    registration_id: str = typer.Option("", "--id", help="Service worker registration ID"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Service worker operations: list, unregister, update."""
    params = ServiceWorkerParams(
        url=url,
        action=action,
        registration_id=registration_id or None,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    try:
        result = asyncio.run(ServiceWorkerAction(params).execute(backend))
    except BrowsixError as e:
        _handle_error(e)
        return

    if result is None:
        _echo("OK")
    else:
        _write_json_output(result, output, "service worker result")


@app.command()
def animation(
    action: str = typer.Argument(..., help="Animation action: list, pause, play, seek"),
    url: str = typer.Argument(..., help="URL to navigate to"),
    animation_id: str = typer.Option("", "--id", help="Animation ID"),
    time_ms: int = typer.Option(0, "--time", help="Seek time in milliseconds"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Animation operations: list, pause, play, seek."""
    params = AnimationParams(
        url=url,
        action=action,
        animation_id=animation_id or None,
        time_ms=time_ms if time_ms else None,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    try:
        result = asyncio.run(AnimationAction(params).execute(backend))
    except BrowsixError as e:
        _handle_error(e)
        return

    if result is None:
        _echo("OK")
    else:
        _write_json_output(result, output, "animation result")


@app.command()
def record(
    url: str = typer.Argument(..., help="URL to record"),
    output: str = typer.Option("session.yml", "-o", "--output", help="Output YAML file"),
    actions: str = typer.Option(
        "screenshot,eval",
        "--actions",
        help="Comma-separated action types to record "
             "(screenshot,eval,navigate,click,type,scrape,pdf,dom)",
    ),
    selector: str = typer.Option(
        "#button", "--selector", help="CSS selector for click/type actions",
    ),
    text: str = typer.Option("hello", "--text", help="Text for type action"),
    expression: str = typer.Option(
        "document.title", "--expression", help="JS expression for eval action",
    ),
) -> None:
    """Record a browsing session to YAML for later replay."""
    from pathlib import Path

    from browsix.record import record_to_yaml

    action_types = [a.strip() for a in actions.split(",") if a.strip()]
    action_list: list[dict[str, Any]] = []
    for at in action_types:
        if at == "screenshot":
            action_list.append({"screenshot": {"url": url, "output": "screenshot.png"}})
        elif at == "eval":
            action_list.append({"eval": {"url": url, "expression": expression}})
        elif at == "navigate":
            action_list.append({"navigate": {"url": url}})
        elif at == "click":
            action_list.append({"dom": {"url": url, "action": "get", "selector": selector}})
        elif at == "type":
            action_list.append({
                "eval": {
                    "url": url,
                    "expression": f"document.querySelector('{selector}').value='{text}'",
                },
            })
        elif at == "scrape":
            action_list.append({
                "scrape": {"url": url, "expression": expression},
            })
        elif at == "pdf":
            action_list.append({"pdf": {"url": url, "paper": "a4"}})
        elif at == "dom":
            action_list.append({"dom": {"url": url, "action": "get", "selector": "body"}})
        else:
            typer.echo(f"Unknown action type: {at}", err=True)
            raise typer.Exit(2)

    if not action_list:
        typer.echo("No actions to record", err=True)
        raise typer.Exit(2)

    record_to_yaml(action_list, Path(output))
    _echo(f"Recorded {len(action_list)} actions to {output}")


@app.command()
def replay(
    config: str = typer.Argument(..., help="Path to YAML config file"),
) -> None:
    """Replay a recorded session from YAML."""
    from pathlib import Path

    from browsix.record import replay_from_yaml

    config_path = Path(config)
    backend = _get_backend()
    try:
        asyncio.run(backend.launch(BrowserOptions(headless=True)))
        results = asyncio.run(replay_from_yaml(config_path, backend))
    except BrowsixError as e:
        _handle_error(e)
        return
    finally:
        asyncio.run(backend.close())

    _echo(f"Replayed {len(results)} actions")
    for i, result in enumerate(results):
        if isinstance(result, bytes):
            _echo(f"  Action {i + 1}: {len(result)} bytes")
        elif isinstance(result, str):
            _echo(f"  Action {i + 1}: {result[:100]}")
        else:
            _echo(f"  Action {i + 1}: {type(result).__name__}")


# ── Phase 9 commands (experimental) ───────────────────────


@app.command()
def webauthn(
    action: str = typer.Argument(
        ...,
        help="WebAuthn action: add-virtual-authenticator, "
             "remove-authenticator, add-credential, get-credentials",
    ),
    url: str = typer.Argument(..., help="URL to navigate to"),
    protocol: str = typer.Option("ctap2", "--protocol", help="Authenticator protocol"),
    transport: str = typer.Option("usb", "--transport", help="Transport type"),
    authenticator_id: str = typer.Option("", "--id", help="Authenticator ID"),
    credential: str = typer.Option("", "--credential", help="Credential JSON"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """WebAuthn virtual authenticator operations (experimental)."""
    import json as _json

    cred_dict: dict[str, Any] | None = None
    if credential:
        try:
            cred_dict = _json.loads(credential)
        except _json.JSONDecodeError as e:
            typer.echo(f"Invalid credential JSON: {e}", err=True)
            raise typer.Exit(2) from e

    params = WebAuthnParams(
        url=url,
        action=action,
        protocol=protocol,
        transport=transport,
        authenticator_id=authenticator_id or None,
        credential=cred_dict,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    try:
        result = asyncio.run(WebAuthnAction(params).execute(backend))
    except BrowsixError as e:
        _handle_error(e)
        return

    if result is None:
        _echo("OK")
    elif isinstance(result, str):
        typer.echo(result)
    else:
        _write_json_output(result, output, "webauthn result")


@app.command()
def webaudio(
    action: str = typer.Argument(
        ..., help="WebAudio action: list, get"
    ),
    url: str = typer.Argument(..., help="URL to navigate to"),
    context_id: str = typer.Option("", "--context-id", help="Audio context ID"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """WebAudio context operations (experimental)."""
    params = WebAudioParams(
        url=url,
        action=action,
        context_id=context_id or None,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    try:
        result = asyncio.run(WebAudioAction(params).execute(backend))
    except BrowsixError as e:
        _handle_error(e)
        return

    if result is None:
        _echo("OK")
    else:
        _write_json_output(result, output, "webaudio result")


@app.command()
def media(
    action: str = typer.Argument(
        ..., help="Media action: list, messages"
    ),
    url: str = typer.Argument(..., help="URL to navigate to"),
    player_id: str = typer.Option("", "--player-id", help="Media player ID"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Media player operations (experimental)."""
    params = MediaParams(
        url=url,
        action=action,
        player_id=player_id or None,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    try:
        result = asyncio.run(MediaAction(params).execute(backend))
    except BrowsixError as e:
        _handle_error(e)
        return

    if result is None:
        _echo("OK")
    else:
        _write_json_output(result, output, "media result")


@app.command()
def cast(
    action: str = typer.Argument(
        ..., help="Cast action: list, start-tab, stop"
    ),
    url: str = typer.Argument("", help="URL to navigate to (optional for list)"),
    sink_name: str = typer.Option("", "--sink-name", help="Cast sink name"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Cast mirroring operations (experimental)."""
    params = CastParams(
        url=url,
        action=action,
        sink_name=sink_name or None,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    try:
        result = asyncio.run(CastAction(params).execute(backend))
    except BrowsixError as e:
        _handle_error(e)
        return

    if result is None:
        _echo("OK")
    else:
        _write_json_output(result, output, "cast result")


@app.command()
def bluetooth(
    action: str = typer.Argument(
        ..., help="Bluetooth action: emulate, stop"
    ),
    url: str = typer.Argument(..., help="URL to navigate to"),
    name: str = typer.Option("", "--name", help="Device name"),
    address: str = typer.Option(
        "00:00:00:00:00:01", "--address", help="Device MAC address"
    ),
) -> None:
    """Bluetooth BLE emulation operations (experimental)."""
    params = BluetoothParams(
        url=url,
        action=action,
        name=name or None,
        address=address,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    try:
        asyncio.run(BluetoothAction(params).execute(backend))
    except BrowsixError as e:
        _handle_error(e)
        return
    _echo("OK")


@app.command()
def raw(
    method: str = typer.Argument(
        ..., help="Protocol method, e.g. 'Page.reload'"
    ),
    params: str = typer.Argument(
        "{}", help="JSON params for the command"
    ),
    backend_name: str = typer.Option(
        None, "--backend", help="Backend: cdp or bidi"
    ),
    output: str = typer.Option(
        None, "-o", "--output", help="Output file (- for stdout)"
    ),
) -> None:
    """Send raw protocol command to backend (escape hatch)."""
    import json as _json

    try:
        raw_params = _json.loads(params)
    except _json.JSONDecodeError as e:
        typer.echo(f"Invalid params JSON: {e}", err=True)
        raise typer.Exit(2) from e

    async def _raw() -> dict[str, Any]:
        """Execute a raw protocol command against a browser backend.

        Returns:
            Raw protocol response as a dictionary.
        """
        backend = _get_backend()
        if backend_name:
            manager = BackendManager()
            backend = manager.select(preferred=backend_name)
        try:
            await backend.launch(BrowserOptions(headless=True))
            result: dict[str, Any] = await backend.raw(method, raw_params)
            return result
        finally:
            await backend.close()

    try:
        result = asyncio.run(_raw())
    except BrowsixError as e:
        _handle_error(e)
        return

    out = output or "-"
    if out == "-":
        typer.echo(_json.dumps(result, indent=2, default=str))
    else:
        with open(out, "w") as f:  # noqa: ASYNC230
            _json.dump(result, f, indent=2, default=str)
        _echo(f"Saved raw result to {out}")


def _write_json_output(
    result: dict[str, Any] | list[dict[str, Any]], output: str, label: str
) -> None:
    """Write JSON result to file or stdout."""
    if output == "-":
        typer.echo(json.dumps(result, indent=2, default=str))
    else:
        with open(output, "w") as f:  # noqa: ASYNC230
            json.dump(result, f, indent=2, default=str)
        _echo(f"Saved {label} to {output}")


@app.command()
def auth(
    context: str = typer.Argument(..., help="Path to auth context JSON file"),
    url: str = typer.Argument(..., help="URL to navigate to with auth context"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
    screenshot: bool = typer.Option(
        False, "--screenshot", help="Take screenshot after applying auth",
    ),
) -> None:
    """Apply auth context (cookies, headers, basic auth) and navigate to a URL."""
    from browsix.auth import load_auth_context
    from browsix.config import CookieParams

    ctx = load_auth_context(context)

    async def _run_auth() -> Any:
        """Execute an authenticated browser session.

        Returns:
            Result of the authenticated action.
        """
        backend = _get_backend()
        await backend.launch(BrowserOptions(headless=True))
        try:
            if ctx.headers:
                await backend.set_headers(ctx.headers)
            if ctx.username and ctx.password:
                auth_header = {
                    "Authorization": f"Basic {_basic_auth(ctx.username, ctx.password)}"
                }
                await backend.set_headers(auth_header)
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
            if screenshot:
                return await backend.screenshot(
                    ScreenshotParams(
                        url=url, wait=WaitStrategy(strategy="load"),
                    ),
                )
            return await backend.eval(
                EvalParams(
                    url=url,
                    expression="document.title",
                    wait=WaitStrategy(strategy="load"),
                ),
            )
        finally:
            await backend.close()

    try:
        result = asyncio.run(_run_auth())
    except BrowsixError as e:
        _handle_error(e)
        return

    if isinstance(result, bytes):
        out = output or "auth_result.png"
        with open(out, "wb") as f:  # noqa: ASYNC230
            f.write(result)
        _echo(f"Screenshot saved to {out}")
    elif isinstance(result, str):
        typer.echo(result)
    else:
        _write_json_output(result, output, "auth result")


def _basic_auth(username: str, password: str) -> str:
    """Encode basic auth credentials as base64."""
    import base64
    return base64.b64encode(f"{username}:{password}".encode()).decode()


if __name__ == "__main__":
    app()
