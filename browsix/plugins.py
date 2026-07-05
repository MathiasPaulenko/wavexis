"""Plugin system for browsix.

Plugins are discovered via Python entry points (group="browsix.plugins").
Each plugin can register CLI commands and hook into action lifecycle.

Example plugin::

    # setup.py or pyproject.toml entry point:
    [project.entry-points."browsix.plugins"]
    my-plugin = "my_plugin:MyPlugin"

    # my_plugin.py
    from browsix.plugins import Plugin, PluginContext

    class MyPlugin(Plugin):
        name = "my-plugin"
        version = "1.0.0"

        def after_action(self, ctx: PluginContext, result: Any) -> None:
            print(f"Action {ctx.command} completed")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib.metadata import entry_points
from typing import Any


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
    """Base class for browsix plugins.

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


def load_plugins() -> list[Plugin]:
    """Discover and load plugins via entry points.

    Plugins are discovered via the "browsix.plugins" entry point group.
    Invalid plugins (not Plugin subclasses) are silently skipped.

    Returns:
        List of loaded Plugin instances. Empty if no plugins installed.
    """
    plugins: list[Plugin] = []
    try:
        eps = entry_points(group="browsix.plugins")
    except Exception:
        return plugins

    for ep in eps:
        try:
            plugin_cls = ep.load()
            if not isinstance(plugin_cls, type) or not issubclass(plugin_cls, Plugin):
                continue
            plugins.append(plugin_cls())
        except Exception:
            continue

    return plugins
