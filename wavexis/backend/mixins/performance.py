"""Performance profiling and tracing mixin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PerformanceBackend(ABC):
    """Performance metrics, traces, profiles, and code coverage."""

    @abstractmethod
    async def perf_metrics(self) -> dict[str, Any]:
        """Get current performance metrics from the page."""

    @abstractmethod
    async def perf_trace(self, duration_ms: int = 3000) -> dict[str, Any]:
        """Capture a performance trace for the given duration.

        Args:
            duration_ms: Trace duration in milliseconds.

        Returns:
            Dict containing trace events and metadata.
        """

    @abstractmethod
    async def perf_profile(self, duration_ms: int = 3000) -> dict[str, Any]:
        """Capture a CPU profile for the given duration.

        Args:
            duration_ms: Profile duration in milliseconds.

        Returns:
            Dict containing CPU profile data.
        """

    @abstractmethod
    async def perf_heap_snapshot(self) -> dict[str, Any]:
        """Capture a heap snapshot and return it as a dict."""

    @abstractmethod
    async def perf_coverage(self) -> dict[str, Any]:
        """Get JavaScript code coverage for the current page."""

    @abstractmethod
    async def perf_css_coverage(self) -> dict[str, Any]:
        """Get CSS rule usage coverage for the current page."""

    @abstractmethod
    async def start_combined_trace(
        self,
        capture_screenshots: bool = True,
        capture_network: bool = True,
        capture_console: bool = True,
    ) -> str:
        """Start a combined trace capturing screenshots, network, and console.

        Returns:
            A trace ID string for later stopping and collecting results.
        """

    @abstractmethod
    async def stop_combined_trace(self, trace_id: str) -> dict[str, Any]:
        """Stop a combined trace and return collected data.

        Args:
            trace_id: The trace ID returned by start_combined_trace.

        Returns:
            Dict with keys: trace_events, screenshots, network, console.
        """

    @abstractmethod
    async def performance_disable(self) -> None:
        """Disable the Performance domain."""

    @abstractmethod
    async def performance_enable(self) -> None:
        """Enable the Performance domain."""

    @abstractmethod
    async def performance_get_metrics(self) -> dict[str, Any]:
        """Get current values of run-time metrics."""

    @abstractmethod
    async def performance_set_time_domain(self, time_domain: str) -> None:
        """Set the time domain to use for collecting and reporting durations.

        Args:
            time_domain: Time domain ('timeTicks' or 'threadTicks').
        """

    # ── Tracing ───────────────────────────────────────────

    @abstractmethod
    async def tracing_start(
        self,
        categories: str = "",
        options: str = "",
        transfer_mode: str = "ReturnAsStream",
    ) -> None:
        """Start trace event collection.

        Args:
            categories: Comma-separated category filter.
            options: Comma-separated tracing options.
            transfer_mode: Transfer mode ('ReturnAsStream' or 'ReportEvents').
        """

    @abstractmethod
    async def tracing_end(self) -> None:
        """Stop trace event collection."""

    @abstractmethod
    async def tracing_get_categories(self) -> list[str]:
        """Get supported tracing categories.

        Returns:
            List of category name strings.
        """

    @abstractmethod
    async def tracing_record_clock_sync_marker(self, sync_id: str) -> None:
        """Record a clock sync marker.

        Args:
            sync_id: The sync marker ID.
        """

    @abstractmethod
    async def tracing_request_memory_dump(self) -> dict[str, Any]:
        """Request a memory dump.

        Returns:
            Dict with memory dump result info.
        """

    @abstractmethod
    async def tracing_get_track_event_descriptor(self, track_event: str) -> dict[str, Any]:
        """Get a track event descriptor.

        Args:
            track_event: The track event name.

        Returns:
            Dict with track event descriptor info.
        """
