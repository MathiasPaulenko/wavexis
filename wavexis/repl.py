"""Interactive REPL for wavexis browser sessions."""

from __future__ import annotations

import asyncio
import contextlib
import shlex
from pathlib import Path
from typing import Any

from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, ScreenshotParams, WaitStrategy
from wavexis.exceptions import WavexisError

__all__ = ["HELP_TEXT", "execute_repl_command", "parse_command", "repl_loop"]

HELP_TEXT = """\
Available commands:
  navigate <url>          Navigate to a URL
  screenshot [file]       Take a screenshot (saves to file or screenshot.png)
  eval <expression>       Evaluate a JS expression
  click <selector>        Click an element
  type <selector> <text>  Type text into an element
  fill <selector> <value> Fill an input with a value
  hover <selector>        Hover over an element
  key <key>               Press a keyboard key (e.g. Enter, Tab)
  cookies                 Get all cookies
  url                     Get current page URL
  title                   Get page title
  wait <selector>         Wait for an element to appear
  back                    Go back in history
  forward                 Go forward in history
  reload                  Reload the page
  help                    Show this help
  exit / quit             Exit the REPL
"""


def parse_command(line: str) -> tuple[str, list[str]]:
    """Parse a REPL input line into command and arguments.

    Args:
        line: Raw input line from the user.

    Returns:
        Tuple of (command, args) where command is lowercase and args is a list.

    Raises:
        ValueError: If the line is empty.
    """
    parts = shlex.split(line.strip())
    if not parts:
        raise ValueError("Empty command")
    return parts[0].lower(), parts[1:]


async def execute_repl_command(
    backend: AbstractBackend,
    command: str,
    args: list[str],
) -> str | bytes | None:
    """Execute a single REPL command against the backend.

    Args:
        backend: An already-launched AbstractBackend instance.
        command: Command name (lowercase).
        args: Command arguments.

    Returns:
        Result string, bytes (for screenshots), or None.

    Raises:
        ValueError: If the command is unknown or arguments are invalid.
    """
    if command == "navigate":
        if not args:
            raise ValueError("Usage: navigate <url>")
        await backend.navigate(args[0], WaitStrategy(strategy="load"))
        return f"Navigated to {args[0]}"

    if command == "screenshot":
        params = ScreenshotParams(
            url="",
            full_page=True,
            format="png",
            wait=WaitStrategy(strategy="load"),
        )
        screenshot_data = await backend.screenshot(params)
        filename = args[0] if args else "screenshot.png"
        await asyncio.to_thread(Path(filename).write_bytes, screenshot_data)
        return f"Screenshot saved to {filename} ({len(screenshot_data)} bytes)"

    if command == "eval":
        if not args:
            raise ValueError("Usage: eval <expression>")
        expr = " ".join(args)
        result = await backend.eval(expr, await_promise=True)
        return str(result)

    if command == "click":
        if not args:
            raise ValueError("Usage: click <selector>")
        await backend.click(args[0])
        return f"Clicked {args[0]}"

    if command == "type":
        if len(args) < 2:
            raise ValueError("Usage: type <selector> <text>")
        await backend.type_text(args[0], " ".join(args[1:]))
        return f"Typed into {args[0]}"

    if command == "fill":
        if len(args) < 2:
            raise ValueError("Usage: fill <selector> <value>")
        await backend.fill(args[0], " ".join(args[1:]))
        return f"Filled {args[0]}"

    if command == "hover":
        if not args:
            raise ValueError("Usage: hover <selector>")
        await backend.hover(args[0])
        return f"Hovered {args[0]}"

    if command == "key":
        if not args:
            raise ValueError("Usage: key <key>")
        await backend.key_press(args[0])
        return f"Pressed {args[0]}"

    if command == "cookies":
        import json

        cookies_data = await backend.get_cookies()
        return json.dumps(cookies_data, indent=2, default=str)

    if command == "url":
        url_data = await backend.eval("window.location.href", await_promise=False)
        return str(url_data)

    if command == "title":
        title_data = await backend.eval("document.title", await_promise=False)
        return str(title_data)

    if command == "wait":
        if not args:
            raise ValueError("Usage: wait <selector>")
        await backend.wait_for(WaitStrategy(strategy="selector", selector=args[0]))
        return f"Waited for {args[0]}"

    if command in ("back", "forward", "reload"):
        from wavexis.actions.navigate import BackAction, ForwardAction, ReloadAction

        if command == "back":
            await BackAction(None).execute(backend)
        elif command == "forward":
            await ForwardAction(None).execute(backend)
        else:
            await ReloadAction(False).execute(backend)
        return f"{command.capitalize()} done"

    if command in ("exit", "quit"):
        return "__EXIT__"

    if command == "help":
        return HELP_TEXT

    raise ValueError(f"Unknown command: {command}. Type 'help' for available commands.")


async def repl_loop(
    backend: AbstractBackend,
    initial_url: str | None = None,
    input_fn: Any = input,
    output_fn: Any = print,
) -> list[str]:
    """Run the interactive REPL loop.

    Args:
        backend: An AbstractBackend instance (will be launched if not already).
        initial_url: Optional URL to navigate to before starting the REPL.
        input_fn: Input function (defaults to built-in input).
        output_fn: Output function (defaults to built-in print).

    Returns:
        List of command strings that were executed.
    """
    await backend.launch(BrowserOptions(headless=False))
    if initial_url:
        await backend.navigate(initial_url, WaitStrategy(strategy="load"))
        output_fn(f"Navigated to {initial_url}")

    output_fn("wavexis REPL — type 'help' for commands, 'exit' to quit")

    executed: list[str] = []
    while True:
        try:
            line = input_fn(">>> ")
        except (EOFError, KeyboardInterrupt):
            output_fn("\nExiting...")
            break

        if not line.strip():
            continue

        try:
            command, args = parse_command(line)
        except ValueError:
            continue

        try:
            result = await execute_repl_command(backend, command, args)
        except ValueError as e:
            output_fn(f"Error: {e}")
            continue
        except WavexisError as e:
            output_fn(f"Error: {e}")
            continue
        except OSError as e:
            output_fn(f"Error: {e}")
            continue

        if result == "__EXIT__":
            output_fn("Exiting...")
            break

        if result is not None:
            output_fn(result)

        executed.append(line)

    with contextlib.suppress(WavexisError, OSError):
        await backend.close()

    return executed
