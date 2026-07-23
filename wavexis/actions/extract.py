"""Extract action for structured data extraction via CSS selector schema."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy, _validate_url
from wavexis.exceptions import ActionError


@dataclass
class ExtractParams:
    """Parameters for structured data extraction.

    Attributes:
        url: URL to navigate to before extraction.
        schema: JSON mapping of field names to CSS selectors.
        selector: Optional CSS selector to scope extraction (repeat per match).
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    schema: dict[str, str] = field(default_factory=dict)
    selector: str | None = None
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)

    def __post_init__(self) -> None:
        """Validate extraction parameters."""
        _validate_url(self.url)
        if not isinstance(self.schema, dict):
            raise ActionError("schema must be a dict of field names to CSS selectors")
        for key, value in self.schema.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ActionError("schema keys and values must be strings")
            if "\x00" in value:
                raise ActionError("selector cannot contain null bytes")
        if self.selector is not None and not isinstance(self.selector, str):
            raise ActionError("selector must be a string or None")


class ExtractAction(BaseAction[ExtractParams, list[dict[str, Any]]]):
    """Action for extracting structured data from a page using a CSS selector schema."""

    async def execute(self, backend: AbstractBackend) -> list[dict[str, Any]]:
        """Execute the extraction on the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            List of dicts with field names mapped to extracted text/HTML.
        """
        if self.params.url:
            await backend.navigate(self.params.url, self.params.wait)

        schema_json = json.dumps(self.params.schema)
        if self.params.selector:
            selector_json = json.dumps(self.params.selector)
            js = f"""
                (() => {{
                    const schema = {schema_json};
                    const elements = document.querySelectorAll({selector_json});
                    return Array.from(elements).map(el => {{
                        const row = {{}};
                        for (const [field, sel] of Object.entries(schema)) {{
                            const node = el.querySelector(sel);
                            row[field] = node ? node.textContent.trim() : null;
                        }}
                        return row;
                    }});
                }})()
            """
        else:
            js = f"""
                (() => {{
                    const schema = {schema_json};
                    const row = {{}};
                    for (const [field, sel] of Object.entries(schema)) {{
                        const node = document.querySelector(sel);
                        row[field] = node ? node.textContent.trim() : null;
                    }}
                    return [row];
                }})()
            """

        result = await backend.eval(js, await_promise=False)
        if isinstance(result, list):
            return result
        return []
