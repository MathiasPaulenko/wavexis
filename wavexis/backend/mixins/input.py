"""Input interaction mixin (clicks, typing, iframe, shadow DOM)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class InputBackend(ABC):
    """Input interactions including iframe and shadow DOM piercing."""

    @abstractmethod
    async def click(
        self,
        selector: str,
        button: str = "left",
        click_count: int = 1,
        auto_wait: bool = True,
    ) -> None:
        """Click an element matching a CSS selector."""

    async def right_click(self, selector: str, auto_wait: bool = True) -> None:
        """Right-click an element matching a CSS selector."""
        await self.click(selector, button="right", click_count=1, auto_wait=auto_wait)

    async def double_click(self, selector: str, auto_wait: bool = True) -> None:
        """Double-click an element matching a CSS selector."""
        await self.click(selector, button="left", click_count=2, auto_wait=auto_wait)

    @abstractmethod
    async def type_text(self, selector: str, text: str, delay: int = 0) -> None:
        """Type text into an element, optionally with delay between keystrokes."""

    @abstractmethod
    async def fill(
        self, selector: str, value: str, auto_wait: bool = True
    ) -> None:
        """Fill an input element with a value (replaces existing content)."""

    @abstractmethod
    async def select_option(self, selector: str, value: str) -> None:
        """Select an option in a <select> element by value."""

    @abstractmethod
    async def hover(self, selector: str, auto_wait: bool = True) -> None:
        """Hover over an element matching a CSS selector."""

    @abstractmethod
    async def key_press(self, key: str) -> None:
        """Press a keyboard key (e.g. 'Enter', 'Tab')."""

    @abstractmethod
    async def drag(self, source: str, target: str) -> None:
        """Drag an element from source selector to target selector."""

    @abstractmethod
    async def tap(self, selector: str) -> None:
        """Tap an element (touch emulation click)."""

    @abstractmethod
    async def set_files(self, selector: str, files: list[str]) -> None:
        """Set files on a file input element.

        Args:
            selector: CSS selector for the <input type="file"> element.
            files: List of absolute file paths to upload.
        """

    @abstractmethod
    async def iframe_eval(
        self, iframe_selector: str, expression: str, await_promise: bool = False
    ) -> Any:
        """Evaluate a JavaScript expression inside an iframe.

        Args:
            iframe_selector: CSS selector for the <iframe> element.
            expression: JavaScript expression to evaluate in the iframe context.
            await_promise: Whether to await a returned Promise.
        """

    @abstractmethod
    async def iframe_click(
        self, iframe_selector: str, selector: str, auto_wait: bool = True
    ) -> None:
        """Click an element inside an iframe.

        Args:
            iframe_selector: CSS selector for the <iframe> element.
            selector: CSS selector inside the iframe for the target element.
            auto_wait: If True, wait for element to be visible before clicking.
        """

    @abstractmethod
    async def iframe_fill(
        self, iframe_selector: str, selector: str, value: str, auto_wait: bool = True
    ) -> None:
        """Fill an input element inside an iframe.

        Args:
            iframe_selector: CSS selector for the <iframe> element.
            selector: CSS selector inside the iframe for the target element.
            value: Value to set in the input field.
            auto_wait: If True, wait for element to be visible before filling.
        """

    @abstractmethod
    async def shadow_eval(
        self, selectors: list[str], expression: str, await_promise: bool = False
    ) -> Any:
        """Evaluate a JavaScript expression inside a shadow DOM tree.

        Args:
            selectors: List of CSS selectors piercing shadow boundaries.
                selectors[0] is in the main document, selectors[1] in
                selectors[0].shadowRoot, and so on.
            expression: JavaScript expression to evaluate in the shadow context.
            await_promise: Whether to await a returned Promise.
        """

    @abstractmethod
    async def shadow_click(
        self, selectors: list[str], auto_wait: bool = True
    ) -> None:
        """Click an element inside a shadow DOM tree.

        Args:
            selectors: List of CSS selectors piercing shadow boundaries.
            auto_wait: If True, wait for element to be visible before clicking.
        """

    @abstractmethod
    async def shadow_fill(
        self, selectors: list[str], value: str, auto_wait: bool = True
    ) -> None:
        """Fill an input element inside a shadow DOM tree.

        Args:
            selectors: List of CSS selectors piercing shadow boundaries.
            value: Value to set in the input field.
            auto_wait: If True, wait for element to be visible before filling.
        """
