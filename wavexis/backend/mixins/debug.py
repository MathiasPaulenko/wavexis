"""Debugger mixin — breakpoints, stepping, pause/resume."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DebugBackend(ABC):
    """JavaScript debugger operations."""

    @abstractmethod
    async def debug_set_breakpoint(
        self, url: str, line: int, condition: str | None = None
    ) -> str:
        """Set a breakpoint by URL and line number.

        Args:
            url: URL of the script to set the breakpoint in.
            line: Line number (0-based) for the breakpoint.
            condition: Optional condition expression.

        Returns:
            The breakpoint ID string.
        """

    @abstractmethod
    async def debug_set_breakpoint_function(self, function_name: str) -> str:
        """Set a breakpoint by function name.

        Args:
            function_name: Name of the function to break on.

        Returns:
            The breakpoint ID string.
        """

    @abstractmethod
    async def debug_remove_breakpoint(self, breakpoint_id: str) -> None:
        """Remove a breakpoint by ID.

        Args:
            breakpoint_id: The breakpoint ID returned from set_breakpoint.
        """

    @abstractmethod
    async def debug_step_over(self) -> None:
        """Step over the current statement in the debugger."""

    @abstractmethod
    async def debug_step_into(self) -> None:
        """Step into the current function call in the debugger."""

    @abstractmethod
    async def debug_step_out(self) -> None:
        """Step out of the current function in the debugger."""

    @abstractmethod
    async def debug_pause(self) -> None:
        """Pause JavaScript execution."""

    @abstractmethod
    async def debug_resume(self) -> None:
        """Resume JavaScript execution after a pause."""

    @abstractmethod
    async def debug_get_listeners(self, selector: str) -> list[dict[str, Any]]:
        """Get event listeners attached to an element by CSS selector.

        Args:
            selector: CSS selector for the target element.

        Returns:
            List of listener dicts (type, useCapture, passive, etc.).
        """
