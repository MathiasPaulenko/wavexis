"""workflow commands for wavexis CLI."""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any

import typer

from wavexis.actions.eval import EvalAction
from wavexis.actions.pdf import PDFAction
from wavexis.actions.scrape import ScrapeAction
from wavexis.actions.screenshot import ScreenshotAction
from wavexis.cli._shared import (
    WavexisError,
    _browser_options,
    _close_backend,
    _echo,
    _get_backend,
    _handle_error,
    _progress,
    _run_async,
    _wait_strategy,
    app,
)
from wavexis.config import EvalParams, PDFParams, ScrapeParams, ScreenshotParams
from wavexis.output import validate_path


def _sanitize_filename(name: str) -> str:
    """Convert an arbitrary URL to a safe filesystem filename.

    Replaces characters that are illegal or problematic on common filesystems
    with an underscore, then collapses repeated underscores and trims length.
    """
    sanitized = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    sanitized = re.sub(r"_+", "_", sanitized)
    return sanitized.strip("._")[:80] or "untitled"


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
        help="Execute all actions concurrently using separate tabs",
    ),
    cache_ttl: int = typer.Option(
        0,
        "--cache-ttl",
        help=(
            "Cache action results for N seconds (0=disabled). "
            "Cacheable: screenshot, dom, scrape, eval, cookies, headers"
        ),
    ),
) -> None:
    """Execute multiple actions from a YAML config file.

    Use --watch to re-run automatically when the config file changes.
    Use --parallel to execute all actions concurrently on separate tabs.
    Use --cache-ttl to cache results and skip re-execution on repeated runs.
    """
    try:
        config_path = validate_path(config)
    except ValueError as e:
        _handle_error(WavexisError(str(e)))
        return

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
        _multi_watch(config_path, parallel=parallel, cache_ttl=cache_ttl)
        return

    results = _run_async(_multi(config_path, parallel=parallel, cache_ttl=cache_ttl))
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


def _multi_watch(config_path: Any, parallel: bool = False, cache_ttl: int = 0) -> None:
    """Watch a config file and re-execute on change.

    Uses polling to detect file modifications (cross-platform compatible).

    Args:
        config_path: Path to the YAML config file to watch.
        parallel: If True, execute actions concurrently.
        cache_ttl: Cache TTL in seconds. 0 = no caching.
    """
    last_mtime: float = 0.0
    typer.echo(f"Watching {config_path} for changes (Ctrl+C to stop)…")
    try:
        while True:
            try:
                mtime = config_path.stat().st_mtime
            except OSError:
                time.sleep(1)
                continue
            if mtime != last_mtime:
                last_mtime = mtime
                time.sleep(0.5)
                try:
                    current_mtime = config_path.stat().st_mtime
                except OSError:
                    continue
                if current_mtime != mtime:
                    last_mtime = current_mtime
                    continue
                typer.echo(f"\n[{time.strftime('%H:%M:%S')}] Re-running actions…")
                results = _run_async(_multi(config_path, parallel=parallel, cache_ttl=cache_ttl))
                if results is not None:
                    typer.echo(f"Completed {len(results)} actions")
            time.sleep(1)
    except KeyboardInterrupt:
        typer.echo("\nStopped.")


