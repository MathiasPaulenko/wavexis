"""emulation commands for wavexis CLI."""

from __future__ import annotations

import typer

from wavexis.cli._shared import (
    DEVICE_PRESETS,
    Output,
    _browser_options,
    _close_backend,
    _echo,
    _get_backend,
    _run_async,
    app,
)
from wavexis.config import WaitStrategy

emulation_app = typer.Typer(
    help="Emulation commands (device, viewport, geolocation, timezone, dark_mode)"
)
app.add_typer(emulation_app, name="emulation")


@app.command()
def devices() -> None:
    """List available device presets."""
    for name, preset in DEVICE_PRESETS.items():
        typer.echo(
            f"  {name}: {preset['width']}x{preset['height']} "
            f"(scale={preset['device_scale_factor']}, "
            f"mobile={preset['mobile']}, touch={preset['touch']})"
        )


@emulation_app.command("device")
def emulation_device(
    url: str = typer.Argument(..., help="URL to navigate to"),
    device: str = typer.Option(..., "--device", help="Device preset name"),
    output: str = typer.Option("screenshot.png", "--output", "-o", help="Output file path"),
) -> None:
    """Emulate a device and take a screenshot."""
    image_bytes = _run_async(_emulation_device(url, device))
    if image_bytes is None:
        return

    Output.write_bytes(image_bytes, output)
    typer.echo(f"Screenshot saved to {output}")


async def _emulation_device(url: str, device: str) -> bytes:
    """Async helper for device emulation + screenshot."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        await backend.emulate_device(device)
        from wavexis.config import ScreenshotParams

        params = ScreenshotParams(url=url, full_page=True)
        return bytes(await backend.screenshot(params))
    finally:
        await _close_backend(backend)


@emulation_app.command("viewport")
def emulation_viewport(
    url: str = typer.Argument(..., help="URL to navigate to"),
    width: int = typer.Option(..., "--width", help="Viewport width in pixels"),
    height: int = typer.Option(..., "--height", help="Viewport height in pixels"),
    output: str = typer.Option("screenshot.png", "--output", "-o", help="Output file path"),
) -> None:
    """Set a custom viewport and take a screenshot."""
    image_bytes = _run_async(_emulation_viewport(url, width, height))
    if image_bytes is None:
        return

    Output.write_bytes(image_bytes, output)
    typer.echo(f"Screenshot saved to {output}")


async def _emulation_viewport(url: str, width: int, height: int) -> bytes:
    """Async helper for viewport emulation + screenshot."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.set_viewport(width, height)
        await backend.navigate(url, WaitStrategy(strategy="load"))
        from wavexis.config import ScreenshotParams

        params = ScreenshotParams(url=url, full_page=True)
        return bytes(await backend.screenshot(params))
    finally:
        await _close_backend(backend)


@emulation_app.command("geolocation")
def emulation_geolocation(
    url: str = typer.Argument(..., help="URL to navigate to"),
    lat: float = typer.Option(..., "--lat", help="Latitude in degrees"),
    lon: float = typer.Option(..., "--lon", help="Longitude in degrees"),
    output: str = typer.Option("screenshot.png", "--output", "-o", help="Output file path"),
) -> None:
    """Override geolocation and take a screenshot."""
    image_bytes = _run_async(_emulation_geolocation(url, lat, lon))
    if image_bytes is None:
        return

    Output.write_bytes(image_bytes, output)
    typer.echo(f"Screenshot saved to {output}")


async def _emulation_geolocation(url: str, lat: float, lon: float) -> bytes:
    """Async helper for geolocation override + screenshot."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        await backend.set_geolocation(lat, lon)
        from wavexis.config import ScreenshotParams

        params = ScreenshotParams(url=url, full_page=True)
        return bytes(await backend.screenshot(params))
    finally:
        await _close_backend(backend)


@emulation_app.command("timezone")
def emulation_timezone(
    url: str = typer.Argument(..., help="URL to navigate to"),
    tz: str = typer.Option(..., "--tz", help="IANA timezone ID"),
    output: str = typer.Option("screenshot.png", "--output", "-o", help="Output file path"),
) -> None:
    """Override timezone and take a screenshot."""
    image_bytes = _run_async(_emulation_timezone(url, tz))
    if image_bytes is None:
        return

    Output.write_bytes(image_bytes, output)
    typer.echo(f"Screenshot saved to {output}")


async def _emulation_timezone(url: str, tz: str) -> bytes:
    """Async helper for timezone override + screenshot."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        await backend.set_timezone(tz)
        from wavexis.config import ScreenshotParams

        params = ScreenshotParams(url=url, full_page=True)
        return bytes(await backend.screenshot(params))
    finally:
        await _close_backend(backend)


