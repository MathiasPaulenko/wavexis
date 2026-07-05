"""Record and replay system for browsix actions.

The Recorder wraps a backend and records all method calls to a list.
Recorded actions can be saved to YAML and replayed later.

The YAML format is compatible with `browsix multi` YAML format:

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

from pathlib import Path
from typing import Any

import yaml

from browsix.backend.base import AbstractBackend
from browsix.multi import execute_actions, parse_yaml


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
        """
        attr = getattr(self._backend, name)
        if callable(attr):
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                params: dict[str, Any] = {}
                if args:
                    params["_args"] = list(args)
                params.update(kwargs)
                self._actions.append({name: params})
                return attr(*args, **kwargs)

            return wrapper
        return attr


def record_to_yaml(actions: list[dict[str, Any]], path: Path) -> None:
    """Save recorded actions to a YAML file.

    The format is compatible with `browsix multi` YAML format.

    Args:
        actions: List of action dicts, each with a single key.
        path: Path to the output YAML file.
    """
    data = {"actions": actions}
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


async def replay_from_yaml(path: Path, backend: AbstractBackend) -> list[Any]:
    """Load a YAML file and replay actions on the given backend.

    Uses the same parser as `browsix multi` for format compatibility.

    Args:
        path: Path to the YAML file.
        backend: An already-launched AbstractBackend instance.

    Returns:
        List of results from each action.
    """
    actions = parse_yaml(path)
    return await execute_actions(actions, backend)
