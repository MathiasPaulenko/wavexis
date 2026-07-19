"""debug commands for wavexis CLI."""

from __future__ import annotations

import json
from typing import Any

import typer

from wavexis.cli._emulation import emulation_app
from wavexis.cli._shared import (
    _browser_options,
    _close_backend,
    _echo,
    _get_backend,
    _run_async,
    _write_json_output,
    app,
)
from wavexis.config import WaitStrategy
from wavexis.exceptions import ElementNotFoundError

css_app = typer.Typer(help="CSS inspection commands (styles, stylesheets, rules, computed)")
app.add_typer(css_app, name="css")

debug_app = typer.Typer(help="Debugging commands (breakpoint, step, pause, resume, listeners)")
app.add_typer(debug_app, name="debug")

overlay_app = typer.Typer(help="Overlay commands (highlight, clear)")
app.add_typer(overlay_app, name="overlay")


def _safe_json_loads(data: str, label: str = "JSON") -> Any:
    """Parse JSON safely, exiting with a user-friendly error on invalid input.

    Args:
        data: JSON string to parse.
        label: Label for the error message (e.g. "config", "quad").

    Returns:
        Parsed JSON data.

    Raises:
        typer.Exit: If the JSON is invalid.
    """
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        typer.echo(f"Error: invalid {label} JSON: {e}", err=True)
        raise typer.Exit(2) from e


dom_app = typer.Typer(help="DOM inspection commands (document, box-model, quads, search, scroll)")
app.add_typer(dom_app, name="dom")

runtime_app = typer.Typer(help="Runtime commands (evaluate, compile, call, objects, heap)")
app.add_typer(runtime_app, name="runtime")

target_app = typer.Typer(help="Target commands (tabs, contexts, attach, discover)")
app.add_typer(target_app, name="target")

device_access_app = typer.Typer(help="DeviceAccess commands (prompts, enable, disable)")
app.add_typer(device_access_app, name="device-access")

device_orientation_app = typer.Typer(help="DeviceOrientation commands (override)")
app.add_typer(device_orientation_app, name="device-orientation")

digital_credentials_app = typer.Typer(help="DigitalCredentials commands (virtual wallet)")
app.add_typer(digital_credentials_app, name="digital-credentials")

dom_snapshot_app = typer.Typer(help="DOMSnapshot commands (capture, get, enable, disable)")
app.add_typer(dom_snapshot_app, name="dom-snapshot")

dom_storage_app = typer.Typer(help="DOMStorage commands (clear, items, set, remove)")
app.add_typer(dom_storage_app, name="dom-storage")

event_breakpoints_app = typer.Typer(help="EventBreakpoints commands (instrumentation)")
app.add_typer(event_breakpoints_app, name="event-breakpoints")

extensions_app = typer.Typer(help="Extensions commands (storage, actions)")
app.add_typer(extensions_app, name="extensions")

fed_cm_app = typer.Typer(help="FedCm commands (dialog, account, cooldown)")
app.add_typer(fed_cm_app, name="fed-cm")

fetch_app = typer.Typer(help="Fetch commands (intercept, continue, fulfill, fail)")
app.add_typer(fetch_app, name="fetch")

file_system_app = typer.Typer(help="FileSystem commands (directory)")
app.add_typer(file_system_app, name="file-system")

headless_experimental_app = typer.Typer(help="HeadlessExperimental commands (begin frame)")
app.add_typer(headless_experimental_app, name="headless-experimental")

inspector_app = typer.Typer(help="Inspector commands (enable, disable)")
app.add_typer(inspector_app, name="inspector")

preload_app = typer.Typer(help="Preload commands (enable, disable)")
app.add_typer(preload_app, name="preload")

io_app = typer.Typer(help="IO commands (read, resolve blob)")
app.add_typer(io_app, name="io")

heap_profiler_app = typer.Typer(help="HeapProfiler commands (snapshot, sampling, tracking)")
app.add_typer(heap_profiler_app, name="heap-profiler")

indexed_db_app = typer.Typer(help="IndexedDB commands (database, object store, data)")
app.add_typer(indexed_db_app, name="indexed-db")

layer_tree_app = typer.Typer(help="LayerTree commands (snapshot, compositing)")
app.add_typer(layer_tree_app, name="layer-tree")

log_app = typer.Typer(help="Log commands (enable, disable, violations)")
app.add_typer(log_app, name="log")

media_app = typer.Typer(help="Media commands (enable, disable)")
app.add_typer(media_app, name="media")

memory_app = typer.Typer(help="Memory commands (sampling, pressure, counters)")
app.add_typer(memory_app, name="memory")

console_app = typer.Typer(help="Console commands (clear, enable, disable)")
app.add_typer(console_app, name="console")

crash_report_context_app = typer.Typer(help="CrashReportContext commands (get entries)")
app.add_typer(crash_report_context_app, name="crash-report-context")

input_domain_app = typer.Typer(help="Input commands (dispatch events, gestures, IME)")
app.add_typer(input_domain_app, name="input-domain")

network_domain_app = typer.Typer(help="Network commands (enable, disable, cookies, emulation)")
app.add_typer(network_domain_app, name="network-domain")


