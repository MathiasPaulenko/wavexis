"""network commands for wavexis CLI."""

from __future__ import annotations

import json
from typing import Annotated, Any

import typer

from wavexis.actions.browser import BrowserAction
from wavexis.cli._shared import (
    Output,
    _browser_options,
    _close_backend,
    _echo,
    _get_backend,
    _run_async,
    _write_json_output,
    app,
)
from wavexis.config import CookieParams, ThrottleParams, WaitStrategy

network_app = typer.Typer(help="Network commands (block, throttle, cache, intercept, mock)")
app.add_typer(network_app, name="network")


@app.command()
def cookies(
    action: str = typer.Argument("get", help="Cookie action: get, set, delete, clear"),
    url: str = typer.Option("", "--url", help="URL for cookie context"),
    name: str = typer.Option("", "--name", help="Cookie name"),
    value: str = typer.Option("", "--value", help="Cookie value"),
    domain: str = typer.Option("", "--domain", help="Cookie domain"),
    path: str = typer.Option("/", "--path", help="Cookie path"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Manage browser cookies (get, set, delete, clear)."""
    result = _run_async(_cookies(action, url, name, value, domain, path))
    if result is None:
        return

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
        await backend.launch(_browser_options())
        if url:
            await backend.navigate(url, WaitStrategy(strategy="load"))

        if action == "get":
            return await backend.get_cookies()
        if action == "set":
            cookie = CookieParams(name=name, value=value, domain=domain, path=path)
            await backend.set_cookie(cookie)
        elif action == "delete":
            await backend.delete_cookie(name, domain)
        elif action == "clear":
            await backend.clear_cookies()
        return None
    finally:
        await _close_backend(backend)


@app.command()
def headers(
    headers_json: str = typer.Argument(
        ..., help="JSON dict of headers, or @path to read from file"
    ),
) -> None:
    """Set extra HTTP headers for all requests."""
    try:
        if headers_json.startswith("@"):
            from pathlib import Path

            data = json.loads(Path(headers_json[1:]).read_text(encoding="utf-8"))
        else:
            data = json.loads(headers_json)
    except json.JSONDecodeError as e:
        typer.echo(f"Error: invalid JSON headers: {e}", err=True)
        raise typer.Exit(1) from e

    _run_async(_headers(data))
    typer.echo("Headers set")


async def _headers(headers: dict[str, str]) -> None:
    """Async helper for setting headers."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.set_headers(headers)
    finally:
        await _close_backend(backend)


@app.command()
def user_agent(
    ua: str = typer.Argument(..., help="User-Agent string to set"),
) -> None:
    """Override the browser's User-Agent string."""
    _run_async(_user_agent(ua))
    typer.echo("User-Agent set")


async def _user_agent(ua: str) -> None:
    """Async helper for setting user agent."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.set_user_agent(ua)
    finally:
        await _close_backend(backend)


@app.command()
def browser(
    action: str = typer.Argument(
        "version", help="Browser action: version, new_context, list_contexts"
    ),
) -> None:
    """Browser management commands (version, contexts)."""
    result = _run_async(_browser(action))
    if result is None:
        return

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
        await backend.launch(_browser_options())
        return await BrowserAction(action).execute(backend)
    finally:
        await _close_backend(backend)


@network_app.command("block")
def network_block(
    patterns: Annotated[list[str], typer.Argument(help="URL patterns to block (glob-style)")],
) -> None:
    """Block requests matching URL patterns."""
    _run_async(_network_block(patterns))
    typer.echo(f"Blocked {len(patterns)} URL pattern(s)")


async def _network_block(patterns: list[str]) -> None:
    """Block network requests matching the given patterns.

    Args:
        patterns: List of URL patterns to block.
    """
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.block_requests(patterns)
    finally:
        await _close_backend(backend)


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
    _run_async(_network_throttle(params))
    typer.echo("Network throttling set")


async def _network_throttle(params: ThrottleParams) -> None:
    """Apply network throttling conditions.

    Args:
        params: Throttle parameters with offline, latency, and bandwidth settings.
    """
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.throttle_network(params)
    finally:
        await _close_backend(backend)


@network_app.command("cache")
def network_cache(
    disabled: bool = typer.Option(True, "--disabled/--enabled", help="Disable or enable cache"),
) -> None:
    """Disable or enable the browser cache."""
    _run_async(_network_cache(disabled))
    typer.echo(f"Cache {'disabled' if disabled else 'enabled'}")


async def _network_cache(disabled: bool) -> None:
    """Enable or disable the browser cache.

    Args:
        disabled: True to disable cache, False to enable.
    """
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.set_cache_disabled(disabled)
    finally:
        await _close_backend(backend)


@network_app.command("intercept")
def network_intercept(
    url_pattern: str = typer.Argument(..., help="URL pattern to intercept"),
    resource_type: str = typer.Option("", "--resource-type", help="Resource type filter"),
) -> None:
    """Intercept requests matching a URL pattern."""
    pattern: dict[str, Any] = {"urlPattern": url_pattern}
    if resource_type:
        pattern["resourceType"] = resource_type
    _run_async(_network_intercept(pattern))
    typer.echo(f"Intercepting requests matching '{url_pattern}'")


async def _network_intercept(pattern: dict[str, Any]) -> None:
    """Intercept network requests matching a pattern.

    Args:
        pattern: Fetch.enable pattern dict with urlPattern and optional resourceType.
    """
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.intercept_requests(pattern)
    finally:
        await _close_backend(backend)


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
    _run_async(_network_mock(url, response))
    typer.echo(f"Mocking responses for '{url}'")


async def _network_mock(url: str, response: dict[str, Any]) -> None:
    """Mock a response for requests matching a URL pattern.

    Args:
        url: URL pattern to mock.
        response: Response dict with status, body, and content_type.
    """
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.mock_response(url, response)
    finally:
        await _close_backend(backend)


@network_app.command("auth")
def network_auth(
    url_pattern: str = typer.Argument(..., help="URL pattern to match auth challenges"),
    username: str | None = typer.Option(None, "--username", "-u", help="Username to provide"),
    password: str | None = typer.Option(None, "--password", "-p", help="Password to provide"),
    navigate_url: str | None = typer.Option(
        None, "--navigate", help="URL to navigate after setting auth handler"
    ),
    wait: str = typer.Option("load", "--wait", help="Wait strategy for navigation"),
) -> None:
    """Handle HTTP authentication challenges for matching URLs."""
    _run_async(_network_auth(url_pattern, username, password, navigate_url, wait))
    typer.echo(f"Auth handler set for '{url_pattern}'")


async def _network_auth(
    url_pattern: str,
    username: str | None,
    password: str | None,
    navigate_url: str | None,
    wait: str,
) -> None:
    """Set up HTTP authentication handling.

    Args:
        url_pattern: URL pattern to match auth challenges.
        username: Username to provide. If None, auth is canceled.
        password: Password to provide.
        navigate_url: Optional URL to navigate after setting auth handler.
        wait: Wait strategy for navigation.
    """
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.handle_auth(url_pattern, username, password)
        if navigate_url:
            await backend.navigate(navigate_url, WaitStrategy(strategy=wait))
    finally:
        await _close_backend(backend)


@network_app.command("clear-cache")
def network_clear_cache() -> None:
    """Clear the browser cache."""
    _run_async(_network_direct(lambda b: b.network_clear_browser_cache()))
    _echo("Browser cache cleared")


@network_app.command("clear-cookies")
def network_clear_cookies() -> None:
    """Clear all browser cookies."""
    _run_async(_network_direct(lambda b: b.network_clear_browser_cookies()))
    _echo("Browser cookies cleared")


@network_app.command("delete-cookies")
def network_delete_cookies(
    name: str = typer.Argument(..., help="Cookie name to delete"),
    domain: str = typer.Option("", "--domain", help="Cookie domain (optional)"),
) -> None:
    """Delete cookies by name and optional domain."""
    _run_async(_network_direct(lambda b: b.network_delete_cookies(name, domain)))
    _echo(f"Deleted cookies named '{name}'")


@network_app.command("block-urls")
def network_block_urls(
    urls: list[str] = typer.Argument(..., help="URLs to block"),
) -> None:
    """Block requests to specific URLs."""
    _run_async(_network_direct(lambda b: b.network_set_blocked_urls(urls)))
    _echo(f"Blocked {len(urls)} URL(s)")


@network_app.command("bypass-sw")
def network_bypass_sw(
    bypass: bool = typer.Option(True, "--bypass/--no-bypass", help="Bypass service worker"),
) -> None:
    """Bypass the service worker for all network requests."""
    _run_async(_network_direct(lambda b: b.network_set_bypass_service_worker(bypass)))
    _echo(f"Service worker {'bypassed' if bypass else 'enabled'}")


@network_app.command("cookie-controls")
def network_cookie_controls(
    mode: str = typer.Option("allow", "--mode", help="Cookie mode: allow, block, only-existing"),
    third_party_mode: str = typer.Option("allow", "--third-party", help="Third-party cookie mode"),
) -> None:
    """Set cookie controls."""
    _run_async(_network_direct(lambda b: b.network_set_cookie_controls(mode, third_party_mode)))
    _echo(f"Cookie controls set: {mode}, third-party: {third_party_mode}")


@network_app.command("extra-headers")
def network_extra_headers(
    headers_json: str = typer.Argument(
        ..., help="JSON dict of headers, or @path to read from file"
    ),
) -> None:
    """Set extra HTTP headers for all requests."""
    try:
        if headers_json.startswith("@"):
            from pathlib import Path

            headers = json.loads(Path(headers_json[1:]).read_text(encoding="utf-8"))
        else:
            headers = json.loads(headers_json)
    except json.JSONDecodeError as e:
        typer.echo(f"Error: invalid JSON headers: {e}", err=True)
        raise typer.Exit(1) from e
    _run_async(_network_direct(lambda b: b.network_set_extra_request_headers(headers)))
    _echo(f"Extra headers set: {len(headers)} header(s)")


@network_app.command("ua-override")
def network_ua_override(
    user_agent: str = typer.Argument(..., help="User-Agent string"),
    accept_language: str = typer.Option("", "--accept-language", help="Accept-Language header"),
    platform: str = typer.Option("", "--platform", help="Platform string"),
) -> None:
    """Override the User-Agent string with metadata."""
    _run_async(
        _network_direct(
            lambda b: b.network_set_user_agent_override(user_agent, accept_language, platform)
        )
    )
    _echo("User-Agent override set")


@network_app.command("replay-xhr")
def network_replay_xhr(
    request_id: str = typer.Argument(..., help="Request ID to replay"),
) -> None:
    """Replay a previously captured XHR request by ID."""
    _run_async(_network_direct(lambda b: b.network_replay_xhr(request_id)))
    _echo(f"Replayed XHR: {request_id}")


@network_app.command("load-resource")
def network_load_resource(
    frame_id: str = typer.Option(..., "--frame-id", help="Frame ID"),
    url: str = typer.Argument(..., help="URL to load"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Load a network resource outside the context of a page."""
    result = _run_async(_network_direct(lambda b: b.network_load_network_resource(frame_id, url)))
    if result is None:
        return
    _write_json_output(result, output, "resource")


async def _network_direct(action_fn: Any) -> Any:
    """Launch backend and run a direct network action."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        return await action_fn(backend)
    finally:
        await _close_backend(backend)
