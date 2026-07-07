"""workflow commands for wavexis CLI."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

import typer

from wavexis.actions.eval import EvalAction
from wavexis.actions.pdf import PDFAction
from wavexis.actions.scrape import ScrapeAction
from wavexis.actions.screenshot import ScreenshotAction
from wavexis.cli._shared import (
    WavexisError,
    _browser_options,
    _echo,
    _get_backend,
    _handle_error,
    _run_async,
    app,
)
from wavexis.config import EvalParams, PDFParams, ScrapeParams, ScreenshotParams, WaitStrategy


@app.command()
def multi(
    config: str = typer.Argument(..., help="Path to YAML config file"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validate config and show planned actions without launching browser",
    ),
    watch: bool = typer.Option(
        False,
        "--watch",
        help="Re-execute actions when the config file changes (Ctrl+C to stop)",
    ),
    parallel: bool = typer.Option(
        False,
        "--parallel",
        help="Execute all actions concurrently instead of sequentially",
    ),
) -> None:
    """Execute multiple actions from a YAML config file.

    Use --watch to re-run automatically when the config file changes.
    Use --parallel to execute all actions concurrently on the same backend.
    """
    config_path = Path(config)

    if dry_run:
        try:
            actions = _parse_and_describe(config_path)
        except WavexisError as e:
            _handle_error(e)
            return
        typer.echo(f"Plan: {len(actions)} action(s)")
        for i, desc in enumerate(actions):
            typer.echo(f"  {i + 1}. {desc}")
        return

    if watch:
        _multi_watch(config_path, parallel=parallel)
        return

    results = _run_async(_multi(config_path, parallel=parallel))
    if results is None:
        return

    typer.echo(f"Completed {len(results)} actions")
    for i, result in enumerate(results):
        if isinstance(result, bytes):
            typer.echo(f"  Action {i + 1}: {len(result)} bytes")
        elif isinstance(result, str):
            typer.echo(f"  Action {i + 1}: {result[:100]}")
        else:
            typer.echo(f"  Action {i + 1}: {type(result).__name__}")


def _multi_watch(config_path: Any, parallel: bool = False) -> None:
    """Watch a config file and re-execute on change.

    Uses polling to detect file modifications (cross-platform compatible).

    Args:
        config_path: Path to the YAML config file to watch.
        parallel: If True, execute actions concurrently.
    """
    last_mtime: float = 0.0
    typer.echo(f"Watching {config_path} for changes (Ctrl+C to stop)…")
    try:
        while True:
            mtime = config_path.stat().st_mtime
            if mtime != last_mtime:
                last_mtime = mtime
                typer.echo(f"\n[{time.strftime('%H:%M:%S')}] Re-running actions…")
                results = asyncio.run(_multi(config_path, parallel=parallel))
                typer.echo(f"Completed {len(results)} actions")
            time.sleep(1)
    except KeyboardInterrupt:
        typer.echo("\nStopped.")


async def _multi(config_path: Any, parallel: bool = False) -> list[Any]:
    """Execute multiple actions from a YAML config file.

    Args:
        config_path: Path to the YAML config file.
        parallel: If True, execute actions concurrently on the same backend.

    Returns:
        List of action results.
    """
    from wavexis.multi import execute_actions, parse_yaml

    actions = parse_yaml(config_path)
    backend = _get_backend()
    await backend.launch(_browser_options())
    try:
        return await execute_actions(actions, backend, parallel=parallel)
    finally:
        await backend.close()


def _parse_and_describe(config_path: Any) -> list[str]:
    """Parse a YAML config and return action descriptions without executing.

    Args:
        config_path: Path to the YAML config file.

    Returns:
        List of human-readable action descriptions.
    """
    from wavexis.multi import parse_yaml

    actions = parse_yaml(config_path)
    return [str(action) for action in actions]


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

    results = _run_async(_batch(urls, action, out_dir, expression, parallel))
    if results is None:
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
    semaphore = asyncio.Semaphore(parallel)

    async def _run_one(url: str) -> Any:
        async with semaphore:
            try:
                return await _batch_single(url, action, out_dir, expression)
            except (WavexisError, OSError) as exc:
                return exc

    tasks = [_run_one(u) for u in urls]
    return await asyncio.gather(*tasks)


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
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())

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
    interactive: bool = typer.Option(
        False,
        "--interactive",
        help=(
            "Launch non-headless browser and capture real interactions "
            "(clicks, inputs, navigations)"
        ),
    ),
    duration: int = typer.Option(
        60, "--duration", "-d", help="Recording duration in seconds (interactive mode)"
    ),
) -> None:
    """Record a browsing session to YAML for later replay.

    Use --interactive to launch a real browser and capture your interactions.
    Without --interactive, generates a YAML from specified action types.
    """
    if interactive:
        from wavexis.actions.record import record_session

        backend = _get_backend()
        yaml_content = _run_async(record_session(backend, url, duration))
        if yaml_content is None:
            return

        out_path = Path(output)
        out_path.write_text(yaml_content, encoding="utf-8")
        _echo(f"Recorded config saved to {output}")
        _echo(f"Run with: wavexis multi {output}")
        return

    from wavexis.record import record_to_yaml

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
    from wavexis.record import replay_from_yaml

    config_path = Path(config)
    backend = _get_backend()

    async def _replay() -> list[Any]:
        await backend.launch(_browser_options())
        try:
            return await replay_from_yaml(config_path, backend)
        finally:
            await backend.close()

    results = _run_async(_replay())
    if results is None:
        return

    _echo(f"Replayed {len(results)} actions")
    for i, result in enumerate(results):
        if isinstance(result, bytes):
            _echo(f"  Action {i + 1}: {len(result)} bytes")
        elif isinstance(result, str):
            _echo(f"  Action {i + 1}: {result[:100]}")
        else:
            _echo(f"  Action {i + 1}: {type(result).__name__}")
