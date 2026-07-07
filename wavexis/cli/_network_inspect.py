"""Network inspection, tracing, axe audit, and event subscription commands."""

from __future__ import annotations

__all__ = ["axe", "events", "har_replay", "inspect", "modify", "modify_response", "trace"]

import json
from typing import Any

import typer

from wavexis.cli._shared import (
    _browser_options,
    _get_backend,
    _run_async,
    app,
)
from wavexis.config import WaitStrategy


@app.command()
def inspect(
    url: str = typer.Argument(..., help="URL to navigate to"),
    request_id: str = typer.Option(
        "", "--request-id", "-r", help="Network request ID to inspect"
    ),
    body_type: str = typer.Option(
        "response",
        "--type",
        "-t",
        help="Body type: request or response",
    ),
) -> None:
    """Inspect request/response bodies by network request ID.

    \b
    wavexis inspect https://example.com -r <request_id> -t response
    wavexis inspect https://example.com -r <request_id> -t request
    """
    result = _run_async(_inspect(url, request_id, body_type))
    if result is None:
        typer.echo("No body found")
    else:
        typer.echo(result)


async def _inspect(url: str, request_id: str, body_type: str) -> str | None:
    """Async helper for request/response body inspection."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        if body_type == "request":
            result: str | None = await backend.get_request_body(request_id)
        else:
            result = await backend.get_response_body(request_id)
        return result
    finally:
        await backend.close()


@app.command()
def modify(
    url: str = typer.Argument(..., help="URL to navigate to"),
    pattern: str = typer.Option(
        ...,
        "--pattern",
        "-p",
        help='URL pattern to match (e.g. "*/api/*")',
    ),
    header: str = typer.Option(
        "",
        "--header",
        "-h",
        help='Header to add/modify (e.g. "X-Custom: value")',
    ),
    method: str = typer.Option(
        "", "--method", "-m", help="Override HTTP method"
    ),
    post_data: str = typer.Option(
        "", "--post-data", "-d", help="Override request body (POST data)"
    ),
    wait: float = typer.Option(
        5.0, "--wait", "-w", help="Seconds to keep interception active (0 = no wait)"
    ),
) -> None:
    """Intercept and modify network requests matching a pattern.

    \b
    wavexis modify https://example.com -p "*/api/*" -h "X-Custom: value"
    wavexis modify https://example.com -p "*/api/*" -m POST -d '{"key":"val"}'
    """
    modifications: dict[str, Any] = {}
    if header:
        key, _, val = header.partition(":")
        modifications["headers"] = [{key.strip(): val.strip()}]
    if method:
        modifications["method"] = method
    if post_data:
        modifications["post_data"] = post_data

    _run_async(_modify(url, pattern, modifications, wait))
    typer.echo(f"Request interception active for pattern: {pattern}")


async def _modify(
    url: str, pattern: str, modifications: dict[str, Any], wait: float = 5.0
) -> None:
    """Async helper for request modification.

    Args:
        url: URL to navigate to.
        pattern: URL pattern to intercept.
        modifications: Dict with optional keys: headers, url, method, post_data.
        wait: Seconds to keep interception active after navigation.
    """
    import asyncio

    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.modify_request(
            {"urlPattern": pattern}, modifications
        )
        await backend.navigate(url, WaitStrategy(strategy="load"))
        if wait > 0:
            await asyncio.sleep(wait)
    finally:
        await backend.close()


@app.command()
def modify_response(
    url: str = typer.Argument(..., help="URL to navigate to"),
    pattern: str = typer.Option(
        ...,
        "--pattern",
        "-p",
        help='URL pattern to match (e.g. "*/api/*")',
    ),
    body: str = typer.Option(
        "", "--body", "-b", help="Replacement response body (string or JSON)"
    ),
    status: int = typer.Option(
        200, "--status", "-s", help="Override HTTP status code"
    ),
    content_type: str = typer.Option(
        "application/json", "--content-type", "-c", help="Content-Type header"
    ),
    wait: float = typer.Option(
        5.0, "--wait", "-w", help="Seconds to keep interception active (0 = no wait)"
    ),
) -> None:
    """Intercept and modify network responses matching a pattern.

    \b
    wavexis modify-response https://example.com -p "*/api/*" -b '{"modified":true}'
    wavexis modify-response https://example.com -p "*/api/*" -s 404
    """
    modifications: dict[str, Any] = {
        "status": status,
        "content_type": content_type,
    }
    if body:
        modifications["body"] = body

    _run_async(_modify_response(url, pattern, modifications, wait))
    typer.echo(f"Response interception active for pattern: {pattern}")


async def _modify_response(
    url: str, pattern: str, modifications: dict[str, Any], wait: float = 5.0
) -> None:
    """Async helper for response modification.

    Args:
        url: URL to navigate to.
        pattern: URL pattern to intercept.
        modifications: Dict with optional keys: status, headers, body.
        wait: Seconds to keep interception active after navigation.
    """
    import asyncio

    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.modify_response(
            {"urlPattern": pattern}, modifications
        )
        await backend.navigate(url, WaitStrategy(strategy="load"))
        if wait > 0:
            await asyncio.sleep(wait)
    finally:
        await backend.close()


@app.command()
def har_replay(
    har_path: str = typer.Argument(..., help="Path to HAR file"),
    url: str = typer.Option(
        "", "--url", "-u", help="Optional URL to navigate to first"
    ),
    filter: str = typer.Option(
        "", "--filter", "-f", help="URL filter pattern to select entries"
    ),
) -> None:
    """Replay network requests from a HAR file.

    \b
    wavexis har-replay traffic.har
    wavexis har-replay traffic.har -u https://example.com -f "api"
    """
    _run_async(_har_replay(har_path, url, filter))
    typer.echo(f"Replayed HAR: {har_path}")


async def _har_replay(har_path: str, url: str, url_filter: str) -> None:
    """Async helper for HAR replay."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        if url:
            await backend.navigate(url, WaitStrategy(strategy="load"))
        await backend.replay_har(har_path, url_filter)
    finally:
        await backend.close()


