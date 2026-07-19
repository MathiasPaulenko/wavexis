"""Shadow DOM commands for wavexis CLI."""

from __future__ import annotations

__all__ = ["shadow"]

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
def shadow(
    action: str = typer.Argument(..., help="Shadow DOM action: click, fill, eval"),
    url: str = typer.Argument(..., help="URL to navigate to"),
    selectors: str = typer.Option(
        ...,
        "--selectors",
        "-s",
        help=(
            "Comma-separated CSS selectors piercing shadow boundaries (e.g. 'my-component,button')"
        ),
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
    """Interact with elements inside Shadow DOM on a web page.

    \b
    Click:  wavexis shadow click https://example.com -s 'my-component,button'
    Fill:   wavexis shadow fill https://example.com -s 'my-component,input' -v "hello"
    Eval:   wavexis shadow eval https://example.com -s 'my-component,span' -e "this.textContent"
    """
    selector_list = [s.strip() for s in selectors.split(",") if s.strip()]
    if not selector_list:
        typer.echo("Error: at least one selector required", err=True)
        raise typer.Exit(1)

    if action == "click":
        _run_async(_shadow_click(url, selector_list, not no_wait))
        typer.echo(f"Clicked {' -> '.join(selector_list)}")

    elif action == "fill":
        _run_async(_shadow_fill(url, selector_list, value, not no_wait))
        typer.echo(f"Filled {' -> '.join(selector_list)} with '{value}'")

    elif action == "eval":
        if not expression:
            typer.echo("Error: --expression required for eval", err=True)
            raise typer.Exit(1)
        result = _run_async(_shadow_eval(url, selector_list, expression, await_promise))
        if result is None:
            return
        Output.write_formatted(result, format, output)
        if output:
            typer.echo(f"Result saved to {output}")

    else:
        typer.echo(
            f"Error: unknown shadow action '{action}'. Use click, fill, or eval.",
            err=True,
        )
        raise typer.Exit(1)


async def _shadow_click(url: str, selectors: list[str], auto_wait: bool) -> None:
    """Async helper for shadow click."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        await backend.shadow_click(selectors, auto_wait=auto_wait)
    finally:
        await _close_backend(backend)


async def _shadow_fill(
    url: str,
    selectors: list[str],
    value: str,
    auto_wait: bool,
) -> None:
    """Async helper for shadow fill."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        await backend.shadow_fill(selectors, value, auto_wait=auto_wait)
    finally:
        await _close_backend(backend)


async def _shadow_eval(url: str, selectors: list[str], expression: str, await_promise: bool) -> Any:
    """Async helper for shadow eval."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        return await backend.shadow_eval(selectors, expression, await_promise)
    finally:
        await _close_backend(backend)
