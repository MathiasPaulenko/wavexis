"""config and setup commands for wavexis CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from wavexis.cli._shared import (
    EXIT_BROWSER_ERROR,
    EXIT_CONFIG_ERROR,
    Output,
    _browser_options,
    _close_backend,
    _echo,
    _get_backend,
    _handle_error,
    _run_async,
    _wait_strategy,
    _write_json_output,
    app,
)
from wavexis.config import (
    _BROWSER_SCHEMES,
    _MAX_TIMEOUT_MS,
    _MAX_VIEWPORT_DIMENSION,
    _REMOTE_SCHEMES,
    ScreenshotParams,
    _validate_int_range,
    _validate_path_string,
    _validate_url,
)
from wavexis.exceptions import ActionError, WavexisError


@app.command()
def completions(
    shell: str = typer.Argument(..., help="Shell: bash, zsh, fish, powershell"),
) -> None:
    """Install shell completions for wavexis.

    Installs through Typer's completion helpers for the requested shell.
    """
    shells = {"bash", "zsh", "fish", "powershell"}
    if shell not in shells:
        Output.error(f"Unsupported shell: {shell}. Choose from: {', '.join(sorted(shells))}")
        raise typer.Exit(EXIT_CONFIG_ERROR)

    # Install directly through Typer's completion helpers. Spawning
    # ``--install-completion <shell>`` does not work: that flag ignores its
    # argument and auto-detects the current shell instead.
    from typer._completion_shared import install as _typer_install

    try:
        installed_shell, path = _typer_install(shell=shell, prog_name="wavexis")
    except Exception as e:
        Output.error(f"Failed to install completions: {e}")
        raise typer.Exit(EXIT_BROWSER_ERROR) from e

    Output.success(f"Completions installed for {installed_shell} ({path})")


@app.command()
def auth(
    context: str = typer.Argument(..., help="Path to auth context JSON file"),
    url: str = typer.Argument(..., help="URL to navigate to with auth context"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
    screenshot: bool = typer.Option(
        False,
        "--screenshot",
        help="Take screenshot after applying auth",
    ),
) -> None:
    """Apply auth context (cookies, headers, basic auth) and navigate to a URL."""
    from wavexis.auth import apply_auth_context, load_auth_context

    try:
        ctx = load_auth_context(context)
    except (json.JSONDecodeError, OSError) as e:
        _handle_error(WavexisError(f"Failed to load auth context: {e}"))
        return

    async def _run_auth() -> Any:
        """Execute an authenticated browser session.

        Returns:
            Result of the authenticated action.
        """
        backend = _get_backend()
        await backend.launch(_browser_options())
        try:
            await apply_auth_context(backend, ctx, url)
            if screenshot:
                return await backend.screenshot(
                    ScreenshotParams(
                        url=url,
                        wait=_wait_strategy(),
                    ),
                )
            return await backend.eval("document.title")
        finally:
            await _close_backend(backend)

    result = _run_async(_run_auth())
    if result is None:
        return

    if isinstance(result, bytes):
        out = output if output and output != "-" else "auth_result.png"
        Output.write_bytes(result, out)
        _echo(f"Screenshot saved to {out}")
    elif isinstance(result, str):
        typer.echo(result)
    else:
        _write_json_output(result, output, "auth result")


@app.command()
def repl(
    url: str = typer.Argument("", help="Optional URL to navigate to before starting the REPL"),
) -> None:
    """Start an interactive REPL session with a live browser.

    Launches a non-headless browser and provides a command prompt
    to execute actions interactively. Type 'help' for available commands.
    """
    from wavexis.repl import repl_loop

    backend = _get_backend()

    async def _repl_and_close() -> Any:
        try:
            return await repl_loop(backend, url or None)
        finally:
            await _close_backend(backend)

    _run_async(_repl_and_close())


_VALID_CONFIG_KEYS = {
    "backend",
    "headless",
    "timeout",
    "wait_strategy",
    "width",
    "height",
    "user_agent",
    "proxy",
    "user_data_dir",
    "browser_url",
    "remote_url",
    "stealth",
}

_PROXY_SCHEMES = frozenset({"http", "https", "socks4", "socks5", "direct"})


def _validate_config_value(key: str, value: str) -> Any:
    """Validate and coerce a config value for the given key.

    Raises:
        ActionError: If the value is not valid for the key.
    """
    if not value:
        raise ActionError(f"value cannot be empty for key '{key}'")

    if key == "headless":
        lowered = value.lower()
        if lowered in ("true", "1", "yes"):
            return True
        if lowered in ("false", "0", "no"):
            return False
        raise ActionError(
            f"headless must be true/yes/1 or false/no/0; got {value!r}"
        )

    if key == "backend":
        if value not in ("cdp", "bidi"):
            raise ActionError(
                f"backend must be 'cdp' or 'bidi'; got {value!r}"
            )
        return value

    if key == "timeout":
        try:
            timeout = int(value)
        except ValueError as exc:
            raise ActionError(f"timeout must be an integer; got {value!r}") from exc
        _validate_int_range(
            timeout, "timeout", min_value=0, max_value=_MAX_TIMEOUT_MS
        )
        return timeout

    if key == "width":
        try:
            width = int(value)
        except ValueError as exc:
            raise ActionError(f"width must be an integer; got {value!r}") from exc
        _validate_int_range(
            width, "width", min_value=1, max_value=_MAX_VIEWPORT_DIMENSION
        )
        return width

    if key == "height":
        try:
            height = int(value)
        except ValueError as exc:
            raise ActionError(f"height must be an integer; got {value!r}") from exc
        _validate_int_range(
            height, "height", min_value=1, max_value=_MAX_VIEWPORT_DIMENSION
        )
        return height

    if key == "wait_strategy":
        if value not in ("load", "domcontentloaded", "networkidle", "selector", "url", "none"):
            raise ActionError(
                f"wait_strategy must be one of load, domcontentloaded, "
                f"networkidle, selector, url, none; got {value!r}"
            )
        return value

    if key == "stealth":
        lowered = value.lower()
        if lowered in ("true", "1", "yes"):
            return True
        if lowered in ("false", "0", "no"):
            return False
        raise ActionError(
            f"stealth must be true/yes/1 or false/no/0; got {value!r}"
        )

    if key == "proxy":
        _validate_url(value, schemes=_PROXY_SCHEMES, name="proxy")
        return value

    if key == "user_data_dir":
        _validate_path_string(value, "user_data_dir")
        return value

    if key == "browser_url":
        _validate_url(value, schemes=_BROWSER_SCHEMES, name="browser_url")
        return value

    if key == "remote_url":
        _validate_url(value, schemes=_REMOTE_SCHEMES, name="remote_url")
        return value

    if key == "user_agent":
        return value

    if key not in _VALID_CONFIG_KEYS:
        raise ActionError(f"unknown config key: {key!r}")

    return value


@app.command()
def config(
    action: str = typer.Argument("show", help="Config action: show, get, set, init, path"),
    key: str = typer.Option(
        "", "--key", help="Config key to get/set (backend, headless, timeout, proxy)"
    ),
    value: str = typer.Option("", "--value", help="Value to set for the given key"),
) -> None:
    """Manage global wavexis configuration at ~/.wavexis/config.yml.

    \b
    Show current config:
        wavexis config show

    \b
    Get a single value:
        wavexis config get --key backend

    \b
    Set a default:
        wavexis config set --key backend --value cdp
        wavexis config set --key headless --value false
        wavexis config set --key timeout --value 60000
        wavexis config set --key proxy --value http://proxy:8080

    \b
    Create initial config file:
        wavexis config init

    \b
    Show config file path:
        wavexis config path
    """
    import yaml

    config_dir = Path.home() / ".wavexis"
    config_path = config_dir / "config.yml"

    if action == "path":
        typer.echo(str(config_path))
        return

    if action == "init":
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            if config_path.exists():
                typer.echo(f"Config already exists at {config_path}")
                return
            defaults: dict[str, Any] = {
                "backend": "cdp",
                "headless": True,
                "timeout": 30000,
            }
            config_path.write_text(
                yaml.dump(defaults, default_flow_style=False, sort_keys=True),
                encoding="utf-8",
            )
            typer.echo(f"Created config at {config_path}")
        except OSError as e:
            _handle_error(WavexisError(f"Failed to create config: {e}"))
        return

    if action == "show":
        if not config_path.exists():
            typer.echo("No config file found. Run: wavexis config init")
            return
        try:
            typer.echo(config_path.read_text(encoding="utf-8"))
        except OSError as e:
            _handle_error(WavexisError(f"Failed to read config: {e}"))
        return

    if action == "get":
        if not key:
            typer.echo("Error: --key is required for 'get'", err=True)
            raise typer.Exit(EXIT_CONFIG_ERROR)
        if not config_path.exists():
            typer.echo(f"Error: no config file at {config_path}", err=True)
            raise typer.Exit(EXIT_CONFIG_ERROR)
        try:
            loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as e:
            _handle_error(WavexisError(f"Failed to read config: {e}"))
            return
        if not isinstance(loaded, dict) or key not in loaded:
            typer.echo(f"Error: key '{key}' not found in config", err=True)
            raise typer.Exit(EXIT_CONFIG_ERROR)
        typer.echo(loaded[key])
        return

    if action == "set":
        if not key:
            typer.echo("Error: --key is required for 'set'", err=True)
            raise typer.Exit(EXIT_CONFIG_ERROR)
        if not value:
            typer.echo("Error: --value is required for 'set'", err=True)
            raise typer.Exit(EXIT_CONFIG_ERROR)

        try:
            coerced = _validate_config_value(key, value)
        except ActionError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(EXIT_CONFIG_ERROR) from e

        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            current: dict[str, Any] = {}
            if config_path.exists():
                loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    current = loaded

            current[key] = coerced

            config_path.write_text(
                yaml.dump(current, default_flow_style=False, sort_keys=True),
                encoding="utf-8",
            )
            typer.echo(f"Set {key} = {current[key]} in {config_path}")
        except OSError as e:
            _handle_error(WavexisError(f"Failed to write config: {e}"))
        return

    typer.echo(f"Unknown action: {action}. Use: show, get, set, init, path")


@app.command()
def init(
    template: str = typer.Option(
        "",
        "--template",
        "-t",
        help="Template name (screenshot, pdf, scrape, eval, multi-step, cookies, har)",
    ),
    url: str = typer.Option("", "--url", "-u", help="URL to use in the generated config"),
    expression: str = typer.Option(
        "", "--expression", "-e", help="JS expression for scrape/eval templates"
    ),
    selector: str = typer.Option(
        "", "--selector", "-s", help="CSS selector for click action in multi-step template"
    ),
    input_selector: str = typer.Option(
        "",
        "--input-selector",
        help=(
            "CSS selector for type action in multi-step template. "
            "Defaults to '#input'. Use a separate selector from --selector "
            "because click and type usually target different elements."
        ),
    ),
    text: str = typer.Option("", "--text", help="Text for type action in multi-step template"),
    output: str = typer.Option("wavexis.yaml", "--output", "-o", help="Output YAML file path"),
    list_templates: bool = typer.Option(False, "--list", help="List available templates and exit"),
) -> None:
    """Generate a wavexis.yaml config from a template.

    Run without --template for an interactive wizard.
    Use --list to see available templates.
    """
    from wavexis.init import generate_config
    from wavexis.init import list_templates as do_list

    if list_templates:
        for name, desc in do_list():
            typer.echo(f"  {name} — {desc}")
        return

    if template:
        try:
            yaml_content = generate_config(
                template=template,
                url=url or None,
                expression=expression or None,
                selector=selector or None,
                text=text or None,
                input_selector=input_selector or None,
            )
        except ValueError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1) from e
    else:
        from wavexis.init import interactive_init

        try:
            yaml_content = interactive_init()
        except (ValueError, EOFError, KeyboardInterrupt) as e:
            typer.echo(f"\nCancelled: {e}", err=True)
            raise typer.Exit(1) from e

    Output.write_text(yaml_content, output)
    typer.echo(f"Config saved to {output}")
    typer.echo(f"Run with: wavexis multi {output}")