@emulation_app.command("dark_mode")
def emulation_dark_mode(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("screenshot.png", "--output", "-o", help="Output file path"),
) -> None:
    """Enable dark mode and take a screenshot."""
    image_bytes = _run_async(_emulation_dark_mode(url))
    if image_bytes is None:
        return

    Output.write_bytes(image_bytes, output)
    typer.echo(f"Screenshot saved to {output}")


async def _emulation_dark_mode(url: str) -> bytes:
    """Async helper for dark mode + screenshot."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))
        await backend.set_dark_mode(True)
        from wavexis.config import ScreenshotParams

        params = ScreenshotParams(url=url, full_page=True)
        return bytes(await backend.screenshot(params))
    finally:
        await _close_backend(backend)


@emulation_app.command("media")
def emulation_media(
    url: str = typer.Argument(..., help="URL to navigate to"),
    media: str = typer.Option(..., "--media", help="Media type (screen, print, braille)"),
) -> None:
    """Set emulated media type."""
    _run_async(_emulation_simple(url, "media", media=media))
    _echo(f"Emulated media set to: {media}")


@emulation_app.command("clear-media")
def emulation_clear_media(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Clear emulated media override."""
    _run_async(_emulation_simple(url, "clear_media"))
    _echo("Emulated media cleared")


@emulation_app.command("vision-deficiency")
def emulation_vision_deficiency(
    url: str = typer.Argument(..., help="URL to navigate to"),
    deficiency: str = typer.Option(
        ...,
        "--type",
        help=(
            "Deficiency type "
            "(none, achromatopsia, blurredVision, deuteranopia, protanopia, tritanopia)"
        ),
    ),
) -> None:
    """Set emulated vision deficiency."""
    _run_async(_emulation_simple(url, "vision_deficiency", deficiency=deficiency))
    _echo(f"Vision deficiency set to: {deficiency}")


@emulation_app.command("idle-override")
def emulation_idle_override(
    url: str = typer.Argument(..., help="URL to navigate to"),
    user_active: bool = typer.Option(True, "--user-active/--no-user-active", help="Is user active"),
    screen_active: bool = typer.Option(
        True, "--screen-active/--no-screen-active", help="Is screen active"
    ),
) -> None:
    """Override idle state to prevent screen sleep/lock."""
    _run_async(
        _emulation_simple(
            url, "idle_override", user_active=user_active, screen_active=screen_active
        )
    )
    _echo("Idle override set")


@emulation_app.command("clear-idle-override")
def emulation_clear_idle_override(
    url: str = typer.Argument(..., help="URL to navigate to"),
) -> None:
    """Clear idle state override."""
    _run_async(_emulation_simple(url, "clear_idle_override"))
    _echo("Idle override cleared")


@emulation_app.command("disable-js")
def emulation_disable_js(
    url: str = typer.Argument(..., help="URL to navigate to"),
    enabled: bool = typer.Option(True, "--disable/--enable", help="Disable (default) or enable JS"),
) -> None:
    """Disable or enable JavaScript execution."""
    _run_async(_emulation_simple(url, "disable_js", disabled=enabled))
    _echo(f"JavaScript {'disabled' if enabled else 'enabled'}")


@emulation_app.command("visible-size")
def emulation_visible_size(
    url: str = typer.Argument(..., help="URL to navigate to"),
    width: int = typer.Option(..., "--width", help="Visible width in pixels"),
    height: int = typer.Option(..., "--height", help="Visible height in pixels"),
) -> None:
    """Set the visible size of the page."""
    _run_async(_emulation_simple(url, "visible_size", width=width, height=height))
    _echo(f"Visible size set to {width}x{height}")


async def _emulation_simple(
    url: str,
    action: str,
    media: str | None = None,
    deficiency: str | None = None,
    user_active: bool = True,
    screen_active: bool = True,
    disabled: bool = True,
    width: int = 0,
    height: int = 0,
) -> None:
    """Async helper for simple emulation actions."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url, WaitStrategy(strategy="load"))

        if action == "media" and media:
            await backend.set_emulated_media(media)
        elif action == "clear_media":
            await backend.clear_emulated_media()
        elif action == "vision_deficiency" and deficiency:
            await backend.set_emulated_vision_deficiency(deficiency)
        elif action == "idle_override":
            await backend.set_idle_override(user_active, screen_active)
        elif action == "clear_idle_override":
            await backend.clear_idle_override()
        elif action == "disable_js":
            await backend.set_script_execution_disabled(disabled)
        elif action == "visible_size":
            await backend.set_visible_size(width, height)
    finally:
        await _close_backend(backend)
