"""EventBreakpoints mixin — event breakpoint instrumentation."""

from __future__ import annotations

from abc import ABC, abstractmethod


class EventBreakpointsBackend(ABC):
    """Event breakpoint operations."""

    @abstractmethod
    async def event_breakpoints_clear_instrumentation_breakpoint(
        self, instrumentation_name: str
    ) -> None:
        """Clear an instrumentation breakpoint for events."""

    @abstractmethod
    async def event_breakpoints_disable(self) -> None:
        """Disable the EventBreakpoints domain."""

    @abstractmethod
    async def event_breakpoints_remove_instrumentation_breakpoint(
        self, instrumentation_name: str
    ) -> None:
        """Remove an instrumentation breakpoint for events."""

    @abstractmethod
    async def event_breakpoints_set_instrumentation_breakpoint(
        self, instrumentation_name: str
    ) -> None:
        """Set an instrumentation breakpoint for events."""
