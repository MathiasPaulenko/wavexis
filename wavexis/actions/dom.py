"""DOM action for element inspection and manipulation."""

from __future__ import annotations

from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import DOMParams


class DOMAction(BaseAction[DOMParams, Any]):
    """Action for DOM operations.

    Supports get (outer/inner HTML), query (single/all), attr get/set/remove,
    remove, focus, and scroll.
    """

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the DOM action.

        Args:
            backend: The browser backend to use.

        Returns:
            str for "get" and "attr" actions, dict/list for "query",
            None for set/remove/focus/scroll.
        """
        params = self.params
        if params.url:
            await backend.navigate(params.url, params.wait)

        if params.action == "get":
            return await backend.dom_get(params.selector, outer=params.outer)

        if params.action == "query":
            return await backend.dom_query(params.selector, all=params.all)

        if params.action == "attr":
            if params.value is not None and params.attribute:
                await backend.dom_set_attr(
                    params.selector, params.attribute, params.value
                )
                return None
            if params.attribute:
                return await backend.dom_get_attr(params.selector, params.attribute)
            return None

        if params.action == "remove_attr":
            if params.attribute:
                await backend.dom_remove_attr(params.selector, params.attribute)
            return None

        if params.action == "remove":
            await backend.dom_remove(params.selector)
            return None

        if params.action == "focus":
            await backend.dom_focus(params.selector)
            return None

        if params.action == "scroll":
            await backend.dom_scroll(
                selector=params.selector or None,
                x=int(params.value or 0),
                y=int(params.attribute or 0) if params.attribute else 0,
            )
            return None

        return None
