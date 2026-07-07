"""config and setup commands for wavexis CLI."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import typer

from wavexis.cli._shared import (
    EXIT_BROWSER_ERROR,
    EXIT_CONFIG_ERROR,
    Output,
    _browser_options,
    _echo,
    _get_backend,
    _run_async,
    _write_json_output,
    app,
)
from wavexis.config import EvalParams, ScreenshotParams, WaitStrategy


@app.command()
def completions(
    shell: str = typer.Argument(..., help="Shell: bash, zsh, fish, powershell"),
) -> None:
    """Install shell completions for wavexis."""
    import subprocess

    shells = {"bash", "zsh", "fish", "powershell"}
    if shell not in shells:
        Output.error(f"Unsupported shell: {shell}. Choose from: {', '.join(sorted(shells))}")
        raise typer.Exit(EXIT_CONFIG_ERROR)

    try:
        subprocess.run(
            [sys.executable, "-m", "wavexis", "completion", shell],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        Output.error(f"Failed to install completions: {e}")
        raise typer.Exit(EXIT_BROWSER_ERROR) from e

    Output.success(f"Completions installed for {shell}")


@app.command()
def auth(
    context: str = typer.Argument(..., help="Path to auth context JSON file"),
    url: str = typer.Argument(..., help="URL to navigate to with auth context"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
    screenshot: bool = typer.Option(
        False, "--screenshot", help="Take screenshot after applying auth",
    ),
) -> None:
    """Apply auth context (cookies, headers, basic auth) and navigate to a URL."""
    from wavexis.auth import apply_auth_context, load_auth_context

    ctx = load_auth_context(context)

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
                        url=url, wait=WaitStrategy(strategy="load"),
                    ),
                )
            return await backend.eval(
                EvalParams(
                    url=url,
                    expression="document.title",
                    wait=WaitStrategy(strategy="load"),
                ),
            )
        finally:
            await backend.close()

    result = _run_async(_run_auth())
    if result is None:
        return

    if isinstance(result, bytes):
        out = output or "auth_result.png"
        with open(out, "wb") as f:
            f.write(result)
        _echo(f"Screenshot saved to {out}")
    elif isinstance(result, str):
        typer.echo(result)
    else:
        _write_json_output(result, output, "auth result")


@app.command()
def repl(
    url: str = typer.Argument(
        "", help="Optional URL to navigate to before starting the REPL"
    ),
) -> None:
    """Start an interactive REPL session with a live browser.

    Launches a non-headless browser and provides a command prompt
    to execute actions interactively. Type 'help' for available commands.
    """
    from wavexis.repl import repl_loop

    backend = _get_backend()
    _run_async(repl_loop(backend, url or None))


@app.command()
def config(
    action: str = typer.Argument(
        "show", help="Config action: show, set, init, path"
    ),
    key: str = typer.Option(
        "", "--key", help="Config key to set (backend, headless, timeout, proxy)"
    ),
    value: str = typer.Option(
        "", "--value", help="Value to set for the given key"
    ),
) -> None:
    """Manage global wavexis configuration at ~/.wavexis/config.yml.

    \b
    Show current config:
        wavexis config show

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
        return

    if action == "show":
        if not config_path.exists():
            typer.echo("No config file found. Run: wavexis config init")
            return
        typer.echo(config_path.read_text(encoding="utf-8"))
        return

    if action == "set":
        if not key:
            typer.echo("Error: --key is required for 'set'")
            raise typer.Exit(EXIT_CONFIG_ERROR)
        if not value:
            typer.echo("Error: --value is required for 'set'")
            raise typer.Exit(EXIT_CONFIG_ERROR)

        config_dir.mkdir(parents=True, exist_ok=True)
        current: dict[str, Any] = {}
        if config_path.exists():
            loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                current = loaded

        if key in ("headless",):
            current[key] = value.lower() in ("true", "1", "yes")
        elif key in ("timeout",):
            current[key] = int(value)
        else:
            current[key] = value

        config_path.write_text(
            yaml.dump(current, default_flow_style=False, sort_keys=True),
            encoding="utf-8",
        )
        typer.echo(f"Set {key} = {current[key]} in {config_path}")
        return

    typer.echo(f"Unknown action: {action}. Use: show, set, init, path")


@app.command()
def init(
    template: str = typer.Option(
        "",
        "--template",
        "-t",
        help="Template name (screenshot, pdf, scrape, eval, multi-step, cookies, har)",
    ),
    url: str = typer.Option(
        "", "--url", "-u", help="URL to use in the generated config"
    ),
    expression: str = typer.Option(
        "", "--expression", "-e", help="JS expression for scrape/eval templates"
    ),
    selector: str = typer.Option(
        "", "--selector", "-s", help="CSS selector for multi-step template"
    ),
    text: str = typer.Option(
        "", "--text", help="Text for type action in multi-step template"
    ),
    output: str = typer.Option(
        "wavexis.yaml", "--output", "-o", help="Output YAML file path"
    ),
    list_templates: bool = typer.Option(
        False, "--list", help="List available templates and exit"
    ),
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

    out_path = Path(output)
    out_path.write_text(yaml_content, encoding="utf-8")
    typer.echo(f"Config saved to {output}")
    typer.echo(f"Run with: wavexis multi {output}")
