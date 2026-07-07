"""serve, websocket, plugins, and backend management commands for wavexis CLI."""

from __future__ import annotations

import json
from typing import Any

import typer

from wavexis.cli._shared import (
    Output,
    WavexisError,
    _get_backend,
    _get_ctx,
    _handle_error,
    _run_async,
    app,
    get_manager,
)
from wavexis.config import WaitStrategy


@app.command()
def backends() -> None:
    """List available backends."""
    manager = get_manager()
    available = manager.list_available()
    if not available:
        typer.echo("No backends available. Install cdpwave or bidiwave.")
        return
    for name in available:
        typer.echo(f"  {name}")


@app.command()
def install_check() -> None:
    """Check which backends are installed and their versions."""
    manager = get_manager()
    status = manager.install_check()
    for name, version in status.items():
        typer.echo(f"  {name}: {version}")


@app.command()
def serve(
    port: int = typer.Option(8080, "--port", "-p", help="Port to listen on"),
    host: str = typer.Option("localhost", "--host", help="Host to bind to"),
    backend: str = typer.Option(
        None, "--backend", help="Preferred backend (cdp or bidi)"
    ),
    rate_limit: int = typer.Option(
        0, "--rate-limit", help="Max requests per minute (0 = no limit)"
    ),
) -> None:
    """Start the wavexis HTTP server."""
    from wavexis.serve import serve as _serve

    try:
        _serve(
            port=port,
            host=host,
            backend=backend or _get_ctx().preferred_backend,
            rate_limit=rate_limit or None,
        )
    except WavexisError as e:
        _handle_error(e)


@app.command()
def plugins() -> None:
    """List discovered plugins (actions, backends, middleware)."""
    from wavexis.plugins import get_registry

    registry = get_registry()
    actions = registry.list_actions()
    backends = registry.list_backends()
    middleware = registry.list_middleware()

    if not actions and not backends and not middleware:
        typer.echo("No plugins discovered.")
        typer.echo(
            "\nInstall a plugin package with entry point group "
            "'wavexis.plugins' to extend wavexis."
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
def ws(
    url: str = typer.Argument(..., help="URL to navigate to"),
    duration: int = typer.Option(
        5000, "--duration", help="How long to capture WS frames (ms)"
    ),
    pattern: str = typer.Option(
        "", "--pattern", help="Regex pattern to filter WS URLs (empty = all)"
    ),
    mock: str = typer.Option(
        "", "--mock",
        help='JSON mapping request payloads to mock response payloads'
    ),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path (.json)"
    ),
    format: str = typer.Option("json", "--format", "-f", help="Output format (json)"),
) -> None:
    """Intercept WebSocket frames on a page. Capture sent/received or mock responses.

    \b
    Examples:
        wavexis ws https://app.com --duration 10000
        wavexis ws https://app.com --pattern '.*api.*' -o frames.json
        wavexis ws https://app.com --mock '{"ping":"pong"}' --duration 5000
    """
    from wavexis.actions.websocket import WebSocketInterceptAction, WebSocketParams

    mock_dict: dict[str, str] = {}
    if mock:
        try:
            mock_dict = json.loads(mock)
        except json.JSONDecodeError as e:
            typer.echo(f"Error: invalid JSON mock: {e}", err=True)
            raise typer.Exit(1) from e

    async def _ws() -> dict[str, Any]:
        backend = _get_backend()
        params = WebSocketParams(
            url=url,
            url_pattern=pattern,
            duration_ms=duration,
            mock_responses=mock_dict,
            wait=WaitStrategy(strategy="load"),
        )
        action = WebSocketInterceptAction(params)
        return await action.execute(backend)

    result = _run_async(_ws())
    if result is None:
        return

    Output.write_formatted(result, format, output)
    sent = len(result.get("sent", []))
    received = len(result.get("received", []))
    typer.echo(f"WS intercept: {sent} sent, {received} received frames")