@css_app.command("styles")
def css_styles(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get inline and matched styles for an element."""
    result = _run_async(_css_action(url, "styles", selector=selector))
    if result is None:
        return
    _write_json_output(result, output, "styles")


@css_app.command("stylesheets")
def css_stylesheets(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """List all stylesheets in the page."""
    result = _run_async(_css_action(url, "stylesheets"))
    if result is None:
        return
    _write_json_output(result, output, "stylesheets")


@css_app.command("rules")
def css_rules(
    url: str = typer.Argument(..., help="URL to navigate to"),
    stylesheet_id: str = typer.Option(..., "--stylesheet-id", help="Stylesheet ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get CSS rules from a specific stylesheet."""
    result = _run_async(_css_action(url, "rules", stylesheet_id=stylesheet_id))
    if result is None:
        return
    _write_json_output(result, output, "rules")


@css_app.command("computed")
def css_computed(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get computed styles for an element."""
    result = _run_async(_css_action(url, "computed", selector=selector))
    if result is None:
        return
    _write_json_output(result, output, "computed styles")


async def _css_action(
    url: str,
    action: str,
    selector: str | None = None,
    stylesheet_id: str | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    """Execute a CSS action on a web page.

    Args:
        url: URL to navigate to.
        action: CSS action ("styles", "stylesheets", "rules", "computed").
        selector: CSS selector for styles/computed actions.
        stylesheet_id: Stylesheet ID for rules action.

    Returns:
        CSS data as a dict or list of dicts depending on the action.
    """
    from wavexis.actions.css import CSSAction, CSSActionParams

    params = CSSActionParams(
        url=url,
        action=action,
        selector=selector,
        stylesheet_id=stylesheet_id,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        act = CSSAction(params)
        return await act.execute(backend)
    finally:
        await _close_backend(backend)


@css_app.command("add-rule")
def css_add_rule(
    url: str = typer.Argument(..., help="URL to navigate to"),
    stylesheet_id: str = typer.Option(..., "--stylesheet-id", help="Stylesheet ID"),
    rule_text: str = typer.Argument(..., help="CSS rule text to add"),
) -> None:
    """Add a new CSS rule to a stylesheet."""
    result = _run_async(_css_direct(url, lambda b: b.css_add_rule(stylesheet_id, rule_text)))
    _echo(f"Rule added with ID: {result}")


@css_app.command("create-stylesheet")
def css_create_stylesheet(
    url: str = typer.Argument(..., help="URL to navigate to"),
    frame_id: str = typer.Option(..., "--frame-id", help="Frame ID"),
) -> None:
    """Create a new stylesheet in the given frame."""
    result = _run_async(_css_direct(url, lambda b: b.css_create_style_sheet(frame_id)))
    _echo(f"Stylesheet created with ID: {result}")


@css_app.command("media-queries")
def css_media_queries(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get all media queries in the current page."""
    result = _run_async(_css_direct(url, lambda b: b.css_get_media_queries()))
    if result is None:
        return
    _write_json_output(result, output, "media queries")


@css_app.command("stylesheet-text")
def css_stylesheet_text(
    url: str = typer.Argument(..., help="URL to navigate to"),
    stylesheet_id: str = typer.Option(..., "--stylesheet-id", help="Stylesheet ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the text content of a stylesheet."""
    result = _run_async(_css_direct(url, lambda b: b.css_get_style_sheet_text(stylesheet_id)))
    if result is None:
        return
    _write_json_output({"text": result}, output, "stylesheet text")


@css_app.command("set-stylesheet-text")
def css_set_stylesheet_text(
    url: str = typer.Argument(..., help="URL to navigate to"),
    stylesheet_id: str = typer.Option(..., "--stylesheet-id", help="Stylesheet ID"),
    text: str = typer.Argument(..., help="New stylesheet text content"),
) -> None:
    """Set the text content of a stylesheet."""
    _run_async(_css_direct(url, lambda b: b.css_set_style_sheet_text(stylesheet_id, text)))
    _echo("Stylesheet text updated")


@css_app.command("set-selector")
def css_set_selector(
    url: str = typer.Argument(..., help="URL to navigate to"),
    stylesheet_id: str = typer.Option(..., "--stylesheet-id", help="Stylesheet ID"),
    rule_id: str = typer.Option(..., "--rule-id", help="Rule ordinal ID"),
    selector: str = typer.Argument(..., help="New selector text"),
) -> None:
    """Set the selector text of a CSS rule."""
    _run_async(
        _css_direct(url, lambda b: b.css_set_rule_selector(stylesheet_id, rule_id, selector))
    )
    _echo("Selector updated")


@css_app.command("force-pseudo")
def css_force_pseudo(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector for target element"),
    pseudo_states: str = typer.Option(
        ..., "--states", help="Comma-separated pseudo states (e.g. hover,focus)"
    ),
) -> None:
    """Force a pseudo state on an element."""
    states = [s.strip() for s in pseudo_states.split(",")]

    async def _action(b: Any) -> None:
        node_id = await _resolve_node_id(b, selector)
        await b.css_force_pseudo_state(node_id, states)

    _run_async(_css_direct(url, _action))
    _echo(f"Pseudo state forced: {states}")


@css_app.command("rule-usage-start")
def css_rule_usage_start(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Start tracking CSS rule usage."""
    _run_async(_css_direct(url, lambda b: b.css_start_rule_usage_tracking()))
    _echo("Rule usage tracking started")


@css_app.command("rule-usage-stop")
def css_rule_usage_stop(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Stop tracking CSS rule usage."""
    _run_async(_css_direct(url, lambda b: b.css_stop_rule_usage_tracking()))
    _echo("Rule usage tracking stopped")


@css_app.command("coverage-delta")
def css_coverage_delta(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get CSS coverage delta."""
    result = _run_async(_css_direct(url, lambda b: b.css_take_coverage_delta()))
    if result is None:
        return
    _write_json_output(result, output, "coverage delta")


@css_app.command("collect-class-names")
def css_collect_class_names(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Collect class names from the subtree of a node by ID."""
    result = _run_async(_css_direct(url, lambda b: b.css_collect_class_names(node_id)))
    if result is None:
        return
    _write_json_output(result, output, "class names")


@css_app.command("disable")
def css_disable(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the CSS domain."""
    _run_async(_css_direct(url, lambda b: b.css_disable()))
    _echo("CSS domain disabled")


@css_app.command("enable")
def css_enable(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the CSS domain."""
    _run_async(_css_direct(url, lambda b: b.css_enable()))
    _echo("CSS domain enabled")


@css_app.command("force-starting-style")
def css_force_starting_style(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    starting_style_id: str = typer.Argument(..., help="Starting style ID (JSON)"),
) -> None:
    """Force a starting style for a node."""
    import json

    style_id = _safe_json_loads(starting_style_id, "starting_style_id")
    _run_async(_css_direct(url, lambda b: b.css_force_starting_style(node_id, style_id)))
    _echo(f"Starting style forced for node {node_id}")


@css_app.command("animated-styles")
def css_animated_styles(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get animated styles for a node by ID."""
    result = _run_async(_css_direct(url, lambda b: b.css_get_animated_styles_for_node(node_id)))
    if result is None:
        return
    _write_json_output(result, output, "animated styles")


@css_app.command("computed-style-for-node")
def css_computed_style_for_node(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get computed style for a node by ID."""
    result = _run_async(_css_direct(url, lambda b: b.css_get_computed_style_for_node(node_id)))
    if result is None:
        return
    _write_json_output(result, output, "computed style")


@css_app.command("environment-variables")
def css_environment_variables(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get environment variables for the CSS domain."""
    result = _run_async(_css_direct(url, lambda b: b.css_get_environment_variables()))
    if result is None:
        return
    _write_json_output(result, output, "environment variables")


@css_app.command("inline-styles")
def css_inline_styles(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get inline styles for a node by ID."""
    result = _run_async(_css_direct(url, lambda b: b.css_get_inline_styles(node_id)))
    if result is None:
        return
    _write_json_output(result, output, "inline styles")


@css_app.command("inline-styles-for-node")
def css_inline_styles_for_node(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get inline styles for a node by ID (alias)."""
    result = _run_async(_css_direct(url, lambda b: b.css_get_inline_styles_for_node(node_id)))
    if result is None:
        return
    _write_json_output(result, output, "inline styles")


@css_app.command("layers-for-node")
def css_layers_for_node(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get CSS layers for a node by ID."""
    result = _run_async(_css_direct(url, lambda b: b.css_get_layers_for_node(node_id)))
    if result is None:
        return
    _write_json_output(result, output, "layers")


@css_app.command("location-for-selector")
def css_location_for_selector(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Argument(..., help="CSS selector"),
    stylesheet_id: str = typer.Argument(..., help="Stylesheet ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the location of a CSS selector in a stylesheet."""
    result = _run_async(
        _css_direct(url, lambda b: b.css_get_location_for_selector(selector, stylesheet_id))
    )
    if result is None:
        return
    _write_json_output(result, output, "location")


@css_app.command("longhand-properties")
def css_longhand_properties(
    url: str = typer.Argument(..., help="URL to navigate to"),
    shorthand_id: str = typer.Argument(..., help="Shorthand ID (JSON)"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get longhand properties for a shorthand property."""
    import json

    sid = _safe_json_loads(shorthand_id, "shorthand_id")
    result = _run_async(_css_direct(url, lambda b: b.css_get_longhand_properties(sid)))
    if result is None:
        return
    _write_json_output(result, output, "longhand properties")


@css_app.command("matched-styles")
def css_matched_styles(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get matched styles for a node by ID."""
    result = _run_async(_css_direct(url, lambda b: b.css_get_matched_styles_for_node(node_id)))
    if result is None:
        return
    _write_json_output(result, output, "matched styles")


@css_app.command("platform-fonts")
def css_platform_fonts(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get platform fonts for a node by ID."""
    result = _run_async(_css_direct(url, lambda b: b.css_get_platform_fonts_for_node(node_id)))
    if result is None:
        return
    _write_json_output(result, output, "platform fonts")


@css_app.command("stylesheet-text-by-id")
def css_stylesheet_text_by_id(
    url: str = typer.Argument(..., help="URL to navigate to"),
    stylesheet_id: str = typer.Argument(..., help="Stylesheet ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the text content of a stylesheet by ID."""
    result = _run_async(_css_direct(url, lambda b: b.css_get_stylesheet_text(stylesheet_id)))
    if result is None:
        return
    _write_json_output({"text": result}, output, "stylesheet text")


@css_app.command("resolve-values")
def css_resolve_values(
    url: str = typer.Argument(..., help="URL to navigate to"),
    values: str = typer.Argument(..., help="CSS values (JSON array)"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Resolve CSS values."""
    import json

    vals = _safe_json_loads(values, "values")
    result = _run_async(_css_direct(url, lambda b: b.css_resolve_values(vals)))
    if result is None:
        return
    _write_json_output(result, output, "resolved values")


@css_app.command("set-container-query")
def css_set_container_query(
    url: str = typer.Argument(..., help="URL to navigate to"),
    stylesheet_id: str = typer.Argument(..., help="Stylesheet ID"),
    container_query_id: str = typer.Argument(..., help="Container query ID (JSON)"),
    text: str = typer.Argument(..., help="Condition text"),
) -> None:
    """Set the condition text of a container query."""
    import json

    cqid = _safe_json_loads(container_query_id, "container_query_id")
    _run_async(
        _css_direct(
            url, lambda b: b.css_set_container_query_condition_text(stylesheet_id, cqid, text)
        )
    )
    _echo("Container query condition text updated")


@css_app.command("set-effective-property")
def css_set_effective_property(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    property_name: str = typer.Argument(..., help="Property name"),
    value: str = typer.Argument(..., help="Property value"),
) -> None:
    """Set the effective property value for a node."""
    _run_async(
        _css_direct(
            url,
            lambda b: b.css_set_effective_property_value_for_node(node_id, property_name, value),
        )
    )
    _echo(f"Effective property set: {property_name}={value}")


@css_app.command("set-keyframe-key")
def css_set_keyframe_key(
    url: str = typer.Argument(..., help="URL to navigate to"),
    stylesheet_id: str = typer.Argument(..., help="Stylesheet ID"),
    keyframe_id: str = typer.Argument(..., help="Keyframe ID (JSON)"),
    key_text: str = typer.Argument(..., help="Key text"),
) -> None:
    """Set the key text of a keyframe rule."""
    import json

    kfid = _safe_json_loads(keyframe_id, "keyframe_id")
    _run_async(_css_direct(url, lambda b: b.css_set_keyframe_key(stylesheet_id, kfid, key_text)))
    _echo("Keyframe key updated")


@css_app.command("set-local-fonts")
def css_set_local_fonts(
    url: str = typer.Argument(..., help="URL to navigate to"),
    enabled: bool = typer.Argument(..., help="Enable or disable local fonts"),
) -> None:
    """Enable or disable local fonts."""
    _run_async(_css_direct(url, lambda b: b.css_set_local_fonts_enabled(enabled)))
    _echo(f"Local fonts {'enabled' if enabled else 'disabled'}")


@css_app.command("set-navigation-text")
def css_set_navigation_text(
    url: str = typer.Argument(..., help="URL to navigate to"),
    stylesheet_id: str = typer.Argument(..., help="Stylesheet ID"),
    navigation_id: str = typer.Argument(..., help="Navigation ID (JSON)"),
    text: str = typer.Argument(..., help="Navigation text"),
) -> None:
    """Set the text of a navigation rule."""
    import json

    nav_id = _safe_json_loads(navigation_id, "navigation_id")
    _run_async(_css_direct(url, lambda b: b.css_set_navigation_text(stylesheet_id, nav_id, text)))
    _echo("Navigation text updated")


@css_app.command("set-property-rule-name")
def css_set_property_rule_name(
    url: str = typer.Argument(..., help="URL to navigate to"),
    stylesheet_id: str = typer.Argument(..., help="Stylesheet ID"),
    property_rule_id: str = typer.Argument(..., help="Property rule ID (JSON)"),
    name: str = typer.Argument(..., help="Property name"),
) -> None:
    """Set the property name of a property rule."""
    import json

    prid = _safe_json_loads(property_rule_id, "property_rule_id")
    _run_async(
        _css_direct(url, lambda b: b.css_set_property_rule_property_name(stylesheet_id, prid, name))
    )
    _echo("Property rule name updated")


@css_app.command("set-rule-style")
def css_set_rule_style(
    url: str = typer.Argument(..., help="URL to navigate to"),
    stylesheet_id: str = typer.Argument(..., help="Stylesheet ID"),
    rule_id: str = typer.Argument(..., help="Rule ID (JSON)"),
    style_text: str = typer.Argument(..., help="Style text"),
) -> None:
    """Set the style text of a CSS rule."""
    import json

    rid = _safe_json_loads(rule_id, "rule_id")
    _run_async(_css_direct(url, lambda b: b.css_set_rule_style(stylesheet_id, rid, style_text)))
    _echo("Rule style updated")


@css_app.command("set-scope-text")
def css_set_scope_text(
    url: str = typer.Argument(..., help="URL to navigate to"),
    stylesheet_id: str = typer.Argument(..., help="Stylesheet ID"),
    scope_id: str = typer.Argument(..., help="Scope ID (JSON)"),
    text: str = typer.Argument(..., help="Scope text"),
) -> None:
    """Set the text of a scope rule."""
    import json

    sid = _safe_json_loads(scope_id, "scope_id")
    _run_async(_css_direct(url, lambda b: b.css_set_scope_text(stylesheet_id, sid, text)))
    _echo("Scope text updated")


@css_app.command("set-style-sheet-text")
def css_set_style_sheet_text(
    url: str = typer.Argument(..., help="URL to navigate to"),
    stylesheet_id: str = typer.Argument(..., help="Stylesheet ID"),
    text: str = typer.Argument(..., help="Stylesheet text"),
) -> None:
    """Set the text content of a stylesheet by ID."""
    _run_async(_css_direct(url, lambda b: b.css_set_style_sheet_text(stylesheet_id, text)))
    _echo("Stylesheet text updated")


@css_app.command("set-style-text")
def css_set_style_text(
    url: str = typer.Argument(..., help="URL to navigate to"),
    edits: str = typer.Argument(..., help="Style edits (JSON array)"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Set style texts for multiple edits."""
    import json

    ed = _safe_json_loads(edits, "edits")
    result = _run_async(_css_direct(url, lambda b: b.css_set_style_text(ed)))
    if result is None:
        return
    _write_json_output(result, output, "styles")


@css_app.command("set-style-texts")
def css_set_style_texts(
    url: str = typer.Argument(..., help="URL to navigate to"),
    edits: str = typer.Argument(..., help="Style edits (JSON array)"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Set style texts for multiple edits (batch)."""
    import json

    ed = _safe_json_loads(edits, "edits")
    result = _run_async(_css_direct(url, lambda b: b.css_set_style_texts(ed)))
    if result is None:
        return
    _write_json_output(result, output, "styles")


@css_app.command("set-stylesheet-text")
def css_set_stylesheet_text(
    url: str = typer.Argument(..., help="URL to navigate to"),
    stylesheet_id: str = typer.Argument(..., help="Stylesheet ID"),
    text: str = typer.Argument(..., help="Stylesheet text"),
) -> None:
    """Set the text content of a stylesheet by ID (alias)."""
    _run_async(_css_direct(url, lambda b: b.css_set_stylesheet_text(stylesheet_id, text)))
    _echo("Stylesheet text updated")


@css_app.command("set-supports-text")
def css_set_supports_text(
    url: str = typer.Argument(..., help="URL to navigate to"),
    stylesheet_id: str = typer.Argument(..., help="Stylesheet ID"),
    supports_id: str = typer.Argument(..., help="Supports ID (JSON)"),
    text: str = typer.Argument(..., help="Supports text"),
) -> None:
    """Set the text of a supports rule."""
    import json

    sup_id = _safe_json_loads(supports_id, "supports_id")
    _run_async(_css_direct(url, lambda b: b.css_set_supports_text(stylesheet_id, sup_id, text)))
    _echo("Supports text updated")


@css_app.command("take-computed-style-updates")
def css_take_computed_style_updates(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Take computed style updates."""
    result = _run_async(_css_direct(url, lambda b: b.css_take_computed_style_updates()))
    if result is None:
        return
    _write_json_output(result, output, "computed style updates")


@css_app.command("track-computed-style-updates")
def css_track_computed_style_updates(
    url: str = typer.Argument(..., help="URL to navigate to"),
    track_properties: bool = typer.Option(True, "--track-properties", help="Track properties"),
) -> None:
    """Track computed style updates."""
    _run_async(_css_direct(url, lambda b: b.css_track_computed_style_updates(track_properties)))
    _echo("Computed style tracking started")


@css_app.command("track-computed-style-updates-for-node")
def css_track_computed_style_updates_for_node(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    track_properties: bool = typer.Option(True, "--track-properties", help="Track properties"),
) -> None:
    """Track computed style updates for a specific node."""
    _run_async(
        _css_direct(
            url, lambda b: b.css_track_computed_style_updates_for_node(node_id, track_properties)
        )
    )
    _echo(f"Computed style tracking started for node {node_id}")


async def _css_direct(url: str, action_fn: Any) -> Any:
    """Launch backend, navigate, and run a direct CSS action."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url)
        return await action_fn(backend)
    finally:
        await _close_backend(backend)


async def _resolve_node_id(backend: Any, selector: str) -> int:
    """Resolve a CSS selector to a CDP node ID."""
    await backend.dom_get_document()
    result = await backend.dom_perform_search(selector)
    node_ids = result.get("nodeIds", [])
    if not node_ids:
        raise ElementNotFoundError(selector)
    return int(node_ids[0])


@debug_app.command("breakpoint")
def debug_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    script_url: str = typer.Option(..., "--url", help="Script URL for breakpoint"),
    line: int = typer.Option(..., "--line", help="Line number (0-based)"),
    condition: str | None = typer.Option(None, "--condition", help="Condition expression"),
) -> None:
    """Set a breakpoint by URL and line number."""
    result = _run_async(
        _debug_action(url, "breakpoint", script_url=script_url, line=line, condition=condition)
    )
    if result is None:
        return
    _echo(f"Breakpoint set: {result}")


@debug_app.command("function-breakpoint")
def debug_function_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    function_name: str = typer.Option(..., "--function-name", help="Function name"),
) -> None:
    """Set a breakpoint by function name."""
    result = _run_async(_debug_action(url, "function_breakpoint", function_name=function_name))
    if result is None:
        return
    _echo(f"Breakpoint set: {result}")


@debug_app.command("remove-breakpoint")
def debug_remove_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    breakpoint_id: str = typer.Option(..., "--breakpoint-id", help="Breakpoint ID"),
) -> None:
    """Remove a breakpoint by ID."""
    _run_async(_debug_action(url, "remove_breakpoint", breakpoint_id=breakpoint_id))
    _echo(f"Breakpoint removed: {breakpoint_id}")


@debug_app.command("step-over")
def debug_step_over(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Step over the current statement."""
    _run_async(_debug_action(url, "step_over"))
    _echo("Stepped over")


@debug_app.command("step-into")
def debug_step_into(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Step into the current function call."""
    _run_async(_debug_action(url, "step_into"))
    _echo("Stepped into")


@debug_app.command("step-out")
def debug_step_out(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Step out of the current function."""
    _run_async(_debug_action(url, "step_out"))
    _echo("Stepped out")


@debug_app.command("pause")
def debug_pause(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Pause JavaScript execution."""
    _run_async(_debug_action(url, "pause"))
    _echo("Paused")


@debug_app.command("resume")
def debug_resume(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Resume JavaScript execution."""
    _run_async(_debug_action(url, "resume"))
    _echo("Resumed")


@debug_app.command("listeners")
def debug_listeners(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get event listeners attached to an element."""
    result = _run_async(_debug_action(url, "listeners", selector=selector))
    if result is None:
        return
    _write_json_output(result, output, "listeners")


async def _debug_action(
    url: str,
    action: str,
    script_url: str | None = None,
    line: int | None = None,
    condition: str | None = None,
    function_name: str | None = None,
    breakpoint_id: str | None = None,
    selector: str | None = None,
) -> Any:
    """Execute a debug action on a web page.

    Args:
        url: URL to navigate to.
        action: Debug action ("breakpoint", "function_breakpoint", "remove_breakpoint",
            "step_over", "step_into", "step_out", "pause", "resume", "listeners").
        script_url: Script URL for breakpoint action.
        line: Line number for breakpoint action.
        condition: Condition expression for conditional breakpoints.
        function_name: Function name for function_breakpoint action.
        breakpoint_id: Breakpoint ID for remove_breakpoint action.
        selector: CSS selector for listeners action.

    Returns:
        Result of the debug operation.
    """
    from wavexis.actions.debug import DebugAction, DebugActionParams

    params = DebugActionParams(
        url=url,
        action=action,
        script_url=script_url,
        line=line,
        condition=condition,
        function_name=function_name,
        breakpoint_id=breakpoint_id,
        selector=selector,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        act = DebugAction(params)
        return await act.execute(backend)
    finally:
        await _close_backend(backend)


@debug_app.command("evaluate")
def debug_evaluate(
    url: str = typer.Argument(..., help="URL to navigate to"),
    call_frame_id: str = typer.Option(..., "--frame-id", help="Call frame ID"),
    expression: str = typer.Argument(..., help="JavaScript expression to evaluate"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Evaluate a JavaScript expression in a paused call frame."""
    result = _run_async(
        _debug_direct(url, lambda b: b.debug_evaluate_on_call_frame(call_frame_id, expression))
    )
    if result is None:
        return
    _write_json_output(result, output, "evaluation result")


@debug_app.command("script-source")
def debug_script_source(
    url: str = typer.Argument(..., help="URL to navigate to"),
    script_id: str = typer.Option(..., "--script-id", help="Script ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the source code of a script by ID."""
    result = _run_async(_debug_direct(url, lambda b: b.debug_get_script_source(script_id)))
    if result is None:
        return
    _write_json_output({"source": result}, output, "script source")


@debug_app.command("stack-trace")
def debug_stack_trace(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the current JavaScript stack trace."""
    result = _run_async(_debug_direct(url, lambda b: b.debug_get_stack_trace()))
    if result is None:
        return
    _write_json_output(result, output, "stack trace")


@debug_app.command("search-in-content")
def debug_search_in_content(
    url: str = typer.Argument(..., help="URL to navigate to"),
    script_id: str = typer.Option(..., "--script-id", help="Script ID"),
    query: str = typer.Argument(..., help="Search query"),
    case_sensitive: bool = typer.Option(False, "--case-sensitive", help="Case sensitive search"),
    is_regex: bool = typer.Option(False, "--regex", help="Treat query as regex"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Search for a string in script content."""
    result = _run_async(
        _debug_direct(
            url, lambda b: b.debug_search_in_content(script_id, query, case_sensitive, is_regex)
        )
    )
    if result is None:
        return
    _write_json_output(result, output, "search results")


@debug_app.command("pause-on-exceptions")
def debug_pause_on_exceptions(
    url: str = typer.Argument(..., help="URL to navigate to"),
    state: str = typer.Option("all", "--state", help="Pause mode: none, uncaught, all"),
) -> None:
    """Set pause on exceptions mode."""
    _run_async(_debug_direct(url, lambda b: b.debug_set_pause_on_exceptions(state)))
    _echo(f"Pause on exceptions set to: {state}")


@debug_app.command("breakpoints-active")
def debug_breakpoints_active(
    url: str = typer.Argument(..., help="URL to navigate to"),
    active: bool = typer.Option(True, "--enable/--disable", help="Enable or disable breakpoints"),
) -> None:
    """Enable or disable all breakpoints."""
    _run_async(_debug_direct(url, lambda b: b.debug_set_breakpoints_active(active)))
    _echo(f"Breakpoints {'enabled' if active else 'disabled'}")


@debug_app.command("skip-pauses")
def debug_skip_pauses(
    url: str = typer.Argument(..., help="URL to navigate to"),
    skip: bool = typer.Option(True, "--skip/--no-skip", help="Skip or allow pauses"),
) -> None:
    """Skip all pauses for the duration of the current script."""
    _run_async(_debug_direct(url, lambda b: b.debug_set_skip_all_pauses(skip)))
    _echo(f"Pauses {'skipped' if skip else 'allowed'}")


@debug_app.command("edit-script")
def debug_edit_script(
    url: str = typer.Argument(..., help="URL to navigate to"),
    script_id: str = typer.Option(..., "--script-id", help="Script ID"),
    source: str = typer.Argument(..., help="New script source code"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Edit the source code of a live script."""
    result = _run_async(_debug_direct(url, lambda b: b.debug_set_script_source(script_id, source)))
    if result is None:
        return
    _write_json_output(result, output, "edit result")


@debug_app.command("continue-to")
def debug_continue_to(
    url: str = typer.Argument(..., help="URL to navigate to"),
    script_url: str = typer.Option(..., "--script-url", help="Script URL"),
    line: int = typer.Option(..., "--line", help="Line number (0-based)"),
    column: int = typer.Option(0, "--column", help="Column number (0-based)"),
) -> None:
    """Continue execution until a specific location is reached."""
    _run_async(_debug_direct(url, lambda b: b.debug_continue_to_location(script_url, line, column)))
    _echo(f"Continuing to {script_url}:{line}:{column}")


@debug_app.command("dbg-disable")
def debug_dbg_disable(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the Debugger domain."""
    _run_async(_debug_direct(url, lambda b: b.debug_disable()))
    _echo("Debugger domain disabled")


@debug_app.command("dbg-enable")
def debug_dbg_enable(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the Debugger domain."""
    _run_async(_debug_direct(url, lambda b: b.debug_enable()))
    _echo("Debugger domain enabled")


@debug_app.command("disassemble-wasm")
def debug_disassemble_wasm(
    url: str = typer.Argument(..., help="URL to navigate to"),
    script_id: str = typer.Option(..., "--script-id", help="Script ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Disassemble a WASM module by script ID."""
    result = _run_async(_debug_direct(url, lambda b: b.debug_disassemble_wasm_module(script_id)))
    if result is None:
        return
    _write_json_output(result, output, "WASM disassembly")


@debug_app.command("wasm-bytecode")
def debug_wasm_bytecode(
    url: str = typer.Argument(..., help="URL to navigate to"),
    script_id: str = typer.Option(..., "--script-id", help="Script ID"),
    offset: int = typer.Option(..., "--offset", help="Bytecode offset"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get WASM bytecode for a script by ID and offset."""
    result = _run_async(_debug_direct(url, lambda b: b.debug_get_wasm_bytecode(script_id, offset)))
    if result is None:
        return
    _write_json_output(result, output, "WASM bytecode")


@debug_app.command("wasm-disassembly-chunk")
def debug_wasm_disassembly_chunk(
    url: str = typer.Argument(..., help="URL to navigate to"),
    disassembly_id: str = typer.Option(..., "--disassembly-id", help="Disassembly ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the next chunk of a WASM disassembly."""
    result = _run_async(
        _debug_direct(url, lambda b: b.debug_next_wasm_disassembly_chunk(disassembly_id))
    )
    if result is None:
        return
    _write_json_output(result, output, "WASM disassembly chunk")


@debug_app.command("dbg-pause")
def debug_dbg_pause(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Pause JavaScript execution (Debugger domain)."""
    _run_async(_debug_direct(url, lambda b: b.debug_pause()))
    _echo("Paused")


@debug_app.command("pause-on-async-call")
def debug_pause_on_async_call(
    url: str = typer.Argument(..., help="URL to navigate to"),
    operation: str = typer.Option(..., "--operation", help="Async call operation"),
) -> None:
    """Pause on an async call operation."""
    _run_async(_debug_direct(url, lambda b: b.debug_pause_on_async_call(operation)))
    _echo(f"Paused on async call: {operation}")


@debug_app.command("dbg-remove-breakpoint")
def debug_dbg_remove_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    breakpoint_id: str = typer.Option(..., "--breakpoint-id", help="Breakpoint ID"),
) -> None:
    """Remove a breakpoint by ID (Debugger domain)."""
    _run_async(_debug_direct(url, lambda b: b.debug_remove_breakpoint(breakpoint_id)))
    _echo(f"Breakpoint removed: {breakpoint_id}")


@debug_app.command("restart-frame")
def debug_restart_frame(
    url: str = typer.Argument(..., help="URL to navigate to"),
    call_frame_id: str = typer.Option(..., "--frame-id", help="Call frame ID"),
) -> None:
    """Restart a call frame by ID."""
    _run_async(_debug_direct(url, lambda b: b.debug_restart_frame(call_frame_id)))
    _echo(f"Frame restarted: {call_frame_id}")


@debug_app.command("dbg-resume")
def debug_dbg_resume(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Resume JavaScript execution (Debugger domain)."""
    _run_async(_debug_direct(url, lambda b: b.debug_resume()))
    _echo("Resumed")


@debug_app.command("async-call-stack-depth")
def debug_async_call_stack_depth(
    url: str = typer.Argument(..., help="URL to navigate to"),
    depth: int = typer.Option(..., "--depth", help="Async call stack depth"),
) -> None:
    """Set the async call stack depth."""
    _run_async(_debug_direct(url, lambda b: b.debug_set_async_call_stack_depth(depth)))
    _echo(f"Async call stack depth set to: {depth}")


@debug_app.command("blackbox-contexts")
def debug_blackbox_contexts(
    url: str = typer.Argument(..., help="URL to navigate to"),
    unique_ids: str = typer.Argument(..., help="Unique IDs (JSON array)"),
) -> None:
    """Set blackboxed execution contexts by unique IDs."""
    import json

    ids = _safe_json_loads(unique_ids, "unique_ids")
    _run_async(_debug_direct(url, lambda b: b.debug_set_blackbox_execution_contexts(ids)))
    _echo("Blackboxed execution contexts set")


@debug_app.command("blackbox-patterns")
def debug_blackbox_patterns(
    url: str = typer.Argument(..., help="URL to navigate to"),
    patterns: str = typer.Argument(..., help="Patterns (JSON array)"),
) -> None:
    """Set blackbox patterns for script URLs."""
    import json

    pats = _safe_json_loads(patterns, "patterns")
    _run_async(_debug_direct(url, lambda b: b.debug_set_blackbox_patterns(pats)))
    _echo("Blackbox patterns set")


@debug_app.command("blackboxed-ranges")
def debug_blackboxed_ranges(
    url: str = typer.Argument(..., help="URL to navigate to"),
    script_id: str = typer.Option(..., "--script-id", help="Script ID"),
    positions: str = typer.Argument(..., help="Positions (JSON array)"),
) -> None:
    """Set blackboxed ranges for a script."""
    import json

    pos = _safe_json_loads(positions, "positions")
    _run_async(_debug_direct(url, lambda b: b.debug_set_blackboxed_ranges(script_id, pos)))
    _echo("Blackboxed ranges set")


@debug_app.command("breakpoint-raw")
def debug_breakpoint_raw(
    url: str = typer.Argument(..., help="URL to navigate to"),
    location: str = typer.Argument(..., help="Location (JSON object)"),
    condition: str = typer.Option("", "--condition", help="Optional condition expression"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Set a breakpoint at a raw location in a script."""
    import json

    loc = _safe_json_loads(location, "location")
    cond = condition if condition else None
    result = _run_async(_debug_direct(url, lambda b: b.debug_set_breakpoint_raw(loc, cond)))
    if result is None:
        return
    _write_json_output(result, output, "breakpoint")


@debug_app.command("breakpoint-by-url")
def debug_breakpoint_by_url(
    url: str = typer.Argument(..., help="URL to navigate to"),
    script_url: str = typer.Option(..., "--script-url", help="Script URL"),
    line: int = typer.Option(..., "--line", help="Line number (0-based)"),
    column: int = typer.Option(0, "--column", help="Column number (0-based)"),
    condition: str = typer.Option("", "--condition", help="Optional condition expression"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Set a breakpoint by URL and line number."""
    cond = condition if condition else None
    result = _run_async(
        _debug_direct(url, lambda b: b.debug_set_breakpoint_by_url(script_url, line, column, cond))
    )
    if result is None:
        return
    _write_json_output(result, output, "breakpoint")


@debug_app.command("breakpoint-on-function-call")
def debug_breakpoint_on_function_call(
    url: str = typer.Argument(..., help="URL to navigate to"),
    object_id: str = typer.Option(..., "--object-id", help="Remote object ID"),
    condition: str = typer.Option("", "--condition", help="Optional condition expression"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Set a breakpoint on a function call by object ID."""
    cond = condition if condition else None
    result = _run_async(
        _debug_direct(url, lambda b: b.debug_set_breakpoint_on_function_call(object_id, cond))
    )
    if result is None:
        return
    _write_json_output(result, output, "breakpoint")


@debug_app.command("instrumentation-breakpoint")
def debug_instrumentation_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    instrumentation: str = typer.Option(..., "--instrumentation", help="Instrumentation name"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Set an instrumentation breakpoint."""
    result = _run_async(
        _debug_direct(url, lambda b: b.debug_set_instrumentation_breakpoint(instrumentation))
    )
    if result is None:
        return
    _write_json_output(result, output, "breakpoint")


@debug_app.command("set-return-value")
def debug_set_return_value(
    url: str = typer.Argument(..., help="URL to navigate to"),
    new_value: str = typer.Argument(..., help="New return value (JSON)"),
) -> None:
    """Set the return value of the current call frame."""
    import json

    val = _safe_json_loads(new_value, "new_value")
    _run_async(_debug_direct(url, lambda b: b.debug_set_return_value(val)))
    _echo("Return value set")


@debug_app.command("set-variable-value")
def debug_set_variable_value(
    url: str = typer.Argument(..., help="URL to navigate to"),
    call_frame_id: str = typer.Option(..., "--frame-id", help="Call frame ID"),
    scope_number: int = typer.Option(..., "--scope", help="Scope number"),
    variable_name: str = typer.Option(..., "--variable", help="Variable name"),
    new_value: str = typer.Argument(..., help="New value (JSON)"),
) -> None:
    """Set a variable value in a scope of a call frame."""
    import json

    val = _safe_json_loads(new_value, "new_value")
    _run_async(
        _debug_direct(
            url,
            lambda b: b.debug_set_variable_value(call_frame_id, scope_number, variable_name, val),
        )
    )
    _echo("Variable value set")


async def _debug_direct(url: str, action_fn: Any) -> Any:
    """Launch backend, navigate, and run a direct debug action."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url)
        return await action_fn(backend)
    finally:
        await _close_backend(backend)


dom_debugger_app = typer.Typer(
    help="DOMDebugger commands (DOM breakpoints, event listener breakpoints, XHR breakpoints)"
)
app.add_typer(dom_debugger_app, name="dom-debugger")


@dom_debugger_app.command("get-event-listeners")
def dom_debugger_get_event_listeners(
    url: str = typer.Argument(..., help="URL to navigate to"),
    object_id: str = typer.Argument(..., help="Remote object ID"),
    depth: int = typer.Option(0, "--depth", help="Depth for shadow DOM traversal"),
    pierce: bool = typer.Option(False, "--pierce", help="Whether to pierce shadow DOM"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get event listeners for an object by its remote object ID."""
    result = _run_async(
        _dom_debugger_direct(
            url, "get_event_listeners", object_id=object_id, depth=depth, pierce=pierce
        )
    )
    if result is None:
        return
    _write_json_output(result, output, "event listeners")


@dom_debugger_app.command("remove-dom-breakpoint")
def dom_debugger_remove_dom_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    type: str = typer.Argument(
        ..., help="Breakpoint type (subtree-modified, node-removed, attribute-modified)"
    ),
) -> None:
    """Remove a DOM breakpoint from a node by ID."""
    _run_async(_dom_debugger_direct(url, "remove_dom_breakpoint", node_id=node_id, type=type))
    _echo(f"DOM breakpoint removed: node {node_id}, type {type}")


@dom_debugger_app.command("remove-event-listener-breakpoint")
def dom_debugger_remove_event_listener_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    event_name: str = typer.Argument(..., help="Event name (e.g. click, load)"),
    target_name: str = typer.Option(None, "--target-name", help="Target name filter"),
) -> None:
    """Remove an event listener breakpoint."""
    _run_async(
        _dom_debugger_direct(
            url, "remove_event_listener_breakpoint", event_name=event_name, target_name=target_name
        )
    )
    _echo(f"Event listener breakpoint removed: {event_name}")


@dom_debugger_app.command("remove-instrumentation-breakpoint")
def dom_debugger_remove_instrumentation_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    event_name: str = typer.Argument(..., help="Instrumentation event name"),
) -> None:
    """Remove an instrumentation breakpoint."""
    _run_async(
        _dom_debugger_direct(url, "remove_instrumentation_breakpoint", event_name=event_name)
    )
    _echo(f"Instrumentation breakpoint removed: {event_name}")


@dom_debugger_app.command("remove-xhr-breakpoint")
def dom_debugger_remove_xhr_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    url_substring: str = typer.Argument(..., help="URL substring to stop breaking on"),
) -> None:
    """Remove an XHR breakpoint for a URL substring."""
    _run_async(_dom_debugger_direct(url, "remove_xhr_breakpoint", url_substring=url_substring))
    _echo(f"XHR breakpoint removed: {url_substring}")


@dom_debugger_app.command("set-break-on-csp-violation")
def dom_debugger_set_break_on_csp_violation(
    url: str = typer.Argument(..., help="URL to navigate to"),
    enabled: bool = typer.Option(
        True, "--enable/--disable", help="Enable or disable CSP violation breakpoints"
    ),
) -> None:
    """Set whether to break on CSP violations."""
    _run_async(_dom_debugger_direct(url, "set_break_on_csp_violation", enabled=enabled))
    _echo(f"CSP violation breakpoints {'enabled' if enabled else 'disabled'}")


@dom_debugger_app.command("set-dom-breakpoint")
def dom_debugger_set_dom_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    type: str = typer.Argument(
        ..., help="Breakpoint type (subtree-modified, node-removed, attribute-modified)"
    ),
) -> None:
    """Set a DOM breakpoint on a node by ID."""
    _run_async(_dom_debugger_direct(url, "set_dom_breakpoint", node_id=node_id, type=type))
    _echo(f"DOM breakpoint set: node {node_id}, type {type}")


@dom_debugger_app.command("set-event-listener-breakpoint")
def dom_debugger_set_event_listener_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    event_name: str = typer.Argument(..., help="Event name (e.g. click, load)"),
    target_name: str = typer.Option(None, "--target-name", help="Target name filter"),
) -> None:
    """Set an event listener breakpoint."""
    _run_async(
        _dom_debugger_direct(
            url, "set_event_listener_breakpoint", event_name=event_name, target_name=target_name
        )
    )
    _echo(f"Event listener breakpoint set: {event_name}")


@dom_debugger_app.command("set-instrumentation-breakpoint")
def dom_debugger_set_instrumentation_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    event_name: str = typer.Argument(..., help="Instrumentation event name"),
) -> None:
    """Set an instrumentation breakpoint."""
    _run_async(_dom_debugger_direct(url, "set_instrumentation_breakpoint", event_name=event_name))
    _echo(f"Instrumentation breakpoint set: {event_name}")


@dom_debugger_app.command("set-xhr-breakpoint")
def dom_debugger_set_xhr_breakpoint(
    url: str = typer.Argument(..., help="URL to navigate to"),
    url_substring: str = typer.Argument(..., help="URL substring to break on"),
) -> None:
    """Set an XHR breakpoint for a URL substring."""
    _run_async(_dom_debugger_direct(url, "set_xhr_breakpoint", url_substring=url_substring))
    _echo(f"XHR breakpoint set: {url_substring}")


async def _dom_debugger_direct(url: str, action: str, **kwargs: Any) -> Any:
    """Launch backend, navigate, and run a DOMDebugger action."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url)
        if action == "get_event_listeners":
            return await backend.dom_debugger_get_event_listeners(
                kwargs["object_id"], kwargs["depth"], kwargs["pierce"]
            )
        if action == "remove_dom_breakpoint":
            await backend.dom_debugger_remove_dom_breakpoint(kwargs["node_id"], kwargs["type"])
            return None
        if action == "remove_event_listener_breakpoint":
            await backend.dom_debugger_remove_event_listener_breakpoint(
                kwargs["event_name"], kwargs.get("target_name")
            )
            return None
        if action == "remove_instrumentation_breakpoint":
            await backend.dom_debugger_remove_instrumentation_breakpoint(kwargs["event_name"])
            return None
        if action == "remove_xhr_breakpoint":
            await backend.dom_debugger_remove_xhr_breakpoint(kwargs["url_substring"])
            return None
        if action == "set_break_on_csp_violation":
            await backend.dom_debugger_set_break_on_csp_violation(kwargs["enabled"])
            return None
        if action == "set_dom_breakpoint":
            await backend.dom_debugger_set_dom_breakpoint(kwargs["node_id"], kwargs["type"])
            return None
        if action == "set_event_listener_breakpoint":
            await backend.dom_debugger_set_event_listener_breakpoint(
                kwargs["event_name"], kwargs.get("target_name")
            )
            return None
        if action == "set_instrumentation_breakpoint":
            await backend.dom_debugger_set_instrumentation_breakpoint(kwargs["event_name"])
            return None
        if action == "set_xhr_breakpoint":
            await backend.dom_debugger_set_xhr_breakpoint(kwargs["url_substring"])
            return None
        raise ValueError(f"Unknown DOMDebugger action: {action}")
    finally:
        await _close_backend(backend)


@overlay_app.command("highlight")
def overlay_highlight(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector"),
    color: str = typer.Option("rgba(255,0,0,0.5)", "--color", help="RGBA color"),
) -> None:
    """Highlight an element with a colored overlay."""
    _run_async(_overlay_action(url, "highlight", selector=selector, color=color))
    _echo(f"Highlighted: {selector}")


@overlay_app.command("clear")
def overlay_clear(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Clear all highlight overlays."""
    _run_async(_overlay_action(url, "clear"))
    _echo("Overlay cleared")


async def _overlay_action(
    url: str,
    action: str,
    selector: str | None = None,
    color: str = "rgba(255,0,0,0.5)",
) -> None:
    """Execute an overlay action on a web page.

    Args:
        url: URL to navigate to.
        action: Overlay action ("highlight" or "clear").
        selector: CSS selector for highlight action.
        color: RGBA color for highlight overlay.
    """
    from wavexis.actions.overlay import OverlayAction, OverlayParams

    params = OverlayParams(
        url=url,
        action=action,
        selector=selector,
        color=color,
        wait=WaitStrategy(strategy="load"),
    )
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        act = OverlayAction(params)
        await act.execute(backend)
    finally:
        await _close_backend(backend)


@overlay_app.command("enable")
def overlay_enable(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the overlay domain."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_enable()))
    _echo("Overlay enabled")


@overlay_app.command("disable")
def overlay_disable(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the overlay domain."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_disable()))
    _echo("Overlay disabled")


@overlay_app.command("highlight-node")
def overlay_highlight_node(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Option(..., "--node-id", help="CDP node ID"),
    color: str = typer.Option("rgba(255,0,0,0.5)", "--color", help="RGBA color"),
) -> None:
    """Highlight a DOM node by node ID."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_highlight_node(node_id, color)))
    _echo(f"Highlighted node: {node_id}")


@overlay_app.command("highlight-quad")
def overlay_highlight_quad(
    url: str = typer.Argument(..., help="URL to navigate to"),
    quad: str = typer.Option(
        ..., "--quad", help="Quad coordinates as JSON array [x1,y1,x2,y2,...]"
    ),
) -> None:
    """Highlight a quad region on the page."""
    import json

    coords = _safe_json_loads(quad, "quad")
    _run_async(_overlay_direct(url, lambda b: b.overlay_highlight_quad(coords)))
    _echo("Highlighted quad")


@overlay_app.command("highlight-rect")
def overlay_highlight_rect(
    url: str = typer.Argument(..., help="URL to navigate to"),
    x: float = typer.Option(..., "--x", help="X coordinate"),
    y: float = typer.Option(..., "--y", help="Y coordinate"),
    width: float = typer.Option(..., "--width", help="Width"),
    height: float = typer.Option(..., "--height", help="Height"),
) -> None:
    """Highlight a rectangular region on the page."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_highlight_rect(x, y, width, height)))
    _echo(f"Highlighted rect: ({x},{y}) {width}x{height}")


@overlay_app.command("inspect-mode")
def overlay_inspect_mode(
    url: str = typer.Argument(..., help="URL to navigate to"),
    mode: str = typer.Option("searchForNode", "--mode", help="Inspect mode"),
) -> None:
    """Set the inspect mode for element selection."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_set_inspect_mode(mode)))
    _echo(f"Inspect mode set: {mode}")


@overlay_app.command("fps")
def overlay_fps(
    url: str = typer.Argument(..., help="URL to navigate to"),
    show: bool = typer.Option(True, "--show/--hide", help="Show or hide FPS counter"),
) -> None:
    """Show or hide the FPS counter overlay."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_set_show_fps_counter(show)))
    _echo(f"FPS counter {'shown' if show else 'hidden'}")


@overlay_app.command("paint-rects")
def overlay_paint_rects(
    url: str = typer.Argument(..., help="URL to navigate to"),
    show: bool = typer.Option(True, "--show/--hide", help="Show or hide paint rects"),
) -> None:
    """Show or hide paint rectangles overlay."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_set_show_paint_rects(show)))
    _echo(f"Paint rects {'shown' if show else 'hidden'}")


@overlay_app.command("debug-borders")
def overlay_debug_borders(
    url: str = typer.Argument(..., help="URL to navigate to"),
    show: bool = typer.Option(True, "--show/--hide", help="Show or hide debug borders"),
) -> None:
    """Show or hide debug borders overlay."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_set_show_debug_borders(show)))
    _echo(f"Debug borders {'shown' if show else 'hidden'}")


@overlay_app.command("ad-highlights")
def overlay_ad_highlights(
    url: str = typer.Argument(..., help="URL to navigate to"),
    show: bool = typer.Option(True, "--show/--hide", help="Show or hide ad highlights"),
) -> None:
    """Show or hide ad highlights overlay."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_set_show_ad_highlights(show)))
    _echo(f"Ad highlights {'shown' if show else 'hidden'}")


@overlay_app.command("grid-highlight-test")
def overlay_grid_highlight_test(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Option(..., "--node-id", help="CDP node ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get grid highlight objects for testing."""
    result = _run_async(
        _overlay_direct(url, lambda b: b.overlay_get_grid_highlight_objects_for_test(node_id))
    )
    _write_json_output(result, output, "highlights")


@overlay_app.command("highlight-test")
def overlay_highlight_test(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Option(..., "--node-id", help="CDP node ID"),
    include_distance: bool = typer.Option(
        False, "--include-distance", help="Include distance info"
    ),
    include_style: bool = typer.Option(False, "--include-style", help="Include style info"),
    color_format: str = typer.Option("hex", "--color-format", help="Color format (hex, rgb, hsl)"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get highlight object for testing."""
    result = _run_async(
        _overlay_direct(
            url,
            lambda b: b.overlay_get_highlight_object_for_test(
                node_id, include_distance, include_style, color_format
            ),
        )
    )
    _write_json_output(result, output, "highlight")


@overlay_app.command("source-order-highlight-test")
def overlay_source_order_highlight_test(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Option(..., "--node-id", help="CDP node ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get source order highlight object for testing."""
    result = _run_async(
        _overlay_direct(
            url, lambda b: b.overlay_get_source_order_highlight_object_for_test(node_id)
        )
    )
    _write_json_output(result, output, "sourceOrderHighlight")


@overlay_app.command("hide-highlight")
def overlay_hide_highlight(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Hide any highlight overlay."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_hide_highlight()))
    _echo("Highlight hidden")


@overlay_app.command("highlight-source-order")
def overlay_highlight_source_order(
    url: str = typer.Argument(..., help="URL to navigate to"),
    config: str = typer.Option(..., "--config", help="Source order config as JSON"),
) -> None:
    """Highlight the source order of a node."""
    import json

    cfg = _safe_json_loads(config, "config")
    _run_async(_overlay_direct(url, lambda b: b.overlay_highlight_source_order(cfg)))
    _echo("Source order highlighted")


@overlay_app.command("paused-debugger-message")
def overlay_paused_debugger_message(
    url: str = typer.Argument(..., help="URL to navigate to"),
    message: str = typer.Option("", "--message", help="Debugger pause message"),
) -> None:
    """Set the paused in debugger message."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_set_paused_in_debugger_message(message)))
    _echo(f"Debugger message set: {message!r}")


@overlay_app.command("container-query-overlays")
def overlay_container_query_overlays(
    url: str = typer.Argument(..., help="URL to navigate to"),
    show: bool = typer.Option(True, "--show/--hide", help="Show or hide container query overlays"),
) -> None:
    """Show or hide container query overlays."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_set_show_container_query_overlays(show)))
    _echo(f"Container query overlays {'shown' if show else 'hidden'}")


@overlay_app.command("display-cutout")
def overlay_display_cutout(
    url: str = typer.Argument(..., help="URL to navigate to"),
    show: bool = typer.Option(True, "--show/--hide", help="Show or hide display cutout"),
) -> None:
    """Show or hide display cutout overlay."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_set_show_display_cutout(show)))
    _echo(f"Display cutout {'shown' if show else 'hidden'}")


@overlay_app.command("flex-overlays")
def overlay_flex_overlays(
    url: str = typer.Argument(..., help="URL to navigate to"),
    show: bool = typer.Option(True, "--show/--hide", help="Show or hide flex overlays"),
) -> None:
    """Show or hide flex overlays."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_set_show_flex_overlays(show)))
    _echo(f"Flex overlays {'shown' if show else 'hidden'}")


@overlay_app.command("grid-overlays")
def overlay_grid_overlays(
    url: str = typer.Argument(..., help="URL to navigate to"),
    configs: str = typer.Option(..., "--configs", help="Grid overlay configs as JSON array"),
) -> None:
    """Show grid overlays for the given configurations."""
    import json

    cfg_list = _safe_json_loads(configs, "configs")
    _run_async(_overlay_direct(url, lambda b: b.overlay_set_show_grid_overlays(cfg_list)))
    _echo(f"Grid overlays set: {len(cfg_list)} config(s)")


@overlay_app.command("hinge")
def overlay_hinge(
    url: str = typer.Argument(..., help="URL to navigate to"),
    config: str = typer.Option("", "--config", help="Hinge config as JSON (empty to clear)"),
) -> None:
    """Show or hide the hinge overlay."""
    import json

    cfg = _safe_json_loads(config, "config") if config else None
    _run_async(_overlay_direct(url, lambda b: b.overlay_set_show_hinge(cfg)))
    _echo(f"Hinge {'shown' if cfg else 'hidden'}")


@overlay_app.command("inspected-element-anchor")
def overlay_inspected_element_anchor(
    url: str = typer.Argument(..., help="URL to navigate to"),
    show: bool = typer.Option(True, "--show/--hide", help="Show or hide inspected element anchor"),
) -> None:
    """Show or hide the inspected element anchor."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_set_show_inspected_element_anchor(show)))
    _echo(f"Inspected element anchor {'shown' if show else 'hidden'}")


@overlay_app.command("isolated-elements")
def overlay_isolated_elements(
    url: str = typer.Argument(..., help="URL to navigate to"),
    configs: str = typer.Option(
        ..., "--configs", help="Isolated element highlight configs as JSON array"
    ),
) -> None:
    """Show isolated elements with the given highlight configurations."""
    import json

    cfg_list = _safe_json_loads(configs, "configs")
    _run_async(_overlay_direct(url, lambda b: b.overlay_set_show_isolated_elements(cfg_list)))
    _echo(f"Isolated elements set: {len(cfg_list)} config(s)")


@overlay_app.command("layout-shift-regions")
def overlay_layout_shift_regions(
    url: str = typer.Argument(..., help="URL to navigate to"),
    show: bool = typer.Option(True, "--show/--hide", help="Show or hide layout shift regions"),
) -> None:
    """Show or hide layout shift regions."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_set_show_layout_shift_regions(show)))
    _echo(f"Layout shift regions {'shown' if show else 'hidden'}")


@overlay_app.command("scroll-bottleneck-rects")
def overlay_scroll_bottleneck_rects(
    url: str = typer.Argument(..., help="URL to navigate to"),
    show: bool = typer.Option(True, "--show/--hide", help="Show or hide scroll bottleneck rects"),
) -> None:
    """Show or hide scroll bottleneck rects."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_set_show_scroll_bottleneck_rects(show)))
    _echo(f"Scroll bottleneck rects {'shown' if show else 'hidden'}")


@overlay_app.command("scroll-snap-overlays")
def overlay_scroll_snap_overlays(
    url: str = typer.Argument(..., help="URL to navigate to"),
    show: bool = typer.Option(True, "--show/--hide", help="Show or hide scroll snap overlays"),
) -> None:
    """Show or hide scroll snap overlays."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_set_show_scroll_snap_overlays(show)))
    _echo(f"Scroll snap overlays {'shown' if show else 'hidden'}")


@overlay_app.command("viewport-size-on-resize")
def overlay_viewport_size_on_resize(
    url: str = typer.Argument(..., help="URL to navigate to"),
    show: bool = typer.Option(True, "--show/--hide", help="Show or hide viewport size on resize"),
) -> None:
    """Show or hide viewport size on resize."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_set_show_viewport_size_on_resize(show)))
    _echo(f"Viewport size on resize {'shown' if show else 'hidden'}")


@overlay_app.command("window-controls-overlay")
def overlay_window_controls_overlay(
    url: str = typer.Argument(..., help="URL to navigate to"),
    show: bool = typer.Option(True, "--show/--hide", help="Show or hide window controls overlay"),
) -> None:
    """Show or hide window controls overlay."""
    _run_async(_overlay_direct(url, lambda b: b.overlay_set_show_window_controls_overlay(show)))
    _echo(f"Window controls overlay {'shown' if show else 'hidden'}")


async def _overlay_direct(url: str, action_fn: Any) -> Any:
    """Launch backend, navigate, and run a direct overlay action."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url)
        return await action_fn(backend)
    finally:
        await _close_backend(backend)


@dom_app.command("document")
def dom_document(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the document root node."""
    result = _run_async(_dom_action(url, "document"))
    if result is None:
        return
    _write_json_output(result, output, "document")


@dom_app.command("box-model")
def dom_box_model(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the box model for an element."""
    result = _run_async(_dom_action(url, "box_model", selector=selector))
    if result is None:
        return
    _write_json_output(result, output, "box model")


@dom_app.command("quads")
def dom_quads(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the content quads for an element."""
    result = _run_async(_dom_action(url, "content_quads", selector=selector))
    if result is None:
        return
    _write_json_output(result, output, "content quads")


@dom_app.command("hit")
def dom_hit(
    url: str = typer.Argument(..., help="URL to navigate to"),
    x: int = typer.Option(..., "--x", help="Horizontal coordinate"),
    y: int = typer.Option(..., "--y", help="Vertical coordinate"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the node at a viewport location (hit testing)."""
    result = _run_async(_dom_action(url, "node_for_location", x=x, y=y))
    if result is None:
        return
    _write_json_output(result, output, "node for location")


@dom_app.command("search")
def dom_search(
    url: str = typer.Argument(..., help="URL to navigate to"),
    query: str = typer.Argument(..., help="Search query"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Search the DOM for a query string."""
    result = _run_async(_dom_action(url, "perform_search", query=query))
    if result is None:
        return
    _write_json_output(result, output, "search")


@dom_app.command("search-results")
def dom_search_results(
    url: str = typer.Argument(..., help="URL to navigate to"),
    search_id: str = typer.Option(..., "--search-id", help="Search session ID"),
    from_index: int = typer.Option(0, "--from", help="Start index"),
    to_index: int = typer.Option(0, "--to", help="End index"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get DOM search results."""
    result = _run_async(
        _dom_action(
            url, "search_results", search_id=search_id, from_index=from_index, to_index=to_index
        )
    )
    if result is None:
        return
    _write_json_output(result, output, "search results")


@dom_app.command("scroll-if-needed")
def dom_scroll_if_needed(
    url: str = typer.Argument(..., help="URL to navigate to"),
    selector: str = typer.Option(..., "--selector", "-s", help="CSS selector"),
) -> None:
    """Scroll an element into view if needed."""
    _run_async(_dom_action(url, "scroll_into_view_if_needed", selector=selector))
    _echo(f"Scrolled into view: {selector}")


async def _dom_action(
    url: str,
    action: str,
    selector: str | None = None,
    query: str | None = None,
    search_id: str | None = None,
    from_index: int = 0,
    to_index: int = 0,
    x: int = 0,
    y: int = 0,
) -> Any:
    """Execute a DOM inspection action on a web page."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))

        if action == "document":
            return await backend.dom_get_document()
        if action == "box_model" and selector:
            return await backend.dom_get_box_model(selector)
        if action == "content_quads" and selector:
            return await backend.dom_get_content_quads(selector)
        if action == "node_for_location":
            return await backend.dom_get_node_for_location(x, y)
        if action == "perform_search" and query:
            return await backend.dom_perform_search(query)
        if action == "search_results" and search_id:
            return await backend.dom_get_search_results(search_id, from_index, to_index)
        if action == "scroll_into_view_if_needed" and selector:
            await backend.dom_scroll_into_view_if_needed(selector)
            return None
        raise ValueError(f"Unknown DOM action: {action}")
    finally:
        await _close_backend(backend)


# ── Runtime commands ────────────────────────────────────


@runtime_app.command("evaluate")
def runtime_evaluate(
    url: str = typer.Argument(..., help="URL to navigate to"),
    expression: str = typer.Argument(..., help="JavaScript expression to evaluate"),
    await_promise: bool = typer.Option(
        False, "--await-promise", help="Await the resulting promise"
    ),
    return_by_value: bool = typer.Option(False, "--return-by-value", help="Return result by value"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Evaluate a JavaScript expression."""
    result = _run_async(
        _runtime_direct(
            url, lambda b: b.runtime_evaluate(expression, await_promise, return_by_value)
        )
    )
    if result is None:
        return
    _write_json_output(result, output, "result")


@runtime_app.command("compile")
def runtime_compile(
    url: str = typer.Argument(..., help="URL to navigate to"),
    expression: str = typer.Argument(..., help="JavaScript expression to compile"),
    source_url: str = typer.Option("", "--source-url", help="Source URL for the script"),
    persist: bool = typer.Option(False, "--persist", help="Persist the script"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Compile a JavaScript expression without running it."""
    result = _run_async(
        _runtime_direct(url, lambda b: b.runtime_compile_script(expression, source_url, persist))
    )
    if result is None:
        return
    _write_json_output(result, output, "result")


@runtime_app.command("run-script")
def runtime_run_script(
    url: str = typer.Argument(..., help="URL to navigate to"),
    script_id: str = typer.Argument(..., help="Script ID to run"),
    await_promise: bool = typer.Option(
        False, "--await-promise", help="Await the resulting promise"
    ),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Run a previously compiled script by ID."""
    result = _run_async(
        _runtime_direct(url, lambda b: b.runtime_run_script(script_id, await_promise))
    )
    if result is None:
        return
    _write_json_output(result, output, "result")


@runtime_app.command("call")
def runtime_call(
    url: str = typer.Argument(..., help="URL to navigate to"),
    function: str = typer.Argument(..., help="JavaScript function declaration"),
    object_id: str = typer.Option("", "--object-id", help="Remote object ID"),
    await_promise: bool = typer.Option(
        False, "--await-promise", help="Await the resulting promise"
    ),
    return_by_value: bool = typer.Option(False, "--return-by-value", help="Return result by value"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Call a function on a remote object."""
    result = _run_async(
        _runtime_direct(
            url,
            lambda b: b.runtime_call_function_on(
                function, object_id, None, await_promise, return_by_value
            ),
        )
    )
    if result is None:
        return
    _write_json_output(result, output, "result")


@runtime_app.command("get-properties")
def runtime_get_properties(
    url: str = typer.Argument(..., help="URL to navigate to"),
    object_id: str = typer.Argument(..., help="Remote object ID"),
    own: bool = typer.Option(True, "--own/--all", help="Get own properties only"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Get properties of a remote object."""
    result = _run_async(_runtime_direct(url, lambda b: b.runtime_get_properties(object_id, own)))
    if result is None:
        return
    _write_json_output(result, output, "result")


@runtime_app.command("release-object")
def runtime_release_object(
    url: str = typer.Argument(..., help="URL to navigate to"),
    object_id: str = typer.Argument(..., help="Remote object ID to release"),
) -> None:
    """Release a remote object."""
    _run_async(_runtime_direct(url, lambda b: b.runtime_release_object(object_id)))
    _echo(f"Released object: {object_id}")


@runtime_app.command("release-group")
def runtime_release_group(
    url: str = typer.Argument(..., help="URL to navigate to"),
    object_group: str = typer.Argument(..., help="Object group name to release"),
) -> None:
    """Release all objects in a group."""
    _run_async(_runtime_direct(url, lambda b: b.runtime_release_object_group(object_group)))
    _echo(f"Released group: {object_group}")


@runtime_app.command("discard-console")
def runtime_discard_console(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Discard collected console entries."""
    _run_async(_runtime_direct(url, lambda b: b.runtime_discard_console_entries()))
    _echo("Console entries discarded")


@runtime_app.command("heap-usage")
def runtime_heap_usage(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Get the current heap usage."""
    result = _run_async(_runtime_direct(url, lambda b: b.runtime_get_heap_usage()))
    if result is None:
        return
    _write_json_output(result, output, "usage")


@runtime_app.command("lexical-scope")
def runtime_lexical_scope(
    url: str = typer.Argument(..., help="URL to navigate to"),
    context_id: int = typer.Option(-1, "--context-id", help="Execution context ID"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Get global lexical scope names."""
    ctx = context_id if context_id >= 0 else None
    result = _run_async(_runtime_direct(url, lambda b: b.runtime_global_lexical_scope_names(ctx)))
    if result is None:
        return
    _write_json_output(result, output, "names")


async def _runtime_direct(url: str, action_fn: Any) -> Any:
    """Launch backend, navigate, and run a direct runtime action."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url)
        return await action_fn(backend)
    finally:
        await _close_backend(backend)


@runtime_app.command("add-binding")
def runtime_add_binding_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    name: str = typer.Argument(..., help="Binding name"),
    context_name: str = typer.Option(None, "--context-name", help="Execution context name filter"),
) -> None:
    """Add a binding with the given name."""
    _run_async(_runtime_direct(url, lambda b: b.runtime_add_binding(name, context_name)))
    _echo(f"Binding added: {name}")


@runtime_app.command("await-promise")
def runtime_await_promise_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    promise_object_id: str = typer.Argument(..., help="Remote object ID of the promise"),
    return_by_value: bool = typer.Option(False, "--return-by-value", help="Return result by value"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Await a promise by its remote object ID."""
    result = _run_async(
        _runtime_direct(url, lambda b: b.runtime_await_promise(promise_object_id, return_by_value))
    )
    if result is None:
        return
    _write_json_output(result, output, "result")


@runtime_app.command("collect-garbage")
def runtime_collect_garbage_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Collect garbage."""
    _run_async(_runtime_direct(url, lambda b: b.runtime_collect_garbage()))
    _echo("Garbage collected")


@runtime_app.command("disable")
def runtime_disable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the Runtime domain."""
    _run_async(_runtime_direct(url, lambda b: b.runtime_disable()))
    _echo("Runtime disabled")


@runtime_app.command("enable")
def runtime_enable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the Runtime domain."""
    _run_async(_runtime_direct(url, lambda b: b.runtime_enable()))
    _echo("Runtime enabled")


@runtime_app.command("exception-details")
def runtime_exception_details_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    error_object_id: str = typer.Argument(..., help="Remote object ID of the error"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Get exception details for an error object."""
    result = _run_async(
        _runtime_direct(url, lambda b: b.runtime_get_exception_details(error_object_id))
    )
    if result is None:
        return
    _write_json_output(result, output, "exception details")


@runtime_app.command("isolate-id")
def runtime_isolate_id_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Get the isolate ID."""
    result = _run_async(_runtime_direct(url, lambda b: b.runtime_get_isolate_id()))
    if result is None:
        return
    _write_json_output(result, output, "isolate id")


@runtime_app.command("query-objects")
def runtime_query_objects_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    prototype_object_id: str = typer.Argument(..., help="Remote object ID of the prototype"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Query objects by prototype."""
    result = _run_async(
        _runtime_direct(url, lambda b: b.runtime_query_objects(prototype_object_id))
    )
    if result is None:
        return
    _write_json_output(result, output, "objects")


@runtime_app.command("remove-binding")
def runtime_remove_binding_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    name: str = typer.Argument(..., help="Binding name to remove"),
) -> None:
    """Remove a previously added binding."""
    _run_async(_runtime_direct(url, lambda b: b.runtime_remove_binding(name)))
    _echo(f"Binding removed: {name}")


@runtime_app.command("run-if-waiting")
def runtime_run_if_waiting_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Run if waiting for debugger to pause."""
    _run_async(_runtime_direct(url, lambda b: b.runtime_run_if_waiting_for_debugger()))
    _echo("Run if waiting for debugger executed")


@runtime_app.command("set-async-call-stack-depth")
def runtime_set_async_call_stack_depth_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    max_depth: int = typer.Argument(..., help="Maximum depth of async call stacks"),
) -> None:
    """Set the async call stack depth."""
    _run_async(_runtime_direct(url, lambda b: b.runtime_set_async_call_stack_depth(max_depth)))
    _echo(f"Async call stack depth set to {max_depth}")


@runtime_app.command("set-custom-formatter")
def runtime_set_custom_formatter_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    enabled: bool = typer.Argument(..., help="Enable or disable the custom formatter"),
) -> None:
    """Enable or disable the custom object formatter."""
    _run_async(
        _runtime_direct(url, lambda b: b.runtime_set_custom_object_formatter_enabled(enabled))
    )
    _echo(f"Custom object formatter {'enabled' if enabled else 'disabled'}")


@runtime_app.command("set-max-call-stack-size")
def runtime_set_max_call_stack_size_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    size: int = typer.Argument(..., help="Maximum call stack size"),
) -> None:
    """Set the max call stack size to capture."""
    _run_async(_runtime_direct(url, lambda b: b.runtime_set_max_call_stack_size_to_capture(size)))
    _echo(f"Max call stack size set to {size}")


@runtime_app.command("terminate")
def runtime_terminate_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Terminate the current execution."""
    _run_async(_runtime_direct(url, lambda b: b.runtime_terminate_execution()))
    _echo("Execution terminated")


# ── Schema commands ──────────────────────────────────────

schema_app = typer.Typer(help="Schema commands (domain introspection)")
app.add_typer(schema_app, name="schema")


@schema_app.command("get-domains")
def schema_get_domains_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Get all available CDP domains."""
    result = _run_async(_debug_direct(url, lambda b: b.schema_get_domains()))
    if result is None:
        return
    _write_json_output(result, output, "domains")


# ── Security commands ────────────────────────────────────

security_app = typer.Typer(help="Security commands (certificate errors, security state)")
app.add_typer(security_app, name="security")


@security_app.command("disable")
def security_disable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the Security domain."""
    _run_async(_debug_direct(url, lambda b: b.security_disable()))
    _echo("Security disabled")


@security_app.command("enable")
def security_enable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the Security domain."""
    _run_async(_debug_direct(url, lambda b: b.security_enable()))
    _echo("Security enabled")


@security_app.command("get-visible-security-state")
def security_get_visible_security_state_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Get the visible security state of the current page."""
    result = _run_async(_debug_direct(url, lambda b: b.security_get_visible_security_state()))
    if result is None:
        return
    _write_json_output(result, output, "security state")


@security_app.command("handle-certificate-error")
def security_handle_certificate_error_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    event_id: int = typer.Argument(..., help="Certificate error event ID"),
    action: str = typer.Argument(..., help="Action to take (continue, cancel)"),
) -> None:
    """Handle a certificate error event."""
    _run_async(_debug_direct(url, lambda b: b.security_handle_certificate_error(event_id, action)))
    _echo(f"Certificate error {event_id} handled with action: {action}")


@security_app.command("set-ignore-certificate-errors")
def security_set_ignore_certificate_errors_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    ignore: bool = typer.Argument(..., help="Whether to ignore certificate errors"),
) -> None:
    """Set whether to ignore certificate errors."""
    _run_async(_debug_direct(url, lambda b: b.security_set_ignore_certificate_errors(ignore)))
    _echo(f"Ignore certificate errors set to {ignore}")


@security_app.command("set-override-certificate-errors")
def security_set_override_certificate_errors_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    override: bool = typer.Argument(..., help="Whether to override certificate errors"),
) -> None:
    """Set whether to override certificate errors."""
    _run_async(_debug_direct(url, lambda b: b.security_set_override_certificate_errors(override)))
    _echo(f"Override certificate errors set to {override}")


# ── Sensor commands ──────────────────────────────────────

sensor_app = typer.Typer(help="Sensor commands (sensor emulation and override)")
app.add_typer(sensor_app, name="sensor")


@sensor_app.command("clear-override")
def sensor_clear_override_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    sensor_type: str = typer.Argument(..., help="Sensor type to clear override for"),
) -> None:
    """Clear a sensor override."""
    _run_async(_debug_direct(url, lambda b: b.sensor_clear_sensor_override(sensor_type)))
    _echo(f"Sensor override cleared for: {sensor_type}")


@sensor_app.command("disable")
def sensor_disable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the Sensor domain."""
    _run_async(_debug_direct(url, lambda b: b.sensor_disable()))
    _echo("Sensor disabled")


@sensor_app.command("enable")
def sensor_enable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the Sensor domain."""
    _run_async(_debug_direct(url, lambda b: b.sensor_enable()))
    _echo("Sensor enabled")


@sensor_app.command("set-override")
def sensor_set_override_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    sensor_type: str = typer.Argument(..., help="Sensor type to override"),
    metadata: str = typer.Option(
        None, "--metadata", help='Sensor metadata JSON (e.g. \'{"key":"value"}\')'
    ),
) -> None:
    """Set a sensor override."""
    import json

    metadata_dict = _safe_json_loads(metadata, "metadata") if metadata else None
    _run_async(
        _debug_direct(url, lambda b: b.sensor_set_sensor_override(sensor_type, metadata_dict))
    )
    _echo(f"Sensor override set for: {sensor_type}")


# ── Target commands ─────────────────────────────────────


@target_app.command("list")
def target_list(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Get all available targets."""
    result = _run_async(_target_direct(url, lambda b: b.target_get_targets()))
    if result is None:
        return
    _write_json_output(result, output, "targets")


@target_app.command("create")
def target_create(
    url: str = typer.Argument(..., help="URL to navigate to"),
    target_url: str = typer.Argument(..., help="URL for the new target"),
) -> None:
    """Create a new target (tab)."""
    result = _run_async(_target_direct(url, lambda b: b.target_create_target(target_url)))
    _echo(f"Created target: {result}")


@target_app.command("close")
def target_close(
    url: str = typer.Argument(..., help="URL to navigate to"),
    target_id: str = typer.Argument(..., help="Target ID to close"),
) -> None:
    """Close a target by ID."""
    _run_async(_target_direct(url, lambda b: b.target_close_target(target_id)))
    _echo(f"Closed target: {target_id}")


@target_app.command("activate")
def target_activate(
    url: str = typer.Argument(..., help="URL to navigate to"),
    target_id: str = typer.Argument(..., help="Target ID to activate"),
) -> None:
    """Activate (focus) a target by ID."""
    _run_async(_target_direct(url, lambda b: b.target_activate_target(target_id)))
    _echo(f"Activated target: {target_id}")


@target_app.command("attach")
def target_attach(
    url: str = typer.Argument(..., help="URL to navigate to"),
    target_id: str = typer.Argument(..., help="Target ID to attach to"),
    flatten: bool = typer.Option(True, "--flatten/--no-flatten", help="Flatten session"),
) -> None:
    """Attach to a target by ID."""
    result = _run_async(
        _target_direct(url, lambda b: b.target_attach_to_target(target_id, flatten))
    )
    _echo(f"Attached session: {result}")


@target_app.command("detach")
def target_detach(
    url: str = typer.Argument(..., help="URL to navigate to"),
    session_id: str = typer.Argument(..., help="Session ID to detach"),
) -> None:
    """Detach from a target by session ID."""
    _run_async(_target_direct(url, lambda b: b.target_detach_from_target(session_id)))
    _echo(f"Detached session: {session_id}")


@target_app.command("auto-attach")
def target_auto_attach(
    url: str = typer.Argument(..., help="URL to navigate to"),
    auto_attach: bool = typer.Argument(..., help="Enable or disable auto-attach"),
    wait: bool = typer.Option(False, "--wait", help="Wait for debugger on start"),
) -> None:
    """Set auto-attach for new targets."""
    _run_async(_target_direct(url, lambda b: b.target_set_auto_attach(auto_attach, wait)))
    _echo(f"Auto-attach {'enabled' if auto_attach else 'disabled'}")


@target_app.command("discover")
def target_discover(
    url: str = typer.Argument(..., help="URL to navigate to"),
    discover: bool = typer.Argument(..., help="Enable or disable discovery"),
) -> None:
    """Enable or disable target discovery."""
    _run_async(_target_direct(url, lambda b: b.target_set_discover_targets(discover)))
    _echo(f"Discovery {'enabled' if discover else 'disabled'}")


@target_app.command("info")
def target_info(
    url: str = typer.Argument(..., help="URL to navigate to"),
    target_id: str = typer.Argument(..., help="Target ID to query"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Get info about a specific target."""
    result = _run_async(_target_direct(url, lambda b: b.target_get_target_info(target_id)))
    if result is None:
        return
    _write_json_output(result, output, "info")


@target_app.command("create-context")
def target_create_context(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Create a new browser context."""
    result = _run_async(_target_direct(url, lambda b: b.target_create_browser_context()))
    _echo(f"Created context: {result}")


@target_app.command("attach-browser")
def target_attach_browser(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Attach to the browser target."""
    result = _run_async(_target_direct(url, lambda b: b.target_attach_to_browser_target()))
    _echo(f"Attached to browser target, session: {result}")


@target_app.command("auto-attach-related")
def target_auto_attach_related(
    url: str = typer.Argument(..., help="URL to navigate to"),
    target_id: str = typer.Argument(..., help="Target ID to auto-attach related targets for"),
    wait: bool = typer.Option(False, "--wait", help="Wait for debugger on start"),
) -> None:
    """Auto-attach to related targets of a given target."""
    _run_async(_target_direct(url, lambda b: b.target_auto_attach_related(target_id, wait)))
    _echo(f"Auto-attach related for {target_id}")


@target_app.command("dispose-context")
def target_dispose_context(
    url: str = typer.Argument(..., help="URL to navigate to"),
    context_id: str = typer.Argument(..., help="Browser context ID to dispose"),
) -> None:
    """Dispose a browser context by ID."""
    _run_async(_target_direct(url, lambda b: b.target_dispose_browser_context(context_id)))
    _echo(f"Disposed context: {context_id}")


@target_app.command("expose-protocol")
def target_expose_protocol(
    url: str = typer.Argument(..., help="URL to navigate to"),
    target_id: str = typer.Argument(..., help="Target ID to expose protocol to"),
    binding_name: str = typer.Argument(..., help="Binding name to use"),
) -> None:
    """Expose DevTools protocol API to the target."""
    _run_async(
        _target_direct(url, lambda b: b.target_expose_dev_tools_protocol(target_id, binding_name))
    )
    _echo(f"Exposed protocol to {target_id}")


@target_app.command("get-contexts")
def target_get_contexts(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Get all browser contexts."""
    result = _run_async(_target_direct(url, lambda b: b.target_get_browser_contexts()))
    _echo(f"Browser contexts: {result}")


@target_app.command("get-devtools-target")
def target_get_devtools_target(
    url: str = typer.Argument(..., help="URL to navigate to"),
    target_id: str = typer.Argument(..., help="Target ID to query"),
) -> None:
    """Get the DevTools target for a given target."""
    result = _run_async(_target_direct(url, lambda b: b.target_get_dev_tools_target(target_id)))
    _echo(f"DevTools target: {result}")


@target_app.command("open-devtools")
def target_open_devtools(
    url: str = typer.Argument(..., help="URL to navigate to"),
    target_id: str = typer.Argument(..., help="Target ID to open DevTools for"),
) -> None:
    """Open DevTools for a target."""
    _run_async(_target_direct(url, lambda b: b.target_open_dev_tools(target_id)))
    _echo(f"Opened DevTools for {target_id}")


@target_app.command("send-message")
def target_send_message(
    url: str = typer.Argument(..., help="URL to navigate to"),
    session_id: str = typer.Argument(..., help="Session ID to send message to"),
    message: str = typer.Argument(..., help="Message to send"),
) -> None:
    """Send a message to a target via session ID."""
    _run_async(_target_direct(url, lambda b: b.target_send_message_to_target(session_id, message)))
    _echo(f"Sent message to {session_id}")


@target_app.command("set-remote-locations")
def target_set_remote_locations(
    url: str = typer.Argument(..., help="URL to navigate to"),
    locations: str = typer.Argument(..., help="JSON array of location dicts with host and port"),
) -> None:
    """Set remote locations for target discovery."""
    import json as _json

    try:
        locs = _json.loads(locations)
    except _json.JSONDecodeError as e:
        typer.echo(f"Invalid locations JSON: {e}", err=True)
        raise typer.Exit(2) from e
    _run_async(_target_direct(url, lambda b: b.target_set_remote_locations(locs)))
    _echo(f"Set remote locations: {locs}")


async def _target_direct(url: str, action_fn: Any) -> Any:
    """Launch backend, navigate, and run a direct target action."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url)
        return await action_fn(backend)
    finally:
        await _close_backend(backend)


# ── DOM node commands ──────────────────────────────────


@dom_app.command("describe")
def dom_describe(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Describe a DOM node by node ID."""
    result = _run_async(_dom_node_direct(url, "describe", node_id=node_id))
    if result is None:
        return
    _write_json_output(result, output, "node")


@dom_app.command("outer-html")
def dom_outer_html(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
) -> None:
    """Get the outer HTML of a node by ID."""
    result = _run_async(_dom_node_direct(url, "outer_html", node_id=node_id))
    if result is None:
        return
    _echo(str(result))


@dom_app.command("remove-node")
def dom_remove_node(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID to remove"),
) -> None:
    """Remove a node from the DOM by ID."""
    _run_async(_dom_node_direct(url, "remove_node", node_id=node_id))
    _echo(f"Removed node: {node_id}")


@dom_app.command("set-value")
def dom_set_value(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    value: str = typer.Argument(..., help="New value"),
) -> None:
    """Set the value of a node by ID."""
    _run_async(_dom_node_direct(url, "set_node_value", node_id=node_id, value=value))
    _echo(f"Set value on node {node_id}")


@dom_app.command("set-outer-html")
def dom_set_outer_html(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    html: str = typer.Argument(..., help="New outer HTML"),
) -> None:
    """Set the outer HTML of a node by ID."""
    _run_async(_dom_node_direct(url, "set_outer_html", node_id=node_id, outer_html=html))
    _echo(f"Set outer HTML on node {node_id}")


@dom_app.command("request-node")
def dom_request_node(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
) -> None:
    """Request a node by ID."""
    result = _run_async(_dom_node_direct(url, "request_node", node_id=node_id))
    _echo(f"Node ID: {result}")


@dom_app.command("resolve-node")
def dom_resolve_node(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Resolve a node to a remote object."""
    result = _run_async(_dom_node_direct(url, "resolve_node", node_id=node_id))
    if result is None:
        return
    _write_json_output(result, output, "object")


@dom_app.command("set-attr")
def dom_set_attr_node(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    name: str = typer.Argument(..., help="Attribute name"),
    value: str = typer.Argument(..., help="Attribute value"),
) -> None:
    """Set an attribute value on a node by ID."""
    _run_async(
        _dom_node_direct(url, "set_attribute_value", node_id=node_id, name=name, value=value)
    )
    _echo(f"Set attribute {name}={value} on node {node_id}")


@dom_app.command("remove-attr")
def dom_remove_attr_node(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    name: str = typer.Argument(..., help="Attribute name to remove"),
) -> None:
    """Remove an attribute from a node by ID."""
    _run_async(_dom_node_direct(url, "remove_attribute", node_id=node_id, name=name))
    _echo(f"Removed attribute {name} from node {node_id}")


@dom_app.command("child-nodes")
def dom_child_nodes(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    depth: int = typer.Option(-1, "--depth", help="Maximum depth (-1 for all)"),
) -> None:
    """Request child nodes of a node by ID."""
    _run_async(_dom_node_direct(url, "request_child_nodes", node_id=node_id, depth=depth))
    _echo(f"Requested child nodes for node {node_id}")


@dom_app.command("collect-class-names")
def dom_collect_class_names(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
) -> None:
    """Collect class names from the subtree of a node."""
    result = _run_async(_dom_node_direct(url, "collect_class_names", node_id=node_id))
    _echo(f"Class names: {result}")


@dom_app.command("copy-to")
def dom_copy_to(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID to copy"),
    target_node_id: int = typer.Argument(..., help="Target node ID"),
    insert_before: int = typer.Option(-1, "--insert-before", help="Insert before this node ID"),
) -> None:
    """Copy a node to a target node."""
    insert_before_id = insert_before if insert_before >= 0 else None
    _run_async(
        _dom_node_direct(
            url,
            "copy_to",
            node_id=node_id,
            target_node_id=target_node_id,
            insert_before_node_id=insert_before_id,
        )
    )
    _echo(f"Copied node {node_id} to {target_node_id}")


@dom_app.command("disable")
def dom_disable(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the DOM agent."""
    _run_async(_dom_node_direct(url, "disable"))
    _echo("DOM agent disabled")


@dom_app.command("discard-search")
def dom_discard_search(
    url: str = typer.Argument(..., help="URL to navigate to"),
    search_id: str = typer.Argument(..., help="Search session ID to discard"),
) -> None:
    """Discard search results for a DOM search session."""
    _run_async(_dom_node_direct(url, "discard_search_results", search_id=search_id))
    _echo(f"Discarded search results for {search_id}")


@dom_app.command("enable")
def dom_enable(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the DOM agent."""
    _run_async(_dom_node_direct(url, "enable"))
    _echo("DOM agent enabled")


@dom_app.command("focus-node")
def dom_focus_node(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID to focus"),
) -> None:
    """Focus a node by ID."""
    _run_async(_dom_node_direct(url, "focus_node", node_id=node_id))
    _echo(f"Focused node {node_id}")


@dom_app.command("force-popover")
def dom_force_popover(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
) -> None:
    """Force show a popover for a node by ID."""
    _run_async(_dom_node_direct(url, "force_show_popover", node_id=node_id))
    _echo(f"Forced popover for node {node_id}")


@dom_app.command("anchor-element")
def dom_anchor_element(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
) -> None:
    """Get the anchor element for a node by ID."""
    result = _run_async(_dom_node_direct(url, "get_anchor_element", node_id=node_id))
    _echo(f"Anchor element: {result}")


@dom_app.command("node-attribute")
def dom_node_attribute(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    name: str = typer.Argument(..., help="Attribute name"),
) -> None:
    """Get an attribute value from a node by ID."""
    result = _run_async(_dom_node_direct(url, "get_node_attribute", node_id=node_id, name=name))
    _echo(f"Attribute {name}: {result}")


@dom_app.command("container-for-node")
def dom_container_for_node(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    container_name: str = typer.Option("", "--container-name", help="Container name filter"),
) -> None:
    """Get the container for a node by ID."""
    cn = container_name if container_name else None
    result = _run_async(
        _dom_node_direct(url, "get_container_for_node", node_id=node_id, container_name=cn)
    )
    _echo(f"Container: {result}")


@dom_app.command("detached-nodes")
def dom_detached_nodes(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Get detached DOM nodes."""
    result = _run_async(_dom_node_direct(url, "get_detached_dom_nodes"))
    _echo(f"Detached nodes: {result}")


@dom_app.command("element-by-relation")
def dom_element_by_relation(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    relation: str = typer.Argument(..., help="Relation type"),
) -> None:
    """Get an element by relation from a node by ID."""
    result = _run_async(
        _dom_node_direct(url, "get_element_by_relation", node_id=node_id, relation=relation)
    )
    _echo(f"Element: {result}")


@dom_app.command("file-info")
def dom_file_info(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
) -> None:
    """Get file info for a node by ID."""
    result = _run_async(_dom_node_direct(url, "get_file_info", node_id=node_id))
    _echo(f"File info: {result}")


@dom_app.command("frame-owner")
def dom_frame_owner(
    url: str = typer.Argument(..., help="URL to navigate to"),
    frame_id: str = typer.Argument(..., help="Frame ID"),
) -> None:
    """Get the frame owner node for a frame ID."""
    result = _run_async(_dom_node_direct(url, "get_frame_owner", frame_id=frame_id))
    _echo(f"Frame owner: {result}")


@dom_app.command("node-stack-traces")
def dom_node_stack_traces(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
) -> None:
    """Get stack traces for a node by ID."""
    result = _run_async(_dom_node_direct(url, "get_node_stack_traces", node_id=node_id))
    _echo(f"Stack traces: {result}")


@dom_app.command("subtree-by-style")
def dom_subtree_by_style(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    styles: str = typer.Argument(..., help="Comma-separated computed style names"),
    pierce: bool = typer.Option(False, "--pierce", help="Pierce iframes"),
) -> None:
    """Get nodes in a subtree matching the given computed styles."""
    computed_styles = [s.strip() for s in styles.split(",")]
    result = _run_async(
        _dom_node_direct(
            url,
            "get_nodes_for_subtree_by_style",
            node_id=node_id,
            computed_styles=computed_styles,
            pierce=pierce,
        )
    )
    _echo(f"Nodes: {result}")


@dom_app.command("querying-descendants")
def dom_querying_descendants(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
) -> None:
    """Get querying descendants for a container node by ID."""
    result = _run_async(
        _dom_node_direct(url, "get_querying_descendants_for_container", node_id=node_id)
    )
    _echo(f"Descendants: {result}")


@dom_app.command("relayout-boundary")
def dom_relayout_boundary(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
) -> None:
    """Get the relayout boundary for a node by ID."""
    result = _run_async(_dom_node_direct(url, "get_relayout_boundary", node_id=node_id))
    _echo(f"Relayout boundary: {result}")


@dom_app.command("top-layer-elements")
def dom_top_layer_elements(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Get top layer elements."""
    result = _run_async(_dom_node_direct(url, "get_top_layer_elements"))
    _echo(f"Top layer elements: {result}")


@dom_app.command("hide-highlight")
def dom_hide_highlight(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Hide any DOM highlight."""
    _run_async(_dom_node_direct(url, "hide_highlight"))
    _echo("Highlight hidden")


@dom_app.command("highlight-node")
def dom_highlight_node(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    highlight_config: str = typer.Argument(..., help="Highlight config JSON"),
) -> None:
    """Highlight a node by ID with the given highlight config."""
    import json

    config = _safe_json_loads(highlight_config, "highlight_config")
    _run_async(_dom_node_direct(url, "highlight_node", node_id=node_id, highlight_config=config))
    _echo(f"Highlighted node {node_id}")


@dom_app.command("highlight-rect")
def dom_highlight_rect(
    url: str = typer.Argument(..., help="URL to navigate to"),
    x: int = typer.Argument(..., help="X coordinate"),
    y: int = typer.Argument(..., help="Y coordinate"),
    width: int = typer.Argument(..., help="Width"),
    height: int = typer.Argument(..., help="Height"),
    highlight_config: str = typer.Argument(..., help="Highlight config JSON"),
) -> None:
    """Highlight a rect with the given highlight config."""
    import json

    config = _safe_json_loads(highlight_config, "highlight_config")
    _run_async(
        _dom_node_direct(
            url, "highlight_rect", x=x, y=y, width=width, height=height, highlight_config=config
        )
    )
    _echo(f"Highlighted rect ({x},{y},{width},{height})")


@dom_app.command("mark-undoable")
def dom_mark_undoable(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Mark an undoable state in the DOM."""
    _run_async(_dom_node_direct(url, "mark_undoable_state"))
    _echo("Marked undoable state")


@dom_app.command("move-to")
def dom_move_to(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID to move"),
    target_node_id: int = typer.Argument(..., help="Target node ID"),
    insert_before: int = typer.Option(-1, "--insert-before", help="Insert before this node ID"),
) -> None:
    """Move a node to a target node."""
    insert_before_id = insert_before if insert_before >= 0 else None
    _run_async(
        _dom_node_direct(
            url,
            "move_to",
            node_id=node_id,
            target_node_id=target_node_id,
            insert_before_node_id=insert_before_id,
        )
    )
    _echo(f"Moved node {node_id} to {target_node_id}")


@dom_app.command("push-node-by-path")
def dom_push_node_by_path(
    url: str = typer.Argument(..., help="URL to navigate to"),
    path: str = typer.Argument(..., help="Node path"),
) -> None:
    """Push a node by path to frontend."""
    result = _run_async(_dom_node_direct(url, "push_node_by_path_to_frontend", path=path))
    _echo(f"Node: {result}")


@dom_app.command("push-nodes-by-backend-ids")
def dom_push_nodes_by_backend_ids(
    url: str = typer.Argument(..., help="URL to navigate to"),
    backend_ids: str = typer.Argument(..., help="Comma-separated backend node IDs"),
) -> None:
    """Push nodes by backend IDs to frontend."""
    ids = [int(x.strip()) for x in backend_ids.split(",")]
    result = _run_async(
        _dom_node_direct(url, "push_nodes_by_backend_ids_to_frontend", backend_node_ids=ids)
    )
    _echo(f"Nodes: {result}")


@dom_app.command("query-selector")
def dom_query_selector(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    selector: str = typer.Argument(..., help="CSS selector"),
) -> None:
    """Query a single selector within a node's subtree."""
    result = _run_async(_dom_node_direct(url, "query_selector", node_id=node_id, selector=selector))
    _echo(f"Result: {result}")


@dom_app.command("query-selector-all")
def dom_query_selector_all(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    selector: str = typer.Argument(..., help="CSS selector"),
) -> None:
    """Query all selectors within a node's subtree."""
    result = _run_async(
        _dom_node_direct(url, "query_selector_all", node_id=node_id, selector=selector)
    )
    _echo(f"Results: {result}")


@dom_app.command("redo")
def dom_redo(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Redo the last DOM action."""
    _run_async(_dom_node_direct(url, "redo"))
    _echo("Redone")


@dom_app.command("remove-node-by-id")
def dom_remove_node_by_id(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID to remove"),
) -> None:
    """Remove a node from the DOM by ID."""
    _run_async(_dom_node_direct(url, "remove_node_by_id", node_id=node_id))
    _echo(f"Removed node {node_id}")


@dom_app.command("set-attributes-as-text")
def dom_set_attributes_as_text(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    text: str = typer.Argument(..., help="Attributes text"),
) -> None:
    """Set attributes on a node from a text string."""
    _run_async(_dom_node_direct(url, "set_attributes_as_text", node_id=node_id, text=text))
    _echo(f"Set attributes on node {node_id}")


@dom_app.command("set-file-input-files")
def dom_set_file_input_files(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    files: str = typer.Argument(..., help="Comma-separated file paths"),
) -> None:
    """Set files for a file input node by ID."""
    file_list = [f.strip() for f in files.split(",")]
    _run_async(_dom_node_direct(url, "set_file_input_files", node_id=node_id, files=file_list))
    _echo(f"Set {len(file_list)} files on node {node_id}")


@dom_app.command("set-inspected-node")
def dom_set_inspected_node(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
) -> None:
    """Set the inspected node by ID."""
    _run_async(_dom_node_direct(url, "set_inspected_node", node_id=node_id))
    _echo(f"Inspected node set to {node_id}")


@dom_app.command("set-node-name")
def dom_set_node_name(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    name: str = typer.Argument(..., help="New node name"),
) -> None:
    """Set the name of a node by ID."""
    result = _run_async(_dom_node_direct(url, "set_node_name", node_id=node_id, name=name))
    _echo(f"Node renamed: {result}")


@dom_app.command("set-node-stack-traces")
def dom_set_node_stack_traces(
    url: str = typer.Argument(..., help="URL to navigate to"),
    enable: bool = typer.Argument(..., help="Enable or disable stack traces"),
) -> None:
    """Enable or disable node stack traces."""
    _run_async(_dom_node_direct(url, "set_node_stack_traces_enabled", enable=enable))
    _echo(f"Node stack traces {'enabled' if enable else 'disabled'}")


@dom_app.command("set-text-content")
def dom_set_text_content(
    url: str = typer.Argument(..., help="URL to navigate to"),
    node_id: int = typer.Argument(..., help="CDP node ID"),
    text: str = typer.Argument(..., help="Text content"),
) -> None:
    """Set the text content of a node by ID."""
    _run_async(_dom_node_direct(url, "set_text_content", node_id=node_id, text=text))
    _echo(f"Text content set on node {node_id}")


@dom_app.command("undo")
def dom_undo(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Undo the last DOM action."""
    _run_async(_dom_node_direct(url, "undo"))
    _echo("Undone")


async def _dom_node_direct(url: str, action: str, **kwargs: Any) -> Any:
    """Launch backend, navigate, and run a DOM node action."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url)
        if action == "describe":
            return await backend.dom_describe_node(kwargs["node_id"])
        if action == "outer_html":
            return await backend.dom_get_outer_html(kwargs["node_id"])
        if action == "remove_node":
            await backend.dom_remove_node(kwargs["node_id"])
            return None
        if action == "set_node_value":
            await backend.dom_set_node_value(kwargs["node_id"], kwargs["value"])
            return None
        if action == "set_outer_html":
            await backend.dom_set_outer_html(kwargs["node_id"], kwargs["outer_html"])
            return None
        if action == "request_node":
            return await backend.dom_request_node(kwargs["node_id"])
        if action == "resolve_node":
            return await backend.dom_resolve_node(kwargs["node_id"])
        if action == "set_attribute_value":
            await backend.dom_set_attribute_value(
                kwargs["node_id"], kwargs["name"], kwargs["value"]
            )
            return None
        if action == "remove_attribute":
            await backend.dom_remove_attribute(kwargs["node_id"], kwargs["name"])
            return None
        if action == "request_child_nodes":
            await backend.dom_request_child_nodes(kwargs["node_id"], kwargs.get("depth", -1))
            return None
        if action == "collect_class_names":
            return await backend.dom_collect_class_names_from_subtree(kwargs["node_id"])
        if action == "copy_to":
            await backend.dom_copy_to(
                kwargs["node_id"], kwargs["target_node_id"], kwargs.get("insert_before_node_id")
            )
            return None
        if action == "disable":
            await backend.dom_disable()
            return None
        if action == "discard_search_results":
            await backend.dom_discard_search_results(kwargs["search_id"])
            return None
        if action == "enable":
            await backend.dom_enable()
            return None
        if action == "focus_node":
            await backend.dom_focus_node(kwargs["node_id"])
            return None
        if action == "force_show_popover":
            await backend.dom_force_show_popover(kwargs["node_id"])
            return None
        if action == "get_anchor_element":
            return await backend.dom_get_anchor_element(kwargs["node_id"])
        if action == "get_node_attribute":
            return await backend.dom_get_node_attribute(kwargs["node_id"], kwargs["name"])
        if action == "get_container_for_node":
            return await backend.dom_get_container_for_node(
                kwargs["node_id"], kwargs.get("container_name")
            )
        if action == "get_detached_dom_nodes":
            return await backend.dom_get_detached_dom_nodes()
        if action == "get_element_by_relation":
            return await backend.dom_get_element_by_relation(kwargs["node_id"], kwargs["relation"])
        if action == "get_file_info":
            return await backend.dom_get_file_info(kwargs["node_id"])
        if action == "get_frame_owner":
            return await backend.dom_get_frame_owner(kwargs["frame_id"])
        if action == "get_node_stack_traces":
            return await backend.dom_get_node_stack_traces(kwargs["node_id"])
        if action == "get_nodes_for_subtree_by_style":
            return await backend.dom_get_nodes_for_subtree_by_style(
                kwargs["node_id"], kwargs["computed_styles"], kwargs.get("pierce", False)
            )
        if action == "get_querying_descendants_for_container":
            return await backend.dom_get_querying_descendants_for_container(kwargs["node_id"])
        if action == "get_relayout_boundary":
            return await backend.dom_get_relayout_boundary(kwargs["node_id"])
        if action == "get_top_layer_elements":
            return await backend.dom_get_top_layer_elements()
        if action == "hide_highlight":
            await backend.dom_hide_highlight()
            return None
        if action == "highlight_node":
            await backend.dom_highlight_node(kwargs["node_id"], kwargs["highlight_config"])
            return None
        if action == "highlight_rect":
            await backend.dom_highlight_rect(
                kwargs["x"],
                kwargs["y"],
                kwargs["width"],
                kwargs["height"],
                kwargs["highlight_config"],
            )
            return None
        if action == "mark_undoable_state":
            await backend.dom_mark_undoable_state()
            return None
        if action == "move_to":
            await backend.dom_move_to(
                kwargs["node_id"], kwargs["target_node_id"], kwargs.get("insert_before_node_id")
            )
            return None
        if action == "push_node_by_path_to_frontend":
            return await backend.dom_push_node_by_path_to_frontend(kwargs["path"])
        if action == "push_nodes_by_backend_ids_to_frontend":
            return await backend.dom_push_nodes_by_backend_ids_to_frontend(
                kwargs["backend_node_ids"]
            )
        if action == "query_selector":
            return await backend.dom_query_selector(kwargs["node_id"], kwargs["selector"])
        if action == "query_selector_all":
            return await backend.dom_query_selector_all(kwargs["node_id"], kwargs["selector"])
        if action == "redo":
            await backend.dom_redo()
            return None
        if action == "remove_node_by_id":
            await backend.dom_remove_node_by_id(kwargs["node_id"])
            return None
        if action == "set_attributes_as_text":
            await backend.dom_set_attributes_as_text(kwargs["node_id"], kwargs["text"])
            return None
        if action == "set_file_input_files":
            await backend.dom_set_file_input_files(kwargs["node_id"], kwargs["files"])
            return None
        if action == "set_inspected_node":
            await backend.dom_set_inspected_node(kwargs["node_id"])
            return None
        if action == "set_node_name":
            return await backend.dom_set_node_name(kwargs["node_id"], kwargs["name"])
        if action == "set_node_stack_traces_enabled":
            await backend.dom_set_node_stack_traces_enabled(kwargs["enable"])
            return None
        if action == "set_text_content":
            await backend.dom_set_text_content(kwargs["node_id"], kwargs["text"])
            return None
        if action == "undo":
            await backend.dom_undo()
            return None
        raise ValueError(f"Unknown DOM node action: {action}")
    finally:
        await _close_backend(backend)


# ── Emulation commands ─────────────────────────────────


@emulation_app.command("add-screen")
def emulation_add_screen(
    url: str = typer.Argument(..., help="URL to navigate to"),
    screen_json: str = typer.Argument(..., help="Screen configuration as JSON string"),
) -> None:
    """Add a virtual screen with the given configuration."""
    import json

    screen = _safe_json_loads(screen_json, "screen")
    _run_async(_emulation_direct(url, "add_screen", screen=screen))
    _echo("Added virtual screen")


@emulation_app.command("can-emulate")
def emulation_can_emulate(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Check whether the browser supports emulation."""
    result = _run_async(_emulation_direct(url, "can_emulate"))
    if result is None:
        return
    _write_json_output({"canEmulate": result}, output, "canEmulate")


@emulation_app.command("clear-auto-dark-mode")
def emulation_clear_auto_dark_mode(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Clear the auto dark mode override."""
    _run_async(_emulation_direct(url, "clear_auto_dark_mode_override"))
    _echo("Cleared auto dark mode override")


@emulation_app.command("clear-default-bg-color")
def emulation_clear_default_bg_color(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Clear the default background color override."""
    _run_async(_emulation_direct(url, "clear_default_background_color_override"))
    _echo("Cleared default background color override")


@emulation_app.command("clear-device-posture")
def emulation_clear_device_posture(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Clear the device posture override."""
    _run_async(_emulation_direct(url, "clear_device_posture_override"))
    _echo("Cleared device posture override")


@emulation_app.command("clear-display-features")
def emulation_clear_display_features(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Clear the display features override."""
    _run_async(_emulation_direct(url, "clear_display_features_override"))
    _echo("Cleared display features override")


@emulation_app.command("clear-geolocation")
def emulation_clear_geolocation(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Clear the geolocation override."""
    _run_async(_emulation_direct(url, "clear_geolocation_override"))
    _echo("Cleared geolocation override")


@emulation_app.command("clear-timezone")
def emulation_clear_timezone(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Clear the timezone override."""
    _run_async(_emulation_direct(url, "clear_timezone_override"))
    _echo("Cleared timezone override")


@emulation_app.command("sensor-info")
def emulation_sensor_info(
    url: str = typer.Argument(..., help="URL to navigate to"),
    sensor_type: str = typer.Argument(..., help="Sensor type (e.g. 'accelerometer')"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get information about overridden sensors."""
    result = _run_async(
        _emulation_direct(url, "get_overridden_sensor_information", sensor_type=sensor_type)
    )
    if result is None:
        return
    _write_json_output(result, output, "sensorInfo")


@emulation_app.command("screen-infos")
def emulation_screen_infos(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get information about all virtual screens."""
    result = _run_async(_emulation_direct(url, "get_screen_infos"))
    if result is None:
        return
    _write_json_output(result, output, "screenInfos")


@emulation_app.command("remove-screen")
def emulation_remove_screen(
    url: str = typer.Argument(..., help="URL to navigate to"),
    screen_id: str = typer.Argument(..., help="Screen ID to remove"),
) -> None:
    """Remove a virtual screen by ID."""
    _run_async(_emulation_direct(url, "remove_screen", screen_id=screen_id))
    _echo(f"Removed screen {screen_id}")


@emulation_app.command("reset-page-scale")
def emulation_reset_page_scale(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Reset the page scale factor to its default."""
    _run_async(_emulation_direct(url, "reset_page_scale_factor"))
    _echo("Reset page scale factor")


@emulation_app.command("auto-dark-mode")
def emulation_auto_dark_mode(
    url: str = typer.Argument(..., help="URL to navigate to"),
    enabled: bool = typer.Argument(..., help="Enable or disable auto dark mode"),
) -> None:
    """Enable or disable auto dark mode override."""
    _run_async(_emulation_direct(url, "set_auto_dark_mode_override", enabled=enabled))
    _echo(f"Auto dark mode override set to {enabled}")


@emulation_app.command("automation-override")
def emulation_automation_override(
    url: str = typer.Argument(..., help="URL to navigate to"),
    enabled: bool = typer.Argument(..., help="Enable or disable automation override"),
) -> None:
    """Enable or disable automation override."""
    _run_async(_emulation_direct(url, "set_automation_override", enabled=enabled))
    _echo(f"Automation override set to {enabled}")


@emulation_app.command("cpu-throttling-rate")
def emulation_cpu_throttling_rate(
    url: str = typer.Argument(..., help="URL to navigate to"),
    rate: float = typer.Argument(..., help="Throttling rate multiplier (e.g. 4 = 4x slower)"),
) -> None:
    """Set CPU throttling rate."""
    _run_async(_emulation_direct(url, "set_cpu_throttling_rate", rate=rate))
    _echo(f"CPU throttling rate set to {rate}")


@emulation_app.command("data-saver")
def emulation_data_saver(
    url: str = typer.Argument(..., help="URL to navigate to"),
    enabled: bool = typer.Argument(..., help="Enable or disable data saver"),
) -> None:
    """Enable or disable data saver override."""
    _run_async(_emulation_direct(url, "set_data_saver_override", enabled=enabled))
    _echo(f"Data saver override set to {enabled}")


@emulation_app.command("default-bg-color")
def emulation_default_bg_color(
    url: str = typer.Argument(..., help="URL to navigate to"),
    color_json: str = typer.Argument(
        ..., help='RGBA color as JSON (e.g. {"r":0,"g":0,"b":0,"a":1})'
    ),
) -> None:
    """Override the default background color."""
    import json

    color = _safe_json_loads(color_json, "color")
    _run_async(_emulation_direct(url, "set_default_background_color_override", color=color))
    _echo("Default background color override set")


@emulation_app.command("device-posture")
def emulation_device_posture(
    url: str = typer.Argument(..., help="URL to navigate to"),
    posture: str = typer.Argument(..., help="Device posture (e.g. 'continuous', 'folded')"),
) -> None:
    """Override the device posture."""
    _run_async(_emulation_direct(url, "set_device_posture_override", posture=posture))
    _echo(f"Device posture set to {posture}")


@emulation_app.command("disabled-image-types")
def emulation_disabled_image_types(
    url: str = typer.Argument(..., help="URL to navigate to"),
    image_types: list[str] = typer.Argument(..., help="Image types to disable"),
) -> None:
    """Disable the given image types from loading."""
    _run_async(_emulation_direct(url, "set_disabled_image_types", image_types=image_types))
    _echo(f"Disabled image types: {image_types}")


@emulation_app.command("display-features")
def emulation_display_features(
    url: str = typer.Argument(..., help="URL to navigate to"),
    features_json: str = typer.Argument(..., help="Display features as JSON array"),
) -> None:
    """Override display features."""
    import json

    features = _safe_json_loads(features_json, "features")
    _run_async(_emulation_direct(url, "set_display_features_override", features=features))
    _echo("Display features override set")


@emulation_app.command("document-cookie-disabled")
def emulation_document_cookie_disabled(
    url: str = typer.Argument(..., help="URL to navigate to"),
    disabled: bool = typer.Argument(..., help="Disable or enable document cookies"),
) -> None:
    """Disable or enable document cookies."""
    _run_async(_emulation_direct(url, "set_document_cookie_disabled", disabled=disabled))
    _echo(f"Document cookies disabled: {disabled}")


@emulation_app.command("emit-touch-for-mouse")
def emulation_emit_touch_for_mouse(
    url: str = typer.Argument(..., help="URL to navigate to"),
    enabled: bool = typer.Argument(..., help="Enable or disable touch events for mouse"),
) -> None:
    """Enable or disable touch event emulation for mouse input."""
    _run_async(_emulation_direct(url, "set_emit_touch_events_for_mouse", enabled=enabled))
    _echo(f"Emit touch events for mouse: {enabled}")


@emulation_app.command("media-feature")
def emulation_media_feature(
    url: str = typer.Argument(..., help="URL to navigate to"),
    features_json: str = typer.Argument(
        ..., help='Media features as JSON (e.g. [{"name":"prefers-color-scheme","value":"dark"}])'
    ),
) -> None:
    """Set emulated media features."""
    import json

    features = _safe_json_loads(features_json, "features")
    _run_async(_emulation_direct(url, "set_emulated_media_feature", features=features))
    _echo("Emulated media features set")


@emulation_app.command("os-text-scale")
def emulation_os_text_scale(
    url: str = typer.Argument(..., help="URL to navigate to"),
    scale: float = typer.Argument(..., help="OS text scale factor (e.g. 1.5)"),
) -> None:
    """Override the OS text scale factor."""
    _run_async(_emulation_direct(url, "set_emulated_os_text_scale", scale=scale))
    _echo(f"OS text scale set to {scale}")


@emulation_app.command("focus-emulation")
def emulation_focus_emulation(
    url: str = typer.Argument(..., help="URL to navigate to"),
    enabled: bool = typer.Argument(..., help="Enable or disable focus emulation"),
) -> None:
    """Enable or disable focus emulation."""
    _run_async(_emulation_direct(url, "set_focus_emulation_enabled", enabled=enabled))
    _echo(f"Focus emulation: {enabled}")


@emulation_app.command("geolocation-override")
def emulation_geolocation_override(
    url: str = typer.Argument(..., help="URL to navigate to"),
    latitude: float = typer.Argument(..., help="Latitude"),
    longitude: float = typer.Argument(..., help="Longitude"),
    accuracy: float = typer.Argument(100.0, help="Accuracy in meters"),
) -> None:
    """Override the geolocation position."""
    _run_async(
        _emulation_direct(
            url,
            "set_geolocation_override",
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
        )
    )
    _echo(f"Geolocation override set to ({latitude}, {longitude})")


@emulation_app.command("hardware-concurrency")
def emulation_hardware_concurrency(
    url: str = typer.Argument(..., help="URL to navigate to"),
    concurrency: int = typer.Argument(..., help="Hardware concurrency value"),
) -> None:
    """Override the hardware concurrency."""
    _run_async(_emulation_direct(url, "set_hardware_concurrency_override", concurrency=concurrency))
    _echo(f"Hardware concurrency set to {concurrency}")


@emulation_app.command("locale-override")
def emulation_locale_override(
    url: str = typer.Argument(..., help="URL to navigate to"),
    locale: str = typer.Argument(..., help="Locale (e.g. 'en-US', 'fr-FR')"),
) -> None:
    """Override the browser locale."""
    _run_async(_emulation_direct(url, "set_locale_override", locale=locale))
    _echo(f"Locale override set to {locale}")


@emulation_app.command("navigator-overrides")
def emulation_navigator_overrides(
    url: str = typer.Argument(..., help="URL to navigate to"),
    navigator_json: str = typer.Argument(..., help="Navigator properties as JSON"),
) -> None:
    """Override navigator properties."""
    import json

    navigator = _safe_json_loads(navigator_json, "navigator")
    _run_async(_emulation_direct(url, "set_navigator_overrides", navigator=navigator))
    _echo("Navigator overrides set")


@emulation_app.command("page-scale-factor")
def emulation_page_scale_factor(
    url: str = typer.Argument(..., help="URL to navigate to"),
    factor: float = typer.Argument(..., help="Page scale factor (e.g. 2.0 for 2x zoom)"),
) -> None:
    """Set the page scale factor."""
    _run_async(_emulation_direct(url, "set_page_scale_factor", factor=factor))
    _echo(f"Page scale factor set to {factor}")


@emulation_app.command("pressure-source")
def emulation_pressure_source(
    url: str = typer.Argument(..., help="URL to navigate to"),
    source: str = typer.Argument(..., help="Pressure source type"),
    enabled: bool = typer.Argument(..., help="Enable or disable"),
) -> None:
    """Enable or disable pressure source override."""
    _run_async(
        _emulation_direct(
            url, "set_pressure_source_override_enabled", source=source, enabled=enabled
        )
    )
    _echo(f"Pressure source {source} override: {enabled}")


@emulation_app.command("pressure-state")
def emulation_pressure_state(
    url: str = typer.Argument(..., help="URL to navigate to"),
    source: str = typer.Argument(..., help="Pressure source type"),
    state: str = typer.Argument(..., help="Pressure state"),
    value: float = typer.Argument(..., help="Pressure value"),
) -> None:
    """Override the pressure state."""
    _run_async(
        _emulation_direct(
            url, "set_pressure_state_override", source=source, state=state, value=value
        )
    )
    _echo(f"Pressure state override set for {source}")


@emulation_app.command("primary-screen")
def emulation_primary_screen(
    url: str = typer.Argument(..., help="URL to navigate to"),
    screen_id: str = typer.Argument(..., help="Screen ID to set as primary"),
) -> None:
    """Set the primary screen by ID."""
    _run_async(_emulation_direct(url, "set_primary_screen", screen_id=screen_id))
    _echo(f"Primary screen set to {screen_id}")


@emulation_app.command("safe-area-insets")
def emulation_safe_area_insets(
    url: str = typer.Argument(..., help="URL to navigate to"),
    insets_json: str = typer.Argument(..., help="Safe area insets as JSON"),
) -> None:
    """Override the safe area insets."""
    import json

    insets = _safe_json_loads(insets_json, "insets")
    _run_async(_emulation_direct(url, "set_safe_area_insets_override", insets=insets))
    _echo("Safe area insets override set")


@emulation_app.command("scrollbars-hidden")
def emulation_scrollbars_hidden(
    url: str = typer.Argument(..., help="URL to navigate to"),
    hidden: bool = typer.Argument(..., help="Hide or show scrollbars"),
) -> None:
    """Hide or show scrollbars."""
    _run_async(_emulation_direct(url, "set_scrollbars_hidden", hidden=hidden))
    _echo(f"Scrollbars hidden: {hidden}")


@emulation_app.command("sensor-override-enabled")
def emulation_sensor_override_enabled(
    url: str = typer.Argument(..., help="URL to navigate to"),
    sensor_type: str = typer.Argument(..., help="Sensor type (e.g. 'accelerometer')"),
    enabled: bool = typer.Argument(..., help="Enable or disable"),
) -> None:
    """Enable or disable sensor override."""
    _run_async(
        _emulation_direct(
            url, "set_sensor_override_enabled", sensor_type=sensor_type, enabled=enabled
        )
    )
    _echo(f"Sensor {sensor_type} override: {enabled}")


@emulation_app.command("sensor-override-readings")
def emulation_sensor_override_readings(
    url: str = typer.Argument(..., help="URL to navigate to"),
    sensor_type: str = typer.Argument(..., help="Sensor type"),
    readings_json: str = typer.Argument(..., help="Sensor readings as JSON array"),
) -> None:
    """Override sensor readings."""
    import json

    readings = _safe_json_loads(readings_json, "readings")
    _run_async(
        _emulation_direct(
            url, "set_sensor_override_readings", sensor_type=sensor_type, readings=readings
        )
    )
    _echo(f"Sensor {sensor_type} readings overridden")


@emulation_app.command("small-viewport-diff")
def emulation_small_viewport_diff(
    url: str = typer.Argument(..., help="URL to navigate to"),
    difference: float = typer.Argument(..., help="Small viewport height difference"),
) -> None:
    """Override the small viewport height difference."""
    _run_async(
        _emulation_direct(
            url, "set_small_viewport_height_difference_override", difference=difference
        )
    )
    _echo(f"Small viewport height difference set to {difference}")


@emulation_app.command("timezone-override")
def emulation_timezone_override(
    url: str = typer.Argument(..., help="URL to navigate to"),
    timezone_id: str = typer.Argument(..., help="IANA timezone ID (e.g. 'America/New_York')"),
) -> None:
    """Override the timezone."""
    _run_async(_emulation_direct(url, "set_timezone_override", timezone_id=timezone_id))
    _echo(f"Timezone override set to {timezone_id}")


@emulation_app.command("touch-emulation")
def emulation_touch_emulation(
    url: str = typer.Argument(..., help="URL to navigate to"),
    enabled: bool = typer.Argument(..., help="Enable or disable touch emulation"),
    max_touch_points: int = typer.Argument(5, help="Max touch points"),
) -> None:
    """Enable or disable touch emulation."""
    _run_async(
        _emulation_direct(
            url, "set_touch_emulation_enabled", enabled=enabled, max_touch_points=max_touch_points
        )
    )
    _echo(f"Touch emulation: {enabled}")


@emulation_app.command("user-agent-override")
def emulation_user_agent_override(
    url: str = typer.Argument(..., help="URL to navigate to"),
    user_agent: str = typer.Argument(..., help="User agent string"),
    accept_language: str = typer.Argument("", help="Accept-Language header value"),
    platform: str = typer.Argument("", help="Platform string"),
) -> None:
    """Override the user agent string."""
    _run_async(
        _emulation_direct(
            url,
            "set_user_agent_override",
            user_agent=user_agent,
            accept_language=accept_language,
            platform=platform,
        )
    )
    _echo(f"User agent override set to {user_agent}")


@emulation_app.command("virtual-time-policy")
def emulation_virtual_time_policy(
    url: str = typer.Argument(..., help="URL to navigate to"),
    policy: str = typer.Argument(..., help="Virtual time policy (e.g. 'advance', 'pause')"),
    budget: int = typer.Argument(0, help="Virtual time budget in ms"),
) -> None:
    """Set the virtual time policy."""
    _run_async(_emulation_direct(url, "set_virtual_time_policy", policy=policy, budget=budget))
    _echo(f"Virtual time policy set to {policy}")


@emulation_app.command("update-screen")
def emulation_update_screen(
    url: str = typer.Argument(..., help="URL to navigate to"),
    screen_id: str = typer.Argument(..., help="Screen ID to update"),
    screen_json: str = typer.Argument(..., help="Screen configuration as JSON"),
) -> None:
    """Update a virtual screen by ID."""
    import json

    screen = _safe_json_loads(screen_json, "screen")
    _run_async(_emulation_direct(url, "update_screen", screen_id=screen_id, screen=screen))
    _echo(f"Screen {screen_id} updated")


async def _emulation_direct(url: str, action: str, **kwargs: Any) -> Any:
    """Launch backend, navigate, and run an emulation action."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url)
        if action == "add_screen":
            await backend.add_screen(kwargs["screen"])
            return None
        if action == "can_emulate":
            return await backend.can_emulate()
        if action == "clear_auto_dark_mode_override":
            await backend.clear_auto_dark_mode_override()
            return None
        if action == "clear_default_background_color_override":
            await backend.clear_default_background_color_override()
            return None
        if action == "clear_device_posture_override":
            await backend.clear_device_posture_override()
            return None
        if action == "clear_display_features_override":
            await backend.clear_display_features_override()
            return None
        if action == "clear_geolocation_override":
            await backend.clear_geolocation_override()
            return None
        if action == "clear_timezone_override":
            await backend.clear_timezone_override()
            return None
        if action == "get_overridden_sensor_information":
            return await backend.get_overridden_sensor_information(kwargs["sensor_type"])
        if action == "get_screen_infos":
            return await backend.get_screen_infos()
        if action == "remove_screen":
            await backend.remove_screen(kwargs["screen_id"])
            return None
        if action == "reset_page_scale_factor":
            await backend.reset_page_scale_factor()
            return None
        if action == "set_auto_dark_mode_override":
            await backend.set_auto_dark_mode_override(kwargs["enabled"])
            return None
        if action == "set_automation_override":
            await backend.set_automation_override(kwargs["enabled"])
            return None
        if action == "set_cpu_throttling_rate":
            await backend.set_cpu_throttling_rate(kwargs["rate"])
            return None
        if action == "set_data_saver_override":
            await backend.set_data_saver_override(kwargs["enabled"])
            return None
        if action == "set_default_background_color_override":
            await backend.set_default_background_color_override(kwargs["color"])
            return None
        if action == "set_device_posture_override":
            await backend.set_device_posture_override(kwargs["posture"])
            return None
        if action == "set_disabled_image_types":
            await backend.set_disabled_image_types(kwargs["image_types"])
            return None
        if action == "set_display_features_override":
            await backend.set_display_features_override(kwargs["features"])
            return None
        if action == "set_document_cookie_disabled":
            await backend.set_document_cookie_disabled(kwargs["disabled"])
            return None
        if action == "set_emit_touch_events_for_mouse":
            await backend.set_emit_touch_events_for_mouse(kwargs["enabled"])
            return None
        if action == "set_emulated_media_feature":
            await backend.set_emulated_media_feature(kwargs["features"])
            return None
        if action == "set_emulated_os_text_scale":
            await backend.set_emulated_os_text_scale(kwargs["scale"])
            return None
        if action == "set_focus_emulation_enabled":
            await backend.set_focus_emulation_enabled(kwargs["enabled"])
            return None
        if action == "set_geolocation_override":
            await backend.set_geolocation_override(
                kwargs["latitude"], kwargs["longitude"], kwargs["accuracy"]
            )
            return None
        if action == "set_hardware_concurrency_override":
            await backend.set_hardware_concurrency_override(kwargs["concurrency"])
            return None
        if action == "set_locale_override":
            await backend.set_locale_override(kwargs["locale"])
            return None
        if action == "set_navigator_overrides":
            await backend.set_navigator_overrides(kwargs["navigator"])
            return None
        if action == "set_page_scale_factor":
            await backend.set_page_scale_factor(kwargs["factor"])
            return None
        if action == "set_pressure_source_override_enabled":
            await backend.set_pressure_source_override_enabled(kwargs["source"], kwargs["enabled"])
            return None
        if action == "set_pressure_state_override":
            await backend.set_pressure_state_override(
                kwargs["source"], kwargs["state"], kwargs["value"]
            )
            return None
        if action == "set_primary_screen":
            await backend.set_primary_screen(kwargs["screen_id"])
            return None
        if action == "set_safe_area_insets_override":
            await backend.set_safe_area_insets_override(kwargs["insets"])
            return None
        if action == "set_scrollbars_hidden":
            await backend.set_scrollbars_hidden(kwargs["hidden"])
            return None
        if action == "set_sensor_override_enabled":
            await backend.set_sensor_override_enabled(kwargs["sensor_type"], kwargs["enabled"])
            return None
        if action == "set_sensor_override_readings":
            await backend.set_sensor_override_readings(kwargs["sensor_type"], kwargs["readings"])
            return None
        if action == "set_small_viewport_height_difference_override":
            await backend.set_small_viewport_height_difference_override(kwargs["difference"])
            return None
        if action == "set_timezone_override":
            await backend.set_timezone_override(kwargs["timezone_id"])
            return None
        if action == "set_touch_emulation_enabled":
            await backend.set_touch_emulation_enabled(kwargs["enabled"], kwargs["max_touch_points"])
            return None
        if action == "set_user_agent_override":
            await backend.set_user_agent_override(
                kwargs["user_agent"], kwargs["accept_language"], kwargs["platform"]
            )
            return None
        if action == "set_virtual_time_policy":
            await backend.set_virtual_time_policy(kwargs["policy"], kwargs["budget"])
            return None
        if action == "update_screen":
            await backend.update_screen(kwargs["screen_id"], kwargs["screen"])
            return None
        raise ValueError(f"Unknown emulation action: {action}")
    finally:
        await _close_backend(backend)


# ── DeviceAccess commands ────────────────────────────────


@device_access_app.command("cancel-prompt")
def device_access_cancel_prompt_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    prompt_id: str = typer.Option(..., "--id", help="Prompt ID"),
) -> None:
    """Cancel a device access prompt by ID."""
    _run_async(_debug_direct(url, lambda b: b.device_access_cancel_prompt(prompt_id)))
    _echo(f"Prompt cancelled: {prompt_id}")


@device_access_app.command("disable")
def device_access_disable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the DeviceAccess domain."""
    _run_async(_debug_direct(url, lambda b: b.device_access_disable()))
    _echo("DeviceAccess disabled")


@device_access_app.command("enable")
def device_access_enable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the DeviceAccess domain."""
    _run_async(_debug_direct(url, lambda b: b.device_access_enable()))
    _echo("DeviceAccess enabled")


@device_access_app.command("select-prompt")
def device_access_select_prompt_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    prompt_id: str = typer.Option(..., "--id", help="Prompt ID"),
    device_id: str = typer.Option(..., "--device-id", help="Device ID"),
) -> None:
    """Select a device in a device access prompt."""
    _run_async(_debug_direct(url, lambda b: b.device_access_select_prompt(prompt_id, device_id)))
    _echo(f"Selected device {device_id} for prompt {prompt_id}")


# ── DeviceOrientation commands ───────────────────────────


@device_orientation_app.command("clear-override")
def device_orientation_clear_override_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Clear device orientation override."""
    _run_async(_debug_direct(url, lambda b: b.device_orientation_clear_override()))
    _echo("Device orientation override cleared")


@device_orientation_app.command("set-override")
def device_orientation_set_override_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    alpha: float = typer.Option(..., "--alpha", help="Alpha angle"),
    beta: float = typer.Option(..., "--beta", help="Beta angle"),
    gamma: float = typer.Option(..., "--gamma", help="Gamma angle"),
) -> None:
    """Set device orientation override."""
    _run_async(_debug_direct(url, lambda b: b.device_orientation_set_override(alpha, beta, gamma)))
    _echo(f"Device orientation set: alpha={alpha}, beta={beta}, gamma={gamma}")


# ── DigitalCredentials commands ──────────────────────────


@digital_credentials_app.command("set-virtual-wallet")
def digital_credentials_set_virtual_wallet_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    behavior: str = typer.Argument(..., help="Behavior (JSON)"),
) -> None:
    """Set the virtual wallet behavior for digital credentials."""
    import json

    beh = _safe_json_loads(behavior, "behavior")
    _run_async(_debug_direct(url, lambda b: b.digital_credentials_set_virtual_wallet_behavior(beh)))
    _echo("Virtual wallet behavior set")


# ── DOMSnapshot commands ─────────────────────────────────


@dom_snapshot_app.command("capture")
def dom_snapshot_capture_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Capture a DOM snapshot of the current page."""
    result = _run_async(_debug_direct(url, lambda b: b.dom_snapshot_capture_snapshot()))
    if result is None:
        return
    _write_json_output(result, output, "DOM snapshot")


@dom_snapshot_app.command("disable")
def dom_snapshot_disable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the DOMSnapshot domain."""
    _run_async(_debug_direct(url, lambda b: b.dom_snapshot_disable()))
    _echo("DOMSnapshot disabled")


@dom_snapshot_app.command("enable")
def dom_snapshot_enable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the DOMSnapshot domain."""
    _run_async(_debug_direct(url, lambda b: b.dom_snapshot_enable()))
    _echo("DOMSnapshot enabled")


@dom_snapshot_app.command("get")
def dom_snapshot_get_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get a DOM snapshot of the current page."""
    result = _run_async(_debug_direct(url, lambda b: b.dom_snapshot_get_snapshot()))
    if result is None:
        return
    _write_json_output(result, output, "DOM snapshot")


# ── DOMStorage commands ──────────────────────────────────


@dom_storage_app.command("clear")
def dom_storage_clear_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    storage_id: str = typer.Argument(
        ..., help="Storage ID (JSON: {securityOrigin, isLocalStorage})"
    ),
) -> None:
    """Clear all entries in a DOM storage."""
    import json

    sid = _safe_json_loads(storage_id, "storage_id")
    _run_async(_debug_direct(url, lambda b: b.dom_storage_clear(sid)))
    _echo("DOM storage cleared")


@dom_storage_app.command("clear-items")
def dom_storage_clear_items_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    storage_id: str = typer.Argument(..., help="Storage ID (JSON)"),
) -> None:
    """Clear all items in a DOM storage."""
    import json

    sid = _safe_json_loads(storage_id, "storage_id")
    _run_async(_debug_direct(url, lambda b: b.dom_storage_clear_items(sid)))
    _echo("DOM storage items cleared")


@dom_storage_app.command("disable")
def dom_storage_disable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the DOMStorage domain."""
    _run_async(_debug_direct(url, lambda b: b.dom_storage_disable()))
    _echo("DOMStorage disabled")


@dom_storage_app.command("enable")
def dom_storage_enable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the DOMStorage domain."""
    _run_async(_debug_direct(url, lambda b: b.dom_storage_enable()))
    _echo("DOMStorage enabled")


@dom_storage_app.command("items")
def dom_storage_items_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    storage_id: str = typer.Argument(..., help="Storage ID (JSON)"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get all items in a DOM storage."""
    import json

    sid = _safe_json_loads(storage_id, "storage_id")
    result = _run_async(_debug_direct(url, lambda b: b.dom_storage_get_items(sid)))
    if result is None:
        return
    _write_json_output(result, output, "DOM storage items")


@dom_storage_app.command("remove-item")
def dom_storage_remove_item_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    storage_id: str = typer.Argument(..., help="Storage ID (JSON)"),
    key: str = typer.Option(..., "--key", help="Item key"),
) -> None:
    """Remove an item from a DOM storage."""
    import json

    sid = _safe_json_loads(storage_id, "storage_id")
    _run_async(_debug_direct(url, lambda b: b.dom_storage_remove_item(sid, key)))
    _echo(f"Item removed: {key}")


@dom_storage_app.command("set-item")
def dom_storage_set_item_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    storage_id: str = typer.Argument(..., help="Storage ID (JSON)"),
    key: str = typer.Option(..., "--key", help="Item key"),
    value: str = typer.Option(..., "--value", help="Item value"),
) -> None:
    """Set an item in a DOM storage."""
    import json

    sid = _safe_json_loads(storage_id, "storage_id")
    _run_async(_debug_direct(url, lambda b: b.dom_storage_set_item(sid, key, value)))
    _echo(f"Item set: {key}={value}")


# ── EventBreakpoints commands ────────────────────────────


@event_breakpoints_app.command("clear-instrumentation")
def event_breakpoints_clear_instrumentation_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    instrumentation_name: str = typer.Argument(..., help="Instrumentation name"),
) -> None:
    """Clear an instrumentation breakpoint for events."""
    _run_async(
        _debug_direct(
            url,
            lambda b: b.event_breakpoints_clear_instrumentation_breakpoint(instrumentation_name),
        )
    )
    _echo(f"Breakpoint cleared: {instrumentation_name}")


@event_breakpoints_app.command("disable")
def event_breakpoints_disable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the EventBreakpoints domain."""
    _run_async(_debug_direct(url, lambda b: b.event_breakpoints_disable()))
    _echo("EventBreakpoints disabled")


@event_breakpoints_app.command("remove-instrumentation")
def event_breakpoints_remove_instrumentation_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    instrumentation_name: str = typer.Argument(..., help="Instrumentation name"),
) -> None:
    """Remove an instrumentation breakpoint for events."""
    _run_async(
        _debug_direct(
            url,
            lambda b: b.event_breakpoints_remove_instrumentation_breakpoint(instrumentation_name),
        )
    )
    _echo(f"Breakpoint removed: {instrumentation_name}")


@event_breakpoints_app.command("set-instrumentation")
def event_breakpoints_set_instrumentation_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    instrumentation_name: str = typer.Argument(..., help="Instrumentation name"),
) -> None:
    """Set an instrumentation breakpoint for events."""
    _run_async(
        _debug_direct(
            url, lambda b: b.event_breakpoints_set_instrumentation_breakpoint(instrumentation_name)
        )
    )
    _echo(f"Breakpoint set: {instrumentation_name}")


# ── Extensions commands ──────────────────────────────────


@extensions_app.command("clear-storage-items")
def extensions_clear_storage_items_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    extension_id: str = typer.Argument(..., help="Extension ID"),
    storage_type: str = typer.Option(..., "--storage-type", help="Storage type"),
) -> None:
    """Clear storage items for an extension."""
    _run_async(
        _debug_direct(url, lambda b: b.extensions_clear_storage_items(extension_id, storage_type))
    )
    _echo(f"Storage cleared: {extension_id}/{storage_type}")


@extensions_app.command("get-storage-items")
def extensions_get_storage_items_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    extension_id: str = typer.Argument(..., help="Extension ID"),
    storage_type: str = typer.Option(..., "--storage-type", help="Storage type"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get storage items for an extension."""
    result = _run_async(
        _debug_direct(url, lambda b: b.extensions_get_storage_items(extension_id, storage_type))
    )
    if result is None:
        return
    _write_json_output(result, output, "Storage items")


@extensions_app.command("remove-storage-items")
def extensions_remove_storage_items_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    extension_id: str = typer.Argument(..., help="Extension ID"),
    storage_type: str = typer.Option(..., "--storage-type", help="Storage type"),
    keys: str = typer.Argument(..., help="Keys (JSON array)"),
) -> None:
    """Remove storage items from an extension."""
    import json

    key_list = _safe_json_loads(keys, "keys")
    _run_async(
        _debug_direct(
            url, lambda b: b.extensions_remove_storage_items(extension_id, storage_type, key_list)
        )
    )
    _echo(f"Items removed: {keys}")


@extensions_app.command("set-storage-items")
def extensions_set_storage_items_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    extension_id: str = typer.Argument(..., help="Extension ID"),
    storage_type: str = typer.Option(..., "--storage-type", help="Storage type"),
    values: str = typer.Argument(..., help="Values (JSON array)"),
) -> None:
    """Set storage items for an extension."""
    import json

    val_list = _safe_json_loads(values, "values")
    _run_async(
        _debug_direct(
            url, lambda b: b.extensions_set_storage_items(extension_id, storage_type, val_list)
        )
    )
    _echo("Storage items set")


@extensions_app.command("trigger-action")
def extensions_trigger_action_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    extension_id: str = typer.Argument(..., help="Extension ID"),
    action: str = typer.Argument(..., help="Action name"),
) -> None:
    """Trigger an action on an extension."""
    _run_async(_debug_direct(url, lambda b: b.extensions_trigger_action(extension_id, action)))
    _echo(f"Action triggered: {action}")


# ── FedCm commands ───────────────────────────────────────


@fed_cm_app.command("click-dialog-button")
def fed_cm_click_dialog_button_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    dialog_id: str = typer.Argument(..., help="Dialog ID"),
    button_index: int = typer.Argument(..., help="Button index"),
) -> None:
    """Click a button in a FedCm dialog."""
    _run_async(_debug_direct(url, lambda b: b.fed_cm_click_dialog_button(dialog_id, button_index)))
    _echo(f"Button clicked: {button_index}")


@fed_cm_app.command("disable")
def fed_cm_disable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the FedCm domain."""
    _run_async(_debug_direct(url, lambda b: b.fed_cm_disable()))
    _echo("FedCm disabled")


@fed_cm_app.command("dismiss-dialog")
def fed_cm_dismiss_dialog_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    dialog_id: str = typer.Argument(..., help="Dialog ID"),
) -> None:
    """Dismiss a FedCm dialog."""
    _run_async(_debug_direct(url, lambda b: b.fed_cm_dismiss_dialog(dialog_id)))
    _echo(f"Dialog dismissed: {dialog_id}")


@fed_cm_app.command("enable")
def fed_cm_enable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the FedCm domain."""
    _run_async(_debug_direct(url, lambda b: b.fed_cm_enable()))
    _echo("FedCm enabled")


@fed_cm_app.command("open-url")
def fed_cm_open_url_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    dialog_id: str = typer.Argument(..., help="Dialog ID"),
    account_index: int = typer.Argument(..., help="Account index"),
    target_url: str = typer.Argument(..., help="URL to open"),
) -> None:
    """Open a URL from a FedCm dialog."""
    _run_async(
        _debug_direct(url, lambda b: b.fed_cm_open_url(dialog_id, account_index, target_url))
    )
    _echo(f"URL opened: {target_url}")


@fed_cm_app.command("reset-cooldown")
def fed_cm_reset_cooldown_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Reset the FedCm cooldown."""
    _run_async(_debug_direct(url, lambda b: b.fed_cm_reset_cooldown()))
    _echo("FedCm cooldown reset")


@fed_cm_app.command("select-account")
def fed_cm_select_account_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    dialog_id: str = typer.Argument(..., help="Dialog ID"),
    account_index: int = typer.Argument(..., help="Account index"),
) -> None:
    """Select an account in a FedCm dialog."""
    _run_async(_debug_direct(url, lambda b: b.fed_cm_select_account(dialog_id, account_index)))
    _echo(f"Account selected: {account_index}")


# ── Fetch commands ───────────────────────────────────────


@fetch_app.command("continue-request")
def fetch_continue_request_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    request_id: str = typer.Argument(..., help="Request ID"),
) -> None:
    """Continue a paused request."""
    _run_async(_debug_direct(url, lambda b: b.fetch_continue_request(request_id)))
    _echo(f"Request continued: {request_id}")


@fetch_app.command("continue-request-with-auth")
def fetch_continue_request_with_auth_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    request_id: str = typer.Argument(..., help="Request ID"),
    auth_response: str = typer.Argument(..., help="Auth challenge response (JSON)"),
) -> None:
    """Continue a paused request with authentication."""
    import json

    resp = _safe_json_loads(auth_response, "auth_response")
    _run_async(_debug_direct(url, lambda b: b.fetch_continue_request_with_auth(request_id, resp)))
    _echo(f"Request continued with auth: {request_id}")


@fetch_app.command("continue-response")
def fetch_continue_response_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    request_id: str = typer.Argument(..., help="Request ID"),
    response_code: int = typer.Option(200, "--code", help="Response code"),
) -> None:
    """Continue a paused response."""
    _run_async(_debug_direct(url, lambda b: b.fetch_continue_response(request_id, response_code)))
    _echo(f"Response continued: {request_id}")


@fetch_app.command("continue-with-auth")
def fetch_continue_with_auth_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    request_id: str = typer.Argument(..., help="Request ID"),
    auth_response: str = typer.Argument(..., help="Auth challenge response (JSON)"),
) -> None:
    """Continue a paused request with auth challenge response."""
    import json

    resp = _safe_json_loads(auth_response, "auth_response")
    _run_async(_debug_direct(url, lambda b: b.fetch_continue_with_auth(request_id, resp)))
    _echo(f"Request continued with auth: {request_id}")


@fetch_app.command("disable")
def fetch_disable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the Fetch domain."""
    _run_async(_debug_direct(url, lambda b: b.fetch_disable()))
    _echo("Fetch disabled")


@fetch_app.command("enable")
def fetch_enable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the Fetch domain."""
    _run_async(_debug_direct(url, lambda b: b.fetch_enable()))
    _echo("Fetch enabled")


@fetch_app.command("fail-request")
def fetch_fail_request_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    request_id: str = typer.Argument(..., help="Request ID"),
    error_reason: str = typer.Argument(..., help="Error reason"),
) -> None:
    """Fail a paused request with an error."""
    _run_async(_debug_direct(url, lambda b: b.fetch_fail_request(request_id, error_reason)))
    _echo(f"Request failed: {request_id}")


@fetch_app.command("fulfill-request")
def fetch_fulfill_request_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    request_id: str = typer.Argument(..., help="Request ID"),
    response_code: int = typer.Option(200, "--code", help="Response code"),
) -> None:
    """Fulfill a paused request with a response."""
    _run_async(_debug_direct(url, lambda b: b.fetch_fulfill_request(request_id, response_code)))
    _echo(f"Request fulfilled: {request_id}")


@fetch_app.command("get-request-post-data")
def fetch_get_request_post_data_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    request_id: str = typer.Argument(..., help="Request ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the POST data of a paused request."""
    result = _run_async(_debug_direct(url, lambda b: b.fetch_get_request_post_data(request_id)))
    if result is None:
        return
    _write_json_output({"postData": result}, output, "POST data")


@fetch_app.command("take-response-body")
def fetch_take_response_body_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    request_id: str = typer.Argument(..., help="Request ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Take the response body of a paused request as a stream."""
    result = _run_async(
        _debug_direct(url, lambda b: b.fetch_take_response_body_as_stream(request_id))
    )
    if result is None:
        return
    _write_json_output(result, output, "Response body stream")


# ── FileSystem commands ──────────────────────────────────


@file_system_app.command("get-directory")
def file_system_get_directory_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    origin: str = typer.Argument(..., help="Origin"),
    fs_type: str = typer.Argument(..., help="File system type"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get a file system directory by origin and type."""
    result = _run_async(_debug_direct(url, lambda b: b.file_system_get_directory(origin, fs_type)))
    if result is None:
        return
    _write_json_output(result, output, "File system directory")


# ── HeadlessExperimental commands ────────────────────────


@headless_experimental_app.command("begin-frame")
def headless_experimental_begin_frame_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Begin a new frame in headless mode."""
    result = _run_async(_debug_direct(url, lambda b: b.headless_experimental_begin_frame()))
    if result is None:
        return
    _write_json_output(result, output, "Frame")


@headless_experimental_app.command("disable")
def headless_experimental_disable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the HeadlessExperimental domain."""
    _run_async(_debug_direct(url, lambda b: b.headless_experimental_disable()))
    _echo("HeadlessExperimental disabled")


@headless_experimental_app.command("enable")
def headless_experimental_enable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the HeadlessExperimental domain."""
    _run_async(_debug_direct(url, lambda b: b.headless_experimental_enable()))
    _echo("HeadlessExperimental enabled")


# ── Inspector commands ───────────────────────────────────


@inspector_app.command("disable")
def inspector_disable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the Inspector domain."""
    _run_async(_debug_direct(url, lambda b: b.inspector_disable()))
    _echo("Inspector disabled")


@inspector_app.command("enable")
def inspector_enable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the Inspector domain."""
    _run_async(_debug_direct(url, lambda b: b.inspector_enable()))
    _echo("Inspector enabled")


# ── Preload commands ─────────────────────────────────────


@preload_app.command("disable")
def preload_disable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the Preload domain."""
    _run_async(_debug_direct(url, lambda b: b.preload_disable()))
    _echo("Preload disabled")


@preload_app.command("enable")
def preload_enable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the Preload domain."""
    _run_async(_debug_direct(url, lambda b: b.preload_enable()))
    _echo("Preload enabled")


@preload_app.command("get-policy")
def preload_get_policy_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the current preload policy."""
    result = _run_async(_debug_direct(url, lambda b: b.preload_get_preload_policy()))
    if result is None:
        return
    _write_json_output(result, output, "preload policy")


@preload_app.command("set-policy")
def preload_set_policy_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    policy: str = typer.Argument(..., help='Preload policy JSON (e.g. \'{"key":"value"}\')'),
) -> None:
    """Set the preload policy."""
    import json

    policy_dict = _safe_json_loads(policy, "policy")
    _run_async(_debug_direct(url, lambda b: b.preload_set_preload_policy(policy_dict)))
    _echo("Preload policy set")


# ── Profiler commands ────────────────────────────────────

profiler_app = typer.Typer(help="Profiler commands (CPU profile, coverage)")
app.add_typer(profiler_app, name="profiler")


@profiler_app.command("disable")
def profiler_disable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the Profiler domain."""
    _run_async(_debug_direct(url, lambda b: b.profiler_disable()))
    _echo("Profiler disabled")


@profiler_app.command("enable")
def profiler_enable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the Profiler domain."""
    _run_async(_debug_direct(url, lambda b: b.profiler_enable()))
    _echo("Profiler enabled")


@profiler_app.command("best-effort-coverage")
def profiler_best_effort_coverage_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get best effort coverage data."""
    result = _run_async(_debug_direct(url, lambda b: b.profiler_get_best_effort_coverage()))
    if result is None:
        return
    _write_json_output(result, output, "best effort coverage")


@profiler_app.command("set-sampling-interval")
def profiler_set_sampling_interval_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    interval: int = typer.Argument(..., help="Sampling interval in microseconds"),
) -> None:
    """Set the CPU sampling interval."""
    _run_async(_debug_direct(url, lambda b: b.profiler_set_sampling_interval(interval)))
    _echo(f"Sampling interval set to {interval}us")


@profiler_app.command("start")
def profiler_start_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Start CPU profiling."""
    _run_async(_debug_direct(url, lambda b: b.profiler_start()))
    _echo("Profiler started")


@profiler_app.command("start-precise-coverage")
def profiler_start_precise_coverage_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    call_count: bool = typer.Option(False, "--call-count", help="Collect call count info"),
    detailed: bool = typer.Option(False, "--detailed", help="Collect detailed coverage info"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Start precise code coverage tracking."""
    result = _run_async(
        _debug_direct(url, lambda b: b.profiler_start_precise_coverage(call_count, detailed))
    )
    if result is None:
        return
    _write_json_output(result, output, "precise coverage started")


@profiler_app.command("stop")
def profiler_stop_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Stop CPU profiling and get the profile."""
    result = _run_async(_debug_direct(url, lambda b: b.profiler_stop()))
    if result is None:
        return
    _write_json_output(result, output, "profile")


@profiler_app.command("stop-precise-coverage")
def profiler_stop_precise_coverage_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Stop precise code coverage tracking."""
    _run_async(_debug_direct(url, lambda b: b.profiler_stop_precise_coverage()))
    _echo("Precise coverage stopped")


@profiler_app.command("take-precise-coverage")
def profiler_take_precise_coverage_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Take a snapshot of precise code coverage."""
    result = _run_async(_debug_direct(url, lambda b: b.profiler_take_precise_coverage()))
    if result is None:
        return
    _write_json_output(result, output, "precise coverage")


# ── PWA commands ─────────────────────────────────────────

pwa_app = typer.Typer(help="PWA commands (install, uninstall, app state)")
app.add_typer(pwa_app, name="pwa")


@pwa_app.command("change-app-user-settings")
def pwa_change_app_user_settings_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    app_id: str = typer.Argument(..., help="App ID"),
    user_settings: str = typer.Argument(..., help='User settings JSON (e.g. \'{"key":"value"}\')'),
) -> None:
    """Change PWA user settings."""
    import json

    settings_dict = _safe_json_loads(user_settings, "user_settings")
    _run_async(_debug_direct(url, lambda b: b.pwa_change_app_user_settings(app_id, settings_dict)))
    _echo("PWA user settings changed")


@pwa_app.command("get-os-app-state")
def pwa_get_os_app_state_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    app_id: str = typer.Argument(..., help="App ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the OS-level state of a PWA."""
    result = _run_async(_debug_direct(url, lambda b: b.pwa_get_os_app_state(app_id)))
    if result is None:
        return
    _write_json_output(result, output, "os app state")


@pwa_app.command("install")
def pwa_install_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    manifest_id: str = typer.Argument(..., help="Manifest ID"),
    install_url: str = typer.Option(None, "--install-url", help="Install URL or bundle URL"),
) -> None:
    """Install a PWA."""
    _run_async(_debug_direct(url, lambda b: b.pwa_install(manifest_id, install_url)))
    _echo("PWA installed")


@pwa_app.command("launch-files-in-app")
def pwa_launch_files_in_app_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    app_id: str = typer.Argument(..., help="App ID"),
    files: list[str] = typer.Argument(..., help="File paths to launch"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Launch files in a PWA."""
    result = _run_async(_debug_direct(url, lambda b: b.pwa_launch_files_in_app(app_id, files)))
    if result is None:
        return
    _write_json_output(result, output, "launch result")


@pwa_app.command("open-current-page-in-app")
def pwa_open_current_page_in_app_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    app_id: str = typer.Argument(..., help="App ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Open the current page in a PWA."""
    result = _run_async(_debug_direct(url, lambda b: b.pwa_open_current_page_in_app(app_id)))
    if result is None:
        return
    _write_json_output(result, output, "target info")


@pwa_app.command("uninstall")
def pwa_uninstall_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    app_id: str = typer.Argument(..., help="App ID"),
) -> None:
    """Uninstall a PWA."""
    _run_async(_debug_direct(url, lambda b: b.pwa_uninstall(app_id)))
    _echo("PWA uninstalled")


# ── IO commands ──────────────────────────────────────────


@io_app.command("read")
def io_read_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    handle: str = typer.Argument(..., help="Blob handle"),
    offset: int = typer.Option(0, "--offset", help="Read offset"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Read data from a blob handle."""
    result = _run_async(_debug_direct(url, lambda b: b.io_read(handle, offset)))
    if result is None:
        return
    _write_json_output(result, output, "IO read")


@io_app.command("resolve-blob")
def io_resolve_blob_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    object_id: str = typer.Argument(..., help="Object ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Resolve a blob object ID to a UUID handle."""
    result = _run_async(_debug_direct(url, lambda b: b.io_resolve_blob(object_id)))
    if result is None:
        return
    _write_json_output({"uuid": result}, output, "Blob UUID")


# ── HeapProfiler commands ─────────────────────────────────


@heap_profiler_app.command("add-inspected-heap-object")
def heap_profiler_add_inspected_heap_object_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    heap_object_id: str = typer.Argument(..., help="Heap object ID"),
) -> None:
    """Add an inspected heap object."""
    _run_async(
        _debug_direct(url, lambda b: b.heap_profiler_add_inspected_heap_object(heap_object_id))
    )
    typer.echo("Inspected heap object added.")


@heap_profiler_app.command("collect-garbage")
def heap_profiler_collect_garbage_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Collect garbage."""
    _run_async(_debug_direct(url, lambda b: b.heap_profiler_collect_garbage()))
    typer.echo("Garbage collected.")


@heap_profiler_app.command("disable")
def heap_profiler_disable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the HeapProfiler domain."""
    _run_async(_debug_direct(url, lambda b: b.heap_profiler_disable()))
    typer.echo("HeapProfiler disabled.")


@heap_profiler_app.command("enable")
def heap_profiler_enable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the HeapProfiler domain."""
    _run_async(_debug_direct(url, lambda b: b.heap_profiler_enable()))
    typer.echo("HeapProfiler enabled.")


@heap_profiler_app.command("get-heap-object-id")
def heap_profiler_get_heap_object_id_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    object_id: str = typer.Argument(..., help="Remote object ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the heap object ID for a remote object."""
    result = _run_async(_debug_direct(url, lambda b: b.heap_profiler_get_heap_object_id(object_id)))
    if result is None:
        return
    _write_json_output({"heapSnapshotObjectId": result}, output, "Heap object ID")


@heap_profiler_app.command("get-object-by-heap-object-id")
def heap_profiler_get_object_by_heap_object_id_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    object_id: str = typer.Argument(..., help="Heap object ID"),
    object_group: str = typer.Option("", "--object-group", help="Object group"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get an object by heap object ID."""
    result = _run_async(
        _debug_direct(
            url, lambda b: b.heap_profiler_get_object_by_heap_object_id(object_id, object_group)
        )
    )
    if result is None:
        return
    _write_json_output(result, output, "Object by heap object ID")


@heap_profiler_app.command("get-sampling-profile")
def heap_profiler_get_sampling_profile_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the current sampling profile."""
    result = _run_async(_debug_direct(url, lambda b: b.heap_profiler_get_sampling_profile()))
    if result is None:
        return
    _write_json_output(result, output, "Sampling profile")


@heap_profiler_app.command("start-sampling")
def heap_profiler_start_sampling_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    sampling_interval: int = typer.Option(0, "--interval", help="Sampling interval in bytes"),
) -> None:
    """Start heap sampling."""
    _run_async(_debug_direct(url, lambda b: b.heap_profiler_start_sampling(sampling_interval)))
    typer.echo("Heap sampling started.")


@heap_profiler_app.command("start-tracking-heap-objects")
def heap_profiler_start_tracking_heap_objects_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    track_allocations: bool = typer.Option(False, "--track-allocations", help="Track allocations"),
) -> None:
    """Start tracking heap objects."""
    _run_async(
        _debug_direct(url, lambda b: b.heap_profiler_start_tracking_heap_objects(track_allocations))
    )
    typer.echo("Heap object tracking started.")


@heap_profiler_app.command("stop-sampling")
def heap_profiler_stop_sampling_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Stop heap sampling and return the profile."""
    result = _run_async(_debug_direct(url, lambda b: b.heap_profiler_stop_sampling()))
    if result is None:
        return
    _write_json_output(result, output, "Sampling profile")


@heap_profiler_app.command("stop-tracking-heap-objects")
def heap_profiler_stop_tracking_heap_objects_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    report_progress: bool = typer.Option(False, "--report-progress", help="Report progress"),
) -> None:
    """Stop tracking heap objects."""
    _run_async(
        _debug_direct(url, lambda b: b.heap_profiler_stop_tracking_heap_objects(report_progress))
    )
    typer.echo("Heap object tracking stopped.")


@heap_profiler_app.command("take-heap-snapshot")
def heap_profiler_take_heap_snapshot_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    report_progress: bool = typer.Option(False, "--report-progress", help="Report progress"),
) -> None:
    """Take a heap snapshot."""
    _run_async(_debug_direct(url, lambda b: b.heap_profiler_take_heap_snapshot(report_progress)))
    typer.echo("Heap snapshot taken.")


# ── IndexedDB commands ────────────────────────────────────


@indexed_db_app.command("clear-object-store")
def indexed_db_clear_object_store_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    security_origin: str = typer.Argument(..., help="Security origin"),
    database_name: str = typer.Argument(..., help="Database name"),
    object_store_name: str = typer.Argument(..., help="Object store name"),
) -> None:
    """Clear all entries in an IndexedDB object store."""
    _run_async(
        _debug_direct(
            url,
            lambda b: b.indexed_db_clear_object_store(
                security_origin, database_name, object_store_name
            ),
        )
    )
    typer.echo("Object store cleared.")


@indexed_db_app.command("delete-database")
def indexed_db_delete_database_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    security_origin: str = typer.Argument(..., help="Security origin"),
    database_name: str = typer.Argument(..., help="Database name"),
) -> None:
    """Delete an IndexedDB database."""
    _run_async(
        _debug_direct(url, lambda b: b.indexed_db_delete_database(security_origin, database_name))
    )
    typer.echo("Database deleted.")


@indexed_db_app.command("delete-object-store-entries")
def indexed_db_delete_object_store_entries_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    security_origin: str = typer.Argument(..., help="Security origin"),
    database_name: str = typer.Argument(..., help="Database name"),
    object_store_name: str = typer.Argument(..., help="Object store name"),
    key_range: str = typer.Argument(..., help="Key range (JSON)"),
) -> None:
    """Delete entries in an IndexedDB object store."""
    import json

    kr = _safe_json_loads(key_range, "key_range")
    _run_async(
        _debug_direct(
            url,
            lambda b: b.indexed_db_delete_object_store_entries(
                security_origin, database_name, object_store_name, kr
            ),
        )
    )
    typer.echo("Entries deleted.")


@indexed_db_app.command("disable")
def indexed_db_disable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the IndexedDB domain."""
    _run_async(_debug_direct(url, lambda b: b.indexed_db_disable()))
    typer.echo("IndexedDB disabled.")


@indexed_db_app.command("enable")
def indexed_db_enable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the IndexedDB domain."""
    _run_async(_debug_direct(url, lambda b: b.indexed_db_enable()))
    typer.echo("IndexedDB enabled.")


@indexed_db_app.command("get-metadata")
def indexed_db_get_metadata_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    security_origin: str = typer.Argument(..., help="Security origin"),
    database_name: str = typer.Argument(..., help="Database name"),
    object_store_name: str = typer.Argument(..., help="Object store name"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get metadata for an IndexedDB object store."""
    result = _run_async(
        _debug_direct(
            url,
            lambda b: b.indexed_db_get_metadata(security_origin, database_name, object_store_name),
        )
    )
    if result is None:
        return
    _write_json_output(result, output, "Object store metadata")


@indexed_db_app.command("request-data")
def indexed_db_request_data_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    security_origin: str = typer.Argument(..., help="Security origin"),
    database_name: str = typer.Argument(..., help="Database name"),
    object_store_name: str = typer.Argument(..., help="Object store name"),
    index_name: str = typer.Argument(..., help="Index name"),
    skip_count: int = typer.Option(0, "--skip", help="Skip count"),
    page_size: int = typer.Option(10, "--page-size", help="Page size"),
    key_range: str = typer.Option("", "--key-range", help="Key range (JSON)"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Request data from an IndexedDB object store."""
    import json

    kr = _safe_json_loads(key_range, "key_range") if key_range else None
    result = _run_async(
        _debug_direct(
            url,
            lambda b: b.indexed_db_request_data(
                security_origin,
                database_name,
                object_store_name,
                index_name,
                skip_count,
                page_size,
                kr,
            ),
        )
    )
    if result is None:
        return
    _write_json_output(result, output, "Object store data")


@indexed_db_app.command("request-database")
def indexed_db_request_database_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    security_origin: str = typer.Argument(..., help="Security origin"),
    database_name: str = typer.Argument(..., help="Database name"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Request an IndexedDB database with its object stores."""
    result = _run_async(
        _debug_direct(url, lambda b: b.indexed_db_request_database(security_origin, database_name))
    )
    if result is None:
        return
    _write_json_output(result, output, "Database")


@indexed_db_app.command("request-database-names")
def indexed_db_request_database_names_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    security_origin: str = typer.Argument(..., help="Security origin"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Request the names of all IndexedDB databases for an origin."""
    result = _run_async(
        _debug_direct(url, lambda b: b.indexed_db_request_database_names(security_origin))
    )
    if result is None:
        return
    _write_json_output(result, output, "Database names")


# ── LayerTree commands ────────────────────────────────────


@layer_tree_app.command("compositing-reasons")
def layer_tree_compositing_reasons_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    layer_id: str = typer.Argument(..., help="Layer ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get compositing reasons for a layer."""
    result = _run_async(_debug_direct(url, lambda b: b.layer_tree_compositing_reasons(layer_id)))
    if result is None:
        return
    _write_json_output(result, output, "Compositing reasons")


@layer_tree_app.command("disable")
def layer_tree_disable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the LayerTree domain."""
    _run_async(_debug_direct(url, lambda b: b.layer_tree_disable()))
    typer.echo("LayerTree disabled.")


@layer_tree_app.command("enable")
def layer_tree_enable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the LayerTree domain."""
    _run_async(_debug_direct(url, lambda b: b.layer_tree_enable()))
    typer.echo("LayerTree enabled.")


@layer_tree_app.command("load-snapshot")
def layer_tree_load_snapshot_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    snapshots: str = typer.Argument(..., help="Snapshots (JSON array)"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Load a layer tree snapshot."""
    import json

    snaps = _safe_json_loads(snapshots, "snapshots")
    result = _run_async(_debug_direct(url, lambda b: b.layer_tree_load_snapshot(snaps)))
    if result is None:
        return
    _write_json_output(result, output, "Layer tree snapshot")


@layer_tree_app.command("make-snapshot")
def layer_tree_make_snapshot_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    layer_id: str = typer.Argument(..., help="Layer ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Make a snapshot of a layer."""
    result = _run_async(_debug_direct(url, lambda b: b.layer_tree_make_snapshot(layer_id)))
    if result is None:
        return
    _write_json_output(result, output, "Layer snapshot")


@layer_tree_app.command("profile-snapshot")
def layer_tree_profile_snapshot_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    snapshot_id: str = typer.Argument(..., help="Snapshot ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Profile a layer snapshot."""
    result = _run_async(_debug_direct(url, lambda b: b.layer_tree_profile_snapshot(snapshot_id)))
    if result is None:
        return
    _write_json_output(result, output, "Snapshot profile")


@layer_tree_app.command("release-snapshot")
def layer_tree_release_snapshot_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    snapshot_id: str = typer.Argument(..., help="Snapshot ID"),
) -> None:
    """Release a layer snapshot."""
    _run_async(_debug_direct(url, lambda b: b.layer_tree_release_snapshot(snapshot_id)))
    typer.echo("Snapshot released.")


@layer_tree_app.command("replay-snapshot")
def layer_tree_replay_snapshot_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    snapshot_id: str = typer.Argument(..., help="Snapshot ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Replay a layer snapshot."""
    result = _run_async(_debug_direct(url, lambda b: b.layer_tree_replay_snapshot(snapshot_id)))
    if result is None:
        return
    _write_json_output(result, output, "Replayed snapshot")


@layer_tree_app.command("snapshot-command-log")
def layer_tree_snapshot_command_log_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    snapshot_id: str = typer.Argument(..., help="Snapshot ID"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the command log for a layer snapshot."""
    result = _run_async(
        _debug_direct(url, lambda b: b.layer_tree_snapshot_command_log(snapshot_id))
    )
    if result is None:
        return
    _write_json_output(result, output, "Snapshot command log")


# ── Log commands ──────────────────────────────────────────


@log_app.command("clear")
def log_clear_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Clear the log."""
    _run_async(_debug_direct(url, lambda b: b.log_clear()))
    typer.echo("Log cleared.")


@log_app.command("disable")
def log_disable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the Log domain."""
    _run_async(_debug_direct(url, lambda b: b.log_disable()))
    typer.echo("Log disabled.")


@log_app.command("enable")
def log_enable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the Log domain."""
    _run_async(_debug_direct(url, lambda b: b.log_enable()))
    typer.echo("Log enabled.")


@log_app.command("start-violations-report")
def log_start_violations_report_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    config: str = typer.Argument(..., help="Violations config (JSON array)"),
) -> None:
    """Start reporting violations."""
    import json

    cfg = _safe_json_loads(config, "config")
    _run_async(_debug_direct(url, lambda b: b.log_start_violations_report(cfg)))
    typer.echo("Violations report started.")


@log_app.command("stop-violations-report")
def log_stop_violations_report_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Stop reporting violations."""
    _run_async(_debug_direct(url, lambda b: b.log_stop_violations_report()))
    typer.echo("Violations report stopped.")


# ── Media commands ────────────────────────────────────────


@media_app.command("disable")
def media_disable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Disable the Media domain."""
    _run_async(_debug_direct(url, lambda b: b.media_disable()))
    typer.echo("Media disabled.")


@media_app.command("enable")
def media_enable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable the Media domain."""
    _run_async(_debug_direct(url, lambda b: b.media_enable()))
    typer.echo("Media enabled.")


# ── Memory commands ───────────────────────────────────────


@memory_app.command("forcibly-purge-javascript-memory")
def memory_forcibly_purge_javascript_memory_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Forcibly purge JavaScript memory."""
    _run_async(_debug_direct(url, lambda b: b.memory_forcibly_purge_javascript_memory()))
    typer.echo("JavaScript memory purged.")


@memory_app.command("get-all-time-sampling-profile")
def memory_get_all_time_sampling_profile_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the all-time sampling profile."""
    result = _run_async(_debug_direct(url, lambda b: b.memory_get_all_time_sampling_profile()))
    if result is None:
        return
    _write_json_output(result, output, "All-time sampling profile")


@memory_app.command("get-browser-sampling-profile")
def memory_get_browser_sampling_profile_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the browser sampling profile."""
    result = _run_async(_debug_direct(url, lambda b: b.memory_get_browser_sampling_profile()))
    if result is None:
        return
    _write_json_output(result, output, "Browser sampling profile")


@memory_app.command("get-dom-counters")
def memory_get_dom_counters_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get DOM counters."""
    result = _run_async(_debug_direct(url, lambda b: b.memory_get_dom_counters()))
    if result is None:
        return
    _write_json_output(result, output, "DOM counters")


@memory_app.command("get-dom-counters-for-leak-detection")
def memory_get_dom_counters_for_leak_detection_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get DOM counters for leak detection."""
    result = _run_async(
        _debug_direct(url, lambda b: b.memory_get_dom_counters_for_leak_detection())
    )
    if result is None:
        return
    _write_json_output(result, output, "DOM counters for leak detection")


@memory_app.command("get-sampling-profile")
def memory_get_sampling_profile_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "--output", "-o", help="Output file (- for stdout)"),
) -> None:
    """Get the current sampling profile."""
    result = _run_async(_debug_direct(url, lambda b: b.memory_get_sampling_profile()))
    if result is None:
        return
    _write_json_output(result, output, "Sampling profile")


@memory_app.command("prepare-for-leak-detection")
def memory_prepare_for_leak_detection_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Prepare for leak detection."""
    _run_async(_debug_direct(url, lambda b: b.memory_prepare_for_leak_detection()))
    typer.echo("Prepared for leak detection.")


@memory_app.command("set-pressure-notifications-suppressed")
def memory_set_pressure_notifications_suppressed_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    suppressed: bool = typer.Argument(..., help="Suppressed state"),
) -> None:
    """Set pressure notifications suppressed state."""
    _run_async(
        _debug_direct(url, lambda b: b.memory_set_pressure_notifications_suppressed(suppressed))
    )
    typer.echo(f"Pressure notifications suppressed: {suppressed}")


@memory_app.command("simulate-pressure-notification")
def memory_simulate_pressure_notification_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    level: str = typer.Argument(..., help="Pressure level (e.g. 'moderate', 'critical')"),
) -> None:
    """Simulate a memory pressure notification."""
    _run_async(_debug_direct(url, lambda b: b.memory_simulate_pressure_notification(level)))
    typer.echo(f"Pressure notification simulated: {level}")


@memory_app.command("start-sampling")
def memory_start_sampling_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    sampling_interval: int = typer.Option(0, "--interval", help="Sampling interval in bytes"),
) -> None:
    """Start memory sampling."""
    _run_async(_debug_direct(url, lambda b: b.memory_start_sampling(sampling_interval)))
    typer.echo("Memory sampling started.")


@memory_app.command("stop-sampling")
def memory_stop_sampling_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Stop memory sampling."""
    _run_async(_debug_direct(url, lambda b: b.memory_stop_sampling()))
    typer.echo("Memory sampling stopped.")


# ── Console ──────────────────────────────────────────────────


@console_app.command("clear-messages")
def console_clear_messages_cmd(url: str = typer.Argument(..., help="URL to navigate to")) -> None:
    """Clear all console messages."""
    _run_async(_debug_direct(url, lambda b: b.console_clear_messages()))
    typer.echo("Console messages cleared.")


@console_app.command("disable")
def console_disable_cmd(url: str = typer.Argument(..., help="URL to navigate to")) -> None:
    """Disable the Console domain."""
    _run_async(_debug_direct(url, lambda b: b.console_disable()))
    typer.echo("Console disabled.")


@console_app.command("enable")
def console_enable_cmd(url: str = typer.Argument(..., help="URL to navigate to")) -> None:
    """Enable the Console domain."""
    _run_async(_debug_direct(url, lambda b: b.console_enable()))
    typer.echo("Console enabled.")


# ── CrashReportContext ───────────────────────────────────────


@crash_report_context_app.command("get-entries")
def crash_report_context_get_entries_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Get crash report entries."""
    result = _run_async(_debug_direct(url, lambda b: b.crash_report_context_get_entries()))
    typer.echo(json.dumps(result, indent=2) if result else "No entries.")


# ── Input (low-level CDP) ────────────────────────────────────


@input_domain_app.command("cancel-dragging")
def input_cancel_dragging_cmd(url: str = typer.Argument(..., help="URL to navigate to")) -> None:
    """Cancel any ongoing drag operation."""
    _run_async(_debug_direct(url, lambda b: b.input_cancel_dragging()))
    typer.echo("Dragging cancelled.")


@input_domain_app.command("dispatch-drag-event")
def input_dispatch_drag_event_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    type: str = typer.Option(..., "--type", help="Event type (dragEnter, dragOver, drop, etc.)"),
    x: float = typer.Option(..., "--x", help="X coordinate"),
    y: float = typer.Option(..., "--y", help="Y coordinate"),
    data: str = typer.Option("{}", "--data", help="Drag data JSON"),
) -> None:
    """Dispatch a drag event."""
    _run_async(
        _debug_direct(url, lambda b: b.input_dispatch_drag_event(type, x, y, _safe_json_loads(data, "data")))
    )
    typer.echo("Drag event dispatched.")


@input_domain_app.command("dispatch-key-event")
def input_dispatch_key_event_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    type: str = typer.Option(..., "--type", help="Event type (keyDown, keyUp, rawKeyDown, char)"),
    key: str = typer.Option("", "--key", help="Key (e.g. 'a', 'Enter')"),
    code: str = typer.Option("", "--code", help="Code (e.g. 'KeyA')"),
    text: str = typer.Option("", "--text", help="Text to insert"),
    modifiers: int = typer.Option(0, "--modifiers", help="Bitmask of modifiers"),
) -> None:
    """Dispatch a key event."""
    _run_async(
        _debug_direct(
            url,
            lambda b: b.input_dispatch_key_event(
                type, key=key, code=code, text=text, modifiers=modifiers
            ),
        )
    )
    typer.echo("Key event dispatched.")


@input_domain_app.command("dispatch-mouse-event")
def input_dispatch_mouse_event_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    type: str = typer.Option(
        ..., "--type", help="Event type (mousePressed, mouseReleased, mouseMoved)"
    ),
    x: float = typer.Option(..., "--x", help="X coordinate"),
    y: float = typer.Option(..., "--y", help="Y coordinate"),
    button: str = typer.Option("none", "--button", help="Button (left, right, middle, none)"),
    click_count: int = typer.Option(0, "--click-count", help="Click count"),
    modifiers: int = typer.Option(0, "--modifiers", help="Bitmask of modifiers"),
) -> None:
    """Dispatch a mouse event."""
    _run_async(
        _debug_direct(
            url,
            lambda b: b.input_dispatch_mouse_event(
                type, x, y, button=button, click_count=click_count, modifiers=modifiers
            ),
        )
    )
    typer.echo("Mouse event dispatched.")


@input_domain_app.command("dispatch-touch-event")
def input_dispatch_touch_event_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    type: str = typer.Option(..., "--type", help="Event type (touchStart, touchEnd, touchMove)"),
    touch_points: str = typer.Option(..., "--touch-points", help="Touch points JSON array"),
    modifiers: int = typer.Option(0, "--modifiers", help="Bitmask of modifiers"),
) -> None:
    """Dispatch a touch event."""
    _run_async(
        _debug_direct(
            url,
            lambda b: b.input_dispatch_touch_event(
                type, _safe_json_loads(touch_points, "touch_points"), modifiers=modifiers
            ),
        )
    )
    typer.echo("Touch event dispatched.")


@input_domain_app.command("emulate-touch-from-mouse-event")
def input_emulate_touch_from_mouse_event_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    type: str = typer.Option(..., "--type", help="Mouse event type"),
    x: float = typer.Option(..., "--x", help="X coordinate"),
    y: float = typer.Option(..., "--y", help="Y coordinate"),
    button: str = typer.Option("none", "--button", help="Button"),
) -> None:
    """Emulate a touch event from a mouse event."""
    _run_async(
        _debug_direct(
            url, lambda b: b.input_emulate_touch_from_mouse_event(type, x, y, button=button)
        )
    )
    typer.echo("Touch event emulated from mouse event.")


@input_domain_app.command("ime-set-composition")
def input_ime_set_composition_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    text: str = typer.Option(..., "--text", help="Composition text"),
    selection_start: int = typer.Option(..., "--selection-start", help="Selection start"),
    selection_end: int = typer.Option(..., "--selection-end", help="Selection end"),
) -> None:
    """Set the IME composition."""
    _run_async(
        _debug_direct(
            url, lambda b: b.input_ime_set_composition(text, selection_start, selection_end)
        )
    )
    typer.echo("IME composition set.")


@input_domain_app.command("insert-text")
def input_insert_text_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    text: str = typer.Option(..., "--text", help="Text to insert"),
) -> None:
    """Insert text into the focused element."""
    _run_async(_debug_direct(url, lambda b: b.input_insert_text(text)))
    typer.echo("Text inserted.")


@input_domain_app.command("set-ignore-input-events")
def input_set_ignore_input_events_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    ignore: bool = typer.Option(
        True, "--ignore/--no-ignore", help="Whether to ignore input events"
    ),
) -> None:
    """Set whether to ignore input events."""
    _run_async(_debug_direct(url, lambda b: b.input_set_ignore_input_events(ignore)))
    typer.echo(f"Input events {'ignored' if ignore else 'allowed'}.")


@input_domain_app.command("set-intercept-drags")
def input_set_intercept_drags_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    enabled: bool = typer.Option(True, "--enabled/--no-enabled", help="Whether to intercept drags"),
) -> None:
    """Set whether to intercept drag operations."""
    _run_async(_debug_direct(url, lambda b: b.input_set_intercept_drags(enabled)))
    typer.echo(f"Drag interception {'enabled' if enabled else 'disabled'}.")


@input_domain_app.command("synthesize-pinch-gesture")
def input_synthesize_pinch_gesture_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    x: float = typer.Option(..., "--x", help="X coordinate"),
    y: float = typer.Option(..., "--y", help="Y coordinate"),
    scale_factor: float = typer.Option(..., "--scale-factor", help="Scale factor"),
    relative_pointer_speed: int = typer.Option(0, "--speed", help="Relative pointer speed"),
) -> None:
    """Synthesize a pinch gesture."""
    _run_async(
        _debug_direct(
            url,
            lambda b: b.input_synthesize_pinch_gesture(x, y, scale_factor, relative_pointer_speed),
        )
    )
    typer.echo("Pinch gesture synthesized.")


@input_domain_app.command("synthesize-scroll-gesture")
def input_synthesize_scroll_gesture_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    x: float = typer.Option(..., "--x", help="X coordinate"),
    y: float = typer.Option(..., "--y", help="Y coordinate"),
    y_distance: float = typer.Option(0, "--y-distance", help="Y scroll distance"),
    x_distance: float = typer.Option(0, "--x-distance", help="X scroll distance"),
    speed: int = typer.Option(0, "--speed", help="Speed"),
) -> None:
    """Synthesize a scroll gesture."""
    _run_async(
        _debug_direct(
            url,
            lambda b: b.input_synthesize_scroll_gesture(
                x, y, x_distance=x_distance, y_distance=y_distance, speed=speed
            ),
        )
    )
    typer.echo("Scroll gesture synthesized.")


@input_domain_app.command("synthesize-tap-gesture")
def input_synthesize_tap_gesture_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    x: float = typer.Option(..., "--x", help="X coordinate"),
    y: float = typer.Option(..., "--y", help="Y coordinate"),
    duration: int = typer.Option(0, "--duration", help="Duration in ms"),
    tap_count: int = typer.Option(1, "--tap-count", help="Number of taps"),
) -> None:
    """Synthesize a tap gesture."""
    _run_async(
        _debug_direct(
            url,
            lambda b: b.input_synthesize_tap_gesture(x, y, duration=duration, tap_count=tap_count),
        )
    )
    typer.echo("Tap gesture synthesized.")


# ── Network (additional CDP methods) ─────────────────────────


@network_domain_app.command("clear-accepted-encodings-override")
def network_clear_accepted_encodings_override_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Clear the accepted encodings override."""
    _run_async(_debug_direct(url, lambda b: b.network_clear_accepted_encodings_override()))
    typer.echo("Accepted encodings override cleared.")


@network_domain_app.command("configure-durable-messages")
def network_configure_durable_messages_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    options: str = typer.Option(..., "--options", help="Options JSON"),
) -> None:
    """Configure durable messages."""
    _run_async(
        _debug_direct(url, lambda b: b.network_configure_durable_messages(_safe_json_loads(options, "options")))
    )
    typer.echo("Durable messages configured.")


@network_domain_app.command("delete-device-bound-session")
def network_delete_device_bound_session_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    session_id: str = typer.Option(..., "--session-id", help="Session ID"),
) -> None:
    """Delete a device-bound session."""
    _run_async(_debug_direct(url, lambda b: b.network_delete_device_bound_session(session_id)))
    typer.echo("Device-bound session deleted.")


@network_domain_app.command("disable")
def network_disable_cmd(url: str = typer.Argument(..., help="URL to navigate to")) -> None:
    """Disable the Network domain."""
    _run_async(_debug_direct(url, lambda b: b.network_disable()))
    typer.echo("Network domain disabled.")


@network_domain_app.command("emulate-network-conditions-by-rule")
def network_emulate_network_conditions_by_rule_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    offline: bool = typer.Option(False, "--offline", help="Offline mode"),
    latency: float = typer.Option(0, "--latency", help="Latency in ms"),
    download_throughput: float = typer.Option(0, "--download", help="Download throughput"),
    upload_throughput: float = typer.Option(0, "--upload", help="Upload throughput"),
    connection_type: str = typer.Option("", "--connection-type", help="Connection type"),
) -> None:
    """Emulate network conditions by rule."""
    _run_async(
        _debug_direct(
            url,
            lambda b: b.network_emulate_network_conditions_by_rule(
                download_throughput=download_throughput,
                upload_throughput=upload_throughput,
                offline=offline,
                latency=latency,
                connection_type=connection_type,
            ),
        )
    )
    typer.echo("Network conditions emulated.")


@network_domain_app.command("enable")
def network_enable_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    max_total_buffer_size: int = typer.Option(
        0, "--max-total-buffer", help="Max total buffer size"
    ),
    max_resource_buffer_size: int = typer.Option(
        0, "--max-resource-buffer", help="Max resource buffer size"
    ),
) -> None:
    """Enable the Network domain."""
    _run_async(
        _debug_direct(
            url, lambda b: b.network_enable(max_total_buffer_size, max_resource_buffer_size)
        )
    )
    typer.echo("Network domain enabled.")


@network_domain_app.command("enable-device-bound-sessions")
def network_enable_device_bound_sessions_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Enable device-bound sessions."""
    _run_async(_debug_direct(url, lambda b: b.network_enable_device_bound_sessions()))
    typer.echo("Device-bound sessions enabled.")


@network_domain_app.command("enable-reporting-api")
def network_enable_reporting_api_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    enable: bool = typer.Option(True, "--enable/--disable", help="Enable or disable Reporting API"),
) -> None:
    """Enable or disable the Reporting API."""
    _run_async(_debug_direct(url, lambda b: b.network_enable_reporting_api(enable)))
    typer.echo(f"Reporting API {'enabled' if enable else 'disabled'}.")


@network_domain_app.command("fetch-schemeful-site")
def network_fetch_schemeful_site_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    request_id: str = typer.Option(..., "--request-id", help="Request ID"),
) -> None:
    """Fetch the schemeful site for a request."""
    result = _run_async(_debug_direct(url, lambda b: b.network_fetch_schemeful_site(request_id)))
    typer.echo(json.dumps(result, indent=2) if result else "No result.")


@network_domain_app.command("get-certificate")
def network_get_certificate_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    origin: str = typer.Option(..., "--origin", help="Origin URL"),
) -> None:
    """Get the certificate for an origin."""
    result = _run_async(_debug_direct(url, lambda b: b.network_get_certificate(origin)))
    typer.echo(json.dumps(result, indent=2) if result else "No certificate.")


@network_domain_app.command("get-request-post-data")
def network_get_request_post_data_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    request_id: str = typer.Option(..., "--request-id", help="Request ID"),
) -> None:
    """Get the POST data for a request."""
    result = _run_async(_debug_direct(url, lambda b: b.network_get_request_post_data(request_id)))
    typer.echo(result if result else "No POST data.")


@network_domain_app.command("get-response-body-for-interception")
def network_get_response_body_for_interception_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    interception_id: str = typer.Option(..., "--interception-id", help="Interception ID"),
) -> None:
    """Get the response body for an interception."""
    result = _run_async(
        _debug_direct(url, lambda b: b.network_get_response_body_for_interception(interception_id))
    )
    typer.echo(result if result else "No response body.")


@network_domain_app.command("get-security-isolation-status")
def network_get_security_isolation_status_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    frame_id: str = typer.Option("", "--frame-id", help="Frame ID"),
) -> None:
    """Get the security isolation status."""
    result = _run_async(
        _debug_direct(url, lambda b: b.network_get_security_isolation_status(frame_id=frame_id))
    )
    typer.echo(json.dumps(result, indent=2) if result else "No status.")


@network_domain_app.command("override-network-state")
def network_override_network_state_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    state: str = typer.Option(..., "--state", help="State JSON"),
) -> None:
    """Override the network state."""
    _run_async(_debug_direct(url, lambda b: b.network_override_network_state(_safe_json_loads(state, "state"))))
    typer.echo("Network state overridden.")


@network_domain_app.command("search-in-response-body")
def network_search_in_response_body_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    request_id: str = typer.Option(..., "--request-id", help="Request ID"),
    query: str = typer.Option(..., "--query", help="Search query"),
    case_sensitive: bool = typer.Option(False, "--case-sensitive", help="Case sensitive search"),
    is_regex: bool = typer.Option(False, "--is-regex", help="Treat query as regex"),
) -> None:
    """Search in a response body."""
    result = _run_async(
        _debug_direct(
            url,
            lambda b: b.network_search_in_response_body(
                request_id, query, case_sensitive=case_sensitive, is_regex=is_regex
            ),
        )
    )
    typer.echo(json.dumps(result, indent=2) if result else "No matches.")


@network_domain_app.command("set-accepted-encodings")
def network_set_accepted_encodings_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    encodings: str = typer.Option(..., "--encodings", help="Encodings JSON array"),
) -> None:
    """Set accepted encodings."""
    _run_async(
        _debug_direct(url, lambda b: b.network_set_accepted_encodings(_safe_json_loads(encodings, "encodings")))
    )
    typer.echo("Accepted encodings set.")


@network_domain_app.command("set-attach-debug-stack")
def network_set_attach_debug_stack_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    enabled: bool = typer.Option(
        True, "--enabled/--no-enabled", help="Whether to attach debug stack"
    ),
) -> None:
    """Set whether to attach debug stack to network requests."""
    _run_async(_debug_direct(url, lambda b: b.network_set_attach_debug_stack(enabled)))
    typer.echo(f"Debug stack {'enabled' if enabled else 'disabled'}.")


@network_domain_app.command("set-cookies")
def network_set_cookies_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    cookies: str = typer.Option(..., "--cookies", help="Cookies JSON array"),
) -> None:
    """Set cookies."""
    _run_async(_debug_direct(url, lambda b: b.network_set_cookies(_safe_json_loads(cookies, "cookies"))))
    typer.echo("Cookies set.")


@network_domain_app.command("stream-resource-content")
def network_stream_resource_content_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    request_id: str = typer.Option(..., "--request-id", help="Request ID"),
) -> None:
    """Stream resource content for a request."""
    result = _run_async(_debug_direct(url, lambda b: b.network_stream_resource_content(request_id)))
    typer.echo(json.dumps(result, indent=2) if result else "No content.")


@network_domain_app.command("take-response-body-for-interception-as-stream")
def network_take_response_body_for_interception_as_stream_cmd(
    url: str = typer.Argument(..., help="URL to navigate to"),
    interception_id: str = typer.Option(..., "--interception-id", help="Interception ID"),
) -> None:
    """Take the response body for an interception as a stream."""
    result = _run_async(
        _debug_direct(
            url, lambda b: b.network_take_response_body_for_interception_as_stream(interception_id)
        )
    )
    typer.echo(json.dumps(result, indent=2) if result else "No stream.")
    typer.echo(json.dumps(result, indent=2) if result else "No stream.")
