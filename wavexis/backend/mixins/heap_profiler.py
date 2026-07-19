"""HeapProfiler mixin — heap snapshot and sampling operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class HeapProfilerBackend(ABC):
    """Heap profiler operations."""

    @abstractmethod
    async def heap_profiler_add_inspected_heap_object(self, heap_object_id: str) -> None:
        """Add an inspected heap object."""

    @abstractmethod
    async def heap_profiler_collect_garbage(self) -> None:
        """Collect garbage."""

    @abstractmethod
    async def heap_profiler_disable(self) -> None:
        """Disable the HeapProfiler domain."""

    @abstractmethod
    async def heap_profiler_enable(self) -> None:
        """Enable the HeapProfiler domain."""

    @abstractmethod
    async def heap_profiler_get_heap_object_id(self, object_id: str) -> str:
        """Get the heap object ID for a remote object."""

    @abstractmethod
    async def heap_profiler_get_object_by_heap_object_id(
        self, object_id: str, object_group: str = ""
    ) -> dict[str, Any]:
        """Get an object by heap object ID."""

    @abstractmethod
    async def heap_profiler_get_sampling_profile(self) -> dict[str, Any]:
        """Get the current sampling profile."""

    @abstractmethod
    async def heap_profiler_start_sampling(self, sampling_interval: int = 0) -> None:
        """Start heap sampling."""

    @abstractmethod
    async def heap_profiler_start_tracking_heap_objects(
        self, track_allocations: bool = False
    ) -> None:
        """Start tracking heap objects."""

    @abstractmethod
    async def heap_profiler_stop_sampling(self) -> dict[str, Any]:
        """Stop heap sampling and return the profile."""

    @abstractmethod
    async def heap_profiler_stop_tracking_heap_objects(self, report_progress: bool = False) -> None:
        """Stop tracking heap objects."""

    @abstractmethod
    async def heap_profiler_take_heap_snapshot(self, report_progress: bool = False) -> None:
        """Take a heap snapshot."""
