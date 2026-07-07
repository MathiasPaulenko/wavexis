"""capture commands for wavexis CLI."""

from __future__ import annotations

__all__ = ["_check_assertion"]

import json
from typing import Annotated, Any

import typer

from wavexis.actions.dom import DOMAction
from wavexis.actions.eval import EvalAction
from wavexis.actions.har import HARAction
from wavexis.actions.pdf import PDFAction
from wavexis.actions.scrape import ScrapeAction
from wavexis.actions.screenshot import ScreenshotAction
from wavexis.cli._shared import (
    Output,
    _browser_options,
    _echo,
    _get_backend,
    _progress,
    _run_async,
    _write_json_output,
    app,
)
from wavexis.config import (
    DOMParams,
    EvalParams,
    HarParams,
    PDFParams,
    ScrapeParams,
    ScreencastParams,
    ScreenshotParams,
    WaitStrategy,
)


@app.command()
def screenshot(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("screenshot.png", "--output", "-o", help="Output file path"),
    full_page: bool = typer.Option(False, "--full-page", help="Capture full page"),
    selector: str | None = typer.Option(
        None, "--selector", help="CSS selector to capture"
    ),
    device: str | None = typer.Option(None, "--device", help="Device preset name"),
    format: str = typer.Option("png", "--format", help="Image format (png or jpeg)"),
    js: str | None = typer.Option(
        None, "--js", help="JavaScript to execute before screenshot"
    ),
    wait_for: str | None = typer.Option(
        None, "--wait-for", help="CSS selector to wait for"
    ),
) -> None:
    """Take a screenshot of a web page."""
    wait = (
        WaitStrategy(strategy="selector", selector=wait_for)
        if wait_for
        else WaitStrategy(strategy="load")
    )
    image_bytes = _run_async(
        _take_screenshot(url, full_page, selector, device, format, js, wait)
    )
    if image_bytes is None:
        return

    Output.write_bytes(image_bytes, output)
    typer.echo(f"Screenshot saved to {output}")


@app.command()
def annotate(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selectors: str = typer.Option(
        ...,
        "--selectors",
        "-s",
        help='Comma-separated CSS selectors to annotate (e.g. "button,#email")',
    ),
    output: str = typer.Option(
        "annotated.png", "--output", "-o", help="Output file path"
    ),
    format: str = typer.Option(
        "png", "--format", help="Image format (png or jpeg)"
    ),
) -> None:
    """Take a screenshot with numbered labels on elements.

    \b
    wavexis annotate https://example.com -s "button,#email,input" -o out.png
    """
    selector_list = [s.strip() for s in selectors.split(",") if s.strip()]
    image_bytes, label_map = _run_async(
        _take_annotated(url, selector_list, format)
    )
    Output.write_bytes(image_bytes, output)
    typer.echo(f"Annotated screenshot saved to {output}")
    typer.echo("Labels:")
    for label, sel in label_map.items():
        typer.echo(f"  @{label} → {sel}")


async def _take_annotated(
    url: str, selectors: list[str], format: str
) -> tuple[bytes, dict[str, str]]:
    """Async helper for annotated screenshot."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        result: tuple[bytes, dict[str, str]] = (
            await backend.annotated_screenshot(selectors, format=format)
        )
        return result
    finally:
        await backend.close()


async def _take_screenshot(
    url: str,
    full_page: bool,
    selector: str | None,
    device: str | None,
    format: str,
    js: str | None,
    wait: WaitStrategy,
) -> bytes:
    """Async helper to take a screenshot via backend."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        params = ScreenshotParams(
            url=url,
            full_page=full_page,
            selector=selector,
            device=device,
            format=format,
            js=js,
            wait=wait,
        )
        action = ScreenshotAction(params)
        return await action.execute(backend)
    finally:
        await backend.close()

@app.command()
def pdf(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("output.pdf", "--output", "-o", help="Output file path"),
    paper: str = typer.Option(
        "letter", "--paper", help="Paper size (a4, letter, legal, a3, a5)"
    ),
    landscape: bool = typer.Option(False, "--landscape", help="Use landscape orientation"),
    margins: str = typer.Option(
        "0.4in", "--margins", help="Margin size (e.g. 0.4in)"
    ),
    media: str = typer.Option(
        "print", "--media", help="CSS media type (print or screen)"
    ),
    no_header_footer: bool = typer.Option(
        False, "--no-header-footer", help="Omit header and footer"
    ),
) -> None:
    """Generate a PDF of a web page."""
    pdf_bytes = _run_async(
        _generate_pdf(url, paper, landscape, margins, media, no_header_footer)
    )
    if pdf_bytes is None:
        return

    Output.write_bytes(pdf_bytes, output)
    typer.echo(f"PDF saved to {output}")