async def _multi(config_path: Any, parallel: bool = False, cache_ttl: int = 0) -> list[Any]:
    """Execute multiple actions from a YAML config file.

    Args:
        config_path: Path to the YAML config file.
        parallel: If True, execute actions concurrently on separate tabs.
        cache_ttl: Cache TTL in seconds. 0 = no caching.

    Returns:
        List of action results.
    """
    from wavexis.actions.cache import ActionCache
    from wavexis.multi import execute_actions, parse_yaml

    actions = await asyncio.to_thread(parse_yaml, config_path)
    total = len(actions)
    _echo(f"Executing {total} action(s)…")
    cache = ActionCache(default_ttl=cache_ttl) if cache_ttl > 0 else None
    backend = _get_backend()
    await backend.launch(_browser_options())
    try:
        results: list[Any] = []
        if parallel:
            results = await execute_actions(actions, backend, parallel=True, cache=cache)
        else:
            for i, action in enumerate(actions):
                _progress(i + 1, total, str(action))
                result = await execute_actions([action], backend, parallel=False, cache=cache)
                results.extend(result)
        return results
    finally:
        await _close_backend(backend)


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
        4, "--parallel", "-p", help="Number of parallel workers (tabs or processes)"
    ),
    mode: str = typer.Option(
        "tabs",
        "--mode",
        "-m",
        help="Concurrency mode: 'tabs' (1 Chrome, N tabs) or 'processes' (N Chrome processes)",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show plan without launching browser"),
) -> None:
    """Run a single action against multiple URLs in parallel."""
    try:
        urls_path = validate_path(urls_file)
    except ValueError as e:
        _handle_error(WavexisError(str(e)))
        return
    if not urls_path.exists():
        typer.echo(f"Error: URLs file not found: {urls_path}")
        raise typer.Exit(1)

    try:
        urls = [
            line.strip()
            for line in urls_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except OSError as e:
        typer.echo(f"Error: URLs file not found or unreadable: {e}", err=True)
        raise typer.Exit(1) from e
    if not urls:
        typer.echo("Error: No URLs found in file")
        raise typer.Exit(1)

    if dry_run:
        typer.echo(f"Plan: {len(urls)} URL(s) x {action}")
        for u in urls:
            typer.echo(f"  {action}({u})")
        return

    try:
        out_dir = validate_path(output_dir)
    except ValueError as e:
        _handle_error(WavexisError(str(e)))
        return
    if out_dir.exists() and not out_dir.is_dir():
        _handle_error(WavexisError(f"Output path exists but is not a directory: {out_dir}"))
        return
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        _handle_error(WavexisError(f"Failed to create output directory: {e}"))
        return

    results = _run_async(_batch(urls, action, out_dir, expression, parallel, mode))
    if results is None:
        return

    typer.echo(f"Completed {len(results)} / {len(urls)} actions")
    for i, (url, result) in enumerate(zip(urls, results, strict=True)):
        if isinstance(result, BaseException) and not isinstance(result, Exception):
            raise result
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
    mode: str = "tabs",
) -> list[Any]:
    """Run an action against multiple URLs with limited concurrency.

    Args:
        urls: List of URLs to process.
        action: Action type — screenshot, pdf, scrape, or eval.
        out_dir: Output directory for saved files.
        expression: JS expression for scrape/eval.
        parallel: Maximum number of concurrent workers.
        mode: 'tabs' (1 Chrome, N tabs) or 'processes' (N Chrome processes).

    Returns:
        List of results (or exceptions) in the same order as urls.
    """
    if mode == "tabs":
        return await _batch_tabs(urls, action, out_dir, expression, parallel)
    return await _batch_processes(urls, action, out_dir, expression, parallel)


