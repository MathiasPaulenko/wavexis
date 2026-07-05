"""Unit tests for PerformanceAction."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from browsix.actions.performance import PerformanceAction, PerformanceParams
from browsix.backend.base import AbstractBackend


@pytest.mark.unit
class TestPerformanceAction:
    """Test suite for performanceaction."""
    def _make_backend(self) -> MagicMock:
        """Create a mock backend for testing.

            Returns:
                A MagicMock backend instance.
            """
        backend = MagicMock(spec=AbstractBackend)
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.perf_metrics = AsyncMock(
            return_value={"Timestamp": 1234.5, "Documents": 1, "Frames": 1}
        )
        backend.perf_trace = AsyncMock(
            return_value={"traceEvents": [{"name": "X", "ts": 100}]}
        )
        backend.perf_profile = AsyncMock(
            return_value={"nodes": [], "samples": [], "timeDeltas": []}
        )
        backend.perf_heap_snapshot = AsyncMock(
            return_value={"snapshot": {"nodes": [], "edges": []}}
        )
        backend.perf_coverage = AsyncMock(
            return_value={"result": [{"scriptId": "1", "url": "test.js"}]}
        )
        backend.perf_css_coverage = AsyncMock(
            return_value={"result": [{"styleSheetId": "1", "ranges": []}]}
        )
        return backend

    async def test_metrics_action(self) -> None:
        """Test metrics action."""
        backend = self._make_backend()
        params = PerformanceParams(url="https://example.com", action="metrics")
        result = await PerformanceAction(params).execute(backend)
        backend.navigate.assert_called_once()
        backend.perf_metrics.assert_called_once()
        assert "Timestamp" in result

    async def test_trace_action(self) -> None:
        """Test trace action."""
        backend = self._make_backend()
        params = PerformanceParams(
            url="https://example.com", action="trace", duration_ms=1000
        )
        result = await PerformanceAction(params).execute(backend)
        backend.perf_trace.assert_called_once_with(1000)
        assert "traceEvents" in result

    async def test_profile_action(self) -> None:
        """Test profile action."""
        backend = self._make_backend()
        params = PerformanceParams(
            url="https://example.com", action="profile", duration_ms=2000
        )
        result = await PerformanceAction(params).execute(backend)
        backend.perf_profile.assert_called_once_with(2000)
        assert "nodes" in result

    async def test_heap_action(self) -> None:
        """Test heap action."""
        backend = self._make_backend()
        params = PerformanceParams(url="https://example.com", action="heap")
        result = await PerformanceAction(params).execute(backend)
        backend.perf_heap_snapshot.assert_called_once()
        assert "snapshot" in result

    async def test_coverage_action(self) -> None:
        """Test coverage action."""
        backend = self._make_backend()
        params = PerformanceParams(url="https://example.com", action="coverage")
        result = await PerformanceAction(params).execute(backend)
        backend.perf_coverage.assert_called_once()
        assert "result" in result

    async def test_css_coverage_action(self) -> None:
        """Test css coverage action."""
        backend = self._make_backend()
        params = PerformanceParams(
            url="https://example.com", action="css-coverage"
        )
        result = await PerformanceAction(params).execute(backend)
        backend.perf_css_coverage.assert_called_once()
        assert "result" in result

    async def test_unknown_action_raises(self) -> None:
        """Test that unknown action raises raises an appropriate error."""
        backend = self._make_backend()
        params = PerformanceParams(url="https://example.com", action="unknown")
        with pytest.raises(ValueError, match="Unknown performance action"):
            await PerformanceAction(params).execute(backend)

    async def test_launch_and_close_called(self) -> None:
        """Test launch and close called."""
        backend = self._make_backend()
        params = PerformanceParams(url="https://example.com", action="metrics")
        await PerformanceAction(params).execute(backend)
        backend.launch.assert_called_once()
        backend.close.assert_called_once()

    async def test_close_called_on_error(self) -> None:
        """Test close called on error."""
        backend = self._make_backend()
        backend.perf_metrics = AsyncMock(side_effect=RuntimeError("boom"))
        params = PerformanceParams(url="https://example.com", action="metrics")
        with pytest.raises(RuntimeError, match="boom"):
            await PerformanceAction(params).execute(backend)
        backend.close.assert_called_once()

    def test_params_defaults(self) -> None:
        """Test params defaults."""
        params = PerformanceParams()
        assert params.action == "metrics"
        assert params.duration_ms == 3000
        assert params.url == ""

    def test_params_custom(self) -> None:
        """Test params custom."""
        params = PerformanceParams(
            url="https://test.com", action="trace", duration_ms=5000
        )
        assert params.url == "https://test.com"
        assert params.action == "trace"
        assert params.duration_ms == 5000
