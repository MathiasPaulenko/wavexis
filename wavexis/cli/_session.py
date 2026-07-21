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
    _handle_error,
    _run_async,
    app,
    _wait_strategy,
)
from wavexis.exceptions import WavexisError
from wavexis.output import validate_path


@app.command()
def session(
    action: str = typer.Argument(..., help="Session action: save, load, list, delete"),
    target: str = typer.Argument(
        "",
        help=(
            "For 'save': URL to navigate to. "
            "For 'load': path to session file to load. "
            "Use --url to specify the URL when loading."
        ),
    ),
    url: str = typer.Option(
        "",
        "--url",
        "-u",
        help="URL to navigate to after loading a session (for 'load').",
    ),
    output: str = typer.Option("session.json", "--output", "-o", help="Session file path (for 'save')"),
    name: str = typer.Option(
        "", "--name", "-n", help="Named session (stored in ~/.wavexis/sessions/)"
    ),
) -> None:
    """Save or load browser session state (cookies + localStorage + sessionStorage).

    \b
    Save:  wavexis session save https://app.com -o mysession.json
    Load:  wavexis session load mysession.json
    Load + navigate:  wavexis session load mysession.json --url https://app.com
    Named: wavexis session save https://app.com --name mysession
    List:  wavexis session list
    Delete: wavexis session delete --name mysession
    """
    from wavexis.actions.session import SessionLoadAction, SessionSaveAction

    sessions_dir = Path.home() / ".wavexis" / "sessions"

    def _session_path_from_output() -> Path:
        if name:
            safe_name = Path(name).name
            if not safe_name or safe_name != name or safe_name in (".", ".."):
                typer.echo("Error: invalid session name", err=True)
                raise typer.Exit(1)
            return sessions_dir / f"{safe_name}.json"
        try:
            return validate_path(output)
        except ValueError as e:
            _handle_error(WavexisError(str(e)))
            raise

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
        target_path = _session_path_from_output()
        if not target_path.exists():
            typer.echo(f"Error: session '{name}' not found", err=True)
            raise typer.Exit(1)
        target_path.unlink()
        typer.echo(f"Deleted session '{name}'")
        return

    if action == "save":
        session_path = _session_path_from_output()
        if name:
            sessions_dir.mkdir(parents=True, exist_ok=True)
        if not target:
            typer.echo("Error: URL required for session save", err=True)
            raise typer.Exit(1)
        save_url = target

        async def _save_session() -> Any:
            backend = _get_backend()
            await backend.launch(_browser_options())
            try:
                await backend.navigate(save_url, _wait_strategy())
                save_action = SessionSaveAction(session_path)
                return await save_action.execute(backend)
            finally:
                await _close_backend(backend)

        _run_async(_save_session())
        typer.echo(f"Session saved to {session_path}")
        return

    if action == "load":
        # For 'load', the positional `target` is the session file path.
        if not target:
            typer.echo(
                "Error: session file path required for load. "
                "Usage: wavexis session load <file.json> [--url URL]",
                err=True,
            )
            raise typer.Exit(1)
        try:
            session_path = validate_path(target)
        except ValueError as e:
            _handle_error(WavexisError(str(e)))
            return
        if not session_path.exists():
            typer.echo(f"Error: session file not found: {session_path}", err=True)
            raise typer.Exit(1)
        # `--url` (option) takes precedence; fall back to nothing.
        nav_url = url

        async def _load_session() -> Any:
            backend = _get_backend()
            await backend.launch(_browser_options())
            try:
                load_action = SessionLoadAction(session_path)
                await load_action.execute(backend)
                if nav_url:
                    await backend.navigate(nav_url, _wait_strategy())
                    title = await backend.eval("document.title", await_promise=False)
                    return title
                return "Session loaded"
            finally:
                await _close_backend(backend)

        result = _run_async(_load_session())
        if result is None:
            return
        typer.echo(f"Session loaded from {session_path}: {result}")
        return

    typer.echo(
        f"Error: unknown session action '{action}'. Use save, load, list, or delete.",
        err=True,
    )
    raise typer.Exit(1)


@app.command()
def extract(
    url: str = typer.Argument(..., help="URL to extract data from"),
    schema: str = typer.Option(
        "",
        "--schema",
        "-s",
        help=(
            "JSON schema mapping field names to CSS selectors, "
            'e.g. \'{"title":"h1","price":".price"}\'. '
            "Mutually exclusive with --schema-file."
        ),
    ),
    schema_file: str = typer.Option(
        "",
        "--schema-file",
        help=(
            "Path to a JSON file containing the extraction schema. "
            "Useful on shells (e.g. PowerShell) where passing inline JSON is awkward. "
            "Mutually exclusive with --schema."
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
        wavexis extract https://shop.com --schema-file schema.json
        wavexis extract https://shop.com/products \\
            -s '{"name":".name","price":".price"}' --selector ".product"
    """
    from wavexis.actions.extract import ExtractAction, ExtractParams

    if schema and schema_file:
        typer.echo("Error: --schema and --schema-file are mutually exclusive", err=True)
        raise typer.Exit(1)
    if not schema and not schema_file:
        typer.echo("Error: --schema or --schema-file is required", err=True)
        raise typer.Exit(1)

    if schema_file:
        try:
            schema = validate_path(schema_file).read_text(encoding="utf-8")
        except OSError as e:
            _handle_error(WavexisError(f"Failed to read schema file: {e}"))
            return

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
                wait=_wait_strategy(),
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
                wait=_wait_strategy(),
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
