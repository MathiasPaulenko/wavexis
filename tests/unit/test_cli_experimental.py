"""Unit tests for wavexis.cli._experimental commands."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from wavexis.cli.app import app

runner = CliRunner()


@pytest.fixture
def backend() -> AsyncMock:
    """Provide a mock backend for experimental CLI tests."""
    return _make_backend()


def _make_backend() -> AsyncMock:
    """Return a mock backend for experimental commands."""
    backend = AsyncMock()
    backend.launch = AsyncMock()
    backend.close = AsyncMock()
    backend.navigate = AsyncMock()
    backend.raw = AsyncMock(return_value={"ok": True})
    backend.tethering_bind = AsyncMock()
    backend.tethering_unbind = AsyncMock()
    backend.tracing_start = AsyncMock()
    backend.tracing_end = AsyncMock()
    backend.tracing_get_categories = AsyncMock(return_value=[])
    backend.tracing_record_clock_sync_marker = AsyncMock()
    backend.tracing_request_memory_dump = AsyncMock(return_value={})
    backend.tracing_get_track_event_descriptor = AsyncMock(return_value={})
    backend.web_mcp_enable = AsyncMock()
    backend.web_mcp_disable = AsyncMock()
    backend.storage_clear_data_for_origin = AsyncMock()
    backend.storage_get_usage_and_quota = AsyncMock(return_value={"usage": 0})
    backend.storage_get_trust_tokens = AsyncMock(return_value=[])
    backend.storage_get_shared_storage_entries = AsyncMock(return_value=[])
    backend.storage_set_shared_storage_entry = AsyncMock()
    backend.storage_delete_shared_storage_entry = AsyncMock()
    backend.storage_clear_shared_storage_entries = AsyncMock()
    backend.storage_get_interest_group_details = AsyncMock(return_value={})
    backend.storage_override_quota_for_origin = AsyncMock()
    return backend


def _run_action_cmd(args: list[str], target: str, result: Any, backend: AsyncMock) -> Any:
    """Invoke an experimental command with the given Action class patched."""
    with patch(f"wavexis.cli._experimental.{target}") as mock_action:
        mock_action.return_value.execute = AsyncMock(return_value=result)
        with patch("wavexis.cli._experimental._get_backend", return_value=backend):
            return runner.invoke(app, args)


@pytest.mark.unit
class TestExperimentalActionCommands:
    """Tests for experimental commands that use Action classes."""

    def test_storage_list(self, backend: AsyncMock) -> None:
        result = _run_action_cmd(
            ["storage", "list", "https://example.com"],
            "StorageAction",
            {"items": []},
            backend,
        )
        assert result.exit_code == 0

    def test_sw_list(self, backend: AsyncMock) -> None:
        result = _run_action_cmd(
            ["sw", "list", "https://example.com"],
            "ServiceWorkerAction",
            [],
            backend,
        )
        assert result.exit_code == 0

    def test_animation_list(self, backend: AsyncMock) -> None:
        result = _run_action_cmd(
            ["animation", "list", "https://example.com"],
            "AnimationAction",
            [],
            backend,
        )
        assert result.exit_code == 0

    def test_webauthn_add(self, backend: AsyncMock) -> None:
        result = _run_action_cmd(
            ["webauthn", "add-virtual-authenticator", "https://example.com"],
            "WebAuthnAction",
            "auth-id",
            backend,
        )
        assert result.exit_code == 0
        assert "auth-id" in result.output

    def test_webaudio_list(self, backend: AsyncMock) -> None:
        result = _run_action_cmd(
            ["webaudio", "list", "https://example.com"],
            "WebAudioAction",
            [],
            backend,
        )
        assert result.exit_code == 0

    def test_cast_list(self, backend: AsyncMock) -> None:
        result = _run_action_cmd(
            ["cast", "list", "https://example.com"],
            "CastAction",
            [],
            backend,
        )
        assert result.exit_code == 0

    def test_bluetooth_emulate(self, backend: AsyncMock) -> None:
        result = _run_action_cmd(
            ["bluetooth", "emulate", "https://example.com", "--name", "Device"],
            "BluetoothAction",
            None,
            backend,
        )
        assert result.exit_code == 0

    def test_smartcard_enable(self, backend: AsyncMock) -> None:
        result = _run_action_cmd(
            ["smartcard", "enable", "https://example.com"],
            "SmartCardEmulationAction",
            {"status": "ok"},
            backend,
        )
        assert result.exit_code == 0

    def test_system_info(self, backend: AsyncMock) -> None:
        result = _run_action_cmd(
            ["system-info", "get-info"],
            "SystemInfoAction",
            {"os": "linux"},
            backend,
        )
        assert result.exit_code == 0
        assert "os" in result.output


@pytest.mark.unit
class TestExperimentalDirectCommands:
    """Tests for experimental commands that call backend methods directly."""

    def test_raw(self, backend: AsyncMock) -> None:
        with patch("wavexis.cli._experimental._get_backend", return_value=backend):
            result = runner.invoke(app, ["raw", "Page.reload"])
        assert result.exit_code == 0
        backend.raw.assert_awaited_once_with("Page.reload", {})

    def test_raw_invalid_json(self, backend: AsyncMock) -> None:
        with patch("wavexis.cli._experimental._get_backend", return_value=backend):
            result = runner.invoke(app, ["raw", "Page.reload", "not-json"])
        assert result.exit_code == 2

    def test_tethering_bind(self, backend: AsyncMock) -> None:
        with patch("wavexis.cli._experimental._get_backend", return_value=backend):
            result = runner.invoke(app, ["tethering", "bind", "9222"])
        assert result.exit_code == 0
        backend.tethering_bind.assert_awaited_once_with(9222)

    def test_tethering_unknown(self, backend: AsyncMock) -> None:
        with patch("wavexis.cli._experimental._get_backend", return_value=backend):
            result = runner.invoke(app, ["tethering", "bad", "9222"])
        assert result.exit_code != 0

    def test_tracing_start(self, backend: AsyncMock) -> None:
        with patch("wavexis.cli._experimental._get_backend", return_value=backend):
            result = runner.invoke(app, ["tracing", "start"])
        assert result.exit_code == 0
        backend.tracing_start.assert_awaited_once_with("", "", "ReturnAsStream")

    def test_tracing_get_categories(self, backend: AsyncMock) -> None:
        with patch("wavexis.cli._experimental._get_backend", return_value=backend):
            result = runner.invoke(app, ["tracing", "get-categories"])
        assert result.exit_code == 0
        backend.tracing_get_categories.assert_awaited_once()

    def test_tracing_record_clock_sync_without_sync_id(self, backend: AsyncMock) -> None:
        with patch("wavexis.cli._experimental._get_backend", return_value=backend):
            result = runner.invoke(app, ["tracing", "record-clock-sync"])
        assert result.exit_code != 0

    def test_web_mcp_enable(self, backend: AsyncMock) -> None:
        with patch("wavexis.cli._experimental._get_backend", return_value=backend):
            result = runner.invoke(app, ["web-mcp", "enable"])
        assert result.exit_code == 0
        backend.web_mcp_enable.assert_awaited_once()


@pytest.mark.unit
class TestExperimentalStorageDirectCommands:
    """Tests for storage_* commands that call backend methods directly."""

    def test_storage_clear_origin(self, backend: AsyncMock) -> None:
        with patch("wavexis.cli._experimental._get_backend", return_value=backend):
            result = runner.invoke(app, ["storage-clear-origin", "https://example.com"])
        assert result.exit_code == 0
        backend.storage_clear_data_for_origin.assert_awaited_once()

    def test_storage_quota(self, backend: AsyncMock) -> None:
        with patch("wavexis.cli._experimental._get_backend", return_value=backend):
            result = runner.invoke(app, ["storage-quota", "https://example.com"])
        assert result.exit_code == 0
        backend.storage_get_usage_and_quota.assert_awaited_once()

    def test_storage_trust_tokens(self, backend: AsyncMock) -> None:
        with patch("wavexis.cli._experimental._get_backend", return_value=backend):
            result = runner.invoke(app, ["storage-trust-tokens", "https://example.com"])
        assert result.exit_code == 0
        backend.storage_get_trust_tokens.assert_awaited_once()

    def test_storage_shared_storage(self, backend: AsyncMock) -> None:
        with patch("wavexis.cli._experimental._get_backend", return_value=backend):
            result = runner.invoke(
                app, ["storage-shared-storage", "https://example.com", "--owner", "https://example.com"]
            )
        assert result.exit_code == 0
        backend.storage_get_shared_storage_entries.assert_awaited_once()

    def test_storage_shared_storage_set(self, backend: AsyncMock) -> None:
        with patch("wavexis.cli._experimental._get_backend", return_value=backend):
            result = runner.invoke(
                app,
                [
                    "storage-shared-storage-set",
                    "https://example.com",
                    "--owner",
                    "https://example.com",
                    "--key",
                    "k",
                    "--value",
                    "v",
                ],
            )
        assert result.exit_code == 0
        backend.storage_set_shared_storage_entry.assert_awaited_once()

    def test_storage_override_quota(self, backend: AsyncMock) -> None:
        with patch("wavexis.cli._experimental._get_backend", return_value=backend):
            result = runner.invoke(
                app, ["storage-override-quota", "https://example.com", "--size", "1000000"]
            )
        assert result.exit_code == 0
        backend.storage_override_quota_for_origin.assert_awaited_once()

    def test_storage_direct_passes_wait_strategy(self, backend: AsyncMock) -> None:
        """Regression: _storage_direct must pass _wait_strategy() to navigate."""
        with patch("wavexis.cli._experimental._get_backend", return_value=backend):
            result = runner.invoke(
                app, ["storage-clear-origin", "https://example.com"]
            )
        assert result.exit_code == 0
        backend.navigate.assert_awaited_once()
        call_args = backend.navigate.call_args
        assert len(call_args.args) >= 2 or "wait" in call_args.kwargs
        wait_arg = call_args.args[1] if len(call_args.args) >= 2 else call_args.kwargs.get("wait")
        assert wait_arg is not None
