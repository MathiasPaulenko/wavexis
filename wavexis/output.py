"""Output helpers for writing data to file or stdout."""

from __future__ import annotations

import contextlib
import csv
import io
import json
import sys
from pathlib import Path
from typing import Any

import typer

__all__ = ["Output", "set_allowed_base_dir", "validate_path"]


_ALLOWED_BASE_DIR: Path | None = None


def set_allowed_base_dir(path: str | Path | None) -> None:
    """Set the base directory that file paths must be inside of.

    When set, :func:`validate_path` resolves the supplied path and ensures it
    is located inside the configured base directory (after resolving symlinks).
    Call with ``None`` to disable the restriction.

    Args:
        path: Absolute path to the allowed base directory, or None to allow
            any path (default, not recommended for server mode).
    """
    global _ALLOWED_BASE_DIR
    _ALLOWED_BASE_DIR = Path(path).resolve() if path else None


def validate_path(path: str | Path, *, base_dir: str | Path | None = None) -> Path:
    """Validate a user-supplied file or directory path.

    Rejects parent-directory traversal, null bytes and, when a base directory
    is configured, paths that resolve outside of it.

    Args:
        path: The path to validate.
        base_dir: Optional base directory the path must be inside of. If not
            provided, the module-level base directory set by
            :func:`set_allowed_base_dir` is used.

    Returns:
        The resolved Path object.

    Raises:
        ValueError: If the path is invalid or outside the allowed base directory.
    """
    if isinstance(path, str) and "\x00" in path:
        raise ValueError(f"Invalid path: {path}")
    p = Path(path)
    if ".." in p.parts or any("\x00" in part for part in p.parts):
        raise ValueError(f"Invalid path: {path}")

    allowed = Path(base_dir).resolve() if base_dir is not None else _ALLOWED_BASE_DIR
    if allowed is not None:
        resolved = p.resolve()
        try:
            resolved.relative_to(allowed)
        except ValueError as exc:
            raise ValueError(f"Invalid path: {path}") from exc
        return resolved
    return p


try:
    import yaml as _yaml
except ImportError:
    _yaml = None  # type: ignore[assignment]

try:
    from rich.console import Console

    # On Windows, the default console encoding (cp1252/cp850) cannot encode
    # many unicode glyphs (e.g. the checkmark U+2713 used in success
    # messages), which causes `OSError: [Errno 22] Invalid argument` when
    # Rich flushes its buffer. Reconfigure stdout/stderr to use UTF-8 so
    # that Rich can render unicode safely. See bug #1 in ref/cli-bugs.md.
    if sys.platform == "win32":
        for _stream_name in ("stdout", "stderr"):
            _stream = getattr(sys, _stream_name, None)
            # `reconfigure` is available on TextIOWrapper (Python 3.7+) and
            # preserves the underlying buffer, so it is safe to use even
            # when pytest or other tools have replaced sys.stdout.
            if _stream is not None and hasattr(_stream, "reconfigure"):
                # Fall back to the original encoding if reconfigure fails.
                with contextlib.suppress(AttributeError, OSError, ValueError):
                    _stream.reconfigure(encoding="utf-8", errors="replace")

    _console_err: Console | None = Console(stderr=True, legacy_windows=False)
    _console_out: Console | None = Console(legacy_windows=False)
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
            path: File path. If None or "-", writes to stdout.buffer.
        """
        if path and path != "-":
            try:
                validate_path(path).write_bytes(data)
            except OSError as e:
                Output.error(f"Failed to write {path}: {e}")
                raise typer.Exit(1) from e
        else:
            sys.stdout.buffer.write(data)

    @staticmethod
    def write_json(data: Any, path: str | None = None) -> None:
        """Write data as JSON to a file or stdout.

        Args:
            data: The data to serialize as JSON.
            path: File path. If None or "-", prints to stdout.
        """
        text = json.dumps(data, indent=2, ensure_ascii=False)
        Output.write_text(text, path)

    @staticmethod
    def write_text(text: str, path: str | None = None) -> None:
        """Write text to a file or stdout.

        Args:
            text: The text to write.
            path: File path. If None or "-", prints to stdout.
        """
        if path and path != "-":
            try:
                validate_path(path).write_text(text, encoding="utf-8")
            except OSError as e:
                Output.error(f"Failed to write {path}: {e}")
                raise typer.Exit(1) from e
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
            return

        fieldnames: list[str] = []
        seen: set[str] = set()
        for row in data:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)

        if path and path != "-":
            try:
                with validate_path(path).open("w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
            except OSError as e:
                Output.error(f"Failed to write {path}: {e}")
                raise typer.Exit(1) from e
        else:
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            print(buf.getvalue(), end="")

    @staticmethod
    def write_yaml(data: Any, path: str | None = None) -> None:
        """Write data as YAML to a file or stdout.

        Args:
            data: The data to serialize as YAML.
            path: File path. If None, prints to stdout.
        """
        if _yaml is None:
            raise ImportError("PyYAML is required for YAML output. Run: pip install pyyaml")
        text = _yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        if path and path != "-":
            Output.write_text(text, path)
        else:
            print(text, end="")

    @staticmethod
    def write_formatted(
        data: Any,
        fmt: str,
        path: str | None = None,
    ) -> None:
        """Write data in the specified format.

        Args:
            data: The data to write.
            fmt: Output format — "json", "csv", or "yaml".
            path: File path. If None, prints to stdout.

        Raises:
            ValueError: If the format is not supported.
        """
        if fmt == "json":
            Output.write_json(data, path)
        elif fmt == "csv":
            if not isinstance(data, list):
                data = [data] if isinstance(data, dict) else [{"value": data}]
            Output.write_csv(data, path)
        elif fmt == "yaml":
            Output.write_yaml(data, path)
        else:
            raise ValueError(f"Unsupported format: {fmt}. Use json, csv, or yaml.")

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
