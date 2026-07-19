"""advanced inspection commands for wavexis CLI."""

from __future__ import annotations

import json
from typing import Annotated, Any

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
def a11y(
    url: str = typer.Argument(..., help="URL to navigate to"),
    action: str = typer.Option("tree", "--action", "-a", help="A11y action: tree, node, ancestors"),
    node_id: str = typer.Option("", "--node-id", help="Node ID for node/ancestors actions"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Get accessibility tree, node, or ancestors from a web page."""
    result = _run_async(_a11y(url, action, node_id))
    if result is None:
        return

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
    from wavexis.actions.accessibility import AccessibilityAction

    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        act = AccessibilityAction(
            params=None,
            action=action,
            node_id=node_id,
            url=url,
            wait=WaitStrategy(strategy="load"),
        )
        return await act.execute(backend)
    finally:
        await _close_backend(backend)


@app.command()
def download(
    url: str = typer.Argument(..., help="URL to navigate to (must trigger a download)"),
    pattern: str = typer.Option(".*", "--pattern", help="URL pattern to match downloads"),
    output: str = typer.Option("download.bin", "--output", "-o", help="Output file path"),
) -> None:
    """Intercept a file download from a web page."""
    data = _run_async(_download(url, pattern))
    if data is None:
        return

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
    from wavexis.actions.download import DownloadAction

    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        act = DownloadAction(
            params=pattern,
            url=url,
            wait=WaitStrategy(strategy="load"),
        )
        return await act.execute(backend)
    finally:
        await _close_backend(backend)


@app.command()
def dialog(
    url: str = typer.Argument(..., help="URL to navigate to"),
    action: str = typer.Option("accept", "--action", "-a", help="Dialog action: accept, dismiss"),
    prompt_text: str = typer.Option("", "--text", help="Text for prompt dialogs"),
) -> None:
    """Accept or dismiss a JavaScript dialog on a web page."""
    _run_async(_dialog(url, action, prompt_text or None))
    typer.echo(f"Dialog {action}ed on {url}")


async def _dialog(url: str, action: str, prompt_text: str | None) -> None:
    """Accept or dismiss a JavaScript dialog on a web page.

    Args:
        url: URL to navigate to.
        action: Dialog action ("accept" or "dismiss").
        prompt_text: Text to enter in prompt dialogs, if applicable.
    """
    from wavexis.actions.dialog import DialogAction

    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        act = DialogAction(
            params="",
            action=action,
            prompt_text=prompt_text,
            url=url,
            wait=WaitStrategy(strategy="load"),
        )
        await act.execute(backend)
    finally:
        await _close_backend(backend)


@app.command()
def permissions(
    action: str = typer.Argument("grant", help="Permissions action: grant, reset"),
    permission: str = typer.Option(
        "geolocation",
        "--permission",
        help="Permission name (e.g. geolocation, notifications)",
    ),
    url: str = typer.Option("", "--url", help="URL to navigate to (optional)"),
) -> None:
    """Grant or reset browser permissions."""
    _run_async(_permissions(action, permission, url))
    typer.echo(f"Permissions {action} for '{permission}'")


async def _permissions(action: str, permission: str, url: str) -> None:
    """Grant or reset browser permissions.

    Args:
        action: Permission action ("grant", "deny", "reset", or "query").
        permission: Permission name (e.g. "geolocation").
        url: URL to navigate to (optional).
    """
    from wavexis.actions.permissions import PermissionsAction

    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        act = PermissionsAction(
            params="",
            action=action,
            permission=permission,
            url=url,
            wait=WaitStrategy(strategy="load") if url else None,
        )
        await act.execute(backend)
    finally:
        await _close_backend(backend)


@app.command()
def security(
    url: str = typer.Argument(..., help="URL to navigate to"),
    action: str = typer.Option(
        "state", "--action", "-a", help="Security action: state, ignore_cert"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Get security state or ignore certificate errors."""
    result = _run_async(_security(url, action))
    if result is None:
        return

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
    from wavexis.actions.security import SecurityAction

    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        act = SecurityAction(
            params="",
            action=action,
            url=url,
            wait=WaitStrategy(strategy="load"),
        )
        return await act.execute(backend)
    finally:
        await _close_backend(backend)


@app.command()
def lighthouse(
    url: str = typer.Argument(..., help="URL to audit"),
    categories: Annotated[
        list[str] | None,
        typer.Option(
            "--category",
            "-c",
            help=(
                "Audit category: performance, accessibility, seo, "
                "best-practices (repeatable, empty=all)"
            ),
        ),
    ] = None,
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (.json)"),
    format: str = typer.Option("json", "--format", "-f", help="Output format (json)"),
    budget: str | None = typer.Option(
        None,
        "--budget",
        "-b",
        help='Path to JSON file with performance budgets (e.g. {"ttfb_ms": 800})',
    ),
    threshold: Annotated[
        list[str] | None,
        typer.Option(
            "--threshold",
            "-t",
            help=(
                "Inline budget threshold: metric=value "
                "(e.g. -t ttfb_ms=800 -t lcp_ms=2500). Repeatable."
            ),
        ),
    ] = None,
) -> None:
    """Run a Lighthouse-style audit (performance, accessibility, SEO, best practices).

    \b
    Examples:
        wavexis lighthouse https://example.com
        wavexis lighthouse https://example.com -c performance -c seo -o report.json
        wavexis lighthouse https://example.com -t ttfb_ms=800 -t lcp_ms=2500
        wavexis lighthouse https://example.com -b budgets.json
    """
    from wavexis.actions.lighthouse import LighthouseAction, LighthouseParams

    cats = categories or []
    budgets: dict[str, float] = {}

    if budget:
        from pathlib import Path

        try:
            budget_text = Path(budget).read_text(encoding="utf-8")
            loaded = json.loads(budget_text)
        except json.JSONDecodeError as e:
            typer.echo(f"Error: invalid JSON in budget file: {e}", err=True)
            raise typer.Exit(1)
        if isinstance(loaded, dict):
            try:
                budgets = {k: float(v) for k, v in loaded.items()}
            except (ValueError, TypeError) as e:
                typer.echo(f"Error: invalid budget value: {e}", err=True)
                raise typer.Exit(1)

    if threshold:
        for t in threshold:
            if "=" in t:
                key, val = t.split("=", 1)
                try:
                    budgets[key.strip()] = float(val.strip())
                except ValueError:
                    typer.echo(f"Error: invalid threshold value '{val.strip()}' for '{key.strip()}'", err=True)
                    raise typer.Exit(1)

    async def _lighthouse() -> dict[str, Any]:
        backend = _get_backend()
        await backend.launch(_browser_options())
        try:
            params = LighthouseParams(
                url=url,
                categories=cats,
                wait=WaitStrategy(strategy="load"),
                budgets=budgets,
            )
            action = LighthouseAction(params)
            return await action.execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_lighthouse())
    if result is None:
        return

    Output.write_formatted(result, format, output)
    scores = {cat: data.get("score", 0) for cat, data in result.get("categories", {}).items()}
    score_str = ", ".join(f"{k}: {v}" for k, v in scores.items())

    budget_str = ""
    perf = result.get("categories", {}).get("performance", {})
    budget_result = perf.get("budgets") if isinstance(perf, dict) else None
    if budget_result and isinstance(budget_result, dict):
        status = "PASS" if budget_result.get("pass") else "FAIL"
        budget_str = f", budgets: {status}"
        for br in budget_result.get("results", []):
            mark = "✓" if br.get("pass") else "✗"
            budget_str += f"\n  {mark} {br['metric']}: {br['actual']} / {br['budget']}"

    if output:
        typer.echo(f"Audit complete ({score_str}){budget_str}, saved to {output}")
    else:
        typer.echo(f"Audit complete ({score_str}){budget_str}")


@app.command()
def extension_install(
    path: str = typer.Argument(..., help="Path to .crx file or unpacked extension directory"),
) -> None:
    """Install a browser extension."""

    async def _run() -> str:
        backend = _get_backend()
        await backend.launch(_browser_options())
        try:
            result: str = await backend.extension_install(path)
            return result
        finally:
            await _close_backend(backend)

    ext_id: Any = _run_async(_run())
    if ext_id is not None:
        typer.echo(f"Installed extension: {ext_id}")


@app.command()
def extension_uninstall(
    extension_id: str = typer.Argument(..., help="Extension ID to uninstall"),
) -> None:
    """Uninstall a browser extension by ID."""

    async def _run() -> None:
        backend = _get_backend()
        await backend.launch(_browser_options())
        try:
            await backend.extension_uninstall(extension_id)
        finally:
            await _close_backend(backend)

    _run_async(_run())
    typer.echo(f"Uninstalled extension: {extension_id}")


@app.command()
def extension_list() -> None:
    """List installed browser extensions."""

    async def _run() -> list[dict[str, Any]]:
        backend = _get_backend()
        await backend.launch(_browser_options())
        try:
            result: list[dict[str, Any]] = await backend.extension_list()
            return result
        finally:
            await _close_backend(backend)

    extensions: Any = _run_async(_run())
    if extensions is None:
        return
    if not extensions:
        typer.echo("No extensions installed.")
        return
    for ext in extensions:
        status = "enabled" if ext.get("enabled") else "disabled"
        typer.echo(f"  {ext['id']}  {ext['name']} v{ext['version']}  ({status})")


@app.command()
def pref_get(
    key: str = typer.Argument(..., help="Preference key (e.g. download.default_directory)"),
) -> None:
    """Get a browser preference value."""

    async def _run() -> Any:
        backend = _get_backend()
        await backend.launch(_browser_options())
        try:
            return await backend.get_pref(key)
        finally:
            await _close_backend(backend)

    value: Any = _run_async(_run())
    if value is not None:
        typer.echo(f"{key} = {value}")


@app.command()
def pref_set(
    key: str = typer.Argument(..., help="Preference key"),
    value: str = typer.Argument(..., help="Preference value"),
) -> None:
    """Set a browser preference value."""

    async def _run() -> None:
        backend = _get_backend()
        await backend.launch(_browser_options())
        try:
            await backend.set_pref(key, value)
        finally:
            await _close_backend(backend)

    _run_async(_run())
    typer.echo(f"Set {key} = {value}")