async def _generate_pdf(
    url: str,
    paper: str,
    landscape: bool,
    margins: str,
    media: str,
    no_header_footer: bool,
) -> bytes:
    """Async helper to generate a PDF via backend."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        params = PDFParams(
            url=url,
            paper=paper,
            landscape=landscape,
            margin=margins,
            media=media,
            no_header_footer=no_header_footer,
            wait=WaitStrategy(strategy="load"),
        )
        action = PDFAction(params)
        return await action.execute(backend)
    finally:
        await backend.close()

@app.command()
def eval(
    url: str = typer.Argument(..., help="URL to navigate to"),
    expression: str = typer.Option(
        "", "--expression", "-e", help="JavaScript expression to evaluate"
    ),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path"
    ),
    format: str = typer.Option(
        "json", "--format", "-f", help="Output format: json, csv, yaml"
    ),
    await_promise: bool = typer.Option(
        False, "--await-promise", help="Await a returned Promise"
    ),
    file: str | None = typer.Option(None, "--file", help="Read expression from file"),
    assert_expr: str = typer.Option(
        "",
        "--assert",
        help=(
            "Assertion: '== value', '!= value', 'contains substring', "
            "'matches regex'. Exit 0 if pass, 1 if fail"
        ),
    ),
) -> None:
    """Evaluate a JavaScript expression on a web page.

    Use --assert to create CI gates that pass/fail based on the result.
    """
    if file and not expression:
        expression = f"@{file}"
    elif file:
        from pathlib import Path
        expression = Path(file).read_text(encoding="utf-8")

    result = _run_async(_eval(url, expression, await_promise, file))
    if result is None:
        return

    if assert_expr:
        passed, message = _check_assertion(result, assert_expr)
        typer.echo(f"assert: {assert_expr}")
        typer.echo(f"result: {result}")
        typer.echo(f"status: {'PASS' if passed else 'FAIL'}")
        if not passed:
            typer.echo(f"  {message}", err=True)
        raise typer.Exit(0 if passed else 1)

    Output.write_formatted(result, format, output)
    if output:
        typer.echo(f"Result saved to {output}")

def _check_assertion(result: Any, assert_expr: str) -> tuple[bool, str]:
    """Check if a result satisfies an assertion expression.

    Supported operators:
        == value   — result equals value (string/number)
        != value   — result does not equal value
        contains substring — result contains substring
        matches regex — result matches regex pattern

    Args:
        result: The evaluation result.
        assert_expr: Assertion expression string.

    Returns:
        Tuple of (passed, message). Message is empty on success.
    """
    result_str = str(result)

    if assert_expr.startswith("== "):
        expected = assert_expr[3:]
        if result_str == expected:
            return True, ""
        return False, f"Expected '{expected}', got '{result_str}'"

    if assert_expr.startswith("!= "):
        expected = assert_expr[3:]
        if result_str != expected:
            return True, ""
        return False, f"Expected not '{expected}', got '{result_str}'"

    if assert_expr.startswith("contains "):
        substring = assert_expr[9:]
        if substring in result_str:
            return True, ""
        return False, f"'{result_str}' does not contain '{substring}'"

    if assert_expr.startswith("matches "):
        import re
        pattern = assert_expr[8:]
        if re.search(pattern, result_str):
            return True, ""
        return False, f"'{result_str}' does not match /{pattern}/"

    return False, (
        f"Unknown assertion: {assert_expr}. "
        "Use: '== value', '!= value', 'contains substring', 'matches regex'"
    )

async def _eval(url: str, expression: str, await_promise: bool, file: str | None) -> Any:
    """Async helper to evaluate JS via backend."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        params = EvalParams(
            url=url,
            expression=expression,
            await_promise=await_promise,
            file=file,
            wait=WaitStrategy(strategy="load"),
        )
        action = EvalAction(params)
        return await action.execute(backend)
    finally:
        await backend.close()

@app.command()
def dom(
    url: str = typer.Argument(..., help="URL to navigate to"),
    action: str = typer.Option(
        "get",
        "--action",
        "-a",
        help=(
            "DOM action: get, query, attr, remove_attr, remove, focus, scroll, "
            "suggest_locator"
        ),
    ),
    selector: str = typer.Option("", "--selector", "-s", help="CSS selector"),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path"
    ),
    outer: bool = typer.Option(True, "--outer/--inner", help="Outer or inner HTML"),
    all: bool = typer.Option(
        False, "--all",
        help="Query all matching elements or all locator suggestions",
    ),
    attribute: str | None = typer.Option(
        None, "--attribute", help="Attribute name for get/set/remove"
    ),
    value: str | None = typer.Option(
        None, "--value", help="Attribute value for set"
    ),
) -> None:
    """DOM operations on a web page."""
    result = _run_async(
        _dom(url, action, selector, outer, all, attribute, value)
    )
    if result is None:
        return

    if isinstance(result, str):
        if output:
            Output.write_text(result, output)
            typer.echo(f"Output saved to {output}")
        else:
            typer.echo(result)
    elif isinstance(result, list):
        if output:
            Output.write_json(result, output)
            typer.echo(f"Output saved to {output}")
        else:
            for item in result:
                typer.echo(item)
    elif result is not None:
        if output:
            Output.write_json(result, output)
            typer.echo(f"Output saved to {output}")
        else:
            typer.echo(json.dumps(result, indent=2, default=str))
    else:
        typer.echo("Done")

