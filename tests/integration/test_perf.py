"""Integration tests for performance actions against a real Chrome browser."""

import json

import pytest

from browsix.actions.performance import PerformanceAction, PerformanceParams
from browsix.backend.cdp import CDPBackend
from browsix.config import BrowserOptions, WaitStrategy

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


@pytest.fixture
def backend() -> CDPBackend:
    return CDPBackend()


@pytest.fixture
def browser_opts() -> BrowserOptions:
    return BrowserOptions(headless=True)


async def test_perf_metrics(backend: CDPBackend, browser_opts: BrowserOptions) -> None:
    params = PerformanceParams(
        url="https://example.com",
        action="metrics",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await PerformanceAction(params).execute(backend)
    assert isinstance(result, dict)
    assert len(result) > 0


async def test_perf_trace(backend: CDPBackend, browser_opts: BrowserOptions) -> None:
    params = PerformanceParams(
        url="https://example.com",
        action="trace",
        duration_ms=1000,
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await PerformanceAction(params).execute(backend)
    assert isinstance(result, dict)
    assert "traceEvents" in result


async def test_perf_profile(backend: CDPBackend, browser_opts: BrowserOptions) -> None:
    params = PerformanceParams(
        url="https://example.com",
        action="profile",
        duration_ms=1000,
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await PerformanceAction(params).execute(backend)
    assert isinstance(result, dict)


async def test_perf_heap(backend: CDPBackend, browser_opts: BrowserOptions) -> None:
    params = PerformanceParams(
        url="https://example.com",
        action="heap",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await PerformanceAction(params).execute(backend)
    assert isinstance(result, dict)


async def test_perf_coverage(backend: CDPBackend, browser_opts: BrowserOptions) -> None:
    params = PerformanceParams(
        url="https://example.com",
        action="coverage",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await PerformanceAction(params).execute(backend)
    assert isinstance(result, dict)


async def test_perf_css_coverage(
    backend: CDPBackend, browser_opts: BrowserOptions
) -> None:
    params = PerformanceParams(
        url="https://example.com",
        action="css-coverage",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await PerformanceAction(params).execute(backend)
    assert isinstance(result, dict)


async def test_perf_metrics_json_serializable(
    backend: CDPBackend, browser_opts: BrowserOptions
) -> None:
    params = PerformanceParams(
        url="https://example.com",
        action="metrics",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await PerformanceAction(params).execute(backend)
    json.dumps(result, default=str)
