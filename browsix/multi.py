"""Multi-action YAML parser and executor."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from browsix.exceptions import MultiConfigError


def parse_yaml(path: Path) -> list[dict[str, Any]]:
    """Parse a YAML config file and validate its structure.

    Args:
        path: Path to the YAML config file.

    Returns:
        A list of action dicts, each with a single key (action type)
        and a dict of parameters.

    Raises:
        MultiConfigError: If the config structure is invalid.
    """
    if not path.exists():
        raise MultiConfigError("file", f"Config file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise MultiConfigError("root", "Config must be a YAML mapping")
    actions = raw.get("actions")
    if not isinstance(actions, list):
        raise MultiConfigError("actions", "Must be a list of action mappings")
    parsed: list[dict[str, Any]] = []
    for i, item in enumerate(actions):
        if not isinstance(item, dict) or len(item) != 1:
            raise MultiConfigError(
                f"actions[{i}]",
                "Each action must be a mapping with exactly one key",
            )
        action_type = next(iter(item))
        action_params = item[action_type]
        if not isinstance(action_params, dict):
            raise MultiConfigError(
                f"actions[{i}].{action_type}",
                "Action parameters must be a mapping",
            )
        parsed.append({action_type: action_params})
    return parsed


async def execute_actions(
    actions: list[dict[str, Any]],
    backend: Any,
) -> list[Any]:
    """Execute each action sequentially, reusing the same backend.

    Args:
        actions: List of action dicts from parse_yaml.
        backend: An launched AbstractBackend instance.

    Returns:
        List of results from each action.
    """
    results: list[Any] = []
    for action_dict in actions:
        action_type = next(iter(action_dict))
        params = action_dict[action_type]
        result = await _dispatch(action_type, params, backend)
        results.append(result)
    return results


async def _dispatch(
    action_type: str,
    params: dict[str, Any],
    backend: Any,
) -> Any:
    """Dispatch a single action to the appropriate action class.

    Args:
        action_type: Action type name (e.g. 'screenshot', 'pdf', 'scrape').
        params: Action parameters dict.
        backend: An launched AbstractBackend instance.

    Returns:
        The result of the action.
    """
    if action_type == "screenshot":
        from browsix.actions.screenshot import ScreenshotAction
        from browsix.config import ScreenshotParams, WaitStrategy

        sp = ScreenshotParams(
            url=params.get("url", ""),
            full_page=params.get("full_page", True),
            format=params.get("format", "png"),
            wait=WaitStrategy(strategy="load"),
        )
        return await ScreenshotAction(sp).execute(backend)

    if action_type == "pdf":
        from browsix.actions.pdf import PDFAction
        from browsix.config import PDFParams, WaitStrategy

        pp = PDFParams(
            url=params.get("url", ""),
            paper=params.get("paper", "letter"),
            wait=WaitStrategy(strategy="load"),
        )
        return await PDFAction(pp).execute(backend)

    if action_type == "scrape":
        from browsix.actions.scrape import ScrapeAction
        from browsix.config import ScrapeParams, WaitStrategy

        urls = params.get("urls") or [params.get("url", "")]
        scp = ScrapeParams(
            urls=urls,
            expression=params.get("expression", "document.title"),
            wait=WaitStrategy(strategy="load"),
        )
        return await ScrapeAction(scp).execute(backend)

    if action_type == "eval":
        from browsix.actions.eval import EvalAction
        from browsix.config import EvalParams, WaitStrategy

        ep = EvalParams(
            url=params.get("url", ""),
            expression=params.get("expression", ""),
            wait=WaitStrategy(strategy="load"),
        )
        return await EvalAction(ep).execute(backend)

    if action_type == "dom":
        from browsix.actions.dom import DOMAction
        from browsix.config import DOMParams, WaitStrategy

        dp = DOMParams(
            url=params.get("url", ""),
            action=params.get("action", "get"),
            selector=params.get("selector", ""),
            wait=WaitStrategy(strategy="load"),
        )
        return await DOMAction(dp).execute(backend)

    if action_type == "navigate":
        from browsix.actions.navigate import NavigateAction, NavigateParams

        np = NavigateParams(url=params.get("url", ""))
        return await NavigateAction(np).execute(backend)

    raise MultiConfigError(
        "action_type",
        f"Unknown action type: {action_type}",
    )