async def _dom(
    url: str,
    action: str,
    selector: str,
    outer: bool,
    all: bool,
    attribute: str | None,
    value: str | None,
) -> Any:
    """Async helper for DOM operations."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        if action == "suggest_locator":
            await backend.navigate(url, WaitStrategy(strategy="load"))
            return await backend.suggest_locator(selector, all=all)
        params = DOMParams(
            url=url,
            action=action,
            selector=selector,
            outer=outer,
            all=all,
            attribute=attribute,
            value=value,
            wait=WaitStrategy(strategy="load"),
        )
        return await DOMAction(params).execute(backend)
    finally:
        await backend.close()

@app.command()
def scrape(
    urls: Annotated[list[str], typer.Argument(help="URLs to scrape")],
    expression: str = typer.Option(
        "document.title", "--expression", "-e", help="JavaScript expression"
    ),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path"
    ),
    format: str = typer.Option(
        "json", "--format", "-f", help="Output format: json, csv, yaml"
    ),
    file: str | None = typer.Option(
        None, "--file", help="Read expression from file (prefix with @)"
    ),
    selector: str | None = typer.Option(
        None, "--selector", "-s", help="CSS selector to wait for"
    ),
    concurrency: int = typer.Option(
        1, "--concurrency", "-c", help="Number of concurrent tabs (1 = sequential)"
    ),
) -> None:
    """Scrape multiple URLs by evaluating a JS expression on each."""
    expr = expression
    if file:
        expr = f"@{file}"

    results = _run_async(_scrape(urls, expr, file, selector, concurrency))
    if results is None:
        return

    Output.write_formatted(results, format, output)
    if output:
        typer.echo(f"Results saved to {output}")

async def _scrape(
    urls: list[str],
    expression: str,
    file: str | None,
    selector: str | None,
    concurrency: int = 1,
) -> list[dict[str, Any]]:
    """Async helper for scraping.

    When concurrency > 1, uses tabs in a single Chrome process for parallel scraping.
    """
    import asyncio

    backend = _get_backend()
    total = len(urls)
    _echo(f"Scraping {total} URL(s)…")
    try:
        await backend.launch(_browser_options())

        if concurrency > 1:
            semaphore = asyncio.Semaphore(concurrency)
            completed = 0
            lock = asyncio.Lock()

            async def _scrape_one(url: str) -> list[dict[str, Any]]:
                nonlocal completed
                async with semaphore:
                    tab = None
                    try:
                        tab = await backend.new_tab_handle(url)
                        params = ScrapeParams(
                            urls=[url],
                            expression=expression,
                            file=file,
                            output_format="json",
                            selector=selector,
                            wait=WaitStrategy(strategy="load"),
                        )
                        return await ScrapeAction(params).execute(tab)
                    finally:
                        if tab is not None:
                            await tab.close()
                        async with lock:
                            completed += 1
                            _progress(completed, total, url)

            tasks = [_scrape_one(u) for u in urls]
            gathered = await asyncio.gather(*tasks)
            results: list[dict[str, Any]] = []
            for batch in gathered:
                results.extend(batch)
            return results

        results_seq: list[dict[str, Any]] = []
        for i, url in enumerate(urls):
            _progress(i + 1, total, url)
            params = ScrapeParams(
                urls=[url],
                expression=expression,
                file=file,
                output_format="json",
                selector=selector,
                wait=WaitStrategy(strategy="load"),
            )
            result = await ScrapeAction(params).execute(backend)
            results_seq.extend(result)
        return results_seq
    finally:
        await backend.close()

@app.command()
def crawl(
    url: str = typer.Argument(..., help="Starting URL to crawl"),
    max_depth: int = typer.Option(
        2, "--depth", "-d", help="Maximum crawl depth (1 = start page only)"
    ),
    max_pages: int = typer.Option(
        50, "--max-pages", help="Maximum number of pages to visit"
    ),
    same_origin: bool = typer.Option(
        True, "--same-origin/--cross-origin", help="Only crawl same-origin links"
    ),
    url_pattern: str = typer.Option(
        "", "--pattern", help="Regex pattern to filter URLs (empty = all)"
    ),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path (.json)"
    ),
    format: str = typer.Option("json", "--format", "-f", help="Output format (json)"),
) -> None:
    """Crawl a website starting from a URL, collecting titles and links.

    \b
    Examples:
        wavexis crawl https://example.com
        wavexis crawl https://example.com --depth 3 --max-pages 100
        wavexis crawl https://example.com --pattern '.*blog.*' -o results.json
    """
    results = _run_async(_crawl(url, max_depth, max_pages, same_origin, url_pattern))
    if results is None:
        return

    Output.write_formatted(results, format, output)
    if output:
        typer.echo(f"Crawled {len(results)} pages, saved to {output}")
    else:
        typer.echo(f"Crawled {len(results)} pages")

async def _crawl(
    url: str,
    max_depth: int,
    max_pages: int,
    same_origin: bool,
    url_pattern: str,
) -> list[dict[str, Any]]:
    """Async helper for crawling a website.

    Args:
        url: Starting URL.
        max_depth: Maximum crawl depth.
        max_pages: Maximum pages to visit.
        same_origin: If True, only crawl same-origin links.
        url_pattern: Regex pattern to filter URLs.

    Returns:
        List of page dicts with url, title, depth, and links_found.
    """
    from wavexis.actions.crawl import CrawlAction, CrawlParams

    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        params = CrawlParams(
            start_url=url,
            max_depth=max_depth,
            max_pages=max_pages,
            same_origin=same_origin,
            url_pattern=url_pattern,
            wait=WaitStrategy(strategy="load"),
        )
        return await CrawlAction(params).execute(backend)
    finally:
        await backend.close()

@app.command()
def har(
    url: str = typer.Argument(..., help="URL to capture HAR for"),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Output file path (.har)"
    ),
    wait: int = typer.Option(
        3000, "--wait", help="Wait time after navigation (ms)"
    ),
    filter: str | None = typer.Option(
        None, "--filter", help="URL filter pattern"
    ),
) -> None:
    """Capture network traffic as HAR 1.2."""
    result = _run_async(_har(url, wait, filter))
    if result is None:
        return

    if output:
        Output.write_json(result, output)
        typer.echo(f"HAR saved to {output}")
    else:
        typer.echo(json.dumps(result, indent=2, default=str))

async def _har(url: str, wait: int, filter: str | None) -> Any:
    """Async helper for HAR capture."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        params = HarParams(url=url, wait=wait, filter=filter)
        return await HARAction(params).execute(backend)
    finally:
        await backend.close()

