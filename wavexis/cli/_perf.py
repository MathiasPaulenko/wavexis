"""perf commands for wavexis CLI."""

from __future__ import annotations

__all__ = ["_perf", "_print_perf_summary", "cwv"]

from typing import Any

import typer

from wavexis.cli._shared import (
    Output,
    _browser_options,
    _close_backend,
    _get_backend,
    _run_async,
    _write_json_output,
    app,
    _wait_strategy,
)
perf_app = typer.Typer(
    help="Performance commands (metrics, trace, profile, heap, coverage)",
    invoke_without_command=True,
)
app.add_typer(perf_app, name="perf")


@perf_app.callback(invoke_without_command=True)
def perf_callback(
    ctx: typer.Context,
    url: str = typer.Option(
        None,
        "--url",
        help=(
            "Shortcut: run `perf metrics <url>` when no subcommand is given. "
            "Equivalent to `wavexis perf metrics <url>`."
        ),
    ),
) -> None:
    """Performance commands.

    If a URL is passed via ``--url`` and no subcommand is given, this
    delegates to ``perf metrics <url>`` for backward compatibility with
    the documented ``wavexis perf <url>`` syntax (Bug #30).

    Note: ``wavexis perf <url>`` (positional) does NOT work because Typer
    interprets the first positional argument as a subcommand name. Use
    ``wavexis perf --url <url>`` or ``wavexis perf metrics <url>``.
    """
    if ctx.invoked_subcommand is None and url:
        # Delegate to the metrics subcommand.
        ctx.invoke(perf_metrics, url=url, output="-")


