"""Record and replay system for wavexis actions.

The Recorder wraps a backend and records all method calls to a list.
Recorded actions can be saved to YAML and replayed later.

The YAML format is compatible with `wavexis multi` YAML format:

```yaml
actions:
  - screenshot:
      url: https://example.com
      output: out.png
  - click:
      selector: "#button"
```
"""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import yaml

from wavexis.backend.base import AbstractBackend
from wavexis.exceptions import WavexisError
from wavexis.multi import execute_actions, parse_yaml
from wavexis.output import validate_path

__all__ = ["Recorder", "record_to_yaml", "replay_from_yaml"]


def _serialize_param(value: Any) -> Any:
    """Convert a recorded argument into a YAML-replayable value."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, (list, tuple)):
        return [_serialize_param(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize_param(v) for k, v in value.items()}
    return str(value)


class Recorder:
    """Wraps a backend and records method calls as action dicts.

    Attributes:
        _backend: The wrapped AbstractBackend instance.
        _actions: List of recorded action dicts.
    """

    def __init__(self, backend: AbstractBackend) -> None:
        """Initialize the Recorder with a backend.

        Args:
            backend: The AbstractBackend to wrap and record.
        """
        self._backend = backend
        self._actions: list[dict[str, Any]] = []

    @property
    def actions(self) -> list[dict[str, Any]]:
        """Return the list of recorded actions."""
        return self._actions

    def record(self, action_type: str, params: dict[str, Any]) -> None:
        """Record an action manually.

        Args:
            action_type: The action type name (e.g. "screenshot", "click").
            params: Action parameters dict.
        """
        self._actions.append({action_type: params})

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the wrapped backend.

        For async methods, record the call before delegating.
        Skips recording for lifecycle methods (launch, close) and internal methods.
        """
        # Skip recording for lifecycle and internal methods
        if name in ("launch", "close", "_get_origin", "_get_session", "_send"):
            attr = getattr(self._backend, name)
            return attr

        attr = getattr(self._backend, name)
        if callable(attr):

            def wrapper(*args: Any, **kwargs: Any) -> Any:
                """Record the method call and delegate to the wrapped backend.

                Args:
                    *args: Positional arguments passed to the original method.
                    **kwargs: Keyword arguments passed to the original method.

                Returns:
                    The return value of the original backend method.
                """
                # Bind positional args to parameter names so the recorded
                # YAML is replayable through the multi-action factories.
                # VAR_KEYWORD (**kwargs) is flattened into the params dict.
                try:
                    sig = inspect.signature(attr)
                    bound = sig.bind(*args, **kwargs)
                    params = {}
                    for pname, param in sig.parameters.items():
                        if param.kind is inspect.Parameter.VAR_POSITIONAL:
                            extra = list(bound.arguments.get(pname, ()))
                            if extra:
                                params["_args"] = [_serialize_param(a) for a in extra]
                        elif param.kind is inspect.Parameter.VAR_KEYWORD:
                            for key, value in bound.arguments.get(pname, {}).items():
                                params[key] = _serialize_param(value)
                        elif pname in bound.arguments:
                            params[pname] = _serialize_param(bound.arguments[pname])
                except (TypeError, ValueError):
                    params = dict(kwargs)
                    if args:
                        params["_args"] = [repr(a) for a in args]
                self._actions.append({name: params})
                return attr(*args, **kwargs)

            return wrapper
        return attr


def record_to_yaml(actions: list[dict[str, Any]], path: Path) -> None:
    """Save recorded actions to a YAML file.

    The format is compatible with `wavexis multi` YAML format.

    Args:
        actions: List of action dicts, each with a single key.
        path: Path to the output YAML file.
    """
    data = {"actions": actions}
    try:
        validate_path(path).write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    except OSError as e:
        raise WavexisError(f"Failed to write recorded config: {e}") from e


async def replay_from_yaml(path: Path, backend: AbstractBackend) -> list[Any]:
    """Load a YAML file and replay actions on the given backend.

    Uses the same parser as `wavexis multi` for format compatibility.

    Args:
        path: Path to the YAML file.
        backend: An already-launched AbstractBackend instance.

    Returns:
        List of results from each action.
    """
    actions = await asyncio.to_thread(parse_yaml, validate_path(path))
    return await execute_actions(actions, backend)
