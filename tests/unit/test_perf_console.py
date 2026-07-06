"""Unit tests for browsix perf command and console enhancements."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from browsix.cli.app import _print_perf_summary


@pytest.mark.unit
class TestPrintPerfSummary:
    """Tests for _print_perf_summary function."""

    def test_prints_key_metrics(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that key metrics are printed in human-readable format."""
        metrics = {
            "LargestContentfulPaint": 2500,
            "FirstContentfulPaint": 1200,
            "CumulativeLayoutShift": 0.05,
            "TimeToFirstByte": 350,
            "DOMContentLoadEventEnd": 1800,
            "LoadEventEnd": 3200,
        }
        _print_perf_summary(metrics)
        captured = capsys.readouterr()
        assert "LCP" in captured.out
        assert "FCP" in captured.out
        assert "CLS" in captured.out
        assert "TTFB" in captured.out
        assert "DCL" in captured.out
        assert "Load" in captured.out
        assert "2500" in captured.out
        assert "0.050" in captured.out

    def test_skips_missing_metrics(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that missing metrics are skipped."""
        metrics = {
            "LargestContentfulPaint": 2500,
        }
        _print_perf_summary(metrics)
        captured = capsys.readouterr()
        assert "LCP" in captured.out
        assert "FCP" not in captured.out

    def test_empty_dict(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test with empty metrics dict."""
        _print_perf_summary({})
        captured = capsys.readouterr()
        assert "Performance Summary" in captured.out

    def test_non_dict_input(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that non-dict input is handled gracefully."""
        _print_perf_summary("not a dict")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_string_value_for_metric(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that string values are printed as-is."""
        metrics = {"LargestContentfulPaint": "N/A"}
        _print_perf_summary(metrics)
        captured = capsys.readouterr()
        assert "N/A" in captured.out

    def test_cls_formatting(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that CLS is formatted with 3 decimal places."""
        metrics = {"CumulativeLayoutShift": 0.123456}
        _print_perf_summary(metrics)
        captured = capsys.readouterr()
        assert "0.123" in captured.out

    def test_ms_formatting(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that time metrics are formatted as ms."""
        metrics = {"LargestContentfulPaint": 1234}
        _print_perf_summary(metrics)
        captured = capsys.readouterr()
        assert "1234" in captured.out
        assert "ms" in captured.out


@pytest.mark.unit
class TestPerfBackend:
    """Tests for _perf async helper."""

    async def test_perf_metrics(self) -> None:
        """Test that _perf calls perf_metrics for metrics type."""
        import sys
        from browsix.cli.app import _perf

        app_module = sys.modules["browsix.cli.app"]

        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.perf_metrics = AsyncMock(
            return_value={"LargestContentfulPaint": 2500}
        )
        backend.close = AsyncMock()

        original_get_backend = app_module._get_backend
        app_module._get_backend = lambda: backend  # type: ignore[assignment]

        try:
            result = await _perf("https://example.com", "metrics", 3000)
            assert result == {"LargestContentfulPaint": 2500}
            backend.perf_metrics.assert_called_once()
        finally:
            app_module._get_backend = original_get_backend  # type: ignore[assignment]

    async def test_perf_trace(self) -> None:
        """Test that _perf calls perf_trace for trace type."""
        import sys
        from browsix.cli.app import _perf

        app_module = sys.modules["browsix.cli.app"]

        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.perf_trace = AsyncMock(return_value={"traceEvents": []})
        backend.close = AsyncMock()

        original_get_backend = app_module._get_backend
        app_module._get_backend = lambda: backend  # type: ignore[assignment]

        try:
            result = await _perf("https://example.com", "trace", 5000)
            assert result == {"traceEvents": []}
            backend.perf_trace.assert_called_once_with(duration_ms=5000)
        finally:
            app_module._get_backend = original_get_backend  # type: ignore[assignment]

    async def test_perf_coverage(self) -> None:
        """Test that _perf calls perf_coverage for coverage type."""
        import sys
        from browsix.cli.app import _perf

        app_module = sys.modules["browsix.cli.app"]

        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.perf_coverage = AsyncMock(return_value={"result": []})
        backend.close = AsyncMock()

        original_get_backend = app_module._get_backend
        app_module._get_backend = lambda: backend  # type: ignore[assignment]

        try:
            result = await _perf("https://example.com", "coverage", 3000)
            assert result == {"result": []}
            backend.perf_coverage.assert_called_once()
        finally:
            app_module._get_backend = original_get_backend  # type: ignore[assignment]


@pytest.mark.unit
class TestConsoleEnhancements:
    """Tests for enhanced console command with --format and --capture."""

    async def test_console_capture_both(self) -> None:
        """Test that _console with capture='both' gets console and logs."""
        import sys
        from browsix.cli.app import _console

        app_module = sys.modules["browsix.cli.app"]

        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.capture_console = AsyncMock(
            return_value=[{"level": "error", "text": "JS error"}]
        )
        backend.capture_logs = AsyncMock(
            return_value=[{"level": "info", "message": "log entry"}]
        )
        backend.close = AsyncMock()

        original_get_backend = app_module._get_backend
        app_module._get_backend = lambda: backend  # type: ignore[assignment]

        try:
            result = await _console("https://example.com", "all", "both")
            assert "console" in result
            assert "logs" in result
            assert result["console"] == [{"level": "error", "text": "JS error"}]
            assert result["logs"] == [{"level": "info", "message": "log entry"}]
        finally:
            app_module._get_backend = original_get_backend  # type: ignore[assignment]

    async def test_console_capture_logs_only(self) -> None:
        """Test that _console with capture='logs' only gets logs."""
        import sys
        from browsix.cli.app import _console

        app_module = sys.modules["browsix.cli.app"]

        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.capture_console = AsyncMock(return_value=[])
        backend.capture_logs = AsyncMock(
            return_value=[{"level": "info", "message": "log"}]
        )
        backend.close = AsyncMock()

        original_get_backend = app_module._get_backend
        app_module._get_backend = lambda: backend  # type: ignore[assignment]

        try:
            result = await _console("https://example.com", "all", "logs")
            assert "console" not in result
            assert "logs" in result
        finally:
            app_module._get_backend = original_get_backend  # type: ignore[assignment]
