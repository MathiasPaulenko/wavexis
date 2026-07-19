"""Input domain mixin for AbstractBackend (low-level CDP Input methods)."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any


class InputDomainBackend:
    """Low-level CDP Input domain for dispatching raw input events."""

    @abstractmethod
    async def input_cancel_dragging(self) -> None:
        """Cancel any ongoing drag operation."""

    @abstractmethod
    async def input_dispatch_drag_event(
        self, type: str, x: float, y: float, data: dict[str, Any] | None = None
    ) -> None:
        """Dispatch a drag event to the page."""

    @abstractmethod
    async def input_dispatch_key_event(
        self,
        type: str,
        key: str = "",
        code: str = "",
        windows_virtual_key_code: int = 0,
        native_virtual_key_code: int = 0,
        modifiers: int = 0,
        text: str = "",
        unmodified_text: str = "",
        auto_repeat: bool = False,
        is_keypad: bool = False,
        is_system_key: bool = False,
        location: int = 0,
        commands: list[str] | None = None,
    ) -> None:
        """Dispatch a key event to the page."""

    @abstractmethod
    async def input_dispatch_mouse_event(
        self,
        type: str,
        x: float,
        y: float,
        button: str = "none",
        click_count: int = 0,
        modifiers: int = 0,
        timestamp: float = 0,
        delta_x: float = 0,
        delta_y: float = 0,
    ) -> None:
        """Dispatch a mouse event to the page."""

    @abstractmethod
    async def input_dispatch_touch_event(
        self,
        type: str,
        touch_points: list[dict[str, Any]],
        modifiers: int = 0,
        timestamp: float = 0,
    ) -> None:
        """Dispatch a touch event to the page."""

    @abstractmethod
    async def input_emulate_touch_from_mouse_event(
        self,
        type: str,
        x: float,
        y: float,
        button: str = "none",
        timestamp: float = 0,
        delta_x: float = 0,
        delta_y: float = 0,
        modifiers: int = 0,
        click_count: int = 0,
    ) -> None:
        """Emulate a touch event from a mouse event."""

    @abstractmethod
    async def input_ime_set_composition(
        self,
        text: str,
        selection_start: int,
        selection_end: int,
        replacement_start: int = 0,
        replacement_end: int = 0,
    ) -> None:
        """Set the IME composition."""

    @abstractmethod
    async def input_insert_text(self, text: str) -> None:
        """Insert text into the focused element."""

    @abstractmethod
    async def input_set_ignore_input_events(self, ignore: bool) -> None:
        """Set whether to ignore input events."""

    @abstractmethod
    async def input_set_intercept_drags(self, enabled: bool) -> None:
        """Set whether to intercept drag operations."""

    @abstractmethod
    async def input_synthesize_pinch_gesture(
        self, x: float, y: float, scale_factor: float, relative_pointer_speed: int = 0
    ) -> None:
        """Synthesize a pinch gesture."""

    @abstractmethod
    async def input_synthesize_scroll_gesture(
        self,
        x: float,
        y: float,
        x_distance: float = 0,
        y_distance: float = 0,
        x_overscroll: float = 0,
        y_overscroll: float = 0,
        prevent_fling: bool = True,
        speed: int = 0,
        repeat_count: int = 0,
        repeat_delay_ms: int = 0,
        interaction_source_name: str = "",
    ) -> None:
        """Synthesize a scroll gesture."""

    @abstractmethod
    async def input_synthesize_tap_gesture(
        self, x: float, y: float, duration: int = 0, tap_count: int = 1
    ) -> None:
        """Synthesize a tap gesture."""
