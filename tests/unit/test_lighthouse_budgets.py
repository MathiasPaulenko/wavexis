"""Unit tests for Lighthouse performance budgets and Core Web Vitals."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.actions.lighthouse import LighthouseAction, LighthouseParams


def _make_backend(
    perf_metrics: dict[str, Any] | None = None,
    eval_result: Any = None,
    eval_cwv: dict[str, Any] | None = None,
) -> Any:
    """Create a mock backend for lighthouse tests."""
    backend = MagicMock()
    backend.launch = AsyncMock()
    backend.close = AsyncMock()
    backend.navigate = AsyncMock()
    backend.perf_metrics = AsyncMock(return_value=perf_metrics or {"js_heap_used": 10_000_000})

    eval_call_count = [0]

    async def _eval(expression: str, await_promise: bool = False) -> Any:
        eval_call_count[0] += 1
        if "PerformanceObserver" in expression:
            return eval_cwv or {}
        if eval_result is not None:
            return eval_result
        return {}

    backend.eval = _eval

    backend.capture_console = AsyncMock(return_value=[])
    backend.a11y_tree = AsyncMock(return_value={})
    return backend


@pytest.mark.unit
class TestLighthouseBudgets:
    """Tests for performance budget checking."""

    def test_budgets_all_pass(self) -> None:
        """Test that all passing budgets return pass=True."""
        metrics = {
            "ttfb_ms": 200,
            "fcp_ms": 1200,
            "lcp_ms": 2000,
            "cls": 0.05,
            "load_ms": 2000,
            "dom_size": 500,
        }
        budgets = {
            "ttfb_ms": 800,
            "fcp_ms": 1800,
            "lcp_ms": 2500,
            "cls": 0.1,
            "load_ms": 3000,
            "dom_size": 1500,
        }
        result = LighthouseAction._check_budgets(metrics, budgets)
        assert result["pass"] is True
        assert len(result["results"]) == 6
        for r in result["results"]:
            assert r["pass"] is True

    def test_budgets_some_fail(self) -> None:
        """Test that failing budgets are reported correctly."""
        metrics = {
            "ttfb_ms": 2000,
            "fcp_ms": 1200,
            "lcp_ms": 5000,
        }
        budgets = {
            "ttfb_ms": 800,
            "fcp_ms": 1800,
            "lcp_ms": 2500,
        }
        result = LighthouseAction._check_budgets(metrics, budgets)
        assert result["pass"] is False
        assert len(result["results"]) == 3
        ttfb_r = next(r for r in result["results"] if r["metric"] == "ttfb_ms")
        assert ttfb_r["pass"] is False
        assert ttfb_r["actual"] == 2000
        assert ttfb_r["budget"] == 800
        fcp_r = next(r for r in result["results"] if r["metric"] == "fcp_ms")
        assert fcp_r["pass"] is True

    def test_budgets_empty(self) -> None:
        """Test that empty budgets return pass=True with no results."""
        result = LighthouseAction._check_budgets({}, {})
        assert result["pass"] is True
        assert result["results"] == []

    def test_budgets_missing_metric_defaults_zero(self) -> None:
        """Test that missing metrics default to 0 and pass."""
        budgets = {"ttfb_ms": 800}
        result = LighthouseAction._check_budgets({}, budgets)
        assert result["pass"] is True
        assert result["results"][0]["actual"] == 0


@pytest.mark.unit
class TestLighthousePerformanceAudit:
    """Tests for performance audit with Core Web Vitals."""

    def test_performance_audit_with_cwv(self) -> None:
        """Test that performance audit collects Core Web Vitals."""
        perf_js_result = {
            "ttfb": 150,
            "fcp": 900,
            "loadComplete": 2000,
            "domSize": 800,
            "transferSize": 50000,
        }
        cwv_result = {"lcp": 1800, "cls": 0.05, "inp": 100, "tbt": 200}
        backend = _make_backend(
            eval_result=perf_js_result,
            eval_cwv=cwv_result,
        )
        action = LighthouseAction(
            LighthouseParams(url="https://example.com", categories=["performance"])
        )
        result = asyncio.run(action.execute(backend))
        perf = result["categories"]["performance"]
        assert "lcp_ms" in perf
        assert "cls" in perf
        assert "inp_ms" in perf
        assert "tbt_ms" in perf
        assert perf["lcp_ms"] == 1800
        assert perf["cls"] == 0.05
        assert perf["inp_ms"] == 100
        assert perf["tbt_ms"] == 200
        assert perf["score"] > 0

    def test_performance_audit_with_budgets(self) -> None:
        """Test that performance audit includes budget results."""
        perf_js_result = {
            "ttfb": 200,
            "fcp": 1200,
            "loadComplete": 2000,
            "domSize": 500,
        }
        cwv_result = {"lcp": 2000, "cls": 0.05, "inp": 100, "tbt": 200}
        backend = _make_backend(
            eval_result=perf_js_result,
            eval_cwv=cwv_result,
        )
        action = LighthouseAction(
            LighthouseParams(
                url="https://example.com",
                categories=["performance"],
                budgets={"ttfb_ms": 800, "lcp_ms": 2500},
            )
        )
        result = asyncio.run(action.execute(backend))
        perf = result["categories"]["performance"]
        assert "budgets" in perf
        assert perf["budgets"]["pass"] is True
        assert len(perf["budgets"]["results"]) == 2

    def test_performance_audit_budgets_fail(self) -> None:
        """Test that failing budgets are reported in audit."""
        perf_js_result = {
            "ttfb": 2000,
            "fcp": 3500,
            "loadComplete": 6000,
            "domSize": 4000,
        }
        cwv_result = {"lcp": 5000, "cls": 0.3, "inp": 600, "tbt": 500}
        backend = _make_backend(
            eval_result=perf_js_result,
            eval_cwv=cwv_result,
        )
        action = LighthouseAction(
            LighthouseParams(
                url="https://example.com",
                categories=["performance"],
                budgets={"ttfb_ms": 800, "lcp_ms": 2500},
            )
        )
        result = asyncio.run(action.execute(backend))
        perf = result["categories"]["performance"]
        assert perf["budgets"]["pass"] is False
        ttfb_r = next(r for r in perf["budgets"]["results"] if r["metric"] == "ttfb_ms")
        assert ttfb_r["pass"] is False

    def test_performance_score_zero_for_very_slow(self) -> None:
        """Test that very slow metrics result in score 0."""
        perf_js_result = {
            "ttfb": 5000,
            "fcp": 8000,
            "loadComplete": 10000,
            "domSize": 5000,
        }
        cwv_result = {"lcp": 8000, "cls": 0.5, "inp": 1000, "tbt": 2000}
        backend = _make_backend(
            eval_result=perf_js_result,
            eval_cwv=cwv_result,
        )
        action = LighthouseAction(
            LighthouseParams(url="https://example.com", categories=["performance"])
        )
        result = asyncio.run(action.execute(backend))
        perf = result["categories"]["performance"]
        assert perf["score"] == 0
