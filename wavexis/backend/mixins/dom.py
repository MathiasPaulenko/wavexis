"""DOM inspection and manipulation mixin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DOMBackend(ABC):
    """DOM query, mutation, and natural-language locator operations."""

    @abstractmethod
    async def dom_get(self, selector: str, outer: bool = True) -> str:
        """Get the HTML of an element matching a CSS selector."""

    @abstractmethod
    async def dom_query(
        self, selector: str, all: bool = False
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Query elements by CSS selector.

        Returns a list when all=True, a single dict when all=False.
        """

    @abstractmethod
    async def dom_set_attr(self, selector: str, name: str, value: str) -> None:
        """Set an attribute on an element matching a CSS selector."""

    @abstractmethod
    async def dom_get_attr(self, selector: str, name: str) -> str:
        """Get an attribute value from an element matching a CSS selector."""

    @abstractmethod
    async def dom_remove_attr(self, selector: str, name: str) -> None:
        """Remove an attribute from an element matching a CSS selector."""

    @abstractmethod
    async def dom_remove(self, selector: str) -> None:
        """Remove an element matching a CSS selector from the DOM."""

    @abstractmethod
    async def dom_focus(self, selector: str) -> None:
        """Focus an element matching a CSS selector."""

    @abstractmethod
    async def dom_scroll(
        self, selector: str | None = None, x: int = 0, y: int = 0
    ) -> None:
        """Scroll to an element or by offset."""

    @abstractmethod
    async def suggest_locator(
        self, selector: str, all: bool = False
    ) -> list[str] | str:
        """Suggest the best CSS selector for an element.

        Analyzes the element and generates optimal selectors in priority order:
        id > data-testid > aria-label > text > tag.classes > nth-of-type chain.

        Args:
            selector: CSS selector for the target element.
            all: If True, return multiple suggestions; otherwise just the best one.

        Returns:
            List of selector strings when all=True, single best selector when all=False.
        """

    @abstractmethod
    async def find_by_text(
        self, query: str, all: bool = False
    ) -> list[str] | str:
        """Find elements by natural language text query.

        Searches all visible elements by text content, aria-label,
        placeholder, title, and alt text using fuzzy matching.

        Args:
            query: Natural language query (e.g. "the login button").
            all: If True, return all matches; otherwise just the best one.

        Returns:
            List of CSS selector strings when all=True, single best when all=False.

        Raises:
            ElementNotFoundError: If no element matches the query.
        """

    @abstractmethod
    async def nl_click(
        self, query: str, auto_wait: bool = True
    ) -> None:
        """Click an element found by natural language text query.

        Args:
            query: Natural language query (e.g. "login button").
            auto_wait: If True, wait for element to be visible before clicking.
        """

    @abstractmethod
    async def nl_fill(
        self, query: str, value: str, auto_wait: bool = True
    ) -> None:
        """Fill an input element found by natural language text query.

        Args:
            query: Natural language query (e.g. "email field").
            value: Value to set in the input field.
            auto_wait: If True, wait for element to be visible before filling.
        """

    @abstractmethod
    async def dom_snapshot(self) -> dict[str, Any]:
        """Capture a DOM snapshot of the current page.

        Returns:
            Dict containing the raw DOM snapshot (documents, strings, etc.).
        """
