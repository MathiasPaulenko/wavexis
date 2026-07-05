"""Integration tests for performance actions against a real Chrome browser."""

import json

import pytest

from browsix.actions.performance import PerformanceAction, PerformanceParams
from browsix.backend.cdp import CDPBackend
from browsix.config import BrowserOptions, WaitStrategy

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


@pytest.fixture
def backend() -> CDPBackend:
    """Backend."""
    return CDPBackend()


@pytest.fixture
def browser_opts() -> BrowserOptions:
    """Browser opts."""
    return BrowserOptions(headless=True)


async def test_perf_metrics(backend: CDPBackend, browser_opts: BrowserOptions) -> None:
    """Test perf metrics."""
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
    """Test perf trace."""
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
    """Test perf profile."""
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
    """Test perf heap."""
    params = PerformanceParams(
        url="https://example.com",
        action="heap",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await PerformanceAction(params).execute(backend)
    assert isinstance(result, dict)


async def test_perf_coverage(backend: CDPBackend, browser_opts: BrowserOptions) -> None:
    """Test perf coverage."""
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
    """Test perf css coverage."""
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
    """Test perf metrics json serializable."""
    params = PerformanceParams(
        url="https://example.com",
        action="metrics",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await PerformanceAction(params).execute(backend)
    json.dumps(result, default=str)
