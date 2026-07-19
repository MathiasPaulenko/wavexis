"""Plugin system for wavexis — custom actions, backends, and serve middleware.

Plugins are discovered via Python entry points (group="wavexis.plugins").
Three plugin types are supported alongside the classic Plugin hooks:

- **actions**: Custom actions for multi-action YAML and serve mode.
  Entry point value must be a ``wavexis.plugins.ActionPlugin`` instance.
- **backends**: Custom backend implementations.
  Entry point value must be a ``type[AbstractBackend]`` subclass.
- **middleware**: Serve mode middleware (aiohttp web middleware factories).
  Entry point value must be a callable that receives the aiohttp web module
  and returns a middleware object.
- **hooks**: Classic lifecycle hooks (before_action, after_action, register_cli).
  Entry point value must be a ``wavexis.plugins.Plugin`` subclass.

Example ``pyproject.toml`` for a plugin package::

    [project.entry-points."wavexis.plugins"]
    my-action = "my_plugin:action_plugin"
    my-backend = "my_plugin:MyBackend"
    my-middleware = "my_plugin:make_middleware"
    my-hooks = "my_plugin:MyPlugin"
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from typing import Any, Protocol, runtime_checkable

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend

__all__ = [
    "ActionFactory",
    "ActionPlugin",
    "MiddlewarePlugin",
    "Plugin",
    "PluginContext",
    "PluginRegistry",
    "get_registry",
    "load_plugins",
    "reset_registry",
]

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "wavexis.plugins"


@runtime_checkable
class ActionFactory(Protocol):
    """Protocol for action factory functions."""

    def __call__(self, params: dict[str, Any]) -> BaseAction[Any, Any]:
        """Create an action instance from params.

        Args:
            params: Action parameters dictionary.

        Returns:
            A BaseAction instance configured with the given params.
        """
        ...


@dataclass
class ActionPlugin:
    """Descriptor for a custom action plugin.

    Attributes:
        name: Action type name (e.g. "screenshot", "my-custom").
        factory: Callable that receives a params dict and returns a BaseAction.
        description: Human-readable description of the action.
    """

    name: str
    factory: ActionFactory
    description: str = ""


@dataclass
class MiddlewarePlugin:
    """Descriptor for a serve middleware plugin.

    Attributes:
        name: Middleware name.
        factory: Callable that receives the aiohttp web module and returns
            a middleware object suitable for ``web.Application(middlewares=[...])``.
        description: Human-readable description.
    """

    name: str
    factory: Callable[[Any], Any]
    description: str = ""


@dataclass
class PluginContext:
    """Context passed to plugin hooks.

    Attributes:
        backend_name: Name of the backend being used ("cdp" or "bidi").
        command: The CLI command being executed.
        params: Parameters for the command.
    """

    backend_name: str = ""
    command: str = ""
    params: dict[str, Any] = field(default_factory=dict)


class Plugin:
    """Base class for classic wavexis lifecycle plugins.

    Subclasses should override the hook methods they need.
    """

    name: str = "base"
    version: str = "0.0.0"

    def register_cli(self, app: Any) -> None:
        """Register additional CLI commands on the Typer app.

        Args:
            app: The Typer application instance.
        """

    def before_action(self, ctx: PluginContext) -> None:
        """Called before an action is executed.

        Args:
            ctx: The plugin context with command info.
        """

    def after_action(self, ctx: PluginContext, result: Any) -> None:
        """Called after an action is executed.

        Args:
            ctx: The plugin context with command info.
            result: The result of the action.
        """


@dataclass
class PluginRegistry:
    """Registry of discovered plugins.

    Holds custom actions, backends, middleware, and lifecycle hooks
    discovered via entry points or registered programmatically.
    """

    actions: dict[str, ActionPlugin] = field(default_factory=dict)
    backends: dict[str, type[AbstractBackend]] = field(default_factory=dict)
    middleware: list[MiddlewarePlugin] = field(default_factory=list)
    hooks: list[Plugin] = field(default_factory=list)

    def register_action(self, plugin: ActionPlugin) -> None:
        """Register a custom action plugin."""
        self.actions[plugin.name] = plugin
        logger.debug("Registered action plugin: %s", plugin.name)

    def register_backend(self, name: str, backend_cls: type[AbstractBackend]) -> None:
        """Register a custom backend."""
        self.backends[name] = backend_cls
        logger.debug("Registered backend plugin: %s", name)

    def register_middleware(self, plugin: MiddlewarePlugin) -> None:
        """Register a serve middleware plugin."""
        self.middleware.append(plugin)
        logger.debug("Registered middleware plugin: %s", plugin.name)

    def register_hooks(self, plugin: Plugin) -> None:
        """Register a classic lifecycle hooks plugin."""
        self.hooks.append(plugin)
        logger.debug("Registered hooks plugin: %s", plugin.name)

    def get_action(self, name: str) -> ActionPlugin | None:
        """Look up a custom action by name."""
        return self.actions.get(name)

    def list_actions(self) -> list[str]:
        """Return names of all registered custom actions."""
        return list(self.actions.keys())

    def list_backends(self) -> list[str]:
        """Return names of all registered custom backends."""
        return list(self.backends.keys())

    def list_middleware(self) -> list[str]:
        """Return names of all registered middleware."""
        return [m.name for m in self.middleware]


def _discover_entry_points() -> PluginRegistry:
    """Discover plugins via importlib.metadata entry points.

    Returns:
        PluginRegistry with all discovered plugins.
    """
    registry = PluginRegistry()

    try:
        eps = entry_points(group=ENTRY_POINT_GROUP)
    except (OSError, ValueError):
        return registry

    for ep in eps:
        try:
            obj = ep.load()
        except (ImportError, AttributeError, ValueError, TypeError) as exc:
            logger.warning("Failed to load plugin %s: %s", ep.name, exc)
            continue

        if isinstance(obj, ActionPlugin):
            registry.register_action(obj)
        elif isinstance(obj, MiddlewarePlugin):
            registry.register_middleware(obj)
        elif isinstance(obj, type) and issubclass(obj, Plugin):
            registry.register_hooks(obj())
        elif isinstance(obj, type) and issubclass(obj, AbstractBackend):
            registry.register_backend(ep.name, obj)
        else:
            logger.warning("Plugin %s has unknown type %s, skipping", ep.name, type(obj))

    return registry


_registry: PluginRegistry | None = None


def get_registry() -> PluginRegistry:
    """Get the global plugin registry, discovering entry points on first call.

    Returns:
        The global PluginRegistry instance.
    """
    global _registry
    if _registry is None:
        _registry = _discover_entry_points()
    return _registry


def reset_registry() -> None:
    """Reset the global registry (useful for tests)."""
    global _registry
    _registry = None


def load_plugins() -> list[Plugin]:
    """Discover and load classic lifecycle plugins via entry points.

    Backward-compatible with the original load_plugins API.

    Returns:
        List of loaded Plugin instances. Empty if no plugins installed.
    """
    return get_registry().hooks