@perf_app.command("metrics")
def perf_metrics(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get performance metrics from a web page."""
    result = _run_async(_perf_action(url, "metrics"))
    if result is None:
        return
    _write_json_output(result, output, "metrics")


@perf_app.command("trace")
def perf_trace(
    url: str = typer.Argument(..., help="URL to navigate to"),
    duration: int = typer.Option(3000, "--duration", help="Trace duration in ms"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Capture a performance trace from a web page."""
    result = _run_async(_perf_action(url, "trace", duration_ms=duration))
    if result is None:
        return
    _write_json_output(result, output, "trace")


@perf_app.command("profile")
def perf_profile(
    url: str = typer.Argument(..., help="URL to navigate to"),
    duration: int = typer.Option(3000, "--duration", help="Profile duration in ms"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Capture a CPU profile from a web page."""
    result = _run_async(_perf_action(url, "profile", duration_ms=duration))
    if result is None:
        return
    _write_json_output(result, output, "profile")


@perf_app.command("heap")
def perf_heap(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Capture a heap snapshot from a web page."""
    result = _run_async(_perf_action(url, "heap"))
    if result is None:
        return
    _write_json_output(result, output, "heap snapshot")


@perf_app.command("coverage")
def perf_coverage(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get JavaScript code coverage from a web page."""
    result = _run_async(_perf_action(url, "coverage"))
    if result is None:
        return
    _write_json_output(result, output, "JS coverage")


@perf_app.command("css-coverage")
def perf_css_coverage(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get CSS rule usage coverage from a web page."""
    result = _run_async(_perf_action(url, "css-coverage"))
    if result is None:
        return
    _write_json_output(result, output, "CSS coverage")


@perf_app.command("disable")
def performance_disable() -> None:
    """Disable the Performance domain."""
    _run_async(_perf_domain_op(lambda b: b.performance_disable()))
    typer.echo("Performance domain disabled")


@perf_app.command("enable")
def performance_enable() -> None:
    """Enable the Performance domain."""
    _run_async(_perf_domain_op(lambda b: b.performance_enable()))
    typer.echo("Performance domain enabled")


@perf_app.command("get-metrics")
def performance_get_metrics(
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get current values of run-time metrics."""
    result = _run_async(_perf_domain_op(lambda b: b.performance_get_metrics()))
    if result is None:
        return
    _write_json_output(result, output, "metrics")


@perf_app.command("timeline-enable")
def performance_timeline_enable() -> None:
    """Enable the PerformanceTimeline domain to receive timeline events."""
    _run_async(_perf_domain_op(lambda b: b.performance_timeline_enable()))
    typer.echo("PerformanceTimeline domain enabled")


@perf_app.command("set-time-domain")
def performance_set_time_domain(
    time_domain: str = typer.Argument(..., help="Time domain ('timeTicks' or 'threadTicks')"),
) -> None:
    """Set the time domain for collecting and reporting durations."""
    _run_async(_perf_domain_op(lambda b: b.performance_set_time_domain(time_domain)))
    typer.echo(f"Time domain set to {time_domain}")


async def _perf_domain_op(action_fn: Any) -> Any:
    """Async helper for Performance domain operations."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        return await action_fn(backend)
    finally:
        await _close_backend(backend)


async def _perf_action(url: str, action: str, duration_ms: int = 3000) -> dict[str, Any]:
    """Execute a performance action on a web page.

    Args:
        url: URL to navigate to.
        action: Performance action ("metrics", "trace", "profile",
            "heap", "coverage", "css-coverage").
        duration_ms: Duration in milliseconds for trace/profile actions.

    Returns:
        Performance data as a dictionary.
    """
    from wavexis.actions.performance import PerformanceAction, PerformanceParams

    params = PerformanceParams(
        url=url,
        action=action,
        duration_ms=duration_ms,
        wait=_wait_strategy(),
    )
    backend = _get_backend()
    act = PerformanceAction(params)
    try:
        await backend.launch(_browser_options())
        return await act.execute(backend)
    finally:
        await _close_backend(backend)


@app.command()
def perf(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json, yaml"),
    metric: str = typer.Option(
        "metrics",
        "--metric",
        "-m",
        help=("Metric to capture: metrics, trace, profile, heap-snapshot, coverage, css-coverage"),
    ),
    duration: int = typer.Option(
        3000, "--duration", "-d", help="Duration in ms (for trace/profile)"
    ),
) -> None:
    """Capture performance metrics from a web page.

    Supports: metrics (LCP/FCP/CLS/TTFB), trace, profile,
    heap-snapshot, coverage, css-coverage.
    """
    valid_metrics = {
        "metrics",
        "trace",
        "profile",
        "heap-snapshot",
        "coverage",
        "css-coverage",
    }
    if metric not in valid_metrics:
        typer.echo(
            f"Error: invalid metric '{metric}'. Valid: {', '.join(sorted(valid_metrics))}",
            err=True,
        )
        raise typer.Exit(1)

    result = _run_async(_perf(url, metric, duration))
    if result is None:
        return

    if metric == "metrics":
        _print_perf_summary(result)

    Output.write_formatted(result, format, output)
    if output:
        typer.echo(f"Performance data saved to {output}")


def _print_perf_summary(metrics: Any) -> None:
    """Print a human-readable summary of key performance metrics.

    Args:
        metrics: Dict of performance metrics from backend.perf_metrics().
    """
    if not isinstance(metrics, dict):
        return

    key_metrics = [
        ("LargestContentfulPaint", "LCP"),
        ("FirstContentfulPaint", "FCP"),
        ("CumulativeLayoutShift", "CLS"),
        ("TimeToFirstByte", "TTFB"),
        ("DOMContentLoadEventEnd", "DCL"),
        ("LoadEventEnd", "Load"),
    ]

    typer.echo("\nPerformance Summary:")
    typer.echo("-" * 40)
    for raw_key, label in key_metrics:
        value = metrics.get(raw_key)
        if value is not None:
            if isinstance(value, (int, float)):
                if label in ("CLS",):
                    typer.echo(f"  {label:8s} {value:.3f}")
                else:
                    typer.echo(f"  {label:8s} {value:.0f} ms")
            else:
                typer.echo(f"  {label:8s} {value}")
    typer.echo("-" * 40)


async def _perf(url: str, metric: str, duration: int) -> Any:
    """Async helper for performance metrics capture.

    Args:
        url: URL to navigate to.
        metric: Metric type to capture.
        duration: Duration in ms for trace/profile.

    Returns:
        Performance data from the backend.
    """
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, _wait_strategy())

        if metric == "metrics":
            return await backend.perf_metrics()
        if metric == "trace":
            return await backend.perf_trace(duration_ms=duration)
        if metric == "profile":
            return await backend.perf_profile(duration_ms=duration)
        if metric == "heap-snapshot":
            return await backend.perf_heap_snapshot()
        if metric == "coverage":
            return await backend.perf_coverage()
        if metric == "css-coverage":
            return await backend.perf_css_coverage()
        return {}
    finally:
        await _close_backend(backend)


@app.command()
def cwv(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
    format: str = typer.Option("json", "--format", "-f", help="Output format (json)"),
    observe: int = typer.Option(
        5000, "--observe", help="Milliseconds to observe PerformanceObserver entries"
    ),
    budget: str = typer.Option(
        "",
        "--budget",
        help='JSON budgets, e.g. \'{"lcp_ms":2500,"cls":0.1,"inp_ms":200}\'',
    ),
) -> None:
    """Measure Core Web Vitals (LCP, CLS, INP) with scoring and ratings.

    \b
    wavexis cwv https://example.com
    wavexis cwv https://example.com --budget '{"lcp_ms":2500,"cls":0.1}'
    """
    import json

    budgets: dict[str, float] = {}
    if budget:
        try:
            budgets = json.loads(budget)
        except json.JSONDecodeError as e:
            typer.echo(f"Error: invalid JSON budget: {e}", err=True)
            raise typer.Exit(1) from e

    async def _cwv() -> dict[str, Any]:
        from wavexis.actions.core_web_vitals import (
            CoreWebVitalsAction,
            CoreWebVitalsParams,
        )

        params = CoreWebVitalsParams(
            url=url,
            wait=_wait_strategy(),
            browser=_browser_options(),
            budgets=budgets,
            observe_ms=observe,
        )
        action = CoreWebVitalsAction(params)
        backend = _get_backend()
        await backend.launch(_browser_options())
        try:
            return await action.execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_cwv())
    if result is None:
        return

    if isinstance(result, dict):
        score = result.get("score", 0)
        ratings = result.get("ratings", {})
        metrics = result.get("metrics", {})
        typer.echo("\nCore Web Vitals:")
        typer.echo("-" * 50)
        typer.echo(f"  Score: {score}/100")
        for key in ("lcp_ms", "cls", "inp_ms", "fcp_ms", "ttfb_ms", "tbt_ms", "load_ms"):
            val = metrics.get(key, 0)
            rating = ratings.get(key, "n/a")
            if key == "cls":
                typer.echo(f"  {key:10s} {val:.3f}    [{rating}]")
            else:
                typer.echo(f"  {key:10s} {val:.0f} ms  [{rating}]")
        budgets_result = result.get("budgets")
        if budgets_result:
            typer.echo("-" * 50)
            all_pass = budgets_result.get("all_pass", False)
            typer.echo(f"  Budgets: {'PASS' if all_pass else 'FAIL'}")
            for bk, bv in budgets_result.items():
                if bk == "all_pass":
                    continue
                status = "PASS" if bv["pass"] else "FAIL"
                typer.echo(f"    {bk}: {bv['value']} / {bv['budget']} [{status}]")
        typer.echo("-" * 50)

    Output.write_formatted(result, format, output)
    if output and output != "-":
        typer.echo(f"Results saved to {output}")
