"""Combined trace action for capturing screenshots, network, console, and trace events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy


@dataclass
class CombinedTraceParams:
    """Parameters for combined trace.

    Attributes:
        url: URL to navigate to before tracing.
        action: "start" or "stop".
        trace_id: Trace ID returned by start (required for stop).
        duration_ms: Duration to wait before stopping (for start action).
        capture_screenshots: Capture screenshots during trace.
        capture_network: Capture network events during trace.
        capture_console: Capture console events during trace.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    action: str = "start"
    trace_id: str = ""
    duration_ms: int = 3000
    capture_screenshots: bool = True
    capture_network: bool = True
    capture_console: bool = True
    wait: WaitStrategy | None = None
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class CombinedTraceAction(BaseAction[CombinedTraceParams, dict[str, Any]]):
    """Action for starting or stopping a combined trace.

    Start: navigates to URL, starts combined trace, waits duration_ms, stops,
    and returns all collected data in one call.
    Stop: stops a previously started trace by ID.
    """

    async def execute(self, backend: AbstractBackend) -> dict[str, Any]:
        """Execute the combined trace action.

        Args:
            backend: The browser backend to use.

        Returns:
            Dict with trace data (trace_events, screenshots, network, console).
        """
        import asyncio

        if self.params.url:
            await backend.navigate(self.params.url, self.params.wait)

        if self.params.action == "start":
            trace_id = await backend.start_combined_trace(
                capture_screenshots=self.params.capture_screenshots,
                capture_network=self.params.capture_network,
                capture_console=self.params.capture_console,
            )
            await asyncio.sleep(self.params.duration_ms / 1000)
            return await backend.stop_combined_trace(trace_id)

        if self.params.action == "stop" and self.params.trace_id:
            return await backend.stop_combined_trace(self.params.trace_id)

        return {"error": f"Unknown action: {self.params.action}"}
