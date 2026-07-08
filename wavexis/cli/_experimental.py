"""experimental commands for wavexis CLI."""

from __future__ import annotations

import json
from typing import Any

import typer

from wavexis.actions.animation import AnimationAction
from wavexis.actions.bluetooth import BluetoothAction, BluetoothParams
from wavexis.actions.cast import CastAction, CastParams
from wavexis.actions.media import MediaAction, MediaParams
from wavexis.actions.service_worker import ServiceWorkerAction, ServiceWorkerParams
from wavexis.actions.storage import StorageAction
from wavexis.actions.webaudio import WebAudioAction, WebAudioParams
from wavexis.actions.webauthn import WebAuthnAction, WebAuthnParams
from wavexis.cli._shared import (
    _browser_options,
    _close_backend,
    _echo,
    _get_backend,
    _run_async,
    app,
    get_manager,
)
from wavexis.config import AnimationParams, StorageParams, WaitStrategy


@app.command()
def storage(
    action: str = typer.Argument(
        ...,
        help="Storage action: get, set, clear, list, cache-list, "
             "cache-entries, cache-delete, indexeddb-list, indexeddb-get, indexeddb-clear",
    ),
    url: str = typer.Argument(..., help="URL to navigate to"),
    key: str = typer.Option("", "--key", help="Storage key"),
    value: str = typer.Option("", "--value", help="Storage value"),
    storage_type: str = typer.Option("local", "--type", help="Storage type: local or session"),
    cache_name: str = typer.Option("", "--cache-name", help="Cache storage name"),
    database: str = typer.Option("", "--database", help="IndexedDB database name"),
    store: str = typer.Option("", "--store", help="IndexedDB object store name"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Storage operations: DOM storage, Cache Storage, IndexedDB."""
    params = StorageParams(
        url=url,
        action=action,
        key=key or None,
        value=value or None,
        storage_type=storage_type,
        cache_name=cache_name or None,
        database=database or None,
        store=store or None,
        wait=WaitStrategy(strategy="load"),
    )

    async def _storage_action() -> Any:
        backend = _get_backend()
        try:
            return await StorageAction(params).execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_storage_action())
    if result is None:
        return

    if result is None:
        _echo("OK")
    elif isinstance(result, str):
        if output == "-":
            typer.echo(result)
        else:
            with open(output, "w") as f:
                f.write(result)
            _echo(f"Saved to {output}")
    else:
        _write_json_output(result, output, "storage result")

@app.command()
def sw(
    action: str = typer.Argument(..., help="SW action: list, unregister, update"),
    url: str = typer.Argument(..., help="URL to navigate to"),
    registration_id: str = typer.Option("", "--id", help="Service worker registration ID"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Service worker operations: list, unregister, update."""
    params = ServiceWorkerParams(
        url=url,
        action=action,
        registration_id=registration_id or None,
        wait=WaitStrategy(strategy="load"),
    )

    async def _sw_action() -> Any:
        backend = _get_backend()
        try:
            return await ServiceWorkerAction(params).execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_sw_action())
    if result is None:
        return

    if result is None:
        _echo("OK")
    else:
        _write_json_output(result, output, "service worker result")

@app.command()
def animation(
    action: str = typer.Argument(..., help="Animation action: list, pause, play, seek"),
    url: str = typer.Argument(..., help="URL to navigate to"),
    animation_id: str = typer.Option("", "--id", help="Animation ID"),
    time_ms: int = typer.Option(0, "--time", help="Seek time in milliseconds"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Animation operations: list, pause, play, seek."""
    params = AnimationParams(
        url=url,
        action=action,
        animation_id=animation_id or None,
        time_ms=time_ms if time_ms else None,
        wait=WaitStrategy(strategy="load"),
    )

    async def _animation_action() -> Any:
        backend = _get_backend()
        try:
            return await AnimationAction(params).execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_animation_action())
    if result is None:
        return

    if result is None:
        _echo("OK")
    else:
        _write_json_output(result, output, "animation result")

@app.command()
def webauthn(
    action: str = typer.Argument(
        ...,
        help="WebAuthn action: add-virtual-authenticator, "
             "remove-authenticator, add-credential, get-credentials",
    ),
    url: str = typer.Argument(..., help="URL to navigate to"),
    protocol: str = typer.Option("ctap2", "--protocol", help="Authenticator protocol"),
    transport: str = typer.Option("usb", "--transport", help="Transport type"),
    authenticator_id: str = typer.Option("", "--id", help="Authenticator ID"),
    credential: str = typer.Option("", "--credential", help="Credential JSON"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """WebAuthn virtual authenticator operations (experimental)."""

    cred_dict: dict[str, Any] | None = None
    if credential:
        try:
            cred_dict = json.loads(credential)
        except json.JSONDecodeError as e:
            typer.echo(f"Invalid credential JSON: {e}", err=True)
            raise typer.Exit(2) from e

    params = WebAuthnParams(
        url=url,
        action=action,
        protocol=protocol,
        transport=transport,
        authenticator_id=authenticator_id or None,
        credential=cred_dict,
        wait=WaitStrategy(strategy="load"),
    )

    async def _webauthn_action() -> Any:
        backend = _get_backend()
        try:
            return await WebAuthnAction(params).execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_webauthn_action())
    if result is None:
        return

    if result is None:
        _echo("OK")
    elif isinstance(result, str):
        typer.echo(result)
    else:
        _write_json_output(result, output, "webauthn result")

@app.command()
def webaudio(
    action: str = typer.Argument(
        ..., help="WebAudio action: list, get"
    ),
    url: str = typer.Argument(..., help="URL to navigate to"),
    context_id: str = typer.Option("", "--context-id", help="Audio context ID"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """WebAudio context operations (experimental)."""
    params = WebAudioParams(
        url=url,
        action=action,
        context_id=context_id or None,
        wait=WaitStrategy(strategy="load"),
    )

    async def _webaudio_action() -> Any:
        backend = _get_backend()
        try:
            return await WebAudioAction(params).execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_webaudio_action())
    if result is None:
        return

    if result is None:
        _echo("OK")
    else:
        _write_json_output(result, output, "webaudio result")

@app.command()
def media(
    action: str = typer.Argument(
        ..., help="Media action: list, messages"
    ),
    url: str = typer.Argument(..., help="URL to navigate to"),
    player_id: str = typer.Option("", "--player-id", help="Media player ID"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Media player operations (experimental)."""
    params = MediaParams(
        url=url,
        action=action,
        player_id=player_id or None,
        wait=WaitStrategy(strategy="load"),
    )

    async def _media_action() -> Any:
        backend = _get_backend()
        try:
            return await MediaAction(params).execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_media_action())
    if result is None:
        return

    if result is None:
        _echo("OK")
    else:
        _write_json_output(result, output, "media result")

@app.command()
def cast(
    action: str = typer.Argument(
        ..., help="Cast action: list, start-tab, stop"
    ),
    url: str = typer.Argument("", help="URL to navigate to (optional for list)"),
    sink_name: str = typer.Option("", "--sink-name", help="Cast sink name"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Cast mirroring operations (experimental)."""
    params = CastParams(
        url=url,
        action=action,
        sink_name=sink_name or None,
        wait=WaitStrategy(strategy="load"),
    )

    async def _cast_action() -> Any:
        backend = _get_backend()
        try:
            return await CastAction(params).execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_cast_action())
    if result is None:
        return

    if result is None:
        _echo("OK")
    else:
        _write_json_output(result, output, "cast result")

@app.command()
def bluetooth(
    action: str = typer.Argument(
        ..., help="Bluetooth action: emulate, stop"
    ),
    url: str = typer.Argument(..., help="URL to navigate to"),
    name: str = typer.Option("", "--name", help="Device name"),
    address: str = typer.Option(
        "00:00:00:00:00:01", "--address", help="Device MAC address"
    ),
) -> None:
    """Bluetooth BLE emulation operations (experimental)."""
    params = BluetoothParams(
        url=url,
        action=action,
        name=name or None,
        address=address,
        wait=WaitStrategy(strategy="load"),
    )

    async def _bluetooth_action() -> None:
        backend = _get_backend()
        try:
            await BluetoothAction(params).execute(backend)
        finally:
            await _close_backend(backend)

    _run_async(_bluetooth_action())
    _echo("OK")

@app.command()
def raw(
    method: str = typer.Argument(
        ..., help="Protocol method, e.g. 'Page.reload'"
    ),
    params: str = typer.Argument(
        "{}", help="JSON params for the command"
    ),
    backend_name: str = typer.Option(
        None, "--backend", help="Backend: cdp or bidi"
    ),
    output: str = typer.Option(
        None, "-o", "--output", help="Output file (- for stdout)"
    ),
) -> None:
    """Send raw protocol command to backend (escape hatch)."""

    try:
        raw_params = json.loads(params)
    except json.JSONDecodeError as e:
        typer.echo(f"Invalid params JSON: {e}", err=True)
        raise typer.Exit(2) from e

    async def _raw() -> dict[str, Any]:
        """Execute a raw protocol command against a browser backend.

        Returns:
            Raw protocol response as a dictionary.
        """
        if backend_name:
            backend = get_manager().select(preferred=backend_name)
        else:
            backend = _get_backend()
        try:
            await backend.launch(_browser_options())
            result: dict[str, Any] = await backend.raw(method, raw_params)
            return result
        finally:
            await _close_backend(backend)

    result = _run_async(_raw())
    if result is None:
        return

    _write_json_output(result, output or "-", "raw result")

def _write_json_output(
    result: dict[str, Any] | list[dict[str, Any]], output: str, label: str
) -> None:
    """Write JSON result to file or stdout."""
    if output == "-":
        typer.echo(json.dumps(result, indent=2, default=str))
    else:
        with open(output, "w") as f:
            json.dump(result, f, indent=2, default=str)
        _echo(f"Saved {label} to {output}")

