"""input commands for wavexis CLI."""

from __future__ import annotations

from typing import Annotated

import typer

from wavexis.cli._shared import (
    _close_backend,
    _get_backend,
    _run_async,
    app,
)
from wavexis.config import InputParams, WaitStrategy

input_app = typer.Typer(help="Input commands (click, type, fill, select, hover, key, drag, tap)")
app.add_typer(input_app, name="input")

@input_app.command("click")
def input_click(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Argument(..., help="CSS selector for element to click"),
    button: str = typer.Option("left", "--button", help="Mouse button (left, right, middle)"),
    click_count: int = typer.Option(1, "--count", help="Number of clicks"),
) -> None:
    """Click an element on a web page."""
    _run_async(_input_action(
        url, "click", selector=selector, button=button, click_count=click_count
    ))
    typer.echo(f"Clicked '{selector}' on {url}")


@input_app.command("right-click")
def input_right_click(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Argument(..., help="CSS selector for element to right-click"),
) -> None:
    """Right-click an element on a web page."""
    _run_async(_input_action(url, "right_click", selector=selector))
    typer.echo(f"Right-clicked '{selector}' on {url}")


@input_app.command("double-click")
def input_double_click(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Argument(..., help="CSS selector for element to double-click"),
) -> None:
    """Double-click an element on a web page."""
    _run_async(_input_action(url, "double_click", selector=selector))
    typer.echo(f"Double-clicked '{selector}' on {url}")

@input_app.command("type")
def input_type(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Argument(..., help="CSS selector for input element"),
    text: str = typer.Argument(..., help="Text to type"),
    delay: int = typer.Option(0, "--delay", help="Delay between keystrokes (ms)"),
) -> None:
    """Type text into an element on a web page."""
    _run_async(_input_action(url, "type", selector=selector, text=text, delay=delay))
    typer.echo(f"Typed text into '{selector}' on {url}")

@input_app.command("fill")
def input_fill(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Argument(..., help="CSS selector for input element"),
    value: str = typer.Argument(..., help="Value to fill"),
) -> None:
    """Fill an input element with a value."""
    _run_async(_input_action(url, "fill", selector=selector, value=value))
    typer.echo(f"Filled '{selector}' with value on {url}")

@input_app.command("select")
def input_select(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Argument(..., help="CSS selector for select element"),
    value: str = typer.Argument(..., help="Option value to select"),
) -> None:
    """Select an option in a <select> element."""
    _run_async(_input_action(url, "select", selector=selector, value=value))
    typer.echo(f"Selected '{value}' in '{selector}' on {url}")

@input_app.command("hover")
def input_hover(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Argument(..., help="CSS selector for element to hover"),
) -> None:
    """Hover over an element on a web page."""
    _run_async(_input_action(url, "hover", selector=selector))
    typer.echo(f"Hovered over '{selector}' on {url}")

@input_app.command("key")
def input_key(
    url: str = typer.Argument(..., help="URL to navigate to"),
    key: str = typer.Argument(..., help="Key to press (e.g. Enter, Tab, Escape)"),
) -> None:
    """Press a keyboard key on a web page."""
    _run_async(_input_action(url, "key", key=key))
    typer.echo(f"Pressed key '{key}' on {url}")

@input_app.command("drag")
def input_drag(
    url: str = typer.Argument(..., help="URL to navigate to"),
    source: str = typer.Argument(..., help="CSS selector for element to drag"),
    target: str = typer.Argument(..., help="CSS selector for drop target"),
) -> None:
    """Drag an element to a target on a web page."""
    _run_async(_input_action(url, "drag", source=source, target=target))
    typer.echo(f"Dragged '{source}' to '{target}' on {url}")

@input_app.command("tap")
def input_tap(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Argument(..., help="CSS selector for element to tap"),
) -> None:
    """Tap an element on a web page (touch emulation)."""
    _run_async(_input_action(url, "tap", selector=selector))
    typer.echo(f"Tapped '{selector}' on {url}")

@input_app.command("scroll")
def input_scroll(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Option(
        "", "--selector", help="CSS selector to scroll to (if empty, scroll by offset)"
    ),
    x: int = typer.Option(0, "--x", help="Horizontal scroll offset"),
    y: int = typer.Option(0, "--y", help="Vertical scroll offset"),
) -> None:
    """Scroll to an element or by offset on a web page."""
    _run_async(_input_action(url, "scroll", selector=selector, scroll_x=x, scroll_y=y))
    if selector:
        typer.echo(f"Scrolled to '{selector}' on {url}")
    else:
        typer.echo(f"Scrolled by ({x}, {y}) on {url}")

@input_app.command("upload")
def input_upload(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Argument(..., help="CSS selector for file input element"),
    files: Annotated[list[str], typer.Argument(help="Absolute file paths to upload")] = [],  # noqa: B006
) -> None:
    """Upload files to a file input element on a web page."""
    _run_async(_input_action(url, "upload", selector=selector, files=files))
    typer.echo(f"Uploaded {len(files)} file(s) to '{selector}' on {url}")

async def _input_action(
    url: str,
    action: str,
    selector: str = "",
    text: str | None = None,
    value: str | None = None,
    key: str | None = None,
    button: str = "left",
    click_count: int = 1,
    delay: int = 0,
    source: str | None = None,
    target: str | None = None,
    scroll_x: int = 0,
    scroll_y: int = 0,
    files: list[str] | None = None,
) -> None:
    """Async helper for input actions."""
    from wavexis.actions.input import InputAction

    backend = _get_backend()
    params = InputParams(
        url=url,
        action=action,
        selector=selector,
        text=text,
        value=value,
        key=key,
        button=button,
        click_count=click_count,
        delay=delay,
        source=source,
        target=target,
        scroll_x=scroll_x,
        scroll_y=scroll_y,
        files=files,
        wait=WaitStrategy(strategy="load"),
    )
    try:
        await InputAction(params).execute(backend)
    finally:
        await _close_backend(backend)