@app.command()
def screencast(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output_dir: str = typer.Option(
        "screencast", "--output", "-o", help="Output directory for frames"
    ),
    duration: float = typer.Option(5.0, "--duration", help="Capture duration in seconds"),
    fps: int = typer.Option(10, "--fps", help="Frames per second (approximate)"),
    quality: int = typer.Option(80, "--quality", help="JPEG quality (0-100)"),
    format: str = typer.Option("png", "--format", help="Image format (png or jpeg)"),
) -> None:
    """Capture a screencast from a web page and save frames as PNGs."""
    params = ScreencastParams(
        url=url,
        format=format,
        quality=quality,
        duration=duration,
        wait=WaitStrategy(strategy="load"),
    )
    frames = _run_async(_screencast(params, output_dir))
    if frames is None:
        return
    typer.echo(f"Saved {len(frames)} frames to {output_dir}/")

async def _screencast(params: ScreencastParams, output_dir: str) -> list[str]:
    """Capture screencast frames and save them to a directory.

    Args:
        params: Screencast parameters including URL, format, and duration.
        output_dir: Directory to save captured frames.

    Returns:
        List of saved frame file paths.
    """
    from wavexis.actions.screencast import ScreencastAction

    backend = _get_backend()
    action = ScreencastAction(params, output_dir=output_dir)
    return await action.execute(backend)

@app.command("dom-snapshot")
def dom_snapshot(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Capture a DOM snapshot of a web page."""
    result = _run_async(_dom_snapshot_action(url))
    if result is None:
        return
    _write_json_output(result, output, "DOM snapshot")

async def _dom_snapshot_action(url: str) -> dict[str, Any]:
    """Capture a DOM snapshot of a web page.

    Args:
        url: URL to navigate to.

    Returns:
        DOM snapshot data as a dictionary.
    """
    from wavexis.actions.dom_snapshot import DOMSnapshotAction, DOMSnapshotParams

    params = DOMSnapshotParams(
        url=url,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    act = DOMSnapshotAction(params)
    return await act.execute(backend)

