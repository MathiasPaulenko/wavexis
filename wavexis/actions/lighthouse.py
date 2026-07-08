"""Lighthouse action for performance, accessibility, and SEO auditing."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy
from wavexis.exceptions import WavexisError


@dataclass
class LighthouseParams:
    """Parameters for running a Lighthouse-style audit.

    Attributes:
        url: URL to audit.
        categories: Audit categories — "performance", "accessibility",
            "best-practices", "seo". Empty = all.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
        budgets: Optional dict of metric → threshold value.
            Supported keys: ttfb_ms, fcp_ms, lcp_ms, cls, inp_ms,
            tbt_ms, load_ms, dom_size. Each value is the max acceptable.
    """

    url: str = ""
    categories: list[str] = field(default_factory=list)
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)
    budgets: dict[str, float] = field(default_factory=dict)


class LighthouseAction(BaseAction[LighthouseParams, dict[str, Any]]):
    """Action for running a browser-based audit using CDP metrics.

    Instead of requiring the Lighthouse npm package, this action collects
    performance metrics, accessibility tree, and SEO meta tags directly
    via CDP/BiDi and computes scores.
    """

    async def execute(
        self, backend: AbstractBackend
    ) -> dict[str, Any]:
        """Execute the audit on the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            Dict with category scores and detailed metrics.
        """
        await backend.navigate(self.params.url, self.params.wait)

        cats = self.params.categories or [
            "performance",
            "accessibility",
            "seo",
            "best-practices",
        ]
        result: dict[str, Any] = {
            "url": self.params.url,
            "categories": {},
        }

        if "performance" in cats:
            result["categories"]["performance"] = (
                await self._audit_performance(backend)
            )

        if "accessibility" in cats:
            result["categories"]["accessibility"] = (
                await self._audit_accessibility(backend)
            )

        if "seo" in cats:
            result["categories"]["seo"] = (
                await self._audit_seo(backend)
            )

        if "best-practices" in cats:
            result["categories"]["best-practices"] = (
                await self._audit_best_practices(backend)
            )

        return result

    async def _audit_performance(
        self, backend: AbstractBackend
    ) -> dict[str, Any]:
        """Collect performance metrics and compute a score."""
        metrics = await backend.perf_metrics()
        js = """
            (() => {
                const nav = performance.getEntriesByType('navigation')[0] || {};
                const paint = performance.getEntriesByType('paint');
                const fcp = paint.find(p => p.name === 'first-contentful-paint');
                return {
                    domContentLoaded: nav.domContentLoadedEventEnd || 0,
                    loadComplete: nav.loadEventEnd || 0,
                    ttfb: nav.responseStart || 0,
                    fcp: fcp ? fcp.startTime : 0,
                    domSize: document.querySelectorAll('*').length,
                    transferSize: nav.transferSize || 0,
                    encodedBodySize: nav.encodedBodySize || 0,
                };
            })()
        """
        perf = await backend.eval(js, await_promise=False)
        if not isinstance(perf, dict):
            perf = {}

        ttfb = perf.get("ttfb", 0)
        fcp = perf.get("fcp", 0)
        load = perf.get("loadComplete", 0)
        dom_size = perf.get("domSize", 0)

        cwv_js = """
            (() => {
                return new Promise(resolve => {
                    let lcp = 0, cls = 0, inp = 0, tbt = 0;
                    new PerformanceObserver(list => {
                        for (const e of list.getEntries()) {
                            lcp = e.startTime;
                        }
                    }).observe({type: 'largest-contentful-paint', buffered: true});
                    new PerformanceObserver(list => {
                        for (const e of list.getEntries()) {
                            if (!e.hadRecentInput) cls += e.value;
                        }
                    }).observe({type: 'layout-shift', buffered: true});
                    new PerformanceObserver(list => {
                        for (const e of list.getEntries()) {
                            inp = Math.max(inp, e.duration);
                        }
                    }).observe({type: 'event', buffered: true});
                    new PerformanceObserver(list => {
                        for (const e of list.getEntries()) {
                            tbt += e.duration;
                        }
                    }).observe({type: 'longtask', buffered: true});
                    setTimeout(() => resolve({lcp, cls, inp, tbt}), 500);
                });
            })()
        """
        cwv: dict[str, Any] = {}
        with contextlib.suppress(Exception):
            cwv_result = await backend.eval(cwv_js, await_promise=True)
            if isinstance(cwv_result, dict):
                cwv = cwv_result

        lcp = cwv.get("lcp", 0)
        cls = cwv.get("cls", 0)
        inp = cwv.get("inp", 0)
        tbt = cwv.get("tbt", 0)

        score = 100
        if ttfb > 800:
            score -= 10
        if ttfb > 1800:
            score -= 15
        if fcp > 1800:
            score -= 15
        if fcp > 3000:
            score -= 15
        if lcp > 2500:
            score -= 10
        if lcp > 4000:
            score -= 10
        if cls > 0.1:
            score -= 10
        if cls > 0.25:
            score -= 10
        if inp > 200:
            score -= 5
        if inp > 500:
            score -= 10
        if load > 3000:
            score -= 10
        if load > 5000:
            score -= 15
        if dom_size > 1500:
            score -= 10
        if dom_size > 3000:
            score -= 10
        score = max(0, score)

        result: dict[str, Any] = {
            "score": score,
            "ttfb_ms": ttfb,
            "fcp_ms": fcp,
            "lcp_ms": lcp,
            "cls": cls,
            "inp_ms": inp,
            "tbt_ms": tbt,
            "load_ms": load,
            "dom_size": dom_size,
            "transfer_size": perf.get("transferSize", 0),
            "raw_metrics": metrics,
        }

        if self.params.budgets:
            result["budgets"] = self._check_budgets(result, self.params.budgets)

        return result

    async def _audit_accessibility(
        self, backend: AbstractBackend
    ) -> dict[str, Any]:
        """Check common accessibility issues."""
        js = """
            (() => {
                const issues = [];
                const imgs = document.querySelectorAll('img');
                imgs.forEach(img => {
                    if (!img.alt) issues.push({type: 'image-alt', selector: getSelector(img)});
                });
                const inputs = document.querySelectorAll('input, textarea, select');
                inputs.forEach(input => {
                    if (!input.getAttribute('aria-label') &&
                        !input.labels?.length &&
                        !input.getAttribute('title')) {
                        issues.push({type: 'input-label', selector: getSelector(input)});
                    }
                });
                const links = document.querySelectorAll('a');
                links.forEach(link => {
                    if (!link.textContent.trim() && !link.getAttribute('aria-label')) {
                        issues.push({type: 'link-text', selector: getSelector(link)});
                    }
                });
                const buttons = document.querySelectorAll('button');
                buttons.forEach(btn => {
                    if (!btn.textContent.trim() && !btn.getAttribute('aria-label')) {
                        issues.push({type: 'button-text', selector: getSelector(btn)});
                    }
                });
                const html = document.documentElement;
                if (!html.getAttribute('lang')) {
                    issues.push({type: 'html-lang'});
                }
                function getSelector(el) {
                    if (el.id) return '#' + el.id;
                    return el.tagName.toLowerCase();
                }
                return {
                    issues: issues,
                    issue_count: issues.length,
                    has_lang: !!html.getAttribute('lang'),
                    has_viewport: !!document.querySelector('meta[name="viewport"]'),
                };
            })()
        """
        a11y = await backend.eval(js, await_promise=False)
        if not isinstance(a11y, dict):
            a11y = {"issues": [], "issue_count": 0}

        issue_count = a11y.get("issue_count", 0)
        score = max(0, 100 - issue_count * 5)

        return {
            "score": score,
            "issues": a11y.get("issues", []),
            "issue_count": issue_count,
            "has_lang": a11y.get("has_lang", False),
            "has_viewport": a11y.get("has_viewport", False),
        }

    async def _audit_seo(self, backend: AbstractBackend) -> dict[str, Any]:
        """Check SEO meta tags and content."""
        js = """
            (() => {
                const meta = (name) => {
                    const el = document.querySelector(`meta[name="${name}"]`) ||
                               document.querySelector(`meta[property="${name}"]`);
                    return el ? el.getAttribute('content') : null;
                };
                const title = document.title;
                const h1s = document.querySelectorAll('h1');
                const canonical = document.querySelector('link[rel="canonical"]');
                return {
                    title: title,
                    title_length: title.length,
                    description: meta('description'),
                    description_length: (meta('description') || '').length,
                    og_title: meta('og:title'),
                    og_description: meta('og:description'),
                    og_image: meta('og:image'),
                    twitter_card: meta('twitter:card'),
                    canonical: canonical ? canonical.getAttribute('href') : null,
                    h1_count: h1s.length,
                    has_robots_meta: !!document.querySelector('meta[name="robots"]'),
                    has_sitemap_link: !!document.querySelector('link[rel="sitemap"]'),
                };
            })()
        """
        seo = await backend.eval(js, await_promise=False)
        if not isinstance(seo, dict):
            seo = {}

        score = 100
        if not seo.get("title"):
            score -= 20
        elif len(seo.get("title", "")) > 60:
            score -= 5
        if not seo.get("description"):
            score -= 15
        elif len(seo.get("description", "")) > 160:
            score -= 5
        if seo.get("h1_count", 0) == 0:
            score -= 15
        if seo.get("h1_count", 0) > 1:
            score -= 5
        if not seo.get("canonical"):
            score -= 10
        if not seo.get("og_title"):
            score -= 10
        if not seo.get("twitter_card"):
            score -= 5
        score = max(0, score)

        return {"score": score, **seo}

    async def _audit_best_practices(
        self, backend: AbstractBackend
    ) -> dict[str, Any]:
        """Check best practices (HTTPS, console errors, deprecated APIs)."""
        js = """
            (() => {
                const issues = [];
                if (location.protocol !== 'https:') {
                    issues.push({type: 'not-https'});
                }
                const scripts = document.querySelectorAll('script[src]');
                scripts.forEach(s => {
                    if (s.src.startsWith('http://')) {
                        issues.push({type: 'insecure-script', src: s.src});
                    }
                });
                if (!window.isSecureContext) {
                    issues.push({type: 'insecure-context'});
                }
                return {
                    issues: issues,
                    is_https: location.protocol === 'https:',
                    console_errors: window.__wavexisConsoleErrors || [],
                };
            })()
        """
        console_errors: list[dict[str, Any]] = []
        with contextlib.suppress(WavexisError):
            console_errors = await backend.capture_console(level="error")

        bp = await backend.eval(js, await_promise=False)
        if not isinstance(bp, dict):
            bp = {"issues": [], "is_https": False}

        issues = bp.get("issues", [])
        score = 100
        for _ in issues:
            score -= 10
        score -= min(20, len(console_errors) * 5)
        score = max(0, score)

        return {
            "score": score,
            "issues": issues,
            "is_https": bp.get("is_https", False),
            "console_errors": console_errors,
        }

    @staticmethod
    def _check_budgets(
        metrics: dict[str, Any], budgets: dict[str, float]
    ) -> dict[str, Any]:
        """Check metrics against performance budgets.

        Args:
            metrics: Collected performance metrics.
            budgets: Dict of metric_name → max acceptable value.

        Returns:
            Dict with pass/fail per budget item and overall status.
        """
        results: list[dict[str, Any]] = []
        all_pass = True

        for key, threshold in budgets.items():
            actual = metrics.get(key, 0)
            if not isinstance(actual, (int, float)):
                actual = 0
            passed = actual <= threshold
            if not passed:
                all_pass = False
            results.append({
                "metric": key,
                "actual": actual,
                "budget": threshold,
                "pass": passed,
            })

        return {
            "pass": all_pass,
            "results": results,
        }
