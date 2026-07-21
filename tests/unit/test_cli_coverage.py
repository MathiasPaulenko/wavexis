"""Unit tests for CLI commands — exercises command handlers with mocked backends."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from wavexis.cli.app import app

runner = CliRunner()


def _mock_backend():
    """Create a mock backend with common return values."""
    backend = MagicMock()
    backend.launch = AsyncMock()
    backend.close = AsyncMock()
    backend.navigate = AsyncMock()
    backend.screenshot = AsyncMock(return_value=b"png-bytes")
    backend.pdf = AsyncMock(return_value=b"pdf-bytes")
    backend.eval = AsyncMock(return_value="result")
    backend.get_cookies = AsyncMock(return_value=[{"name": "session"}])
    backend.set_cookie = AsyncMock()
    backend.clear_cookies = AsyncMock()
    backend.set_headers = AsyncMock()
    backend.set_user_agent = AsyncMock()
    backend.dom_get = AsyncMock(return_value="<html></html>")
    backend.dom_query = AsyncMock(return_value={"nodeId": 1})
    backend.dom_set_attr = AsyncMock()
    backend.dom_get_attr = AsyncMock(return_value="value")
    backend.dom_remove_attr = AsyncMock()
    backend.dom_remove = AsyncMock()
    backend.dom_focus = AsyncMock()
    backend.dom_scroll = AsyncMock()
    backend.click = AsyncMock()
    backend.type = AsyncMock()
    backend.type_text = AsyncMock()
    backend.fill = AsyncMock()
    backend.hover = AsyncMock()
    backend.focus = AsyncMock()
    backend.select = AsyncMock()
    backend.press_key = AsyncMock()
    backend.key_press = AsyncMock()
    backend.scroll = AsyncMock()
    backend.go_back = AsyncMock()
    backend.go_forward = AsyncMock()
    backend.reload = AsyncMock()
    backend.stop_loading = AsyncMock()
    backend.wait_for = AsyncMock()
    backend.screencast = AsyncMock(return_value=[b"frame1"])
    backend.capture_console = AsyncMock(return_value=[{"type": "log"}])
    backend.capture_logs = AsyncMock(return_value=[{"level": "info"}])
    backend.capture_har = AsyncMock(return_value={"log": {"entries": []}})
    backend.new_context = AsyncMock(return_value="ctx-1")
    backend.list_contexts = AsyncMock(return_value=[{"contextId": "ctx-1"}])
    backend.close_context = AsyncMock()
    backend.new_tab = AsyncMock(return_value="tab-1")
    backend.list_tabs = AsyncMock(return_value=[{"targetId": "tab1"}])
    backend.close_tab = AsyncMock()
    backend.activate_tab = AsyncMock()
    backend.emulate_device = AsyncMock()
    backend.set_viewport = AsyncMock()
    backend.set_timezone = AsyncMock()
    backend.set_dark_mode = AsyncMock()
    backend.set_geolocation = AsyncMock()
    backend.browser_version = AsyncMock(return_value="Chrome/120")
    backend.get_window_bounds = AsyncMock(
        return_value={"width": 1280, "height": 800, "x": 0, "y": 0}
    )
    backend.set_window_bounds = AsyncMock()
    backend.start_combined_trace = AsyncMock(return_value="trace-1")
    backend.stop_combined_trace = AsyncMock(
        return_value={"events": [], "screenshots": [], "network": [], "console": []}
    )
    backend.replay_har = AsyncMock()
    backend.modify_request = AsyncMock()
    backend.download = AsyncMock()
    backend.print_page = AsyncMock()
    backend.crash = AsyncMock()
    backend.reset_permissions = AsyncMock()
    backend.set_permission = AsyncMock()
    backend.handle_dialog = AsyncMock()
    backend.list_dialogs = AsyncMock(return_value=[])
    return backend


@pytest.mark.unit
class TestCLISessionCommands:
    """Test session CLI commands."""

    def test_session_list_help(self) -> None:
        result = runner.invoke(app, ["session", "list", "--help"])
        assert result.exit_code == 0

    def test_session_save_help(self) -> None:
        result = runner.invoke(app, ["session", "save", "--help"])
        assert result.exit_code == 0

    def test_session_list_empty(self, tmp_path: Path) -> None:
        with patch("pathlib.Path.home", return_value=tmp_path):
            result = runner.invoke(app, ["session", "list"])
            assert result.exit_code == 0

    def test_session_list_with_existing_sessions(self, tmp_path: Path) -> None:
        """session list should print existing session names."""
        sessions_dir = tmp_path / ".wavexis" / "sessions"
        sessions_dir.mkdir(parents=True)
        (sessions_dir / "test1.json").write_text("{}")
        (sessions_dir / "test2.json").write_text("{}")
        with patch("pathlib.Path.home", return_value=tmp_path):
            result = runner.invoke(app, ["session", "list"])
            assert result.exit_code == 0
            assert "test1" in result.output
            assert "test2" in result.output

    def test_session_save_invalid_name(self, tmp_path: Path) -> None:
        """session save with a path traversal name should be rejected."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            result = runner.invoke(app, ["session", "save", "--name", "../escape"])
            assert result.exit_code == 1

    def test_session_save_dot_name(self, tmp_path: Path) -> None:
        """session save with '.' as name should be rejected."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            result = runner.invoke(app, ["session", "save", "--name", "."])
            assert result.exit_code == 1

    def test_session_save_double_dot_name(self, tmp_path: Path) -> None:
        """session save with '..' as name should be rejected."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            result = runner.invoke(app, ["session", "save", "--name", ".."])
            assert result.exit_code == 1

    def test_session_unknown_action(self, tmp_path: Path) -> None:
        """session with an unknown action should error out."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            result = runner.invoke(app, ["session", "unknown"])
            assert result.exit_code != 0

    def test_session_delete_help(self) -> None:
        """session delete --help should work."""
        result = runner.invoke(app, ["session", "delete", "--help"])
        assert result.exit_code == 0

    def test_session_load_help(self) -> None:
        """session load --help should work."""
        result = runner.invoke(app, ["session", "load", "--help"])
        assert result.exit_code == 0


@pytest.mark.unit
class TestCLINavigationCommands:
    """Test navigation CLI commands."""

    def test_back_help(self) -> None:
        result = runner.invoke(app, ["back", "--help"])
        assert result.exit_code == 0

    def test_forward_help(self) -> None:
        result = runner.invoke(app, ["forward", "--help"])
        assert result.exit_code == 0

    def test_reload_help(self) -> None:
        result = runner.invoke(app, ["reload", "--help"])
        assert result.exit_code == 0

    def test_stop_help(self) -> None:
        result = runner.invoke(app, ["stop", "--help"])
        assert result.exit_code == 0

    def test_wait_help(self) -> None:
        result = runner.invoke(app, ["navigate", "--help"])
        assert result.exit_code == 0


@pytest.mark.unit
class TestCLICaptureCommands:
    """Test capture CLI commands."""

    def test_screenshot_help(self) -> None:
        result = runner.invoke(app, ["screenshot", "--help"])
        assert result.exit_code == 0

    def test_pdf_help(self) -> None:
        result = runner.invoke(app, ["pdf", "--help"])
        assert result.exit_code == 0

    def test_har_help(self) -> None:
        result = runner.invoke(app, ["har", "--help"])
        assert result.exit_code == 0

    def test_console_help(self) -> None:
        result = runner.invoke(app, ["console", "--help"])
        assert result.exit_code == 0

    def test_screencast_help(self) -> None:
        result = runner.invoke(app, ["screencast", "--help"])
        assert result.exit_code == 0

    def test_cookies_help(self) -> None:
        result = runner.invoke(app, ["cookies", "--help"])
        assert result.exit_code == 0

    def test_dom_help(self) -> None:
        result = runner.invoke(app, ["dom", "--help"])
        assert result.exit_code == 0

    def test_scrape_help(self) -> None:
        result = runner.invoke(app, ["scrape", "--help"])
        assert result.exit_code == 0

    def test_extract_help(self) -> None:
        result = runner.invoke(app, ["extract", "--help"])
        assert result.exit_code == 0


@pytest.mark.unit
class TestCLIDebugCommands:
    """Test debug CLI commands."""

    def test_logs_help(self) -> None:
        result = runner.invoke(app, ["logs", "--help"])
        assert result.exit_code == 0

    def test_trace_help(self) -> None:
        result = runner.invoke(app, ["trace", "--help"])
        assert result.exit_code == 0

    def test_version_flag(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "wavexis" in result.stdout


@pytest.mark.unit
class TestCLIEmulationCommands:
    """Test emulation CLI commands."""

    def test_devices_help(self) -> None:
        result = runner.invoke(app, ["devices", "--help"])
        assert result.exit_code == 0

    def test_browser_help(self) -> None:
        result = runner.invoke(app, ["browser", "--help"])
        assert result.exit_code == 0


@pytest.mark.unit
class TestCLIExperimentalCommands:
    """Test experimental CLI commands."""

    def test_bluetooth_help(self) -> None:
        result = runner.invoke(app, ["bluetooth", "--help"])
        assert result.exit_code == 0

    def test_webaudio_help(self) -> None:
        result = runner.invoke(app, ["webaudio", "--help"])
        assert result.exit_code == 0

    def test_webauthn_help(self) -> None:
        result = runner.invoke(app, ["webauthn", "--help"])
        assert result.exit_code == 0

    def test_cast_help(self) -> None:
        result = runner.invoke(app, ["cast", "--help"])
        assert result.exit_code == 0

    def test_media_help(self) -> None:
        result = runner.invoke(app, ["media", "--help"])
        assert result.exit_code == 0


@pytest.mark.unit
class TestCLIIframeCommands:
    """Test iframe CLI commands."""

    def test_iframe_help(self) -> None:
        result = runner.invoke(app, ["iframe", "--help"])
        assert result.exit_code == 0


@pytest.mark.unit
class TestCLINetworkInspectCommands:
    """Test network inspect CLI commands."""

    def test_inspect_help(self) -> None:
        result = runner.invoke(app, ["inspect", "--help"])
        assert result.exit_code == 0

    def test_events_help(self) -> None:
        result = runner.invoke(app, ["events", "--help"])
        assert result.exit_code == 0


@pytest.mark.unit
class TestCLIPerfCommands:
    """Test performance CLI commands."""

    def test_perf_help(self) -> None:
        result = runner.invoke(app, ["perf", "--help"])
        assert result.exit_code == 0

    def test_lighthouse_help(self) -> None:
        result = runner.invoke(app, ["lighthouse", "--help"])
        assert result.exit_code == 0

    def test_cwv_help(self) -> None:
        result = runner.invoke(app, ["cwv", "--help"])
        assert result.exit_code == 0

    def test_perf_cmd_help(self) -> None:
        result = runner.invoke(app, ["perf", "--help"])
        assert result.exit_code == 0

    def test_backends_help(self) -> None:
        result = runner.invoke(app, ["backends", "--help"])
        assert result.exit_code == 0


@pytest.mark.unit
class TestCLIServeCommands:
    """Test serve CLI commands."""

    def test_serve_help(self) -> None:
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0


@pytest.mark.unit
class TestCLIShadowCommands:
    """Test shadow DOM CLI commands."""

    def test_shadow_help(self) -> None:
        result = runner.invoke(app, ["shadow", "--help"])
        assert result.exit_code == 0


@pytest.mark.unit
class TestCLIWorkflowCommands:
    """Test workflow CLI commands."""

    def test_multi_help(self) -> None:
        result = runner.invoke(app, ["multi", "--help"])
        assert result.exit_code == 0

    def test_multi_dry_run(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("actions:\n  - screenshot:\n      url: https://example.com\n")
        result = runner.invoke(app, ["multi", str(yaml_file), "--dry-run"])
        assert result.exit_code == 0

    def test_record_help(self) -> None:
        result = runner.invoke(app, ["record", "--help"])
        assert result.exit_code == 0

    def test_replay_help(self) -> None:
        result = runner.invoke(app, ["replay", "--help"])
        assert result.exit_code == 0


@pytest.mark.unit
class TestCLINLCommands:
    """Test natural language CLI commands."""

    def test_nl_help(self) -> None:
        result = runner.invoke(app, ["nl", "--help"])
        assert result.exit_code == 0


@pytest.mark.unit
class TestCLIAdvancedCommands:
    """Test advanced CLI commands."""

    def test_tabs_help(self) -> None:
        result = runner.invoke(app, ["tabs", "--help"])
        assert result.exit_code == 0

    def test_context_help(self) -> None:
        result = runner.invoke(app, ["session", "--help"])
        assert result.exit_code == 0

    def test_storage_help(self) -> None:
        result = runner.invoke(app, ["storage", "--help"])
        assert result.exit_code == 0

    def test_headers_help(self) -> None:
        result = runner.invoke(app, ["headers", "--help"])
        assert result.exit_code == 0

    def test_user_agent_help(self) -> None:
        result = runner.invoke(app, ["user-agent", "--help"])
        assert result.exit_code == 0

    def test_annotate_help(self) -> None:
        result = runner.invoke(app, ["annotate", "--help"])
        assert result.exit_code == 0

    def test_overlay_help(self) -> None:
        result = runner.invoke(app, ["overlay", "--help"])
        assert result.exit_code == 0

    def test_animation_help(self) -> None:
        result = runner.invoke(app, ["animation", "--help"])
        assert result.exit_code == 0

    def test_modify_help(self) -> None:
        result = runner.invoke(app, ["modify", "--help"])
        assert result.exit_code == 0

    def test_modify_response_help(self) -> None:
        result = runner.invoke(app, ["modify-response", "--help"])
        assert result.exit_code == 0

    def test_har_replay_help(self) -> None:
        result = runner.invoke(app, ["har-replay", "--help"])
        assert result.exit_code == 0

    def test_trace_help(self) -> None:
        result = runner.invoke(app, ["trace", "--help"])
        assert result.exit_code == 0

    def test_sw_help(self) -> None:
        result = runner.invoke(app, ["sw", "--help"])
        assert result.exit_code == 0

    def test_ws_help(self) -> None:
        result = runner.invoke(app, ["ws", "--help"])
        assert result.exit_code == 0

    def test_raw_help(self) -> None:
        result = runner.invoke(app, ["raw", "--help"])
        assert result.exit_code == 0

    def test_axe_help(self) -> None:
        result = runner.invoke(app, ["axe", "--help"])
        assert result.exit_code == 0

    def test_a11y_help(self) -> None:
        """a11y --help should work."""
        result = runner.invoke(app, ["a11y", "--help"])
        assert result.exit_code == 0

    def test_security_help(self) -> None:
        """security --help should work."""
        result = runner.invoke(app, ["security", "--help"])
        assert result.exit_code == 0

    def test_permissions_help(self) -> None:
        """permissions --help should work."""
        result = runner.invoke(app, ["permissions", "--help"])
        assert result.exit_code == 0

    def test_emulation_help(self) -> None:
        """emulation --help should work."""
        result = runner.invoke(app, ["emulation", "--help"])
        assert result.exit_code == 0

    def test_crawl_help(self) -> None:
        result = runner.invoke(app, ["crawl", "--help"])
        assert result.exit_code == 0

    def test_dom_snapshot_help(self) -> None:
        result = runner.invoke(app, ["dom-snapshot", "--help"])
        assert result.exit_code == 0

    def test_plugins_help(self) -> None:
        result = runner.invoke(app, ["plugins", "--help"])
        assert result.exit_code == 0

    def test_batch_help(self) -> None:
        result = runner.invoke(app, ["batch", "--help"])
        assert result.exit_code == 0

    def test_form_help(self) -> None:
        result = runner.invoke(app, ["form", "--help"])
        assert result.exit_code == 0

    def test_auth_help(self) -> None:
        result = runner.invoke(app, ["auth", "--help"])
        assert result.exit_code == 0

    def test_repl_help(self) -> None:
        result = runner.invoke(app, ["repl", "--help"])
        assert result.exit_code == 0

    def test_install_check_help(self) -> None:
        result = runner.invoke(app, ["install-check", "--help"])
        assert result.exit_code == 0

    def test_extension_commands_help(self) -> None:
        for cmd in ["extension-install", "extension-uninstall", "extension-list"]:
            result = runner.invoke(app, [cmd, "--help"])
            assert result.exit_code == 0

    def test_pref_commands_help(self) -> None:
        for cmd in ["pref-get", "pref-set"]:
            result = runner.invoke(app, [cmd, "--help"])
            assert result.exit_code == 0

    def test_completions_help(self) -> None:
        result = runner.invoke(app, ["completions", "--help"])
        assert result.exit_code == 0


@pytest.mark.unit
class TestCLIConfigCommands:
    """Test config CLI commands."""

    def test_config_help(self) -> None:
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0

    def test_config_init(self, tmp_path: Path) -> None:
        with patch("pathlib.Path.home", return_value=tmp_path):
            result = runner.invoke(app, ["config", "init"])
            assert result.exit_code == 0

    def test_config_show(self, tmp_path: Path) -> None:
        with patch("pathlib.Path.home", return_value=tmp_path):
            result = runner.invoke(app, ["config", "show"])
            assert result.exit_code == 0


@pytest.mark.unit
class TestCLISharedFunctions:
    """Test _shared.py helper functions directly."""

    def test_get_ctx_creates_default(self) -> None:
        from wavexis.cli._shared import CLIContext, _ctx, _get_ctx

        _ctx.set(None)
        ctx = _get_ctx()
        assert isinstance(ctx, CLIContext)
        assert ctx.headless is True

    def test_echo_quiet(self) -> None:
        from wavexis.cli._shared import CLIContext, _ctx, _echo

        ctx = CLIContext(quiet=True)
        _ctx.set(ctx)
        _echo("should not print")

    def test_echo_verbose(self) -> None:
        from wavexis.cli._shared import CLIContext, _ctx, _echo

        ctx = CLIContext(quiet=False, verbose=True)
        _ctx.set(ctx)
        _echo("should print")

    def test_progress_quiet(self) -> None:
        from wavexis.cli._shared import CLIContext, _ctx, _progress

        ctx = CLIContext(quiet=True)
        _ctx.set(ctx)
        _progress(1, 10, "test")

    def test_progress_normal(self) -> None:
        from wavexis.cli._shared import CLIContext, _ctx, _progress

        ctx = CLIContext(quiet=False)
        _ctx.set(ctx)
        _progress(1, 10, "test")

    def test_browser_options(self) -> None:
        from wavexis.cli._shared import CLIContext, _browser_options, _ctx

        ctx = CLIContext(headless=False, timeout=5000, proxy="http://proxy:8080")
        _ctx.set(ctx)
        opts = _browser_options()
        assert opts.headless is False
        assert opts.timeout == 5000
        assert opts.proxy == "http://proxy:8080"

    def test_handle_error_wavexis_error(self) -> None:
        import typer

        from wavexis.cli._shared import _handle_error
        from wavexis.exceptions import WavexisError

        with pytest.raises(typer.Exit):
            _handle_error(WavexisError("test error"))

    def test_handle_error_unhandled(self) -> None:
        from wavexis.cli._shared import _handle_error

        with pytest.raises(ValueError):
            _handle_error(ValueError("not handled"))

    def test_write_json_output_stdout(self) -> None:
        from wavexis.cli._shared import _write_json_output

        _write_json_output({"key": "value"}, "-", "result")

    def test_write_json_output_file(self, tmp_path: Path) -> None:
        from wavexis.cli._shared import _write_json_output

        out_file = str(tmp_path / "out.json")
        _write_json_output({"key": "value"}, out_file, "result")
        assert Path(out_file).exists()

    def test_load_global_config_no_file(self, tmp_path: Path) -> None:
        from wavexis.cli._shared import CLIContext, _ctx, _load_global_config

        ctx = CLIContext()
        _ctx.set(ctx)
        with patch("pathlib.Path.home", return_value=tmp_path):
            _load_global_config()

    def test_load_global_config_with_file(self, tmp_path: Path) -> None:
        from wavexis.cli._shared import CLIContext, _ctx, _load_global_config

        config_dir = tmp_path / ".wavexis"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text(
            "backend: cdp\nheadless: false\ntimeout: 60000\nproxy: http://proxy\n"
        )

        ctx = CLIContext()
        _ctx.set(ctx)
        with patch("pathlib.Path.home", return_value=tmp_path):
            _load_global_config()

        assert ctx.preferred_backend == "cdp"
        assert ctx.headless is False
        assert ctx.timeout == 60000

    def test_load_global_config_invalid_yaml(self, tmp_path: Path) -> None:
        from wavexis.cli._shared import CLIContext, _ctx, _load_global_config

        config_dir = tmp_path / ".wavexis"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text("not: valid: yaml: [")

        ctx = CLIContext(verbose=True)
        _ctx.set(ctx)
        with patch("pathlib.Path.home", return_value=tmp_path):
            _load_global_config()

    def test_load_global_config_all_keys(self, tmp_path: Path) -> None:
        """All supported config keys should be loaded into the context."""
        from wavexis.cli._shared import CLIContext, _ctx, _load_global_config

        config_dir = tmp_path / ".wavexis"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text(
            "backend: cdp\n"
            "headless: false\n"
            "timeout: 60000\n"
            "proxy: http://proxy\n"
            "user_data_dir: /tmp/profile\n"
            "browser_url: http://localhost:9222\n"
            "remote_url: http://remote:8080\n"
            "stealth: true\n"
        )

        ctx = CLIContext()
        _ctx.set(ctx)
        with patch("pathlib.Path.home", return_value=tmp_path):
            _load_global_config()

        assert ctx.preferred_backend == "cdp"
        assert ctx.headless is False
        assert ctx.timeout == 60000
        assert ctx.proxy == "http://proxy"
        assert ctx.user_data_dir == "/tmp/profile"
        assert ctx.browser_url == "http://localhost:9222"
        assert ctx.remote_url == "http://remote:8080"
        assert ctx.stealth is True

    def test_load_global_config_non_dict_yaml(self, tmp_path: Path) -> None:
        """A YAML file containing a non-dict value should be ignored."""
        from wavexis.cli._shared import CLIContext, _ctx, _load_global_config

        config_dir = tmp_path / ".wavexis"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text("- just\n- a\n- list\n")

        ctx = CLIContext()
        _ctx.set(ctx)
        with patch("pathlib.Path.home", return_value=tmp_path):
            _load_global_config()
        # Should not crash, and no fields should be set
        assert ctx.preferred_backend is None

    def test_load_global_config_pyyaml_missing(self, tmp_path: Path) -> None:
        """Missing PyYAML should be handled gracefully with a verbose warning."""
        from wavexis.cli._shared import CLIContext, _ctx, _load_global_config

        config_dir = tmp_path / ".wavexis"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text("backend: cdp\n")

        ctx = CLIContext(verbose=True)
        _ctx.set(ctx)
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("no yaml")
            return real_import(name, *args, **kwargs)

        with patch("pathlib.Path.home", return_value=tmp_path), patch(
            "builtins.__import__", side_effect=fake_import
        ):
            _load_global_config()

    def test_run_coro_handles_wavexis_error(self) -> None:
        """_run_async should handle WavexisError by raising typer.Exit."""
        import typer

        from wavexis.cli._shared import _run_async
        from wavexis.exceptions import WavexisError

        async def fail() -> None:
            raise WavexisError("boom")

        with pytest.raises(typer.Exit):
            _run_async(fail())

    def test_run_coro_returns_value(self) -> None:
        """_run_async should return the coroutine's result on success."""
        from wavexis.cli._shared import _run_async

        async def succeed() -> str:
            return "ok"

        result = _run_async(succeed())
        assert result == "ok"
