"""DOMDebugger mixin — DOM breakpoints, event listener breakpoints, XHR breakpoints."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DOMDebuggerBackend(ABC):
    """DOM debugger operations for breakpoints on DOM mutations, events, and XHR."""

    @abstractmethod
    async def dom_debugger_get_event_listeners(
        self, object_id: str, depth: int = 0, pierce: bool = False
    ) -> list[dict[str, Any]]:
        """Get event listeners for an object by its remote object ID."""

    @abstractmethod
    async def dom_debugger_remove_dom_breakpoint(self, node_id: int, type: str) -> None:
        """Remove a DOM breakpoint from a node by ID."""

    @abstractmethod
    async def dom_debugger_remove_event_listener_breakpoint(
        self, event_name: str, target_name: str | None = None
    ) -> None:
        """Remove an event listener breakpoint."""

    @abstractmethod
    async def dom_debugger_remove_instrumentation_breakpoint(self, event_name: str) -> None:
        """Remove an instrumentation breakpoint."""

    @abstractmethod
    async def dom_debugger_remove_xhr_breakpoint(self, url: str) -> None:
        """Remove an XHR breakpoint for a URL substring."""

    @abstractmethod
    async def dom_debugger_set_break_on_csp_violation(self, enabled: bool) -> None:
        """Set whether to break on CSP violations."""

    @abstractmethod
    async def dom_debugger_set_dom_breakpoint(self, node_id: int, type: str) -> None:
        """Set a DOM breakpoint on a node by ID."""

    @abstractmethod
    async def dom_debugger_set_event_listener_breakpoint(
        self, event_name: str, target_name: str | None = None
    ) -> None:
        """Set an event listener breakpoint."""

    @abstractmethod
    async def dom_debugger_set_instrumentation_breakpoint(self, event_name: str) -> None:
        """Set an instrumentation breakpoint."""

    @abstractmethod
    async def dom_debugger_set_xhr_breakpoint(self, url: str) -> None:
        """Set an XHR breakpoint for a URL substring."""
