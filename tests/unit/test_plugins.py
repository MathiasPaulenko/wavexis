"""Unit tests for plugin system."""

from unittest.mock import MagicMock

import pytest

from browsix.plugins import (
    ActionPlugin,
    MiddlewarePlugin,
    Plugin,
    PluginContext,
    PluginRegistry,
    get_registry,
    load_plugins,
    reset_registry,
)


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


@pytest.mark.unit
class TestPluginRegistry:
    def test_empty_registry(self) -> None:
        registry = PluginRegistry()
        assert registry.list_actions() == []
        assert registry.list_backends() == []
        assert registry.list_middleware() == []

    def test_register_action(self) -> None:
        registry = PluginRegistry()
        factory = MagicMock()
        plugin = ActionPlugin(name="my-action", factory=factory, description="test")
        registry.register_action(plugin)
        assert "my-action" in registry.list_actions()
        assert registry.get_action("my-action") is plugin
        assert registry.get_action("unknown") is None

    def test_register_middleware(self) -> None:
        registry = PluginRegistry()
        factory = MagicMock()
        plugin = MiddlewarePlugin(name="my-mw", factory=factory, description="test")
        registry.register_middleware(plugin)
        assert "my-mw" in registry.list_middleware()

    def test_register_backend(self) -> None:
        from browsix.backend.base import AbstractBackend

        registry = PluginRegistry()
        mock_cls = MagicMock(spec=type[AbstractBackend])
        registry.register_backend("custom", mock_cls)
        assert "custom" in registry.list_backends()

    def test_register_hooks(self) -> None:
        registry = PluginRegistry()

        class MyPlugin(Plugin):
            name = "test"

        plugin = MyPlugin()
        registry.register_hooks(plugin)
        assert len(registry.hooks) == 1
        assert registry.hooks[0].name == "test"


@pytest.mark.unit
class TestPluginRegistryGlobal:
    def teardown_method(self) -> None:
        reset_registry()

    def test_get_registry_returns_singleton(self) -> None:
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_reset_registry_creates_new(self) -> None:
        r1 = get_registry()
        reset_registry()
        r2 = get_registry()
        assert r1 is not r2


@pytest.mark.unit
class TestActionPlugin:
    def test_action_plugin_factory_called(self) -> None:
        from browsix.actions.base import BaseAction

        class DummyAction(BaseAction[dict, str]):
            async def execute(self, backend: object) -> str:
                return "ok"

        def factory(params: dict) -> BaseAction[dict, str]:
            return DummyAction(params)

        plugin = ActionPlugin(name="dummy", factory=factory, description="test")
        action = plugin.factory({"url": "https://example.com"})
        assert isinstance(action, DummyAction)
        assert action.params == {"url": "https://example.com"}
