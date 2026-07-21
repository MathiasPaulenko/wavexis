"""Multi-action YAML parser and executor."""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeAlias

import yaml

from wavexis.actions.base import BaseAction
from wavexis.actions.cache import ActionCache
from wavexis.exceptions import MultiConfigError, WavexisError
from wavexis.output import validate_path

__all__ = ["parse_yaml", "execute_actions"]


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
                return str(variables[expr])
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
    valid_path = validate_path(path)
    if not valid_path.exists():
        raise MultiConfigError("file", f"Config file not found: {path}")
    try:
        raw = yaml.safe_load(valid_path.read_text(encoding="utf-8"))
    except OSError as e:
        raise MultiConfigError("file", f"Config file not found or unreadable: {e}") from e
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
    cache: ActionCache | None = None,
) -> list[Any]:
    """Execute each action, reusing the same backend.

    Args:
        actions: List of action dicts from parse_yaml.
        backend: An launched AbstractBackend instance.
        parallel: If True, execute all actions concurrently using separate tabs.
        cache: Optional ActionCache. If provided, cacheable actions
            (screenshot, dom, scrape, eval, cookies, headers) will
            be served from cache on repeated calls with same URL+params.

    Returns:
        List of results from each action, in the same order as actions.
    """
    if parallel:

        async def _run_in_tab(action_dict: dict[str, Any]) -> Any:
            action_type = next(iter(action_dict))
            params = action_dict[action_type]
            url = params.get("url", "about:blank")
            tab = await backend.new_tab_handle(url)
            try:
                return await _dispatch(action_type, params, tab, cache=cache)
            finally:
                await tab.close()

        tasks = [_run_in_tab(ad) for ad in actions]
        gathered = await asyncio.gather(*tasks, return_exceptions=True)

        failures: list[str] = []
        for i, result in enumerate(gathered):
            if isinstance(result, BaseException) and not isinstance(result, Exception):
                raise result
            if isinstance(result, Exception):
                action_type = next(iter(actions[i]))
                failures.append(f"actions[{i}] ({action_type}): {result}")

        if failures:
            raise WavexisError("One or more actions failed:\n" + "\n".join(failures))

        return gathered

    results: list[Any] = []
    for action_dict in actions:
        action_type = next(iter(action_dict))
        params = action_dict[action_type]
        result = await _dispatch(action_type, params, backend, cache=cache)
        results.append(result)
    return results


_CACHEABLE_ACTIONS = frozenset(
    {
        "screenshot",
        "dom",
        "scrape",
        "eval",
        "cookies",
        "headers",
    }
)


async def _dispatch(
    action_type: str,
    params: dict[str, Any],
    backend: Any,
    cache: ActionCache | None = None,
) -> Any:
    """Dispatch a single action to the appropriate action class.

    Args:
        action_type: Action type name (e.g. 'screenshot', 'pdf', 'scrape').
        params: Action parameters dict.
        backend: An launched AbstractBackend instance.
        cache: Optional ActionCache for cacheable actions.

    Returns:
        The result of the action.
    """
    if cache is not None and action_type in _CACHEABLE_ACTIONS:
        url = params.get("url", "")
        if url:
            cached = cache.get(url, action_type, params)
            if cached is not None:
                return cached

    result = await _execute_action(action_type, params, backend)

    if cache is not None and action_type in _CACHEABLE_ACTIONS:
        url = params.get("url", "")
        if url:
            cache.set(url, action_type, params, result)

    return result


ActionFactory: TypeAlias = Callable[[dict[str, Any]], BaseAction[Any, Any]]


def _screenshot_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.screenshot import ScreenshotAction
    from wavexis.config import ScreenshotParams, WaitStrategy

    return ScreenshotAction(
        ScreenshotParams(
            url=params.get("url", ""),
            full_page=params.get("full_page", True),
            format=params.get("format", "png"),
            wait=WaitStrategy(strategy="load"),
        )
    )


def _pdf_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.pdf import PDFAction
    from wavexis.config import PDFParams, WaitStrategy

    return PDFAction(
        PDFParams(
            url=params.get("url", ""),
            paper=params.get("paper", "letter"),
            wait=WaitStrategy(strategy="load"),
        )
    )


