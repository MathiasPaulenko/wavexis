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
    async def dom_scroll(self, selector: str | None = None, x: int = 0, y: int = 0) -> None:
        """Scroll to an element or by offset."""

    @abstractmethod
    async def suggest_locator(self, selector: str, all: bool = False) -> list[str] | str:
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
    async def find_by_text(self, query: str, all: bool = False) -> list[str] | str:
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
    async def nl_click(self, query: str, auto_wait: bool = True) -> None:
        """Click an element found by natural language text query.

        Args:
            query: Natural language query (e.g. "login button").
            auto_wait: If True, wait for element to be visible before clicking.
        """

    @abstractmethod
    async def nl_fill(self, query: str, value: str, auto_wait: bool = True) -> None:
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

    @abstractmethod
    async def dom_get_document(self) -> dict[str, Any]:
        """Get the document root node."""

    @abstractmethod
    async def dom_get_flattened_document(self) -> dict[str, Any]:
        """Get the flattened document tree."""

    @abstractmethod
    async def dom_get_box_model(self, selector: str) -> dict[str, Any]:
        """Get the box model for an element matching a CSS selector."""

    @abstractmethod
    async def dom_get_content_quads(self, selector: str) -> list[dict[str, Any]]:
        """Get the content quads for an element matching a CSS selector."""

    @abstractmethod
    async def dom_get_node_for_location(self, x: int, y: int) -> dict[str, Any]:
        """Get the node ID for a location in the viewport (hit testing)."""

    @abstractmethod
    async def dom_perform_search(self, query: str) -> dict[str, Any]:
        """Search the DOM for the given query string."""

    @abstractmethod
    async def dom_get_search_results(
        self, search_id: str, from_index: int = 0, to_index: int = 0
    ) -> list[dict[str, Any]]:
        """Get search results for a DOM search session."""

    @abstractmethod
    async def dom_scroll_into_view_if_needed(self, selector: str) -> None:
        """Scroll an element matching a CSS selector into view if needed."""

    @abstractmethod
    async def dom_describe_node(self, node_id: int) -> dict[str, Any]:
        """Describe a DOM node by node ID.

        Args:
            node_id: The CDP node ID to describe.

        Returns:
            Node description dict with attributes like nodeName, nodeValue, etc.
        """

    @abstractmethod
    async def dom_get_outer_html(self, node_id: int) -> str:
        """Get the outer HTML of a node by ID.

        Args:
            node_id: The CDP node ID.

        Returns:
            The outer HTML string.
        """

    @abstractmethod
    async def dom_remove_node(self, node_id: int) -> None:
        """Remove a node from the DOM by ID.

        Args:
            node_id: The CDP node ID to remove.
        """

    @abstractmethod
    async def dom_set_node_value(self, node_id: int, value: str) -> None:
        """Set the value of a node by ID.

        Args:
            node_id: The CDP node ID.
            value: The new value.
        """

    @abstractmethod
    async def dom_set_outer_html(self, node_id: int, outer_html: str) -> None:
        """Set the outer HTML of a node by ID.

        Args:
            node_id: The CDP node ID.
            outer_html: The new outer HTML string.
        """

    @abstractmethod
    async def dom_request_node(self, node_id: int) -> int:
        """Request a node by ID and return its node ID.

        Args:
            node_id: The CDP node ID.

        Returns:
            The node ID.
        """

    @abstractmethod
    async def dom_resolve_node(self, node_id: int) -> dict[str, Any]:
        """Resolve a node to a remote object.

        Args:
            node_id: The CDP node ID.

        Returns:
            Remote object dict with objectId, type, etc.
        """

    @abstractmethod
    async def dom_set_attribute_value(self, node_id: int, name: str, value: str) -> None:
        """Set an attribute value on a node by ID.

        Args:
            node_id: The CDP node ID.
            name: The attribute name.
            value: The attribute value.
        """

    @abstractmethod
    async def dom_remove_attribute(self, node_id: int, name: str) -> None:
        """Remove an attribute from a node by ID.

        Args:
            node_id: The CDP node ID.
            name: The attribute name to remove.
        """

    @abstractmethod
    async def dom_request_child_nodes(self, node_id: int, depth: int = -1) -> None:
        """Request child nodes of a node by ID.

        Args:
            node_id: The CDP node ID.
            depth: Maximum depth (-1 for all).
        """

    @abstractmethod
    async def dom_collect_class_names_from_subtree(self, node_id: int) -> list[str]:
        """Collect class names from the subtree of a node by ID."""

    @abstractmethod
    async def dom_copy_to(
        self, node_id: int, target_node_id: int, insert_before_node_id: int | None = None
    ) -> None:
        """Copy a node to a target node, optionally before another node."""

    @abstractmethod
    async def dom_disable(self) -> None:
        """Disable the DOM agent."""

    @abstractmethod
    async def dom_discard_search_results(self, search_id: str) -> None:
        """Discard search results for a DOM search session."""

    @abstractmethod
    async def dom_enable(self) -> None:
        """Enable the DOM agent."""

    @abstractmethod
    async def dom_focus_node(self, node_id: int) -> None:
        """Focus a node by ID."""

    @abstractmethod
    async def dom_force_show_popover(self, node_id: int) -> None:
        """Force show a popover for a node by ID."""

    @abstractmethod
    async def dom_get_anchor_element(self, node_id: int) -> dict[str, Any]:
        """Get the anchor element for a node by ID."""

    @abstractmethod
    async def dom_get_node_attribute(self, node_id: int, name: str) -> str:
        """Get an attribute value from a node by ID."""

    @abstractmethod
    async def dom_get_container_for_node(
        self, node_id: int, container_name: str | None = None
    ) -> dict[str, Any]:
        """Get the container for a node by ID."""

    @abstractmethod
    async def dom_get_detached_dom_nodes(self) -> list[dict[str, Any]]:
        """Get detached DOM nodes."""

    @abstractmethod
    async def dom_get_element_by_relation(self, node_id: int, relation: str) -> dict[str, Any]:
        """Get an element by relation from a node by ID."""

    @abstractmethod
    async def dom_get_file_info(self, node_id: int) -> dict[str, Any]:
        """Get file info for a node by ID."""

    @abstractmethod
    async def dom_get_frame_owner(self, frame_id: str) -> dict[str, Any]:
        """Get the frame owner node for a frame ID."""

    @abstractmethod
    async def dom_get_node_stack_traces(self, node_id: int) -> dict[str, Any]:
        """Get stack traces for a node by ID."""

    @abstractmethod
    async def dom_get_nodes_for_subtree_by_style(
        self, node_id: int, computed_styles: list[str], pierce: bool = False
    ) -> list[dict[str, Any]]:
        """Get nodes in a subtree matching the given computed styles."""

    @abstractmethod
    async def dom_get_querying_descendants_for_container(
        self, node_id: int
    ) -> list[dict[str, Any]]:
        """Get querying descendants for a container node by ID."""

    @abstractmethod
    async def dom_get_relayout_boundary(self, node_id: int) -> dict[str, Any]:
        """Get the relayout boundary for a node by ID."""

    @abstractmethod
    async def dom_get_top_layer_elements(self) -> list[dict[str, Any]]:
        """Get top layer elements."""

    @abstractmethod
    async def dom_hide_highlight(self) -> None:
        """Hide any DOM highlight."""

    @abstractmethod
    async def dom_highlight_node(self, node_id: int, highlight_config: dict[str, Any]) -> None:
        """Highlight a node by ID with the given highlight config."""

    @abstractmethod
    async def dom_highlight_rect(
        self, x: int, y: int, width: int, height: int, highlight_config: dict[str, Any]
    ) -> None:
        """Highlight a rect with the given highlight config."""

    @abstractmethod
    async def dom_mark_undoable_state(self) -> None:
        """Mark an undoable state in the DOM."""

    @abstractmethod
    async def dom_move_to(
        self, node_id: int, target_node_id: int, insert_before_node_id: int | None = None
    ) -> None:
        """Move a node to a target node, optionally before another node."""

    @abstractmethod
    async def dom_push_node_by_path_to_frontend(self, path: str) -> dict[str, Any]:
        """Push a node by path to frontend."""

    @abstractmethod
    async def dom_push_nodes_by_backend_ids_to_frontend(
        self, backend_node_ids: list[int]
    ) -> dict[str, Any]:
        """Push nodes by backend IDs to frontend."""

    @abstractmethod
    async def dom_query_selector(self, node_id: int, selector: str) -> dict[str, Any]:
        """Query a single selector within a node's subtree."""

    @abstractmethod
    async def dom_query_selector_all(self, node_id: int, selector: str) -> list[dict[str, Any]]:
        """Query all selectors within a node's subtree."""

    @abstractmethod
    async def dom_redo(self) -> None:
        """Redo the last DOM action."""

    @abstractmethod
    async def dom_remove_node_by_id(self, node_id: int) -> None:
        """Remove a node from the DOM by ID."""

    @abstractmethod
    async def dom_set_attributes_as_text(self, node_id: int, text: str) -> None:
        """Set attributes on a node from a text string."""

    @abstractmethod
    async def dom_set_file_input_files(self, node_id: int, files: list[str]) -> None:
        """Set files for a file input node by ID."""

    @abstractmethod
    async def dom_set_inspected_node(self, node_id: int) -> None:
        """Set the inspected node by ID."""

    @abstractmethod
    async def dom_set_node_name(self, node_id: int, name: str) -> dict[str, Any]:
        """Set the name of a node by ID."""

    @abstractmethod
    async def dom_set_node_stack_traces_enabled(self, enable: bool) -> None:
        """Enable or disable node stack traces."""

    @abstractmethod
    async def dom_set_text_content(self, node_id: int, text: str) -> None:
        """Set the text content of a node by ID."""

    @abstractmethod
    async def dom_undo(self) -> None:
        """Undo the last DOM action."""
