"""Core Web Vitals action — LCP, CLS, INP scoring with actionable ratings."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy

THRESHOLDS: dict[str, dict[str, float]] = {
    "lcp_ms": {"good": 2500, "poor": 4000},
    "cls": {"good": 0.1, "poor": 0.25},
    "inp_ms": {"good": 200, "poor": 500},
    "fcp_ms": {"good": 1800, "poor": 3000},
    "ttfb_ms": {"good": 800, "poor": 1800},
    "tbt_ms": {"good": 200, "poor": 600},
    "load_ms": {"good": 3000, "poor": 5000},
}


def _rating(value: float, good: float, poor: float) -> str:
    """Return rating for a metric value.

    Args:
        value: The metric value.
        good: Threshold for 'good' rating.
        poor: Threshold for 'poor' rating.

    Returns:
        'good', 'needs-improvement', or 'poor'.
    """
    if value <= good:
        return "good"
    if value <= poor:
        return "needs-improvement"
    return "poor"


@dataclass
class CoreWebVitalsParams:
    """Parameters for Core Web Vitals measurement.

    Attributes:
        url: URL to navigate to.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
        budgets: Optional dict of metric → max acceptable value.
            Keys: lcp_ms, cls, inp_ms, fcp_ms, ttfb_ms, tbt_ms, load_ms.
        observe_ms: How long to observe PerformanceObserver entries (ms).
    """

    url: str = ""
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)
    budgets: dict[str, float] = field(default_factory=dict)
    observe_ms: int = 5000


class CoreWebVitalsAction(BaseAction[CoreWebVitalsParams, dict[str, Any]]):
    """Action for measuring Core Web Vitals (LCP, CLS, INP) with scoring.

    Collects LCP, CLS, INP, FCP, TTFB, TBT, and load time via
    PerformanceObserver and the Performance API. Computes ratings
    (good/needs-improvement/poor) and an overall score.
    """

    async def execute(self, backend: AbstractBackend) -> dict[str, Any]:
        """Execute the Core Web Vitals measurement.

        Args:
            backend: The browser backend to use.

        Returns:
            Dict with metrics, ratings, score, and budget check results.
        """
        await backend.navigate(self.params.url, self.params.wait)
        return await self._collect_cwv(backend)

    async def _collect_cwv(self, backend: AbstractBackend) -> dict[str, Any]:
        """Collect Core Web Vitals from the page.

        Args:
            backend: The launched browser backend.

        Returns:
            Dict with raw metrics, ratings, score, and budgets.
        """

        cwv_js = f"""
            (() => {{
                return new Promise(resolve => {{
                    let lcp = 0, cls = 0, inp = 0, tbt = 0;
                    new PerformanceObserver(list => {{
                        for (const e of list.getEntries()) {{
                            lcp = e.startTime;
                        }}
                    }}).observe({{type: 'largest-contentful-paint', buffered: true}});
                    new PerformanceObserver(list => {{
                        for (const e of list.getEntries()) {{
                            if (!e.hadRecentInput) cls += e.value;
                        }}
                    }}).observe({{type: 'layout-shift', buffered: true}});
                    new PerformanceObserver(list => {{
                        for (const e of list.getEntries()) {{
                            inp = Math.max(inp, e.duration);
                        }}
                    }}).observe({{type: 'event', buffered: true}});
                    new PerformanceObserver(list => {{
                        for (const e of list.getEntries()) {{
                            tbt += e.duration;
                        }}
                    }}).observe({{type: 'longtask', buffered: true}});
                    setTimeout(() => resolve({{lcp, cls, inp, tbt}}), {self.params.observe_ms});
                }});
            }})()
        """

        cwv: dict[str, Any] = {}
        with contextlib.suppress(Exception):
            cwv_result = await backend.eval(cwv_js, await_promise=True)
            if isinstance(cwv_result, dict):
                cwv = cwv_result

        timing_js = """
            (() => {
                const nav = performance.getEntriesByType('navigation')[0] || {};
                const paint = performance.getEntriesByType('paint');
                const fcp = paint.find(p => p.name === 'first-contentful-paint');
                return {
                    ttfb: nav.responseStart || 0,
                    fcp: fcp ? fcp.startTime : 0,
                    load: nav.loadEventEnd || 0,
                    domSize: document.querySelectorAll('*').length,
                    transferSize: nav.transferSize || 0,
                };
            })()
        """
        timing: dict[str, Any] = {}
        with contextlib.suppress(Exception):
            timing_result = await backend.eval(timing_js, await_promise=False)
            if isinstance(timing_result, dict):
                timing = timing_result

        lcp = cwv.get("lcp", 0)
        cls = cwv.get("cls", 0)
        inp = cwv.get("inp", 0)
        tbt = cwv.get("tbt", 0)
        ttfb = timing.get("ttfb", 0)
        fcp = timing.get("fcp", 0)
        load = timing.get("load", 0)
        dom_size = timing.get("domSize", 0)

        metrics: dict[str, float] = {
            "lcp_ms": lcp,
            "cls": cls,
            "inp_ms": inp,
            "fcp_ms": fcp,
            "ttfb_ms": ttfb,
            "tbt_ms": tbt,
            "load_ms": load,
        }

        ratings: dict[str, str] = {}
        for key, value in metrics.items():
            if key in THRESHOLDS:
                thresholds = THRESHOLDS[key]
                ratings[key] = _rating(value, thresholds["good"], thresholds["poor"])

        score = self._compute_score(metrics, dom_size)

        result: dict[str, Any] = {
            "url": self.params.url,
            "metrics": metrics,
            "ratings": ratings,
            "score": score,
            "dom_size": dom_size,
            "transfer_size": timing.get("transferSize", 0),
        }

        if self.params.budgets:
            result["budgets"] = self._check_budgets(metrics, self.params.budgets)

        return result

    def _compute_score(self, metrics: dict[str, float], dom_size: int) -> int:
        """Compute a 0-100 score from Core Web Vitals metrics.

        Args:
            metrics: Dict of metric name → value.
            dom_size: Number of DOM elements.

        Returns:
            Score from 0 to 100.
        """
        score = 100
        for key, value in metrics.items():
            if key not in THRESHOLDS:
                continue
            thresholds = THRESHOLDS[key]
            if value > thresholds["poor"]:
                score -= 15
            elif value > thresholds["good"]:
                score -= 8
        if dom_size > 3000:
            score -= 10
        elif dom_size > 1500:
            score -= 5
        return max(0, score)

    def _check_budgets(
        self, metrics: dict[str, float], budgets: dict[str, float]
    ) -> dict[str, Any]:
        """Check metrics against budget thresholds.

        Args:
            metrics: Dict of metric name → value.
            budgets: Dict of metric name → max acceptable value.

        Returns:
            Dict with pass/fail status per metric and overall.
        """
        results: dict[str, Any] = {}
        all_pass = True
        for key, threshold in budgets.items():
            value = metrics.get(key, 0)
            passed = value <= threshold
            if not passed:
                all_pass = False
            results[key] = {
                "value": value,
                "budget": threshold,
                "pass": passed,
            }
        results["all_pass"] = all_pass
        return results
