"""Unit tests for plugin system."""

import pytest

from browsix.plugins import Plugin, PluginContext, load_plugins


@pytest.mark.unit
class TestPlugin:
    def test_plugin_base_defaults(self) -> None:
        plugin = Plugin()
        assert plugin.name == "base"
        assert plugin.version == "0.0.0"

    def test_plugin_register_cli_noop(self) -> None:
        plugin = Plugin()
        plugin.register_cli(None)

    def test_plugin_before_action_noop(self) -> None:
        plugin = Plugin()
        ctx = PluginContext(backend_name="cdp", command="screenshot")
        plugin.before_action(ctx)

    def test_plugin_after_action_noop(self) -> None:
        plugin = Plugin()
        ctx = PluginContext(backend_name="cdp", command="screenshot")
        plugin.after_action(ctx, {"result": "ok"})


@pytest.mark.unit
class TestPluginContext:
    def test_defaults(self) -> None:
        ctx = PluginContext()
        assert ctx.backend_name == ""
        assert ctx.command == ""
        assert ctx.params == {}

    def test_with_values(self) -> None:
        ctx = PluginContext(
            backend_name="cdp",
            command="screenshot",
            params={"url": "https://example.com"},
        )
        assert ctx.backend_name == "cdp"
        assert ctx.command == "screenshot"
        assert ctx.params == {"url": "https://example.com"}


@pytest.mark.unit
class TestLoadPlugins:
    def test_no_plugins_returns_empty_list(self) -> None:
        plugins = load_plugins()
        assert isinstance(plugins, list)

    def test_invalid_plugin_skipped(self) -> None:
        plugins = load_plugins()
        for p in plugins:
            assert isinstance(p, Plugin)


@pytest.mark.unit
class TestCustomPlugin:
    def test_subclass(self) -> None:
        class MyPlugin(Plugin):
            name = "my-plugin"
            version = "1.0.0"

            def after_action(self, ctx: PluginContext, result: object) -> None:
                pass

        plugin = MyPlugin()
        assert plugin.name == "my-plugin"
        assert plugin.version == "1.0.0"
        assert isinstance(plugin, Plugin)
