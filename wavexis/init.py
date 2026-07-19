"""Interactive config generator for wavexis.yaml."""

from __future__ import annotations

from typing import Any

import yaml

__all__ = [
    "TEMPLATES",
    "TEMPLATE_NAMES",
    "generate_config",
    "interactive_init",
    "list_templates",
]

TEMPLATES: dict[str, dict[str, Any]] = {
    "screenshot": {
        "description": "Take a screenshot of a URL",
        "actions": [
            {"screenshot": {"url": "https://example.com", "full_page": True, "format": "png"}},
        ],
    },
    "pdf": {
        "description": "Generate a PDF from a URL",
        "actions": [
            {"pdf": {"url": "https://example.com", "paper": "a4"}},
        ],
    },
    "scrape": {
        "description": "Scrape data from one or more URLs",
        "actions": [
            {"scrape": {"urls": ["https://example.com"], "expression": "document.title"}},
        ],
    },
    "eval": {
        "description": "Evaluate a JavaScript expression on a page",
        "actions": [
            {"eval": {"url": "https://example.com", "expression": "document.title"}},
        ],
    },
    "multi-step": {
        "description": "Navigate, interact, and screenshot in sequence",
        "actions": [
            {"navigate": {"url": "https://example.com"}},
            {"click": {"selector": "#button"}},
            {"type": {"selector": "#input", "text": "hello"}},
            {"screenshot": {"url": "", "full_page": True, "format": "png"}},
        ],
    },
    "cookies": {
        "description": "Navigate and get cookies from a page",
        "actions": [
            {"navigate": {"url": "https://example.com"}},
            {"eval": {"url": "", "expression": "document.cookie"}},
        ],
    },
    "har": {
        "description": "Capture network traffic as HAR",
        "actions": [
            {"navigate": {"url": "https://example.com"}},
            {"har": {"wait": {"strategy": "load"}}},
        ],
    },
}

TEMPLATE_NAMES = list(TEMPLATES.keys())


def generate_config(
    template: str,
    url: str | None = None,
    expression: str | None = None,
    selector: str | None = None,
    text: str | None = None,
) -> str:
    """Generate a wavexis YAML config from a template with optional overrides.

    Args:
        template: Template name (must be in TEMPLATES).
        url: Override URL for all actions that accept a url.
        expression: Override JS expression for scrape/eval.
        selector: Override CSS selector for click/type.
        text: Override text for type action.

    Returns:
        YAML string representing the config.

    Raises:
        ValueError: If the template name is not recognized.
    """
    if template not in TEMPLATES:
        raise ValueError(f"Unknown template: {template}. Available: {', '.join(TEMPLATE_NAMES)}")

    config = TEMPLATES[template]
    actions: list[dict[str, Any]] = []

    for action_dict in config["actions"]:
        action_type = next(iter(action_dict))
        params = dict(action_dict[action_type])

        if url and "url" in params:
            params["url"] = url
        if url and "urls" in params:
            params["urls"] = [url]
        if expression and action_type in ("scrape", "eval"):
            params["expression"] = expression
        if selector and action_type in ("click", "type"):
            params["selector"] = selector
        if text and action_type == "type":
            params["text"] = text

        actions.append({action_type: params})

    return str(
        yaml.dump(
            {"actions": actions},
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
    )


def list_templates() -> list[tuple[str, str]]:
    """List available templates with their descriptions.

    Returns:
        List of (name, description) tuples.
    """
    return [(name, TEMPLATES[name]["description"]) for name in TEMPLATE_NAMES]


def interactive_init(
    input_fn: Any = input,
    output_fn: Any = print,
) -> str:
    """Run an interactive wizard to generate a wavexis.yaml config.

    Args:
        input_fn: Input function (defaults to built-in input).
        output_fn: Output function (defaults to built-in print).

    Returns:
        Generated YAML string.
    """
    output_fn("wavexis init — generate a wavexis.yaml config\n")

    output_fn("\nAvailable templates:")
    for i, (name, desc) in enumerate(list_templates(), 1):
        output_fn(f"  {i}. {name} — {desc}")

    choice = input_fn(f"\nSelect template (1-{len(TEMPLATE_NAMES)}) or name: ").strip()
    if choice.isdigit():
        idx = int(choice) - 1
        if idx < 0 or idx >= len(TEMPLATE_NAMES):
            raise ValueError(f"Invalid selection: {choice}")
        template = TEMPLATE_NAMES[idx]
    elif choice in TEMPLATES:
        template = choice
    else:
        raise ValueError(f"Unknown template: {choice}. Available: {', '.join(TEMPLATE_NAMES)}")

    url = input_fn("URL [https://example.com]: ").strip() or None
    expression: str | None = None
    selector: str | None = None
    text: str | None = None

    if template in ("scrape", "eval"):
        expression = input_fn("JS expression [document.title]: ").strip() or None

    if template in ("multi-step",):
        selector = input_fn("CSS selector for click [#button]: ").strip() or None
        text = input_fn("Text for type action [hello]: ").strip() or None

    return generate_config(
        template=template,
        url=url,
        expression=expression,
        selector=selector,
        text=text,
    )
