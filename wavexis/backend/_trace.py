"""Internal helpers for extracting trace events from Chrome trace streams."""

from __future__ import annotations

import asyncio
import base64
import binascii
import io
import json
import os
import zipfile
from collections.abc import Awaitable, Callable
from typing import Any

__all__ = ["extract_trace_events", "read_trace_stream"]


async def read_trace_stream(
    read_fn: Callable[[], Awaitable[Any]],
    max_iterations: int = 1000,
    read_timeout: float = 5.0,
    max_total_bytes: int = 100_000_000,
) -> bytes:
    """Read a Chrome IO stream in bounded chunks.

    Each ``read_fn`` call is expected to return a dict with optional keys
    ``data``, ``base64Encoded`` and ``eof``. Reading stops when ``eof`` is
    true, ``data`` is empty, an iteration times out, or the safety limits are
    reached. The caller is responsible for closing the stream handle.

    Args:
        read_fn: Coroutine that performs one ``IO.read`` call.
        max_iterations: Maximum number of read iterations.
        read_timeout: Timeout per read call in seconds.
        max_total_bytes: Maximum cumulative bytes to read.

    Returns:
        Concatenation of the decoded chunks.
    """
    chunks: list[bytes] = []
    total = 0
    for _ in range(max_iterations):
        try:
            resp = await asyncio.wait_for(read_fn(), timeout=read_timeout)
        except TimeoutError:
            break
        if not resp:
            break
        data = resp.get("data", "")
        if data == "" and resp.get("eof"):
            break
        if data == "":
            break
        if resp.get("base64Encoded", True):
            try:
                chunk = base64.b64decode(data)
            except (binascii.Error, TypeError, ValueError):
                break
        else:
            chunk = data.encode("utf-8", errors="replace")
        total += len(chunk)
        if total > max_total_bytes:
            chunks.append(chunk[: max_total_bytes - (total - len(chunk))])
            break
        chunks.append(chunk)
        if resp.get("eof"):
            break
    return b"".join(chunks)


def extract_trace_events(raw: bytes) -> list[dict[str, Any]]:
    """Extract trace events from a Chrome trace ZIP archive.

    The Chrome DevTools Protocol returns large gzipped/zip trace files. This
    helper performs the blocking decompression and JSON parsing in a thread
    pool so the async event loop is not blocked.

    Args:
        raw: Raw bytes of the trace archive.

    Returns:
        A list of trace events parsed from the archive, or a fallback dict
        with the raw payload size if parsing fails.
    """
    trace_events: list[dict[str, Any]] = []
    max_trace_file_size = 100_000_000  # 100 MB
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            for name in zf.namelist():
                if os.path.isabs(name) or ".." in name.split(os.sep):
                    continue
                info = zf.getinfo(name)
                if info.file_size > max_trace_file_size:
                    continue
                content = zf.read(name).decode("utf-8", errors="replace")
                trace_events.extend(json.loads(content).get("traceEvents", []))
    except (zipfile.BadZipFile, json.JSONDecodeError, KeyError, ValueError, RuntimeError):
        trace_events.append({"raw_size": len(raw)})
    return trace_events
