# Plugin System

wavexis supports plugins via Python entry points (`importlib.metadata`).
Plugins can extend wavexis with custom actions, backends, and serve middleware.

## Plugin types

| Type | Entry point value | Description |
|------|-------------------|-------------|
| **actions** | `ActionPlugin` instance | Custom actions for multi-action YAML and serve mode |
| **backends** | `AbstractBackend` subclass | Custom browser backend implementations |
| **middleware** | `MiddlewarePlugin` instance | Serve mode HTTP middleware (aiohttp) |
| **hooks** | `Plugin` subclass | Classic lifecycle hooks (before/after action, CLI registration) |

## Creating a plugin

### Custom action

```python
# my_plugin.py
from wavexis.plugins import ActionPlugin
from wavexis.actions.base import BaseAction


class ScreenshotAction(BaseAction[dict, bytes]):
    async def execute(self, backend):
        from wavexis.config import ScreenshotParams
        params = ScreenshotParams(url=self.params.get("url", ""))
        return await backend.screenshot(params)


action_plugin = ActionPlugin(
    name="my-screenshot",
    factory=lambda params: ScreenshotAction(params),
    description="Custom screenshot action",
)
```

### Custom backend

```python
# my_plugin.py
from wavexis.backend.base import AbstractBackend


class MyBackend(AbstractBackend):
    async def launch(self, options):
        ...

    async def close(self):
        ...

    async def navigate(self, url, wait):
        ...

    async def screenshot(self, params):
        ...

    # ... implement other AbstractBackend methods
```

### Serve middleware

```python
# my_plugin.py
from wavexis.plugins import MiddlewarePlugin


def make_logging_middleware(web):
    @web.middleware
    async def logging_middleware(request, handler):
        print(f"Request: {request.method} {request.path}")
        response = await handler(request)
        print(f"Response: {response.status}")
        return response
    return logging_middleware


middleware_plugin = MiddlewarePlugin(
    name="logging",
    factory=make_logging_middleware,
    description="Request logging middleware",
)
```

### Lifecycle hooks

```python
# my_plugin.py
from wavexis.plugins import Plugin, PluginContext


class MyPlugin(Plugin):
    name = "my-plugin"
    version = "1.0.0"

    def before_action(self, ctx: PluginContext):
        print(f"Before: {ctx.command}")

    def after_action(self, ctx: PluginContext, result):
        print(f"After: {ctx.command} -> {result}")
```

## Registering plugins

In your plugin package's `pyproject.toml`:

```toml
[project.entry-points."wavexis.plugins"]
my-action = "my_plugin:action_plugin"
my-backend = "my_plugin:MyBackend"
my-middleware = "my_plugin:middleware_plugin"
my-hooks = "my_plugin:MyPlugin"
```

Install the package with `pip install my-plugin` and wavexis will discover it automatically.

## Using plugins

### CLI

```bash
wavexis plugins
```

Lists all discovered plugins (actions, backends, middleware).

### Multi-action YAML

Custom actions are available in multi-action YAML:

```yaml
actions:
  - my-screenshot:
      url: https://example.com
```

### Serve mode

Custom middleware is applied to the aiohttp application automatically.

```bash
curl http://localhost:8080/plugins
```

Returns JSON with discovered plugins.

### Custom backends

Custom backends are registered with `BackendManager` and can be selected with `--backend`:

```bash
wavexis screenshot https://example.com --backend my-backend
```