async def _batch_tabs(
    urls: list[str],
    action: str,
    out_dir: Any,
    expression: str,
    parallel: int,
) -> list[Any]:
    """Run actions using tabs in a single Chrome process.

    Args:
        urls: List of URLs to process.
        action: Action type.
        out_dir: Output directory.
        expression: JS expression for scrape/eval.
        parallel: Maximum concurrent tabs.

    Returns:
        List of results (or exceptions) in the same order as urls.
    """
    backend = _get_backend()
    await backend.launch(_browser_options())
    try:
        semaphore = asyncio.Semaphore(parallel)
        total = len(urls)
        completed = 0
        lock = asyncio.Lock()

        async def _run_one(url: str) -> Any:
            nonlocal completed
            async with semaphore:
                tab = None
                try:
                    tab = await backend.new_tab_handle(url)
                    result = await _batch_single_on(url, action, out_dir, expression, tab)
                    return result
                except (WavexisError, OSError) as exc:
                    return exc
                finally:
                    if tab is not None:
                        await tab.close()
                    async with lock:
                        completed += 1
                        _progress(completed, total, url)

        tasks = [_run_one(u) for u in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        await _close_backend(backend)


async def _batch_processes(
    urls: list[str],
    action: str,
    out_dir: Any,
    expression: str,
    parallel: int,
) -> list[Any]:
    """Run actions using separate Chrome processes.

    Args:
        urls: List of URLs to process.
        action: Action type.
        out_dir: Output directory.
        expression: JS expression for scrape/eval.
        parallel: Maximum concurrent processes.

    Returns:
        List of results (or exceptions) in the same order as urls.
    """
    semaphore = asyncio.Semaphore(parallel)
    total = len(urls)
    completed = 0
    lock = asyncio.Lock()

    async def _run_one(url: str) -> Any:
        nonlocal completed
        async with semaphore:
            try:
                result = await _batch_single(url, action, out_dir, expression)
                return result
            except (WavexisError, OSError) as exc:
                return exc
            finally:
                async with lock:
                    completed += 1
                    _progress(completed, total, url)

    tasks = [_run_one(u) for u in urls]
    return await asyncio.gather(*tasks, return_exceptions=True)


async def _batch_single(
    url: str,
    action: str,
    out_dir: Any,
    expression: str,
) -> Any:
    """Execute a single action for one URL in batch mode (own process).

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
        return await _batch_single_on(url, action, out_dir, expression, backend)
    finally:
        await _close_backend(backend)


async def _batch_single_on(
    url: str,
    action: str,
    out_dir: Any,
    expression: str,
    backend: Any,
) -> Any:
    """Execute a single action on a given backend (tab or process).

    Args:
        url: URL to process.
        action: Action type — screenshot, pdf, scrape, or eval.
        out_dir: Output directory for saved files.
        expression: JS expression for scrape/eval.
        backend: An already-launched backend or TabHandle.

    Returns:
        Result of the action.

    Raises:
        WavexisError: If the action type is unknown.
    """
    if action == "screenshot":
        sp = ScreenshotParams(url=url, full_page=True, wait=_wait_strategy())
        result = await ScreenshotAction(sp).execute(backend)
        safe_url = _sanitize_filename(url)
        try:
            (out_dir / f"{safe_url}.png").write_bytes(result)
        except OSError as e:
            raise WavexisError(f"Failed to write {safe_url}.png: {e}") from e
        return result

    if action == "pdf":
        pp = PDFParams(url=url, wait=_wait_strategy())
        result = await PDFAction(pp).execute(backend)
        safe_url = _sanitize_filename(url)
        try:
            (out_dir / f"{safe_url}.pdf").write_bytes(result)
        except OSError as e:
            raise WavexisError(f"Failed to write {safe_url}.pdf: {e}") from e
        return result

    if action == "scrape":
        scp = ScrapeParams(
            urls=[url],
            expression=expression,
            wait=_wait_strategy(),
        )
        return await ScrapeAction(scp).execute(backend)

    if action == "eval":
        ep = EvalParams(url=url, expression=expression, wait=_wait_strategy())
        return await EvalAction(ep).execute(backend)

    raise WavexisError(f"Unknown batch action: {action}")


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
        "#button",
        "--selector",
        help="CSS selector for click/type actions",
    ),
    text: str = typer.Option("hello", "--text", help="Text for type action"),
    expression: str = typer.Option(
        "document.title",
        "--expression",
        help="JS expression for eval action",
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

        async def _record_and_close() -> str | None:
            try:
                return await record_session(backend, url, duration)
            finally:
                await _close_backend(backend)

        yaml_content = _run_async(_record_and_close())
        if yaml_content is None:
            return

        try:
            out_path = validate_path(output)
        except ValueError as e:
            _handle_error(WavexisError(str(e)))
            return
        try:
            out_path.write_text(yaml_content, encoding="utf-8")
        except OSError as e:
            _handle_error(WavexisError(f"Failed to write recorded config: {e}"))
            return
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
            action_list.append({"input": {"url": url, "action": "click", "selector": selector}})
        elif at == "type":
            action_list.append(
                {
                    "input": {"url": url, "action": "type", "selector": selector, "text": text},
                }
            )
        elif at == "scrape":
            action_list.append(
                {
                    "scrape": {"url": url, "expression": expression},
                }
            )
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

    try:
        out_path = validate_path(output)
    except ValueError as e:
        _handle_error(WavexisError(str(e)))
        return
    try:
        record_to_yaml(action_list, out_path)
    except (OSError, WavexisError) as e:
        _handle_error(WavexisError(f"Failed to write recorded config: {e}"))
        return
    _echo(f"Recorded {len(action_list)} actions to {output}")


@app.command()
def replay(
    config: str = typer.Argument(..., help="Path to YAML config file"),
) -> None:
    """Replay a recorded session from YAML."""
    from wavexis.record import replay_from_yaml

    try:
        config_path = validate_path(config)
    except ValueError as e:
        _handle_error(WavexisError(str(e)))
        return
    backend = _get_backend()

    async def _replay() -> list[Any]:
        await backend.launch(_browser_options())
        try:
            return await replay_from_yaml(config_path, backend)
        finally:
            await _close_backend(backend)

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
