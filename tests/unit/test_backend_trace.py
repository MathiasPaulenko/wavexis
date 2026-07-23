"""Unit tests for backend trace helpers."""

from __future__ import annotations

import base64
from typing import Any

import pytest

from wavexis.backend._trace import extract_trace_events, read_trace_stream

pytestmark = pytest.mark.unit


class TestReadTraceStream:
    """Tests for the bounded IO stream reader."""

    async def _make_reader(self, chunks: list[dict[str, Any]]) -> Any:
        calls = iter(chunks)

        async def read() -> Any:
            return next(calls)

        return read

    async def test_reads_all_chunks(self) -> None:
        read = await self._make_reader(
            [
                {"data": base64.b64encode(b"hello ").decode(), "base64Encoded": True, "eof": False},
                {"data": base64.b64encode(b"world").decode(), "base64Encoded": True, "eof": True},
            ]
        )
        result = await read_trace_stream(read)
        assert result == b"hello world"

    async def test_stops_on_empty_data(self) -> None:
        read = await self._make_reader([{"data": "", "base64Encoded": True, "eof": False}])
        result = await read_trace_stream(read)
        assert result == b""

    async def test_stops_on_missing_response(self) -> None:
        read = await self._make_reader([None])
        result = await read_trace_stream(read)
        assert result == b""

    async def test_limits_iterations(self) -> None:
        chunk = {"data": base64.b64encode(b"x").decode(), "base64Encoded": True, "eof": False}
        read = await self._make_reader([chunk] * 2000)
        result = await read_trace_stream(read, max_iterations=10)
        assert len(result) == 10

    async def test_limits_total_bytes(self) -> None:
        chunk = b"abcd" * 10
        b64 = base64.b64encode(chunk).decode()
        read = await self._make_reader(
            [{"data": b64, "base64Encoded": True, "eof": False}] * 10
        )
        result = await read_trace_stream(read, max_total_bytes=20)
        assert len(result) == 20

    async def test_uses_utf8_when_not_base64(self) -> None:
        read = await self._make_reader(
            [
                {"data": "hello", "base64Encoded": False, "eof": False},
                {"data": "", "base64Encoded": False, "eof": True},
            ]
        )
        result = await read_trace_stream(read)
        assert result == b"hello"

    async def test_breaks_on_timeout(self) -> None:
        import asyncio

        async def slow_read() -> dict[str, Any]:
            await asyncio.sleep(1)
            return {"data": "", "base64Encoded": True, "eof": True}

        result = await read_trace_stream(slow_read, read_timeout=0.01)
        assert result == b""


class TestExtractTraceEvents:
    """Tests for trace event extraction."""

    def _zip_trace(self, payload: bytes) -> bytes:
        import io
        import zipfile

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("trace.json", payload)
        return buffer.getvalue()

    def test_extracts_trace_events_from_zip(self) -> None:
        raw = self._zip_trace(b'{"traceEvents":[{"name":"test"}]}')
        events = extract_trace_events(raw)
        assert events == [{"name": "test"}]

    def test_returns_raw_size_for_invalid_data(self) -> None:
        events = extract_trace_events(b"not a zip")
        assert events == [{"raw_size": len(b"not a zip")}]
