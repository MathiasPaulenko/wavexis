"""Output helpers for writing data to file or stdout."""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path
from typing import Any

try:
    from rich.console import Console

    _console_err: Console | None = Console(stderr=True)
    _console_out: Console | None = Console()
except ImportError:
    _console_err = None
    _console_out = None


def _has_rich() -> bool:
    """Check if rich console output is available.

    Returns:
        True if both error and output consoles are initialized, False otherwise.
    """
    return _console_err is not None and _console_out is not None


class Output:
    """Static helpers for writing output to file or stdout."""

    @staticmethod
    def write_bytes(data: bytes, path: str | None = None) -> None:
        """Write bytes to a file or stdout buffer.

        Args:
            data: The bytes to write.
            path: File path. If None, writes to stdout.buffer.
        """
        if path:
            Path(path).write_bytes(data)
        else:
            sys.stdout.buffer.write(data)

    @staticmethod
    def write_json(data: Any, path: str | None = None) -> None:
        """Write data as JSON to a file or stdout.

        Args:
            data: The data to serialize as JSON.
            path: File path. If None, prints to stdout.
        """
        text = json.dumps(data, indent=2, ensure_ascii=False)
        if path:
            Path(path).write_text(text, encoding="utf-8")
        else:
            print(text)

    @staticmethod
    def write_text(text: str, path: str | None = None) -> None:
        """Write text to a file or stdout.

        Args:
            text: The text to write.
            path: File path. If None, prints to stdout.
        """
        if path:
            Path(path).write_text(text, encoding="utf-8")
        else:
            print(text)

    @staticmethod
    def write_csv(data: list[dict[str, Any]], path: str | None = None) -> None:
        """Write a list of dicts as CSV to a file or stdout.

        Uses the union of all keys as column headers.

        Args:
            data: List of dicts to write as CSV rows.
            path: File path. If None, writes to stdout.
        """
        if not data:
            if path:
                Path(path).write_text("", encoding="utf-8")
            return

        fieldnames: list[str] = []
        for row in data:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)

        if path:
            with Path(path).open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
        else:
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            print(buf.getvalue(), end="")

    @staticmethod
    def error(msg: str) -> None:
        """Print an error message to stderr.

        Uses rich formatting if available, otherwise plain print.

        Args:
            msg: The error message to print.
        """
        if _has_rich() and _console_err is not None:
            _console_err.print(f"[bold red]Error:[/bold red] {msg}")
        else:
            print(f"Error: {msg}", file=sys.stderr)

    @staticmethod
    def success(msg: str) -> None:
        """Print a success message to stdout.

        Uses rich formatting if available, otherwise plain print.

        Args:
            msg: The success message to print.
        """
        if _has_rich() and _console_out is not None:
            _console_out.print(f"[bold green]✓[/bold green] {msg}")
        else:
            print(msg)

    @staticmethod
    def info(msg: str) -> None:
        """Print an info message to stdout.

        Uses rich formatting if available, otherwise plain print.

        Args:
            msg: The info message to print.
        """
        if _has_rich() and _console_out is not None:
            _console_out.print(f"[bold blue]ℹ[/bold blue] {msg}")
        else:
            print(msg)