@app.command()
def trace(
    action: str = typer.Argument(
        ..., help="Trace action: start or stop"
    ),
    url: str = typer.Argument(
        "", help="URL to navigate to (for start)"
    ),
    trace_id: str = typer.Option(
        "", "--trace-id", "-t", help="Trace ID (for stop)"
    ),
    no_screenshots: bool = typer.Option(
        False, "--no-screenshots", help="Disable screenshot capture"
    ),
    no_network: bool = typer.Option(
        False, "--no-network", help="Disable network capture"
    ),
    no_console: bool = typer.Option(
        False, "--no-console", help="Disable console capture"
    ),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path (for stop)"
    ),
) -> None:
    """Combined tracing: screenshots + network + console + trace events.

    \b
    wavexis trace start https://example.com
    wavexis trace stop --trace-id trace-1234567890 -o trace.json
    """
    if action == "start":
        trace_id_result = _run_async(
            _trace_start(
                url,
                not no_screenshots,
                not no_network,
                not no_console,
            )
        )
        typer.echo(f"Trace started: {trace_id_result}")

    elif action == "stop":
        if not trace_id:
            typer.echo("Error: --trace-id required for stop", err=True)
            raise typer.Exit(1)
        result = _run_async(_trace_stop(trace_id))
        if output:
            from wavexis.output import Output

            Output.write_json(result, output)
            typer.echo(f"Trace saved to {output}")
        else:
            typer.echo(json.dumps(result, indent=2, default=str))

    else:
        typer.echo(
            f"Error: unknown trace action '{action}'. Use start or stop.",
            err=True,
        )
        raise typer.Exit(1)


async def _trace_start(
    url: str,
    screenshots: bool,
    network: bool,
    console: bool,
) -> str:
    """Async helper for starting a combined trace."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        trace_id: str = await backend.start_combined_trace(
            capture_screenshots=screenshots,
            capture_network=network,
            capture_console=console,
        )
        return trace_id
    finally:
        await backend.close()


async def _trace_stop(trace_id: str) -> dict[str, Any]:
    """Async helper for stopping a combined trace."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        result: dict[str, Any] = await backend.stop_combined_trace(trace_id)
        return result
    finally:
        await backend.close()


@app.command()
def axe(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path (.json)"
    ),
) -> None:
    """Run axe-core accessibility audit on a page.

    \b
    wavexis axe https://example.com
    wavexis axe https://example.com -o audit.json
    """
    result = _run_async(_axe(url))
    if output:
        from wavexis.output import Output

        Output.write_json(result, output)
        typer.echo(f"Audit saved to {output}")
    else:
        typer.echo(json.dumps(result, indent=2, default=str))


async def _axe(url: str) -> dict[str, Any]:
    """Async helper for axe-core audit."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        result: dict[str, Any] = await backend.axe_audit()
        return result
    finally:
        await backend.close()


@app.command()
def events(
    action: str = typer.Argument(
        ..., help="Events action: subscribe or unsubscribe"
    ),
    url: str = typer.Argument(
        "", help="URL to navigate to (for subscribe)"
    ),
    types: str = typer.Option(
        "console,network_request,network_response",
        "--types",
        "-t",
        help="Comma-separated event types",
    ),
    duration: int = typer.Option(
        10, "--duration", "-d", help="Duration in seconds (for subscribe)"
    ),
) -> None:
    """Subscribe to real-time browser events.

    \b
    wavexis events subscribe https://example.com -t "console,network_request" -d 5
    """
    if action == "subscribe":
        event_types = [t.strip() for t in types.split(",") if t.strip()]
        _run_async(_events_subscribe(url, event_types, duration))
    else:
        typer.echo(
            f"Error: unknown events action '{action}'. Use subscribe.",
            err=True,
        )
        raise typer.Exit(1)


async def _events_subscribe(
    url: str, event_types: list[str], duration: int
) -> None:
    """Async helper for event subscription."""
    import asyncio

    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))

        def on_event(event: dict[str, Any]) -> None:
            typer.echo(json.dumps(event, default=str))

        sub_id: str = await backend.subscribe_events(event_types, on_event)
        typer.echo(f"Subscribed: {sub_id}")
        await asyncio.sleep(duration)
        await backend.unsubscribe_events(sub_id)
        typer.echo("Unsubscribed")
    finally:
        await backend.close()
