"""Debug action for breakpoints, stepping, pause/resume, and listeners."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from browsix.actions.base import BaseAction
from browsix.backend.base import AbstractBackend
from browsix.config import BrowserOptions, DebugParams, WaitStrategy


@dataclass
class DebugActionParams:
    """Parameters for debugging operations.

    Attributes:
        url: URL to navigate to before debugging (optional for step/pause/resume).
        line: Line number for breakpoint (0-based).
        function_name: Function name for function breakpoint.
        condition: Optional condition expression for breakpoint.
        action: Debug action — "breakpoint", "function_breakpoint",
            "remove_breakpoint", "step_over", "step_into", "step_out",
            "pause", "resume", "listeners".
        breakpoint_id: Breakpoint ID for remove_breakpoint.
        selector: CSS selector for listeners action.
        script_url: URL of the script for breakpoint (distinct from page url).
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str | None = None
    line: int | None = None
    function_name: str | None = None
    condition: str | None = None
    action: str = "breakpoint"
    breakpoint_id: str | None = None
    selector: str | None = None
    script_url: str | None = None
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class DebugAction(BaseAction[DebugActionParams, Any]):
    """Action for debugging operations."""

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the debug action on the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            Result of the debug action (breakpoint ID, listener list, or None).

        Raises:
            ValueError: If the action is not recognized or required params missing.
        """
        await backend.launch(self.params.browser)
        try:
            if self.params.url:
                await backend.navigate(self.params.url, self.params.wait)
            return await self._run_action(backend)
        finally:
            await backend.close()

    async def _run_action(self, backend: AbstractBackend) -> Any:
        action = self.params.action
        if action == "breakpoint":
            if self.params.script_url is None or self.params.line is None:
                raise ValueError(
                    "script_url and line are required for breakpoint action"
                )
            return await backend.debug_set_breakpoint(
                self.params.script_url, self.params.line, self.params.condition
            )
        if action == "function_breakpoint":
            if not self.params.function_name:
                raise ValueError(
                    "function_name is required for function_breakpoint action"
                )
            return await backend.debug_set_breakpoint_function(
                self.params.function_name
            )
        if action == "remove_breakpoint":
            if not self.params.breakpoint_id:
                raise ValueError(
                    "breakpoint_id is required for remove_breakpoint action"
                )
            await backend.debug_remove_breakpoint(self.params.breakpoint_id)
            return None
        if action == "step_over":
            await backend.debug_step_over()
            return None
        if action == "step_into":
            await backend.debug_step_into()
            return None
        if action == "step_out":
            await backend.debug_step_out()
            return None
        if action == "pause":
            await backend.debug_pause()
            return None
        if action == "resume":
            await backend.debug_resume()
            return None
        if action == "listeners":
            if not self.params.selector:
                raise ValueError("selector is required for listeners action")
            return await backend.debug_get_listeners(self.params.selector)
        raise ValueError(f"Unknown debug action: {action}")


def debug_action_from_config(params: DebugParams) -> DebugAction:
    """Create a DebugAction from DebugParams config dataclass.

    Args:
        params: DebugParams from browsix.config.

    Returns:
        DebugAction instance with mapped parameters.
    """
    action_params = DebugActionParams(
        url=params.url,
        line=params.line,
        function_name=params.function_name,
        condition=params.condition,
        action=params.action,
        breakpoint_id=params.breakpoint_id,
        selector=params.selector,
        wait=params.wait,
        browser=params.browser,
    )
    return DebugAction(action_params)
