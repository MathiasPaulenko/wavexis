"""iframe commands for wavexis CLI."""

from __future__ import annotations

__all__ = ["iframe"]

from typing import Any

import typer

from wavexis.cli._shared import (
    Output,
    _browser_options,
    _close_backend,
    _get_backend,
    _run_async,
    app,
)
from wavexis.config import WaitStrategy


@app.command()
def iframe(
    action: str = typer.Argument(..., help="iframe action: click, fill, eval"),
    url: str = typer.Argument(..., help="URL to navigate to"),
    iframe_selector: str = typer.Option(
        ..., "--iframe", help="CSS selector for the <iframe> element"
    ),
    selector: str = typer.Option(
        "", "--selector", "-s", help="CSS selector inside the iframe (for click/fill)"
    ),
    value: str = typer.Option("", "--value", "-v", help="Value to fill (for fill)"),
    expression: str = typer.Option(
        "", "--expression", "-e", help="JavaScript expression (for eval)"
    ),
    await_promise: bool = typer.Option(
        False, "--await-promise", help="Await a returned Promise (for eval)"
    ),
    no_wait: bool = typer.Option(
        False, "--no-wait", help="Skip auto-waiting for element visibility"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (for eval)"),
    format: str = typer.Option(
        "json", "--format", "-f", help="Output format: json, csv, yaml (for eval)"
    ),
) -> None:
    """Interact with elements inside an iframe on a web page.

    \b
    Click:  wavexis iframe click https://example.com --iframe #ad --selector #btn
    Fill:   wavexis iframe fill https://example.com --iframe #ad --selector #input --value "hello"
    Eval:   wavexis iframe eval https://example.com --iframe #ad --expression "document.title"
    """
    if action == "click":
        if not selector:
            typer.echo("Error: --selector required for click", err=True)
            raise typer.Exit(1)
        _run_async(_iframe_click(url, iframe_selector, selector, not no_wait))
        typer.echo(f"Clicked {selector} inside {iframe_selector}")

    elif action == "fill":
        if not selector:
            typer.echo("Error: --selector required for fill", err=True)
            raise typer.Exit(1)
        _run_async(_iframe_fill(url, iframe_selector, selector, value, not no_wait))
        typer.echo(f"Filled {selector} with '{value}' inside {iframe_selector}")

    elif action == "eval":
        if not expression:
            typer.echo("Error: --expression required for eval", err=True)
            raise typer.Exit(1)
        result = _run_async(_iframe_eval(url, iframe_selector, expression, await_promise))
        if result is None:
            return
        Output.write_formatted(result, format, output)
        if output:
            typer.echo(f"Result saved to {output}")

    else:
        typer.echo(
            f"Error: unknown iframe action '{action}'. Use click, fill, or eval.",
            err=True,
        )
        raise typer.Exit(1)


async def _iframe_click(url: str, iframe_selector: str, selector: str, auto_wait: bool) -> None:
    """Async helper for iframe click."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        await backend.iframe_click(iframe_selector, selector, auto_wait=auto_wait)
    finally:
        await _close_backend(backend)


async def _iframe_fill(
    url: str,
    iframe_selector: str,
    selector: str,
    value: str,
    auto_wait: bool,
) -> None:
    """Async helper for iframe fill."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        await backend.iframe_fill(iframe_selector, selector, value, auto_wait=auto_wait)
    finally:
        await _close_backend(backend)


async def _iframe_eval(url: str, iframe_selector: str, expression: str, await_promise: bool) -> Any:
    """Async helper for iframe eval."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        return await backend.iframe_eval(iframe_selector, expression, await_promise)
    finally:
        await _close_backend(backend)
