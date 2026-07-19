"""navigation commands for wavexis CLI."""

from __future__ import annotations

__all__ = ["_console"]

import json
from typing import Any

import typer

from wavexis.actions.console import ConsoleAction, ConsoleParams
from wavexis.actions.navigate import (
    BackAction,
    ForwardAction,
    NavigateAction,
    NavigateParams,
    ReloadAction,
    StopAction,
)
from wavexis.actions.tabs import TabsAction, TabsParams
from wavexis.cli._shared import (
    Output,
    _browser_options,
    _close_backend,
    _get_backend,
    _run_async,
    app,
)
from wavexis.config import WaitStrategy


@app.command()
def navigate(
    url: str = typer.Argument(..., help="URL to navigate to"),
    wait_for: str | None = typer.Option(None, "--wait-for", help="CSS selector to wait for"),
) -> None:
    """Navigate to a URL and optionally wait for an element."""
    wait = (
        WaitStrategy(strategy="selector", selector=wait_for)
        if wait_for
        else WaitStrategy(strategy="load")
    )
    _run_async(_navigate(url, wait))
    typer.echo(f"Navigated to {url}")


async def _navigate(url: str, wait: WaitStrategy) -> None:
    """Async helper for navigation."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        action = NavigateAction(NavigateParams(url=url, wait=wait))
        await action.execute(backend)
    finally:
        await _close_backend(backend)


@app.command()
def back() -> None:
    """Navigate back in browser history."""
    _run_async(_nav_simple(lambda b: BackAction(None).execute(b)))
    typer.echo("Navigated back")


@app.command()
def forward() -> None:
    """Navigate forward in browser history."""
    _run_async(_nav_simple(lambda b: ForwardAction(None).execute(b)))
    typer.echo("Navigated forward")


@app.command()
def reload(
    ignore_cache: bool = typer.Option(False, "--ignore-cache", help="Bypass browser cache"),
) -> None:
    """Reload the current page."""
    _run_async(_nav_simple(lambda b: ReloadAction(ignore_cache).execute(b)))
    typer.echo("Page reloaded")


@app.command()
def stop() -> None:
    """Stop all pending navigations and resource loads."""
    _run_async(_nav_simple(lambda b: StopAction(None).execute(b)))
    typer.echo("Stopped loading")


async def _nav_simple(action_fn: Any) -> None:
    """Async helper for simple navigation actions (back, forward, reload, stop)."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await action_fn(backend)
    finally:
        await _close_backend(backend)


@app.command()
def tabs(
    action: str = typer.Argument("list", help="Tab action: list, new, close, activate"),
    url: str = typer.Option("about:blank", "--url", help="URL for new tab"),
    tab_id: str = typer.Option("", "--tab-id", help="Target ID for close/activate"),
) -> None:
    """Manage browser tabs (list, new, close, activate)."""
    result = _run_async(_tabs(action, url, tab_id))
    if result is None:
        return

    if action == "list":
        typer.echo(json.dumps(result, indent=2, default=str))
    elif action == "new":
        typer.echo(f"New tab created: {result}")
    elif action == "close":
        typer.echo(f"Tab closed: {tab_id}")
    elif action == "activate":
        typer.echo(f"Tab activated: {tab_id}")


async def _tabs(action: str, url: str, tab_id: str) -> Any:
    """Async helper for tab operations."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        params = TabsParams(action=action, url=url, tab_id=tab_id)
        return await TabsAction(params).execute(backend)
    finally:
        await _close_backend(backend)


@app.command()
def contexts(
    action: str = typer.Argument("list", help="Context action: list, new, close, user-context"),
    context_id: str = typer.Option("", "--context-id", "-c", help="Context ID for close"),
) -> None:
    """Manage browser contexts and user contexts."""
    result = _run_async(_contexts(action, context_id))
    if result is None:
        return

    if action == "list":
        typer.echo(json.dumps(result, indent=2, default=str))
    elif action == "new":
        typer.echo(f"New context created: {result}")
    elif action == "close":
        typer.echo(f"Context closed: {context_id}")
    elif action == "user-context":
        typer.echo(f"New user context created: {result}")


async def _contexts(action: str, context_id: str) -> Any:
    """Async helper for context operations."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        if action == "list":
            return await backend.list_contexts()
        if action == "new":
            return await backend.new_context()
        if action == "close":
            await backend.close_context(context_id)
            return None
        if action == "user-context":
            return await backend.new_user_context()
        raise ValueError(f"Unknown context action: {action}")
    finally:
        await _close_backend(backend)


