"""debug commands for wavexis CLI."""

from __future__ import annotations

from typing import Any

import typer

from wavexis.cli._shared import (
    _echo,
    _get_backend,
    _run_async,
    _write_json_output,
    app,
)
from wavexis.config import WaitStrategy

css_app = typer.Typer(help="CSS inspection commands (styles, stylesheets, rules, computed)")
app.add_typer(css_app, name="css")

debug_app = typer.Typer(help="Debugging commands (breakpoint, step, pause, resume, listeners)")
app.add_typer(debug_app, name="debug")

overlay_app = typer.Typer(help="Overlay commands (highlight, clear)")
app.add_typer(overlay_app, name="overlay")

@css_app.command("styles")
def css_styles(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get inline and matched styles for an element."""
    result = _run_async(_css_action(url, "styles", selector=selector))
    if result is None:
        return
    _write_json_output(result, output, "styles")

@css_app.command("stylesheets")
def css_stylesheets(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """List all stylesheets in the page."""
    result = _run_async(_css_action(url, "stylesheets"))
    if result is None:
        return
    _write_json_output(result, output, "stylesheets")

@css_app.command("rules")
def css_rules(
    url: str = typer.Argument(..., help="URL to navigate to"),
    stylesheet_id: str = typer.Option(..., "--stylesheet-id", help="Stylesheet ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get CSS rules from a specific stylesheet."""
    result = _run_async(_css_action(url, "rules", stylesheet_id=stylesheet_id))
    if result is None:
        return
    _write_json_output(result, output, "rules")

@css_app.command("computed")
def css_computed(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get computed styles for an element."""
    result = _run_async(_css_action(url, "computed", selector=selector))
    if result is None:
        return
    _write_json_output(result, output, "computed styles")

async def _css_action(
    url: str,
    action: str,
    selector: str | None = None,
    stylesheet_id: str | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    """Execute a CSS action on a web page.

    Args:
        url: URL to navigate to.
        action: CSS action ("styles", "stylesheets", "rules", "computed").
        selector: CSS selector for styles/computed actions.
        stylesheet_id: Stylesheet ID for rules action.

    Returns:
        CSS data as a dict or list of dicts depending on the action.
    """
    from wavexis.actions.css import CSSAction, CSSActionParams

    params = CSSActionParams(
        url=url,
        action=action,
        selector=selector,
        stylesheet_id=stylesheet_id,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    act = CSSAction(params)
    return await act.execute(backend)

@debug_app.command("breakpoint")
def debug_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    script_url: str = typer.Option(..., "--url", help="Script URL for breakpoint"),
    line: int = typer.Option(..., "--line", help="Line number (0-based)"),
    condition: str | None = typer.Option(None, "--condition", help="Condition expression"),
) -> None:
    """Set a breakpoint by URL and line number."""
    result = _run_async(
        _debug_action(url, "breakpoint", script_url=script_url, line=line, condition=condition)
    )
    if result is None:
        return
    _echo(f"Breakpoint set: {result}")

@debug_app.command("function-breakpoint")
def debug_function_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    function_name: str = typer.Option(..., "--function-name", help="Function name"),
) -> None:
    """Set a breakpoint by function name."""
    result = _run_async(
        _debug_action(url, "function_breakpoint", function_name=function_name)
    )
    if result is None:
        return
    _echo(f"Breakpoint set: {result}")

@debug_app.command("remove-breakpoint")
def debug_remove_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    breakpoint_id: str = typer.Option(..., "--breakpoint-id", help="Breakpoint ID"),
) -> None:
    """Remove a breakpoint by ID."""
    _run_async(_debug_action(url, "remove_breakpoint", breakpoint_id=breakpoint_id))
    _echo(f"Breakpoint removed: {breakpoint_id}")

@debug_app.command("step-over")
def debug_step_over(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Step over the current statement."""
    _run_async(_debug_action(url, "step_over"))
    _echo("Stepped over")

@debug_app.command("step-into")
def debug_step_into(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Step into the current function call."""
    _run_async(_debug_action(url, "step_into"))
    _echo("Stepped into")

@debug_app.command("step-out")
def debug_step_out(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Step out of the current function."""
    _run_async(_debug_action(url, "step_out"))
    _echo("Stepped out")

@debug_app.command("pause")
def debug_pause(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Pause JavaScript execution."""
    _run_async(_debug_action(url, "pause"))
    _echo("Paused")

@debug_app.command("resume")
def debug_resume(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Resume JavaScript execution."""
    _run_async(_debug_action(url, "resume"))
    _echo("Resumed")

@debug_app.command("listeners")
def debug_listeners(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get event listeners attached to an element."""
    result = _run_async(_debug_action(url, "listeners", selector=selector))
    if result is None:
        return
    _write_json_output(result, output, "listeners")

async def _debug_action(
    url: str,
    action: str,
    script_url: str | None = None,
    line: int | None = None,
    condition: str | None = None,
    function_name: str | None = None,
    breakpoint_id: str | None = None,
    selector: str | None = None,
) -> Any:
    """Execute a debug action on a web page.

    Args:
        url: URL to navigate to.
        action: Debug action ("breakpoint", "function_breakpoint", "remove_breakpoint",
            "step_over", "step_into", "step_out", "pause", "resume", "listeners").
        script_url: Script URL for breakpoint action.
        line: Line number for breakpoint action.
        condition: Condition expression for conditional breakpoints.
        function_name: Function name for function_breakpoint action.
        breakpoint_id: Breakpoint ID for remove_breakpoint action.
        selector: CSS selector for listeners action.

    Returns:
        Result of the debug operation.
    """
    from wavexis.actions.debug import DebugAction, DebugActionParams

    params = DebugActionParams(
        url=url,
        action=action,
        script_url=script_url,
        line=line,
        condition=condition,
        function_name=function_name,
        breakpoint_id=breakpoint_id,
        selector=selector,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    act = DebugAction(params)
    return await act.execute(backend)

@overlay_app.command("highlight")
def overlay_highlight(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector"),
    color: str = typer.Option("rgba(255,0,0,0.5)", "--color", help="RGBA color"),
) -> None:
    """Highlight an element with a colored overlay."""
    _run_async(_overlay_action(url, "highlight", selector=selector, color=color))
    _echo(f"Highlighted: {selector}")

@overlay_app.command("clear")
def overlay_clear(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Clear all highlight overlays."""
    _run_async(_overlay_action(url, "clear"))
    _echo("Overlay cleared")

async def _overlay_action(
    url: str,
    action: str,
    selector: str | None = None,
    color: str = "rgba(255,0,0,0.5)",
) -> None:
    """Execute an overlay action on a web page.

    Args:
        url: URL to navigate to.
        action: Overlay action ("highlight" or "clear").
        selector: CSS selector for highlight action.
        color: RGBA color for highlight overlay.
    """
    from wavexis.actions.overlay import OverlayAction, OverlayParams

    params = OverlayParams(
        url=url,
        action=action,
        selector=selector,
        color=color,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    act = OverlayAction(params)
    await act.execute(backend)

