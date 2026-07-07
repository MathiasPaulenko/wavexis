"""Natural language selector commands for wavexis CLI."""

from __future__ import annotations

__all__ = ["nl"]

import typer

from wavexis.cli._shared import (
    _browser_options,
    _get_backend,
    _run_async,
    app,
)
from wavexis.config import WaitStrategy


@app.command()
def nl(
    action: str = typer.Argument(
        ..., help="Natural language action: click, fill, find"
    ),
    url: str = typer.Argument(..., help="URL to navigate to"),
    query: str = typer.Argument(
        ..., help='Natural language query (e.g. "the login button")'
    ),
    value: str = typer.Option(
        "", "--value", "-v", help="Value to fill (for fill)"
    ),
    no_wait: bool = typer.Option(
        False, "--no-wait", help="Skip auto-waiting for element visibility"
    ),
    all: bool = typer.Option(
        False, "--all", help="Return all matches (for find)"
    ),
) -> None:
    """Interact with elements using natural language text queries.

    \b
    Click:  wavexis nl click https://example.com "the login button"
    Fill:   wavexis nl fill https://example.com "email field" -v "user@example.com"
    Find:   wavexis nl find https://example.com "submit button" --all
    """
    if action == "click":
        _run_async(_nl_click(url, query, not no_wait))
        typer.echo(f"Clicked element matching '{query}'")

    elif action == "fill":
        _run_async(_nl_fill(url, query, value, not no_wait))
        typer.echo(f"Filled element matching '{query}' with '{value}'")

    elif action == "find":
        result = _run_async(_nl_find(url, query, all))
        if isinstance(result, list):
            for sel in result:
                typer.echo(sel)
        else:
            typer.echo(result)

    else:
        typer.echo(
            f"Error: unknown nl action '{action}'. "
            "Use click, fill, or find.",
            err=True,
        )
        raise typer.Exit(1)


async def _nl_click(url: str, query: str, auto_wait: bool) -> None:
    """Async helper for natural language click."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        await backend.nl_click(query, auto_wait=auto_wait)
    finally:
        await backend.close()


async def _nl_fill(
    url: str, query: str, value: str, auto_wait: bool
) -> None:
    """Async helper for natural language fill."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        await backend.nl_fill(query, value, auto_wait=auto_wait)
    finally:
        await backend.close()


async def _nl_find(url: str, query: str, all: bool) -> list[str] | str:
    """Async helper for natural language find."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        result: list[str] | str = await backend.find_by_text(query, all=all)
        return result
    finally:
        await backend.close()