def _scrape_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.scrape import ScrapeAction
    from wavexis.config import ScrapeParams, WaitStrategy

    urls = params.get("urls") or [params.get("url", "")]
    return ScrapeAction(
        ScrapeParams(
            urls=urls,
            expression=params.get("expression", "document.title"),
            wait=WaitStrategy(strategy="load"),
        )
    )


def _eval_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.eval import EvalAction
    from wavexis.config import EvalParams, WaitStrategy

    return EvalAction(
        EvalParams(
            url=params.get("url", ""),
            expression=params.get("expression", ""),
            wait=WaitStrategy(strategy="load"),
        )
    )


def _dom_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.dom import DOMAction
    from wavexis.config import DOMParams, WaitStrategy

    return DOMAction(
        DOMParams(
            url=params.get("url", ""),
            action=params.get("action", "get"),
            selector=params.get("selector", ""),
            wait=WaitStrategy(strategy="load"),
        )
    )


def _navigate_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.navigate import NavigateAction, NavigateParams

    return NavigateAction(NavigateParams(url=params.get("url", "")))


def _click_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.input import InputAction
    from wavexis.config import InputParams, WaitStrategy

    return InputAction(
        InputParams(
            url=params.get("url", ""),
            action="click",
            selector=params.get("selector", ""),
            wait=WaitStrategy(strategy="load"),
        )
    )


def _type_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.input import InputAction
    from wavexis.config import InputParams, WaitStrategy

    return InputAction(
        InputParams(
            url=params.get("url", ""),
            action="type",
            selector=params.get("selector", ""),
            text=params.get("text", ""),
            wait=WaitStrategy(strategy="load"),
        )
    )


def _fill_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.input import InputAction
    from wavexis.config import InputParams, WaitStrategy

    return InputAction(
        InputParams(
            url=params.get("url", ""),
            action="fill",
            selector=params.get("selector", ""),
            value=params.get("value", ""),
            wait=WaitStrategy(strategy="load"),
        )
    )


def _select_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.input import InputAction
    from wavexis.config import InputParams, WaitStrategy

    return InputAction(
        InputParams(
            url=params.get("url", ""),
            action="select",
            selector=params.get("selector", ""),
            value=params.get("value", ""),
            wait=WaitStrategy(strategy="load"),
        )
    )


def _hover_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.input import InputAction
    from wavexis.config import InputParams, WaitStrategy

    return InputAction(
        InputParams(
            url=params.get("url", ""),
            action="hover",
            selector=params.get("selector", ""),
            wait=WaitStrategy(strategy="load"),
        )
    )


def _keypress_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.input import InputAction
    from wavexis.config import InputParams, WaitStrategy

    return InputAction(
        InputParams(
            url=params.get("url", ""),
            action="key",
            key=params.get("key", "Enter"),
            wait=WaitStrategy(strategy="load"),
        )
    )


def _right_click_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.input import InputAction
    from wavexis.config import InputParams, WaitStrategy

    return InputAction(
        InputParams(
            url=params.get("url", ""),
            action="right_click",
            selector=params.get("selector", ""),
            wait=WaitStrategy(strategy="load"),
        )
    )


def _double_click_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.input import InputAction
    from wavexis.config import InputParams, WaitStrategy

    return InputAction(
        InputParams(
            url=params.get("url", ""),
            action="double_click",
            selector=params.get("selector", ""),
            wait=WaitStrategy(strategy="load"),
        )
    )


def _drag_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.input import InputAction
    from wavexis.config import InputParams, WaitStrategy

    return InputAction(
        InputParams(
            url=params.get("url", ""),
            action="drag",
            source=params.get("source", ""),
            target=params.get("target", ""),
            wait=WaitStrategy(strategy="load"),
        )
    )


def _tap_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.input import InputAction
    from wavexis.config import InputParams, WaitStrategy

    return InputAction(
        InputParams(
            url=params.get("url", ""),
            action="tap",
            selector=params.get("selector", ""),
            wait=WaitStrategy(strategy="load"),
        )
    )


