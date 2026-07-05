"""Performance action for metrics, tracing, profiling, heap, and coverage."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from browsix.actions.base import BaseAction
from browsix.backend.base import AbstractBackend
from browsix.config import BrowserOptions, WaitStrategy


@dataclass
class PerformanceParams:
    """Parameters for performance operations.

    Attributes:
        url: URL to navigate to before collecting performance data.
        action: Performance action — "metrics", "trace", "profile",
            "heap", "coverage", "css-coverage".
        duration_ms: Duration in milliseconds for trace and profile actions.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    action: str = "metrics"
    duration_ms: int = 3000
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class PerformanceAction(BaseAction[PerformanceParams, dict[str, Any]]):
    """Action for collecting performance data from a web page."""

    async def execute(self, backend: AbstractBackend) -> dict[str, Any]:
        """Execute the performance action on the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            Dict containing the performance data.

        Raises:
            ValueError: If the action is not recognized.
        """
        await backend.launch(self.params.browser)
        try:
            await backend.navigate(self.params.url, self.params.wait)
            return await self._run_action(backend)
        finally:
            await backend.close()

    async def _run_action(self, backend: AbstractBackend) -> dict[str, Any]:
        action = self.params.action
        if action == "metrics":
            return await backend.perf_metrics()
        if action == "trace":
            return await backend.perf_trace(self.params.duration_ms)
        if action == "profile":
            return await backend.perf_profile(self.params.duration_ms)
        if action == "heap":
            return await backend.perf_heap_snapshot()
        if action == "coverage":
            return await backend.perf_coverage()
        if action == "css-coverage":
            return await backend.perf_css_coverage()
        raise ValueError(f"Unknown performance action: {action}")
