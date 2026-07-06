"""Multi-action YAML parser and executor."""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Any

import yaml

from wavexis.exceptions import MultiConfigError


def _substitute_variables(value: Any, variables: dict[str, str]) -> Any:
    """Recursively substitute {{var}} and {{env.X}} in strings.

    Args:
        value: The value to substitute in (str, dict, list, etc.).
        variables: User-defined variables from the config's 'vars' section.

    Returns:
        The value with all substitutions applied.
    """
    if isinstance(value, str):
        def replacer(match: re.Match[str]) -> str:
            expr = match.group(1).strip()
            if expr.startswith("env."):
                env_key = expr[4:]
                return os.environ.get(env_key, match.group(0))
            if expr in variables:
                return variables[expr]
            return match.group(0)

        return re.sub(r"\{\{(.+?)\}\}", replacer, value)
    if isinstance(value, dict):
        return {k: _substitute_variables(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute_variables(item, variables) for item in value]
    return value


def parse_yaml(path: Path) -> list[dict[str, Any]]:
    """Parse a YAML config file and validate its structure.

    Supports a top-level 'vars' key for variable definitions. Variables
    are substituted in all action parameters using {{var}} syntax.
    Environment variables are accessible via {{env.KEY}}.

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
    variables = raw.get("vars", {})
    if variables and not isinstance(variables, dict):
        raise MultiConfigError("vars", "vars must be a mapping of key-value pairs")
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
        action_params = _substitute_variables(action_params, variables)
        parsed.append({action_type: action_params})
    return parsed


async def execute_actions(
    actions: list[dict[str, Any]],
    backend: Any,
    parallel: bool = False,
) -> list[Any]:
    """Execute each action, reusing the same backend.

    Args:
        actions: List of action dicts from parse_yaml.
        backend: An launched AbstractBackend instance.
        parallel: If True, execute all actions concurrently.

    Returns:
        List of results from each action, in the same order as actions.
    """
    if parallel:
        tasks = [
            _dispatch(next(iter(ad)), ad[next(iter(ad))], backend)
            for ad in actions
        ]
        return await asyncio.gather(*tasks)

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
        from wavexis.actions.screenshot import ScreenshotAction
        from wavexis.config import ScreenshotParams, WaitStrategy

        sp = ScreenshotParams(
            url=params.get("url", ""),
            full_page=params.get("full_page", True),
            format=params.get("format", "png"),
            wait=WaitStrategy(strategy="load"),
        )
        return await ScreenshotAction(sp).execute(backend)

    if action_type == "pdf":
        from wavexis.actions.pdf import PDFAction
        from wavexis.config import PDFParams, WaitStrategy

        pp = PDFParams(
            url=params.get("url", ""),
            paper=params.get("paper", "letter"),
            wait=WaitStrategy(strategy="load"),
        )
        return await PDFAction(pp).execute(backend)

    if action_type == "scrape":
        from wavexis.actions.scrape import ScrapeAction
        from wavexis.config import ScrapeParams, WaitStrategy

        urls = params.get("urls") or [params.get("url", "")]
        scp = ScrapeParams(
            urls=urls,
            expression=params.get("expression", "document.title"),
            wait=WaitStrategy(strategy="load"),
        )
        return await ScrapeAction(scp).execute(backend)

    if action_type == "eval":
        from wavexis.actions.eval import EvalAction
        from wavexis.config import EvalParams, WaitStrategy

        ep = EvalParams(
            url=params.get("url", ""),
            expression=params.get("expression", ""),
            wait=WaitStrategy(strategy="load"),
        )
        return await EvalAction(ep).execute(backend)

    if action_type == "dom":
        from wavexis.actions.dom import DOMAction
        from wavexis.config import DOMParams, WaitStrategy

        dp = DOMParams(
            url=params.get("url", ""),
            action=params.get("action", "get"),
            selector=params.get("selector", ""),
            wait=WaitStrategy(strategy="load"),
        )
        return await DOMAction(dp).execute(backend)

    if action_type == "navigate":
        from wavexis.actions.navigate import NavigateAction, NavigateParams

        np = NavigateParams(url=params.get("url", ""))
        return await NavigateAction(np).execute(backend)

    if action_type == "click":
        from wavexis.actions.input import InputAction
        from wavexis.config import InputParams, WaitStrategy

        ip = InputParams(
            url=params.get("url", ""),
            action="click",
            selector=params.get("selector", ""),
            wait=WaitStrategy(strategy="load"),
        )
        return await InputAction(ip).execute(backend)

    if action_type == "type":
        from wavexis.actions.input import InputAction
        from wavexis.config import InputParams, WaitStrategy

        ip = InputParams(
            url=params.get("url", ""),
            action="type",
            selector=params.get("selector", ""),
            text=params.get("text", ""),
            wait=WaitStrategy(strategy="load"),
        )
        return await InputAction(ip).execute(backend)

    if action_type == "cookies":
        from wavexis.actions.cookies import CookieAction
        from wavexis.config import CookieActionParams, CookieParams, WaitStrategy

        cookie_data = params.get("cookie")
        if cookie_data and isinstance(cookie_data, dict):
            cookie_obj = CookieParams(
                name=cookie_data.get("name", ""),
                value=cookie_data.get("value", ""),
                domain=cookie_data.get("domain", ""),
                path=cookie_data.get("path", "/"),
            )
        else:
            cookie_obj = CookieParams()
        cp = CookieActionParams(
            url=params.get("url", ""),
            action=params.get("action", "get"),
            cookie=cookie_obj,
            name=params.get("name", ""),
            domain=params.get("domain", ""),
            wait=WaitStrategy(strategy="load"),
        )
        return await CookieAction(cp).execute(backend)

    if action_type == "headers":
        from wavexis.actions.headers import HeaderAction
        from wavexis.config import HeaderParams, WaitStrategy

        hp = HeaderParams(
            url=params.get("url", ""),
            action=params.get("action", "set-headers"),
            headers=params.get("headers", {}),
            user_agent=params.get("user_agent", ""),
            wait=WaitStrategy(strategy="load"),
        )
        return await HeaderAction(hp).execute(backend)

    if action_type == "wait":
        from wavexis.actions.wait import WaitAction
        from wavexis.config import WaitStrategy

        ws = WaitStrategy(
            strategy=params.get("strategy", "load"),
            selector=params.get("selector"),
            url_pattern=params.get("url_pattern"),
            timeout=params.get("timeout", 30000),
        )
        return await WaitAction(ws).execute(backend)

    if action_type == "emulation":
        from wavexis.actions.emulation import EmulationAction
        from wavexis.config import EmulationParams, WaitStrategy

        emp = EmulationParams(
            action=params.get("action", "device"),
            device=params.get("device"),
            width=params.get("width", 0),
            height=params.get("height", 0),
            device_scale_factor=params.get("device_scale_factor", 1.0),
            latitude=params.get("latitude", 0.0),
            longitude=params.get("longitude", 0.0),
            accuracy=params.get("accuracy", 100.0),
            timezone=params.get("timezone", ""),
            dark_mode=params.get("dark_mode", False),
            url=params.get("url", ""),
            wait=WaitStrategy(strategy="load"),
        )
        return await EmulationAction(emp).execute(backend)

    from wavexis.plugins import get_registry

    plugin = get_registry().get_action(action_type)
    if plugin is not None:
        action = plugin.factory(params)
        return await action.execute(backend)

    raise MultiConfigError(
        "action_type",
        f"Unknown action type: {action_type}",
    )
