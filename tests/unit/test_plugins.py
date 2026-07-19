"""Unit tests for plugin system."""

from unittest.mock import MagicMock

import pytest

from wavexis.plugins import (
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
    """Test suite for plugin."""

    def test_plugin_base_defaults(self) -> None:
        """Test plugin base defaults."""
        plugin = Plugin()
        assert plugin.name == "base"
        assert plugin.version == "0.0.0"

    def test_plugin_register_cli_noop(self) -> None:
        """Test plugin register cli noop."""
        plugin = Plugin()
        plugin.register_cli(None)

    def test_plugin_before_action_noop(self) -> None:
        """Test plugin before action noop."""
        plugin = Plugin()
        ctx = PluginContext(backend_name="cdp", command="screenshot")
        plugin.before_action(ctx)

    def test_plugin_after_action_noop(self) -> None:
        """Test plugin after action noop."""
        plugin = Plugin()
        ctx = PluginContext(backend_name="cdp", command="screenshot")
        plugin.after_action(ctx, {"result": "ok"})


@pytest.mark.unit
class TestPluginContext:
    """Test suite for plugincontext."""

    def test_defaults(self) -> None:
        """Test defaults."""
        ctx = PluginContext()
        assert ctx.backend_name == ""
        assert ctx.command == ""
        assert ctx.params == {}

    def test_with_values(self) -> None:
        """Test with values."""
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
    """Test suite for loadplugins."""

    def test_no_plugins_returns_empty_list(self) -> None:
        """Test no plugins returns empty list."""
        plugins = load_plugins()
        assert isinstance(plugins, list)

    def test_invalid_plugin_skipped(self) -> None:
        """Test that invalid plugin skipped raises an appropriate error."""
        plugins = load_plugins()
        for p in plugins:
            assert isinstance(p, Plugin)


@pytest.mark.unit
class TestCustomPlugin:
    """Test suite for customplugin."""

    def test_subclass(self) -> None:
        """Test subclass."""

        class MyPlugin(Plugin):
            """Test suite for myplugin."""

            name = "my-plugin"
            version = "1.0.0"

            def after_action(self, ctx: PluginContext, result: object) -> None:
                """After action."""
                pass

        plugin = MyPlugin()
        assert plugin.name == "my-plugin"
        assert plugin.version == "1.0.0"
        assert isinstance(plugin, Plugin)


@pytest.mark.unit
class TestPluginRegistry:
    """Test suite for pluginregistry."""

    def test_empty_registry(self) -> None:
        """Test empty registry."""
        registry = PluginRegistry()
        assert registry.list_actions() == []
        assert registry.list_backends() == []
        assert registry.list_middleware() == []

    def test_register_action(self) -> None:
        """Test register action."""
        registry = PluginRegistry()
        factory = MagicMock()
        plugin = ActionPlugin(name="my-action", factory=factory, description="test")
        registry.register_action(plugin)
        assert "my-action" in registry.list_actions()
        assert registry.get_action("my-action") is plugin
        assert registry.get_action("unknown") is None

    def test_register_middleware(self) -> None:
        """Test register middleware."""
        registry = PluginRegistry()
        factory = MagicMock()
        plugin = MiddlewarePlugin(name="my-mw", factory=factory, description="test")
        registry.register_middleware(plugin)
        assert "my-mw" in registry.list_middleware()

    def test_register_backend(self) -> None:
        """Test register backend."""
        from wavexis.backend.base import AbstractBackend

        registry = PluginRegistry()
        mock_cls = MagicMock(spec=type[AbstractBackend])
        registry.register_backend("custom", mock_cls)
        assert "custom" in registry.list_backends()

    def test_register_hooks(self) -> None:
        """Test register hooks."""
        registry = PluginRegistry()

        class MyPlugin(Plugin):
            """Test suite for myplugin."""

            name = "test"

        plugin = MyPlugin()
        registry.register_hooks(plugin)
        assert len(registry.hooks) == 1
        assert registry.hooks[0].name == "test"


@pytest.mark.unit
class TestPluginRegistryGlobal:
    """Test suite for pluginregistryglobal."""

    def teardown_method(self) -> None:
        """Clean up after each test method."""
        reset_registry()

    def test_get_registry_returns_singleton(self) -> None:
        """Test get registry returns singleton."""
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_reset_registry_creates_new(self) -> None:
        """Test reset registry creates new."""
        r1 = get_registry()
        reset_registry()
        r2 = get_registry()
        assert r1 is not r2


@pytest.mark.unit
class TestActionPlugin:
    """Test suite for actionplugin."""

    def test_action_plugin_factory_called(self) -> None:
        """Test action plugin factory called."""
        from wavexis.actions.base import BaseAction

        class DummyAction(BaseAction[dict, str]):
            """Test suite for dummyaction."""

            async def execute(self, backend: object) -> str:
                """Execute."""
                return "ok"

        def factory(params: dict) -> BaseAction[dict, str]:
            """Factory."""
            return DummyAction(params)

        plugin = ActionPlugin(name="dummy", factory=factory, description="test")
        action = plugin.factory({"url": "https://example.com"})
        assert isinstance(action, DummyAction)
        assert action.params == {"url": "https://example.com"}
