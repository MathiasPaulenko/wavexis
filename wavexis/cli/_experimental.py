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
from wavexis.actions.smart_card_emulation import (
    SmartCardEmulationAction,
    SmartCardEmulationParams,
)
from wavexis.actions.storage import StorageAction
from wavexis.actions.system_info import SystemInfoAction
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
from wavexis.config import AnimationParams, StorageParams, SystemInfoParams, WaitStrategy


@app.command()
def storage(
    action: str = typer.Argument(
        ...,
        help="Storage action: get, set, clear, list, cache-list, "
        "cache-entries, cache-delete, indexeddb-list, indexeddb-get, "
        "indexeddb-clear, clear-data-for-storage-key, delete-bucket, "
        "related-website-sets, shared-storage-metadata, "
        "get-storage-key, get-storage-key-for-frame, "
        "reset-shared-storage-budget, run-bounce-tracking, "
        "set-cookies, set-ig-auction-tracking, set-ig-tracking, "
        "set-protected-audience-k-anonymity, set-shared-storage-tracking, "
        "set-bucket-tracking, track-cache-origin, track-cache-key, "
        "track-idb-origin, track-idb-key, "
        "untrack-cache-origin, untrack-cache-key, "
        "untrack-idb-origin, untrack-idb-key",
    ),
    url: str = typer.Argument(..., help="URL to navigate to"),
    key: str = typer.Option("", "--key", help="Storage key"),
    value: str = typer.Option("", "--value", help="Storage value"),
    storage_type: str = typer.Option("local", "--type", help="Storage type: local or session"),
    cache_name: str = typer.Option("", "--cache-name", help="Cache storage name"),
    database: str = typer.Option("", "--database", help="IndexedDB database name"),
    store: str = typer.Option("", "--store", help="IndexedDB object store name"),
    origin: str = typer.Option("", "--origin", help="Origin for origin-based operations"),
    storage_key: str = typer.Option(
        "", "--storage-key", help="Storage key for key-based operations"
    ),
    bucket_name: str = typer.Option("", "--bucket-name", help="Storage bucket name"),
    owner_origin: str = typer.Option("", "--owner-origin", help="Owner origin for shared storage"),
    frame_id: str = typer.Option("", "--frame-id", help="Frame ID for storage key operations"),
    cookies: str = typer.Option("", "--cookies", help="Cookies JSON array"),
    enable: bool = typer.Option(False, "--enable", help="Enable flag for tracking toggles"),
    context_id: int = typer.Option(None, "--context-id", help="Auction context ID"),
    hashed_mac_key: str = typer.Option("", "--hashed-mac-key", help="Hashed MAC key"),
    storage_types: str = typer.Option("all", "--storage-types", help="Storage types to clear"),
    cache_id: str = typer.Option("", "--cache-id", help="CDP cache ID for cache operations"),
    request_url: str = typer.Option(
        "", "--request-url", help="Request URL for cache entry operations"
    ),
    request_headers: str = typer.Option("", "--request-headers", help="Request headers JSON array"),
    skip_count: int = typer.Option(0, "--skip-count", help="Number of entries to skip"),
    page_size: int = typer.Option(100, "--page-size", help="Maximum entries to return"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Storage operations: DOM storage, Cache Storage, IndexedDB, and tracking."""
    cookies_list: list[dict[str, Any]] | None = None
    if cookies:
        try:
            cookies_list = json.loads(cookies)
        except json.JSONDecodeError as e:
            typer.echo(f"Invalid cookies JSON: {e}", err=True)
            raise typer.Exit(2) from e

    request_headers_list: list[dict[str, str]] | None = None
    if request_headers:
        try:
            request_headers_list = json.loads(request_headers)
        except json.JSONDecodeError as e:
            typer.echo(f"Invalid request headers JSON: {e}", err=True)
            raise typer.Exit(2) from e

    params = StorageParams(
        url=url,
        action=action,
        key=key or None,
        value=value or None,
        storage_type=storage_type,
        cache_name=cache_name or None,
        database=database or None,
        store=store or None,
        origin=origin or None,
        storage_key=storage_key or None,
        bucket_name=bucket_name or None,
        owner_origin=owner_origin or None,
        frame_id=frame_id or None,
        cookies=cookies_list,
        enable=enable,
        context_id=context_id,
        hashed_mac_key=hashed_mac_key or None,
        storage_types=storage_types,
        cache_id=cache_id or None,
        request_url=request_url or None,
        request_headers=request_headers_list,
        skip_count=skip_count,
        page_size=page_size,
        wait=WaitStrategy(strategy="load"),
    )

    async def _storage_action() -> Any:
        backend = _get_backend()
        try:
            await backend.launch(_browser_options())
            return await StorageAction(params).execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_storage_action())
    if result is None:
        _echo("OK")
    elif isinstance(result, str):
        if output == "-":
            typer.echo(result)
        else:
            with open(output, "w", encoding="utf-8") as f:
                f.write(result)
            _echo(f"Saved to {output}")
    else:
        _write_json_output(result, output, "storage result")


@app.command()
def storage_clear_origin(
    url: str = typer.Argument(..., help="URL to navigate to"),
    origin: str = typer.Option("", "--origin", help="Origin to clear (empty = page origin)"),
    storage_types: str = typer.Option(
        "all", "--types", help="Storage types to clear (comma-separated)"
    ),
) -> None:
    """Clear storage data for a given origin."""
    _run_async(
        _storage_direct(
            url,
            lambda b: b.storage_clear_data_for_origin(
                origin or _extract_origin(url), storage_types
            ),
        )
    )
    _echo("Storage cleared for origin")


@app.command()
def storage_quota(
    url: str = typer.Argument(..., help="URL to navigate to"),
    origin: str = typer.Option("", "--origin", help="Origin to check (empty = page origin)"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Get usage and quota for a given origin."""
    result = _run_async(
        _storage_direct(
            url, lambda b: b.storage_get_usage_and_quota(origin or _extract_origin(url))
        )
    )
    if result is None:
        return
    _write_json_output(result, output, "usage and quota")


@app.command()
def storage_trust_tokens(
    url: str = typer.Argument(..., help="URL to navigate to"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Get all trust tokens."""
    result = _run_async(_storage_direct(url, lambda b: b.storage_get_trust_tokens()))
    if result is None:
        return
    _write_json_output(result, output, "trust tokens")


@app.command()
def storage_shared_storage(
    url: str = typer.Argument(..., help="URL to navigate to"),
    owner_origin: str = typer.Option(..., "--owner", help="Owner origin"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Get shared storage entries for an owner origin."""
    result = _run_async(
        _storage_direct(url, lambda b: b.storage_get_shared_storage_entries(owner_origin))
    )
    if result is None:
        return
    _write_json_output(result, output, "shared storage entries")


@app.command()
def storage_shared_storage_set(
    url: str = typer.Argument(..., help="URL to navigate to"),
    owner_origin: str = typer.Option(..., "--owner", help="Owner origin"),
    key: str = typer.Option(..., "--key", help="Entry key"),
    value: str = typer.Option(..., "--value", help="Entry value"),
) -> None:
    """Set a shared storage entry."""
    _run_async(
        _storage_direct(url, lambda b: b.storage_set_shared_storage_entry(owner_origin, key, value))
    )
    _echo("Shared storage entry set")


@app.command()
def storage_shared_storage_delete(
    url: str = typer.Argument(..., help="URL to navigate to"),
    owner_origin: str = typer.Option(..., "--owner", help="Owner origin"),
    key: str = typer.Option(..., "--key", help="Entry key"),
) -> None:
    """Delete a shared storage entry."""
    _run_async(
        _storage_direct(url, lambda b: b.storage_delete_shared_storage_entry(owner_origin, key))
    )
    _echo("Shared storage entry deleted")


@app.command()
def storage_shared_storage_clear(
    url: str = typer.Argument(..., help="URL to navigate to"),
    owner_origin: str = typer.Option(..., "--owner", help="Owner origin"),
) -> None:
    """Clear all shared storage entries for an owner origin."""
    _run_async(_storage_direct(url, lambda b: b.storage_clear_shared_storage_entries(owner_origin)))
    _echo("Shared storage entries cleared")


@app.command()
def storage_interest_group(
    url: str = typer.Argument(..., help="URL to navigate to"),
    owner_origin: str = typer.Option(..., "--owner", help="Owner origin"),
    name: str = typer.Option(..., "--name", help="Interest group name"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Get interest group details."""
    result = _run_async(
        _storage_direct(url, lambda b: b.storage_get_interest_group_details(owner_origin, name))
    )
    if result is None:
        return
    _write_json_output(result, output, "interest group details")


@app.command()
def storage_override_quota(
    url: str = typer.Argument(..., help="URL to navigate to"),
    origin: str = typer.Option("", "--origin", help="Origin to override (empty = page origin)"),
    quota_size: float = typer.Option(0, "--size", help="Quota size in bytes (0 = reset)"),
) -> None:
    """Override quota for a given origin."""
    _run_async(
        _storage_direct(
            url,
            lambda b: b.storage_override_quota_for_origin(
                origin or _extract_origin(url), quota_size if quota_size > 0 else None
            ),
        )
    )
    _echo("Quota overridden")


async def _storage_direct(url: str, action_fn: Any) -> Any:
    """Launch backend, navigate, and run a direct storage action."""
    backend = _get_backend()
    try:
        await backend.launch(_browser_options())
        await backend.navigate(url)
        return await action_fn(backend)
    finally:
        await _close_backend(backend)


def _extract_origin(url: str) -> str:
    """Extract origin from URL."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


@app.command()
def sw(
    action: str = typer.Argument(
        ...,
        help="SW action: list, unregister, update, enable, disable, "
        "deliver-push, dispatch-sync, get-messages, inspect, "
        "skip-waiting, start-worker, stop-worker",
    ),
    url: str = typer.Argument(..., help="URL to navigate to"),
    registration_id: str = typer.Option("", "--id", help="Service worker registration ID"),
    worker_id: str = typer.Option("", "--worker-id", help="Service worker target ID"),
    origin: str = typer.Option("", "--origin", help="Origin of the service worker"),
    scope_url: str = typer.Option("", "--scope-url", help="Scope URL"),
    data: str = typer.Option("", "--data", help="Push message data"),
    tag: str = typer.Option("", "--tag", help="Sync tag"),
    last_chance: bool = typer.Option(False, "--last-chance", help="Last chance for sync"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Service worker operations: list, unregister, update, and lifecycle."""
    params = ServiceWorkerParams(
        url=url,
        action=action,
        registration_id=registration_id or None,
        worker_id=worker_id or None,
        origin=origin or None,
        scope_url=scope_url or None,
        data=data,
        tag=tag,
        last_chance=last_chance,
        wait=WaitStrategy(strategy="load"),
    )

    async def _sw_action() -> Any:
        backend = _get_backend()
        try:
            await backend.launch(_browser_options())
            return await ServiceWorkerAction(params).execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_sw_action())
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
            await backend.launch(_browser_options())
            return await AnimationAction(params).execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_animation_action())
    if result is None:
        _echo("OK")
    else:
        _write_json_output(result, output, "animation result")


@app.command()
def webauthn(
    action: str = typer.Argument(
        ...,
        help="WebAuthn action: add-virtual-authenticator, "
        "remove-authenticator, add-credential, get-credentials, "
        "enable, disable, get-credential, remove-credential, "
        "clear-credentials, set-user-verified, "
        "set-automatic-presence-simulation, "
        "set-credential-properties, set-response-override-bits",
    ),
    url: str = typer.Argument(..., help="URL to navigate to"),
    protocol: str = typer.Option("ctap2", "--protocol", help="Authenticator protocol"),
    transport: str = typer.Option("usb", "--transport", help="Transport type"),
    authenticator_id: str = typer.Option("", "--id", help="Authenticator ID"),
    credential: str = typer.Option("", "--credential", help="Credential JSON"),
    credential_id: str = typer.Option("", "--credential-id", help="Credential ID"),
    is_user_verified: bool = typer.Option(False, "--user-verified", help="User verified flag"),
    enabled: bool = typer.Option(False, "--enabled", help="Enabled flag for presence simulation"),
    backup_state: bool = typer.Option(False, "--backup-state", help="Backup state"),
    backup_eligibility: bool = typer.Option(
        False, "--backup-eligibility", help="Backup eligibility"
    ),
    is_bogus_signature: bool = typer.Option(
        False, "--bogus-signature", help="Bogus signature flag"
    ),
    is_bad_uv: bool = typer.Option(False, "--bad-uv", help="Bad UV flag"),
    is_bad_up: bool = typer.Option(False, "--bad-up", help="Bad UP flag"),
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
        credential_id=credential_id or None,
        is_user_verified=is_user_verified,
        enabled=enabled,
        backup_state=backup_state,
        backup_eligibility=backup_eligibility,
        is_bogus_signature=is_bogus_signature,
        is_bad_uv=is_bad_uv,
        is_bad_up=is_bad_up,
        wait=WaitStrategy(strategy="load"),
    )

    async def _webauthn_action() -> Any:
        backend = _get_backend()
        try:
            await backend.launch(_browser_options())
            return await WebAuthnAction(params).execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_webauthn_action())
    if result is None:
        _echo("OK")
    elif isinstance(result, str):
        typer.echo(result)
    else:
        _write_json_output(result, output, "webauthn result")


@app.command()
def webaudio(
    action: str = typer.Argument(
        ..., help="WebAudio action: list, get, enable, disable, get-realtime-data"
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
            await backend.launch(_browser_options())
            return await WebAudioAction(params).execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_webaudio_action())
    if result is None:
        _echo("OK")
    else:
        _write_json_output(result, output, "webaudio result")


@app.command()
def media(
    action: str = typer.Argument(..., help="Media action: list, messages"),
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
            await backend.launch(_browser_options())
            return await MediaAction(params).execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_media_action())
    if result is None:
        _echo("OK")
    else:
        _write_json_output(result, output, "media result")


@app.command()
def cast(
    action: str = typer.Argument(
        ...,
        help="Cast action: list, start-tab, stop, enable, disable, "
        "set-sink, start-desktop-mirroring, start-tab-mirroring, "
        "stop-casting",
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
            await backend.launch(_browser_options())
            return await CastAction(params).execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_cast_action())
    if result is None:
        _echo("OK")
    else:
        _write_json_output(result, output, "cast result")


@app.command()
def bluetooth(
    action: str = typer.Argument(..., help="Bluetooth action: emulate, stop"),
    url: str = typer.Argument(..., help="URL to navigate to"),
    name: str = typer.Option("", "--name", help="Device name"),
    address: str = typer.Option("00:00:00:00:00:01", "--address", help="Device MAC address"),
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
            await backend.launch(_browser_options())
            await BluetoothAction(params).execute(backend)
        finally:
            await _close_backend(backend)

    _run_async(_bluetooth_action())
    _echo("OK")


@app.command()
def smartcard(
    action: str = typer.Argument(
        ...,
        help="SmartCard action: enable, disable, report-error, report-plain, "
        "report-connect, report-data, report-status, "
        "report-begin-transaction, report-establish-context, "
        "report-release-context, report-list-readers, "
        "report-get-status-change",
    ),
    url: str = typer.Argument("", help="URL to navigate to (optional for enable/disable)"),
    request_id: str = typer.Option("", "--request-id", help="Pending request identifier"),
    result_code: int = typer.Option(0, "--result-code", help="Smart card result code"),
    error: str = typer.Option("", "--error", help="Error code string"),
    connection_id: str = typer.Option("", "--connection-id", help="Connection identifier"),
    context_id: str = typer.Option("", "--context-id", help="Context identifier"),
    data: str = typer.Option("", "--data", help="Response data (hex-encoded)"),
    status: str = typer.Option("", "--status", help="Status string"),
    readers: str = typer.Option("", "--readers", help="Readers JSON array"),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Smart card reader emulation operations (experimental)."""
    readers_list: list[dict[str, Any]] | None = None
    if readers:
        try:
            readers_list = json.loads(readers)
        except json.JSONDecodeError as e:
            typer.echo(f"Invalid readers JSON: {e}", err=True)
            raise typer.Exit(2) from e

    params = SmartCardEmulationParams(
        url=url,
        action=action,
        request_id=request_id or None,
        result_code=result_code,
        error=error or None,
        connection_id=connection_id or None,
        context_id=context_id or None,
        data=data or None,
        status=status or None,
        readers=readers_list,
        wait=WaitStrategy(strategy="load"),
    )

    async def _smartcard_action() -> Any:
        backend = _get_backend()
        try:
            await backend.launch(_browser_options())
            return await SmartCardEmulationAction(params).execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_smartcard_action())
    if result is None:
        _echo("OK")
    else:
        _write_json_output(result, output, "smartcard result")


@app.command()
def raw(
    method: str = typer.Argument(..., help="Protocol method, e.g. 'Page.reload'"),
    params: str = typer.Argument("{}", help="JSON params for the command"),
    backend_name: str = typer.Option(None, "--backend", help="Backend: cdp or bidi"),
    output: str = typer.Option(None, "-o", "--output", help="Output file (- for stdout)"),
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
        backend = get_manager().select(preferred=backend_name) if backend_name else _get_backend()
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
        with open(output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
        _echo(f"Saved {label} to {output}")


@app.command()
def system_info(
    action: str = typer.Argument(
        ..., help="System info action: get-info, get-process-info, get-feature-state"
    ),
    url: str = typer.Argument("", help="URL to navigate to (optional)"),
    feature_name: str = typer.Option(
        "", "--feature-name", help="Feature name for get-feature-state"
    ),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """System information operations (experimental)."""
    params = SystemInfoParams(
        url=url,
        action=action,
        feature_name=feature_name or None,
        wait=WaitStrategy(strategy="load"),
    )

    async def _system_info_action() -> Any:
        backend = _get_backend()
        try:
            await backend.launch(_browser_options())
            return await SystemInfoAction(params).execute(backend)
        finally:
            await _close_backend(backend)

    result = _run_async(_system_info_action())
    if result is None:
        _echo("OK")
    else:
        _write_json_output(result, output, "system info result")


@app.command()
def tethering(
    action: str = typer.Argument(..., help="Tethering action: bind, unbind"),
    port: int = typer.Argument(..., help="Port number to bind/unbind"),
) -> None:
    """Tethering operations (accept/stop incoming connections on a port)."""

    async def _tethering_action() -> Any:
        backend = _get_backend()
        try:
            await backend.launch(_browser_options())
            if action == "bind":
                await backend.tethering_bind(port)
            elif action == "unbind":
                await backend.tethering_unbind(port)
            else:
                raise ValueError(f"Unknown tethering action: {action}")
        finally:
            await _close_backend(backend)

    _run_async(_tethering_action())
    _echo(f"Tethering {action} port {port}")


@app.command()
def tracing(
    action: str = typer.Argument(
        ...,
        help=(
            "Tracing action: start, end, get-categories, "
            "record-clock-sync, request-memory-dump, get-track-event"
        ),
    ),
    categories: str = typer.Option(
        "", "--categories", help="Comma-separated category filter for start"
    ),
    options: str = typer.Option("", "--options", help="Comma-separated tracing options for start"),
    transfer_mode: str = typer.Option(
        "ReturnAsStream", "--transfer-mode", help="Transfer mode for start"
    ),
    sync_id: str = typer.Option("", "--sync-id", help="Sync marker ID for record-clock-sync"),
    track_event: str = typer.Option(
        "", "--track-event", help="Track event name for get-track-event"
    ),
    output: str = typer.Option("-", "-o", "--output", help="Output file (- for stdout)"),
) -> None:
    """Tracing operations (collect trace events, memory dumps, categories)."""

    async def _tracing_action() -> Any:
        backend = _get_backend()
        try:
            await backend.launch(_browser_options())
            if action == "start":
                await backend.tracing_start(categories, options, transfer_mode)
                return None
            if action == "end":
                await backend.tracing_end()
                return None
            if action == "get-categories":
                return await backend.tracing_get_categories()
            if action == "record-clock-sync":
                if not sync_id:
                    raise ValueError("sync_id is required for record-clock-sync")
                await backend.tracing_record_clock_sync_marker(sync_id)
                return None
            if action == "request-memory-dump":
                return await backend.tracing_request_memory_dump()
            if action == "get-track-event":
                if not track_event:
                    raise ValueError("track_event is required for get-track-event")
                return await backend.tracing_get_track_event_descriptor(track_event)
            raise ValueError(f"Unknown tracing action: {action}")
        finally:
            await _close_backend(backend)

    result = _run_async(_tracing_action())
    if result is None:
        _echo("OK")
    else:
        _write_json_output(result, output, "tracing result")


@app.command()
def web_mcp(
    action: str = typer.Argument(..., help="WebMcp action: enable, disable"),
) -> None:
    """WebMcp operations (enable/disable the WebMcp domain)."""

    async def _web_mcp_action() -> Any:
        backend = _get_backend()
        try:
            await backend.launch(_browser_options())
            if action == "enable":
                await backend.web_mcp_enable()
            elif action == "disable":
                await backend.web_mcp_disable()
            else:
                raise ValueError(f"Unknown web_mcp action: {action}")
        finally:
            await _close_backend(backend)

    _run_async(_web_mcp_action())
    _echo(f"WebMcp {action}")