@app.command()
def console(
    url: str = typer.Argument(..., help="URL to navigate to"),
    level: str = typer.Option(
        "all", "--level", help="Minimum log level (all, error, warning, info)"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json, csv, yaml"),
    capture: str = typer.Option(
        "console",
        "--capture",
        help="What to capture: console, logs, or both",
    ),
) -> None:
    """Capture console messages and/or browser logs from a web page."""
    result = _run_async(_console(url, level, capture))
    if result is None:
        return

    Output.write_formatted(result, format, output)
    if output:
        typer.echo(f"Console output saved to {output}")


async def _console(url: str, level: str, capture: str = "console") -> Any:
    """Async helper for console capture."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        params = ConsoleParams(
            url=url,
            level=level,
            wait=WaitStrategy(strategy="load"),
            capture=capture,
        )
        return await ConsoleAction(params).execute(backend)
    finally:
        await _close_backend(backend)


@app.command()
def logs(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Capture browser log entries from a web page."""
    result = _run_async(_logs(url))
    if result is None:
        return

    if output:
        Output.write_json(result, output)
        typer.echo(f"Logs saved to {output}")
    else:
        typer.echo(json.dumps(result, indent=2, default=str))


async def _logs(url: str) -> Any:
    """Async helper for log capture."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        params = ConsoleParams(
            url=url,
            wait=WaitStrategy(strategy="load"),
            capture="logs",
        )
        return await ConsoleAction(params).execute(backend)
    finally:
        await _close_backend(backend)


@app.command()
def page_frame_tree(
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Get the current page frame tree."""
    result = _run_async(_page_op(lambda b: b.page_get_frame_tree()))
    Output.write_json(result, output)


@app.command()
def page_layout_metrics(
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Get page layout metrics (viewport, content size, etc.)."""
    result = _run_async(_page_op(lambda b: b.page_get_layout_metrics()))
    Output.write_json(result, output)


@app.command()
def page_history(
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Get the navigation history for the current page."""
    result = _run_async(_page_op(lambda b: b.page_get_navigation_history()))
    Output.write_json(result, output)


@app.command()
def page_download(
    behavior: str = typer.Argument(..., help="Download behavior: allow or deny"),
    path: str = typer.Option("", "--path", "-p", help="Download directory path"),
) -> None:
    """Set page download behavior and optional download path."""
    _run_async(_page_op(lambda b: b.page_set_download_behavior(behavior, path)))
    typer.echo(f"Download behavior set to {behavior}")
    if path:
        typer.echo(f"Download path: {path}")


@app.command()
def page_snapshot(
    output: str = typer.Option("snapshot.mhtml", "--output", "-o", help="Output file path"),
    fmt: str = typer.Option("mhtml", "--format", help="Snapshot format (mhtml or text)"),
) -> None:
    """Capture a snapshot of the current page."""
    data = _run_async(_page_op(lambda b: b.page_capture_snapshot(fmt)))
    if data is None:
        return
    Output.write_bytes(data.encode("utf-8"), output)
    typer.echo(f"Snapshot saved to {output}")


@app.command()
def page_pdf(
    output: str = typer.Option("page.pdf", "--output", "-o", help="Output PDF file path"),
    landscape: bool = typer.Option(False, "--landscape", help="Landscape orientation"),
    scale: float = typer.Option(1.0, "--scale", help="Scale factor"),
) -> None:
    """Print the current page to PDF."""
    import base64

    data = _run_async(_page_op(lambda b: b.page_print_to_pdf(landscape=landscape, scale=scale)))
    if data is None:
        return
    Output.write_bytes(base64.b64decode(data), output)
    typer.echo(f"PDF saved to {output}")


@app.command()
def page_screencast_start(
    fmt: str = typer.Option("jpeg", "--format", help="Image format (jpeg or png)"),
    quality: int = typer.Option(80, "--quality", help="JPEG quality (0-100)"),
) -> None:
    """Start screencasting the page."""
    _run_async(_page_op(lambda b: b.page_start_screencast(format=fmt, quality=quality)))
    typer.echo("Screencast started")


@app.command()
def page_screencast_stop() -> None:
    """Stop screencasting the page."""
    _run_async(_page_op(lambda b: b.page_stop_screencast()))
    typer.echo("Screencast stopped")


@app.command()
def page_bypass_csp(
    enabled: bool = typer.Option(True, "--enable/--disable", help="Enable or disable CSP bypass"),
) -> None:
    """Enable or disable CSP bypass for the page."""
    _run_async(_page_op(lambda b: b.page_set_bypass_csp(enabled)))
    typer.echo(f"CSP bypass {'enabled' if enabled else 'disabled'}")


@app.command()
def page_ad_block(
    enabled: bool = typer.Option(True, "--enable/--disable", help="Enable or disable ad blocking"),
) -> None:
    """Enable or disable ad blocking for the page."""
    _run_async(_page_op(lambda b: b.page_set_ad_blocking_enabled(enabled)))
    typer.echo(f"Ad blocking {'enabled' if enabled else 'disabled'}")


@app.command()
def page_inject_script(
    source: str = typer.Argument(..., help="JavaScript source code to inject"),
    world: str = typer.Option("", "--world", help="Isolated world name"),
) -> None:
    """Add a script to evaluate on every new document."""
    script_id = _run_async(
        _page_op(lambda b: b.page_add_script_to_evaluate_on_new_document(source, world))
    )
    typer.echo(f"Script added with ID: {script_id}")


@app.command()
def page_remove_script(
    script_id: str = typer.Argument(..., help="Script identifier to remove"),
) -> None:
    """Remove a previously injected script by ID."""
    _run_async(_page_op(lambda b: b.page_remove_script_to_evaluate_on_new_document(script_id)))
    typer.echo(f"Script removed: {script_id}")


@app.command()
def page_manifest(
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Get the web app manifest for the current page."""
    result = _run_async(_page_op(lambda b: b.page_get_app_manifest()))
    Output.write_json(result, output)


@app.command()
def page_resource_tree(
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Get the resource tree for the current page."""
    result = _run_async(_page_op(lambda b: b.page_get_resource_tree()))
    Output.write_json(result, output)


@app.command()
def page_add_compilation_cache(
    url: str = typer.Argument(..., help="URL for the compilation cache entry"),
    data: str = typer.Argument(..., help="Base64-encoded compilation cache data"),
) -> None:
    """Add data to the compilation cache for the given URL."""
    _run_async(_page_op(lambda b: b.page_add_compilation_cache(url, data)))
    typer.echo(f"Compilation cache added for {url}")


@app.command()
def page_add_script_on_load(
    source: str = typer.Argument(..., help="Script source to evaluate on page load"),
) -> None:
    """Add a script to evaluate on page load."""
    script_id = _run_async(_page_op(lambda b: b.page_add_script_to_evaluate_on_load(source)))
    typer.echo(f"Script added with ID: {script_id}")


@app.command()
def page_capture_screenshot(
    fmt: str = typer.Option("png", "--format", help="Image format (png or jpeg)"),
    quality: int = typer.Option(80, "--quality", help="JPEG quality (0-100)"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Capture a screenshot of the page."""
    import base64

    data = _run_async(_page_op(lambda b: b.page_capture_screenshot(format=fmt, quality=quality)))
    if data is None:
        return
    if output == "-":
        typer.echo(base64.b64decode(data), nl=False)
    else:
        with open(output, "wb") as f:
            f.write(base64.b64decode(data))
        typer.echo(f"Screenshot saved to {output}")


@app.command()
def page_clear_compilation_cache() -> None:
    """Clear the compilation cache."""
    _run_async(_page_op(lambda b: b.page_clear_compilation_cache()))
    typer.echo("Compilation cache cleared")


@app.command()
def page_clear_device_orientation() -> None:
    """Clear the device orientation override."""
    _run_async(_page_op(lambda b: b.page_clear_device_orientation_override()))
    typer.echo("Device orientation override cleared")


@app.command()
def page_clear_geolocation() -> None:
    """Clear the geolocation override."""
    _run_async(_page_op(lambda b: b.page_clear_geolocation_override()))
    typer.echo("Geolocation override cleared")


@app.command()
def page_crash() -> None:
    """Crash the renderer."""
    _run_async(_page_op(lambda b: b.page_crash()))
    typer.echo("Renderer crashed")


@app.command()
def page_create_isolated_world(
    frame_id: str = typer.Argument(..., help="Frame ID"),
    world_name: str = typer.Option("", "--world-name", help="Name for the isolated world"),
) -> None:
    """Create an isolated world for the given frame."""
    ctx_id = _run_async(_page_op(lambda b: b.page_create_isolated_world(frame_id, world_name)))
    typer.echo(f"Isolated world created with context ID: {ctx_id}")


@app.command()
def page_disable() -> None:
    """Disable the page domain."""
    _run_async(_page_op(lambda b: b.page_disable()))
    typer.echo("Page domain disabled")


@app.command()
def page_enable() -> None:
    """Enable the page domain."""
    _run_async(_page_op(lambda b: b.page_enable()))
    typer.echo("Page domain enabled")


@app.command()
def page_ad_script_ancestry(
    frame_id: str = typer.Argument(..., help="Frame ID"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Get the ad script ancestry for a frame."""
    result = _run_async(_page_op(lambda b: b.page_get_ad_script_ancestry(frame_id)))
    Output.write_json(result, output)


@app.command()
def page_annotated_content(
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Get annotated page content."""
    result = _run_async(_page_op(lambda b: b.page_get_annotated_page_content()))
    Output.write_json(result, output)


@app.command()
def page_app_id(
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Get the app ID for the current page."""
    result = _run_async(_page_op(lambda b: b.page_get_app_id()))
    Output.write_json(result, output)


@app.command()
def page_installability_errors(
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Get installability errors for the current page."""
    result = _run_async(_page_op(lambda b: b.page_get_installability_errors()))
    Output.write_json(result, output)


@app.command()
def page_manifest_icons(
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Get manifest icons for the current page."""
    result = _run_async(_page_op(lambda b: b.page_get_manifest_icons()))
    Output.write_json(result, output)


@app.command()
def page_origin_trials(
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Get origin trials for the current page."""
    result = _run_async(_page_op(lambda b: b.page_get_origin_trials()))
    Output.write_json(result, output)


@app.command()
def page_permissions_policy_state(
    frame_id: str = typer.Argument(..., help="Frame ID"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Get permissions policy state for a frame."""
    result = _run_async(_page_op(lambda b: b.page_get_permissions_policy_state(frame_id)))
    Output.write_json(result, output)


@app.command()
def page_handle_dialog(
    accept: bool = typer.Argument(..., help="Whether to accept the dialog"),
    prompt_text: str = typer.Option("", "--prompt-text", help="Text to enter in the prompt"),
) -> None:
    """Handle a JavaScript dialog."""
    _run_async(_page_op(lambda b: b.page_handle_javascript_dialog(accept, prompt_text)))
    typer.echo(f"Dialog {'accepted' if accept else 'dismissed'}")


@app.command()
def page_produce_compilation_cache(
    url: str = typer.Argument(..., help="URL to produce compilation cache for"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Produce compilation cache for the given URL."""
    result = _run_async(_page_op(lambda b: b.page_produce_compilation_cache(url)))
    Output.write_json(result, output)


@app.command()
def page_remove_script_on_load(
    script_id: str = typer.Argument(..., help="Script identifier to remove"),
) -> None:
    """Remove a script previously added to evaluate on load."""
    _run_async(_page_op(lambda b: b.page_remove_script_to_evaluate_on_load(script_id)))
    typer.echo(f"Script removed: {script_id}")


@app.command()
def page_reset_navigation_history() -> None:
    """Reset the navigation history."""
    _run_async(_page_op(lambda b: b.page_reset_navigation_history()))
    typer.echo("Navigation history reset")


@app.command()
def page_screencast_ack(
    session_id: int = typer.Argument(..., help="Screencast session ID"),
) -> None:
    """Acknowledge a screencast frame."""
    _run_async(_page_op(lambda b: b.page_screencast_frame_ack(session_id)))
    typer.echo(f"Screencast frame acknowledged for session {session_id}")


@app.command()
def page_search_in_resource(
    frame_id: str = typer.Argument(..., help="Frame ID"),
    url: str = typer.Argument(..., help="Resource URL"),
    query: str = typer.Argument(..., help="Search query"),
    case_sensitive: bool = typer.Option(False, "--case-sensitive", help="Case-sensitive search"),
    is_regex: bool = typer.Option(False, "--is-regex", help="Treat query as regex"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),
) -> None:
    """Search for a string in a resource."""
    result = _run_async(
        _page_op(
            lambda b: b.page_search_in_resource(frame_id, url, query, case_sensitive, is_regex)
        )
    )
    Output.write_json(result, output)


@app.command()
def page_set_device_orientation(
    alpha: float = typer.Argument(..., help="Alpha angle"),
    beta: float = typer.Argument(..., help="Beta angle"),
    gamma: float = typer.Argument(..., help="Gamma angle"),
) -> None:
    """Override the device orientation."""
    _run_async(_page_op(lambda b: b.page_set_device_orientation_override(alpha, beta, gamma)))
    typer.echo(f"Device orientation set: alpha={alpha}, beta={beta}, gamma={gamma}")


@app.command()
def page_set_document_content(
    frame_id: str = typer.Argument(..., help="Frame ID"),
    html: str = typer.Argument(..., help="HTML content to set"),
) -> None:
    """Set the document content for a frame."""
    _run_async(_page_op(lambda b: b.page_set_document_content(frame_id, html)))
    typer.echo(f"Document content set for frame {frame_id}")


@app.command()
def page_set_font_families(
    config: str = typer.Argument(..., help="Font families config as JSON"),
) -> None:
    """Set font families for the page."""
    try:
        font_families = json.loads(config)
    except json.JSONDecodeError as e:
        typer.echo(f"Error: invalid JSON config: {e}", err=True)
        raise typer.Exit(1) from e
    _run_async(_page_op(lambda b: b.page_set_font_families(font_families)))
    typer.echo("Font families set")


@app.command()
def page_set_font_sizes(
    config: str = typer.Argument(..., help="Font sizes config as JSON"),
) -> None:
    """Set font sizes for the page."""
    try:
        font_sizes = json.loads(config)
    except json.JSONDecodeError as e:
        typer.echo(f"Error: invalid JSON config: {e}", err=True)
        raise typer.Exit(1) from e
    _run_async(_page_op(lambda b: b.page_set_font_sizes(font_sizes)))
    typer.echo("Font sizes set")


@app.command()
def page_set_geolocation(
    latitude: float = typer.Option(0.0, "--lat", help="Latitude"),
    longitude: float = typer.Option(0.0, "--lon", help="Longitude"),
    accuracy: float = typer.Option(0.0, "--accuracy", help="Accuracy in meters"),
) -> None:
    """Override the geolocation."""
    _run_async(_page_op(lambda b: b.page_set_geolocation_override(latitude, longitude, accuracy)))
    typer.echo(f"Geolocation set: lat={latitude}, lon={longitude}, accuracy={accuracy}")


@app.command()
def page_intercept_file_chooser(
    enabled: bool = typer.Argument(..., help="Enable or disable file chooser interception"),
) -> None:
    """Intercept file chooser dialogs."""
    _run_async(_page_op(lambda b: b.page_set_intercept_file_chooser_dialog(enabled)))
    typer.echo(f"File chooser interception {'enabled' if enabled else 'disabled'}")


@app.command()
def page_set_lifecycle_events(
    enabled: bool = typer.Argument(..., help="Enable or disable lifecycle events"),
) -> None:
    """Enable or disable lifecycle events."""
    _run_async(_page_op(lambda b: b.page_set_lifecycle_events_enabled(enabled)))
    typer.echo(f"Lifecycle events {'enabled' if enabled else 'disabled'}")


@app.command()
def page_set_prerendering(
    is_allowed: bool = typer.Argument(..., help="Whether prerendering is allowed"),
) -> None:
    """Set whether prerendering is allowed."""
    _run_async(_page_op(lambda b: b.page_set_prerendering_allowed(is_allowed)))
    typer.echo(f"Prerendering {'allowed' if is_allowed else 'disallowed'}")


@app.command()
def page_set_rph_mode(
    mode: str = typer.Argument(..., help="RPH registration mode"),
) -> None:
    """Set the RPH registration mode."""
    _run_async(_page_op(lambda b: b.page_set_rph_registration_mode(mode)))
    typer.echo(f"RPH registration mode set: {mode}")


@app.command()
def page_set_spc_mode(
    mode: str = typer.Argument(..., help="SPC transaction mode"),
) -> None:
    """Set the SPC transaction mode."""
    _run_async(_page_op(lambda b: b.page_set_spc_transaction_mode(mode)))
    typer.echo(f"SPC transaction mode set: {mode}")


@app.command()
def page_set_touch_emulation(
    enabled: bool = typer.Argument(..., help="Enable or disable touch emulation"),
    configuration: str = typer.Option("", "--configuration", help="Touch emulation configuration"),
) -> None:
    """Enable or disable touch emulation."""
    _run_async(_page_op(lambda b: b.page_set_touch_emulation_enabled(enabled, configuration)))
    typer.echo(f"Touch emulation {'enabled' if enabled else 'disabled'}")


@app.command()
def page_set_web_lifecycle_state(
    state: str = typer.Argument(..., help="Web lifecycle state (frozen, active, destroyed)"),
) -> None:
    """Set the web lifecycle state."""
    _run_async(_page_op(lambda b: b.page_set_web_lifecycle_state(state)))
    typer.echo(f"Web lifecycle state set: {state}")


@app.command()
def page_stop() -> None:
    """Stop all page loading."""
    _run_async(_page_op(lambda b: b.page_stop()))
    typer.echo("Page loading stopped")


async def _page_op(action_fn: Any) -> Any:
    """Async helper for page inspection operations."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        return await action_fn(backend)
    finally:
        await _close_backend(backend)
