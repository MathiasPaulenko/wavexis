"""session, extract, and form commands for wavexis CLI."""

from __future__ import annotations

import json
import time
from pathlib import Path
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
def session(
    action: str = typer.Argument(..., help="Session action: save, load, list, delete"),
    url: str = typer.Argument(
        "", help="URL to navigate to (for save) or load before navigating (for load)"
    ),
    output: str = typer.Option("session.json", "--output", "-o", help="Session file path"),
    name: str = typer.Option(
        "", "--name", "-n", help="Named session (stored in ~/.wavexis/sessions/)"
    ),
) -> None:
    """Save or load browser session state (cookies + localStorage + sessionStorage).

    \b
    Save:  wavexis session save https://app.com -o mysession.json
    Load:  wavexis session load mysession.json https://app.com
    Named: wavexis session save https://app.com --name mysession
    List:  wavexis session list
    Delete: wavexis session delete --name mysession
    """
    from wavexis.actions.session import SessionLoadAction, SessionSaveAction

    sessions_dir = Path.home() / ".wavexis" / "sessions"

    def _session_path() -> Path:
        if name:
            return sessions_dir / f"{name}.json"
        return Path(output)

    if action == "list":
        if not sessions_dir.exists():
            typer.echo("No saved sessions found.")
            return
        sessions = list(sessions_dir.glob("*.json"))
        if not sessions:
            typer.echo("No saved sessions found.")
            return
        typer.echo(f"Saved sessions ({len(sessions)}):")
        for s in sorted(sessions):
            stat = s.stat()
            modified = time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))
            typer.echo(f"  {s.stem}  ({stat.st_size} bytes, {modified})")
        return

    if action == "delete":
        if not name:
            typer.echo("Error: --name required for delete", err=True)
            raise typer.Exit(1)
        target = _session_path()
        if not target.exists():
            typer.echo(f"Error: session '{name}' not found", err=True)
            raise typer.Exit(1)
        target.unlink()
        typer.echo(f"Deleted session '{name}'")
        return

    session_path = _session_path()

    if action == "save":
        if name:
            sessions_dir.mkdir(parents=True, exist_ok=True)
        if not url:
            typer.echo("Error: URL required for session save", err=True)
            raise typer.Exit(1)

        async def _save_session() -> Any:
            backend = _get_backend()
            await backend.launch(_browser_options())
            try:
                await backend.navigate(url, WaitStrategy(strategy="load"))
                save_action = SessionSaveAction(session_path)
                return await save_action.execute(backend)
            finally:
                await _close_backend(backend)

        _run_async(_save_session())
        typer.echo(f"Session saved to {session_path}")

    elif action == "load":
        if not session_path.exists():
            typer.echo(f"Error: session file not found: {session_path}", err=True)
            raise typer.Exit(1)

        async def _load_session() -> Any:
            backend = _get_backend()
            await backend.launch(_browser_options())
            try:
                load_action = SessionLoadAction(session_path)
                await load_action.execute(backend)
                if url:
                    await backend.navigate(url, WaitStrategy(strategy="load"))
                    title = await backend.eval("document.title", await_promise=False)
                    return title
                return "Session loaded"
            finally:
                await _close_backend(backend)

        result = _run_async(_load_session())
        if result is None:
            return
        typer.echo(f"Session loaded from {session_path}: {result}")

    else:
        typer.echo(
            f"Error: unknown session action '{action}'. Use save, load, list, or delete.",
            err=True,
        )
        raise typer.Exit(1)


@app.command()
def extract(
    url: str = typer.Argument(..., help="URL to extract data from"),
    schema: str = typer.Option(
        ...,
        "--schema",
        "-s",
        help=(
            "JSON schema mapping field names to CSS selectors, "
            'e.g. \'{"title":"h1","price":".price"}\''
        ),
    ),
    selector: str = typer.Option(
        "", "--selector", help="CSS selector to scope extraction (repeats per match)"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (.json)"),
    format: str = typer.Option("json", "--format", "-f", help="Output format (json)"),
) -> None:
    """Extract structured data from a web page using a CSS selector schema.

    \b
    Examples:
        wavexis extract https://shop.com -s '{"title":"h1","price":".price"}'
        wavexis extract https://shop.com/products \
            -s '{"name":".name","price":".price"}' --selector ".product"
    """
    from wavexis.actions.extract import ExtractAction, ExtractParams

    try:
        schema_dict = json.loads(schema)
    except json.JSONDecodeError as e:
        typer.echo(f"Error: invalid JSON schema: {e}", err=True)
        raise typer.Exit(1) from e

    async def _extract() -> list[dict[str, Any]]:
        backend = _get_backend()
        await backend.launch(_browser_options())
        try:
            params = ExtractParams(
                url=url,
                schema=schema_dict,
                selector=selector or None,
                wait=WaitStrategy(strategy="load"),
            )
            action = ExtractAction(params)
            return await action.execute(backend)
        finally:
            await _close_backend(backend)

    results = _run_async(_extract())
    if results is None:
        return

    Output.write_formatted(results, format, output)
    if output:
        typer.echo(f"Extracted {len(results)} record(s), saved to {output}")
    else:
        typer.echo(f"Extracted {len(results)} record(s)")


@app.command()
def form(
    url: str = typer.Argument(..., help="URL to navigate to"),
    data: str = typer.Option(
        ...,
        "--data",
        "-d",
        help=(
            "JSON mapping CSS selectors to values, "
            'e.g. \'{"#name":"Mathias","#email":"test@test.com"}\''
        ),
    ),
    submit: str = typer.Option(
        "", "--submit", help="CSS selector for submit button to click after filling"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (.json)"),
    format: str = typer.Option("json", "--format", "-f", help="Output format (json)"),
) -> None:
    """Auto-fill form fields from JSON data and optionally submit.

    \b
    Examples:
        wavexis form https://app.com/register -d '{"#name":"Mathias","#email":"test@test.com"}'
        wavexis form https://app.com/register -d '{"#name":"Mathias"}' --submit "#submit-btn"
    """
    from wavexis.actions.form import FormAction, FormParams

    try:
        fields = json.loads(data)
    except json.JSONDecodeError as e:
        typer.echo(f"Error: invalid JSON data: {e}", err=True)
        raise typer.Exit(1) from e

    async def _form() -> dict[str, Any]:
        backend = _get_backend()
        await backend.launch(_browser_options())
        try:
            params = FormParams(
                url=url,
                fields=fields,
                submit=submit or None,
                wait=WaitStrategy(strategy="load"),
            )
            action = FormAction(params)
            return await action.execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_form())
    if result is None:
        return

    Output.write_formatted(result, format, output)
    typer.echo(
        f"Filled {result['fields_filled']}/{result['fields_total']} fields"
        + (", submitted" if result["submitted"] else "")
    )