def _scroll_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.input import InputAction
    from wavexis.config import InputParams, WaitStrategy

    return InputAction(
        InputParams(
            url=params.get("url", ""),
            action="scroll",
            selector=params.get("selector", ""),
            scroll_x=int(params.get("x", 0)),
            scroll_y=int(params.get("y", 0)),
            wait=WaitStrategy(strategy="load"),
        )
    )


def _upload_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.input import InputAction
    from wavexis.config import InputParams, WaitStrategy

    files = params.get("files", [])
    if isinstance(files, str):
        files = [files]
    return InputAction(
        InputParams(
            url=params.get("url", ""),
            action="upload",
            selector=params.get("selector", ""),
            files=files,
            wait=WaitStrategy(strategy="load"),
        )
    )


def _cookies_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
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
    return CookieAction(
        CookieActionParams(
            url=params.get("url", ""),
            action=params.get("action", "get"),
            cookie=cookie_obj,
            name=params.get("name", ""),
            domain=params.get("domain", ""),
            wait=WaitStrategy(strategy="load"),
        )
    )


def _headers_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.headers import HeaderAction
    from wavexis.config import HeaderParams, WaitStrategy

    return HeaderAction(
        HeaderParams(
            url=params.get("url", ""),
            action=params.get("action", "set-headers"),
            headers=params.get("headers", {}),
            user_agent=params.get("user_agent", ""),
            wait=WaitStrategy(strategy="load"),
        )
    )


def _wait_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.wait import WaitAction
    from wavexis.config import WaitStrategy

    return WaitAction(
        WaitStrategy(
            strategy=params.get("strategy", "load"),
            selector=params.get("selector"),
            url_pattern=params.get("url_pattern"),
            timeout=params.get("timeout", 30000),
        )
    )


def _har_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.har import HARAction
    from wavexis.config import HarParams, WaitStrategy

    return HARAction(
        HarParams(
            url=params.get("url", ""),
            wait=WaitStrategy(
                strategy=params.get("wait", {}).get("strategy", "load")
                if isinstance(params.get("wait"), dict)
                else "load",
                timeout=params.get("wait", {}).get("timeout", 30000)
                if isinstance(params.get("wait"), dict)
                else 30000,
            ),
            filter=params.get("filter"),
            timeout=params.get("timeout", 5000),
        )
    )


def _emulation_factory(params: dict[str, Any]) -> BaseAction[Any, Any]:
    from wavexis.actions.emulation import EmulationAction
    from wavexis.config import EmulationParams, WaitStrategy

    return EmulationAction(
        EmulationParams(
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
    )


_ACTION_REGISTRY: dict[str, ActionFactory] = {
    "screenshot": _screenshot_factory,
    "pdf": _pdf_factory,
    "scrape": _scrape_factory,
    "eval": _eval_factory,
    "dom": _dom_factory,
    "navigate": _navigate_factory,
    "click": _click_factory,
    "type": _type_factory,
    "fill": _fill_factory,
    "select": _select_factory,
    "hover": _hover_factory,
    "keypress": _keypress_factory,
    "right_click": _right_click_factory,
    "double_click": _double_click_factory,
    "drag": _drag_factory,
    "tap": _tap_factory,
    "scroll": _scroll_factory,
    "upload": _upload_factory,
    "cookies": _cookies_factory,
    "headers": _headers_factory,
    "wait": _wait_factory,
    "har": _har_factory,
    "emulation": _emulation_factory,
}


async def _execute_action(
    action_type: str,
    params: dict[str, Any],
    backend: Any,
) -> Any:
    """Execute a single action without caching.

    Args:
        action_type: Action type name.
        params: Action parameters dict.
        backend: An launched AbstractBackend instance.

    Returns:
        The result of the action.
    """
    factory = _ACTION_REGISTRY.get(action_type)
    if factory is not None:
        action = factory(params)
        return await action.execute(backend)

    from wavexis.plugins import get_registry

    plugin = get_registry().get_action(action_type)
    if plugin is not None:
        action = plugin.factory(params)
        return await action.execute(backend)

    raise MultiConfigError(
        "action_type",
        f"Unknown action type: {action_type}",
    )
