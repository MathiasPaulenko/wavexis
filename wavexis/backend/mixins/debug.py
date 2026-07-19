"""Debugger mixin — breakpoints, stepping, pause/resume."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DebugBackend(ABC):
    """JavaScript debugger operations."""

    @abstractmethod
    async def debug_set_breakpoint(self, url: str, line: int, condition: str | None = None) -> str:
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

    @abstractmethod
    async def debug_evaluate_on_call_frame(
        self, call_frame_id: str, expression: str
    ) -> dict[str, Any]:
        """Evaluate a JavaScript expression in the context of a paused call frame."""

    @abstractmethod
    async def debug_get_script_source(self, script_id: str) -> str:
        """Get the source code of a script by ID."""

    @abstractmethod
    async def debug_get_stack_trace(self) -> dict[str, Any]:
        """Get the current JavaScript stack trace."""

    @abstractmethod
    async def debug_get_possible_breakpoints(
        self, start: dict[str, Any], end: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Get possible breakpoint locations for a range in a script."""

    @abstractmethod
    async def debug_search_in_content(
        self, script_id: str, query: str, case_sensitive: bool = False, is_regex: bool = False
    ) -> list[dict[str, Any]]:
        """Search for a string in script content."""

    @abstractmethod
    async def debug_set_pause_on_exceptions(self, state: str) -> None:
        """Set pause on exceptions mode (none, uncaught, all)."""

    @abstractmethod
    async def debug_set_breakpoints_active(self, active: bool) -> None:
        """Enable or disable all breakpoints."""

    @abstractmethod
    async def debug_set_skip_all_pauses(self, skip: bool) -> None:
        """Skip all pauses (including breakpoints) for the duration of the current script."""

    @abstractmethod
    async def debug_set_script_source(self, script_id: str, source: str) -> dict[str, Any]:
        """Edit the source code of a live script."""

    @abstractmethod
    async def debug_continue_to_location(self, url: str, line: int, column: int = 0) -> None:
        """Continue execution until a specific location is reached."""

    @abstractmethod
    async def debug_disable(self) -> None:
        """Disable the Debugger domain."""

    @abstractmethod
    async def debug_disassemble_wasm_module(self, script_id: str) -> dict[str, Any]:
        """Disassemble a WASM module by script ID."""

    @abstractmethod
    async def debug_enable(self) -> None:
        """Enable the Debugger domain."""

    @abstractmethod
    async def debug_get_wasm_bytecode(self, script_id: str, offset: int) -> dict[str, Any]:
        """Get WASM bytecode for a script by ID and offset."""

    @abstractmethod
    async def debug_next_wasm_disassembly_chunk(self, disassembly_id: str) -> dict[str, Any]:
        """Get the next chunk of a WASM disassembly."""

    @abstractmethod
    async def debug_pause_on_async_call(self, operation: str) -> None:
        """Pause on an async call operation."""

    @abstractmethod
    async def debug_restart_frame(self, call_frame_id: str) -> None:
        """Restart a call frame by ID."""

    @abstractmethod
    async def debug_set_async_call_stack_depth(self, depth: int) -> None:
        """Set the async call stack depth."""

    @abstractmethod
    async def debug_set_blackbox_execution_contexts(self, unique_ids: list[str]) -> None:
        """Set blackboxed execution contexts by unique IDs."""

    @abstractmethod
    async def debug_set_blackbox_patterns(self, patterns: list[str]) -> None:
        """Set blackbox patterns for script URLs."""

    @abstractmethod
    async def debug_set_blackboxed_ranges(
        self, script_id: str, positions: list[dict[str, Any]]
    ) -> None:
        """Set blackboxed ranges for a script."""

    @abstractmethod
    async def debug_set_breakpoint_raw(
        self, location: dict[str, Any], condition: str | None = None
    ) -> dict[str, Any]:
        """Set a breakpoint at a raw location in a script."""

    @abstractmethod
    async def debug_set_breakpoint_by_url(
        self, url: str, line_number: int, column_number: int = 0, condition: str | None = None
    ) -> dict[str, Any]:
        """Set a breakpoint by URL and line number."""

    @abstractmethod
    async def debug_set_breakpoint_on_function_call(
        self, object_id: str, condition: str | None = None
    ) -> dict[str, Any]:
        """Set a breakpoint on a function call by object ID."""

    @abstractmethod
    async def debug_set_instrumentation_breakpoint(self, instrumentation: str) -> dict[str, Any]:
        """Set an instrumentation breakpoint."""

    @abstractmethod
    async def debug_set_return_value(self, new_value: dict[str, Any]) -> None:
        """Set the return value of the current call frame."""

    @abstractmethod
    async def debug_set_variable_value(
        self, call_frame_id: str, scope_number: int, variable_name: str, new_value: dict[str, Any]
    ) -> None:
        """Set a variable value in a scope of a call frame."""
