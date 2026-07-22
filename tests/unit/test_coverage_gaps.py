"""Unit tests to close coverage gaps for actions and modules at 0% or low coverage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from tests.conftest import MockBackend


@pytest.mark.unit
class TestCoreWebVitals:
    """Tests for core_web_vitals action."""

    def test_rating_good(self) -> None:
        from wavexis.actions.core_web_vitals import _rating

        assert _rating(100, 2500, 4000) == "good"

    def test_rating_needs_improvement(self) -> None:
        from wavexis.actions.core_web_vitals import _rating

        assert _rating(3000, 2500, 4000) == "needs-improvement"

    def test_rating_poor(self) -> None:
        from wavexis.actions.core_web_vitals import _rating

        assert _rating(5000, 2500, 4000) == "poor"

    async def test_execute_collects_metrics(self) -> None:
        from wavexis.actions.core_web_vitals import (
            CoreWebVitalsAction,
            CoreWebVitalsParams,
        )

        backend = MockBackend()
        backend.eval = AsyncMock(
            side_effect=[
                {"lcp": 2000, "cls": 0.05, "inp": 100, "tbt": 50},
                {"ttfb": 400, "fcp": 1200, "load": 2500, "domSize": 500, "transferSize": 10000},
            ]
        )
        params = CoreWebVitalsParams(url="https://example.com")
        action = CoreWebVitalsAction(params)
        result = await action.execute(backend)

        assert "metrics" in result
        assert "ratings" in result
        assert "score" in result
        assert result["ratings"]["lcp_ms"] == "good"
        assert result["ratings"]["cls"] == "good"
        assert result["score"] == 100

    async def test_execute_with_budgets(self) -> None:
        from wavexis.actions.core_web_vitals import (
            CoreWebVitalsAction,
            CoreWebVitalsParams,
        )

        backend = MockBackend()
        backend.eval = AsyncMock(
            side_effect=[
                {"lcp": 5000, "cls": 0.3, "inp": 600, "tbt": 700},
                {"ttfb": 2000, "fcp": 3500, "load": 6000, "domSize": 4000, "transferSize": 50000},
            ]
        )
        params = CoreWebVitalsParams(
            url="https://example.com",
            budgets={"lcp_ms": 2500, "cls": 0.1},
        )
        action = CoreWebVitalsAction(params)
        result = await action.execute(backend)

        assert "budgets" in result
        assert result["budgets"]["all_pass"] is False
        assert result["budgets"]["lcp_ms"]["pass"] is False
        assert result["score"] < 100

    def test_compute_score_poor_metrics(self) -> None:
        from wavexis.actions.core_web_vitals import CoreWebVitalsAction, CoreWebVitalsParams

        action = CoreWebVitalsAction(CoreWebVitalsParams())
        metrics = {
            "lcp_ms": 5000,
            "cls": 0.3,
            "inp_ms": 600,
            "fcp_ms": 3500,
            "ttfb_ms": 2000,
            "tbt_ms": 700,
            "load_ms": 6000,
        }
        score = action._compute_score(metrics, dom_size=4000)
        assert score < 50

    def test_compute_score_good_metrics(self) -> None:
        from wavexis.actions.core_web_vitals import CoreWebVitalsAction, CoreWebVitalsParams

        action = CoreWebVitalsAction(CoreWebVitalsParams())
        metrics = {
            "lcp_ms": 1000,
            "cls": 0.05,
            "inp_ms": 100,
            "fcp_ms": 1000,
            "ttfb_ms": 400,
            "tbt_ms": 50,
            "load_ms": 2000,
        }
        score = action._compute_score(metrics, dom_size=500)
        assert score == 100

    def test_check_budgets_all_pass(self) -> None:
        from wavexis.actions.core_web_vitals import CoreWebVitalsAction, CoreWebVitalsParams

        action = CoreWebVitalsAction(CoreWebVitalsParams())
        metrics = {"lcp_ms": 1000, "cls": 0.05}
        budgets = {"lcp_ms": 2500, "cls": 0.1}
        result = action._check_budgets(metrics, budgets)
        assert result["all_pass"] is True

    def test_check_budgets_some_fail(self) -> None:
        from wavexis.actions.core_web_vitals import CoreWebVitalsAction, CoreWebVitalsParams

        action = CoreWebVitalsAction(CoreWebVitalsParams())
        metrics = {"lcp_ms": 5000, "cls": 0.05}
        budgets = {"lcp_ms": 2500, "cls": 0.1}
        result = action._check_budgets(metrics, budgets)
        assert result["all_pass"] is False
        assert result["lcp_ms"]["pass"] is False
        assert result["cls"]["pass"] is True


@pytest.mark.unit
class TestMultiAction:
    """Tests for actions/multi.py."""

    async def test_multi_action_executes(self, tmp_path: Path) -> None:
        from wavexis.actions.multi import MultiAction

        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("actions:\n  - screenshot:\n      url: https://example.com\n")
        backend = MockBackend()
        action = MultiAction(yaml_file)
        result = await action.execute(backend)

        assert isinstance(result, list)
        assert len(result) == 1

    async def test_multi_action_parallel(self, tmp_path: Path) -> None:
        from wavexis.actions.multi import MultiAction

        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            "actions:\n"
            "  - screenshot:\n"
            "      url: https://example.com\n"
            "  - pdf:\n"
            "      url: https://example.com\n"
        )
        backend = MockBackend()
        tab_mock = AsyncMock()
        tab_mock.close = AsyncMock()
        backend.new_tab_handle = AsyncMock(return_value=tab_mock)
        action = MultiAction(yaml_file, parallel=True)
        result = await action.execute(backend)

        assert isinstance(result, list)
        assert len(result) == 2


@pytest.mark.unit
class TestCombinedTraceAction:
    """Tests for combined_trace action."""

    async def test_start_trace(self) -> None:
        from wavexis.actions.combined_trace import (
            CombinedTraceAction,
            CombinedTraceParams,
        )

        backend = MockBackend()
        backend.start_combined_trace = AsyncMock(return_value="trace-1")
        backend.stop_combined_trace = AsyncMock(
            return_value={"events": [], "screenshots": [], "network": [], "console": []}
        )
        params = CombinedTraceParams(url="https://example.com", action="start", duration_ms=100)
        action = CombinedTraceAction(params)
        result = await action.execute(backend)

        assert "events" in result

    async def test_stop_trace(self) -> None:
        from wavexis.actions.combined_trace import (
            CombinedTraceAction,
            CombinedTraceParams,
        )

        backend = MockBackend()
        backend.stop_combined_trace = AsyncMock(
            return_value={"events": ["evt1"], "screenshots": [], "network": [], "console": []}
        )
        params = CombinedTraceParams(action="stop", trace_id="trace-abc")
        action = CombinedTraceAction(params)
        result = await action.execute(backend)

        assert "events" in result
        assert result["events"] == ["evt1"]

    async def test_unknown_action(self) -> None:
        from wavexis.actions.combined_trace import (
            CombinedTraceAction,
            CombinedTraceParams,
        )

        backend = MockBackend()
        params = CombinedTraceParams(action="invalid")
        action = CombinedTraceAction(params)

        with pytest.raises(ValueError, match="Unknown combined_trace action"):
            await action.execute(backend)


@pytest.mark.unit
class TestHARReplayAction:
    """Tests for har_replay action."""

    async def test_replay(self) -> None:
        from wavexis.actions.har_replay import HARReplayAction, HARReplayParams

        backend = MockBackend()
        backend.replay_har = AsyncMock()
        params = HARReplayParams(har_path="/tmp/test.har", url="https://example.com")
        action = HARReplayAction(params)
        result = await action.execute(backend)

        assert result["status"] == "ok"
        assert result["har_path"] == "/tmp/test.har"

    async def test_replay_no_url(self) -> None:
        from wavexis.actions.har_replay import HARReplayAction, HARReplayParams

        backend = MockBackend()
        backend.replay_har = AsyncMock()
        params = HARReplayParams(har_path="/tmp/test.har")
        action = HARReplayAction(params)
        result = await action.execute(backend)

        assert result["status"] == "ok"


@pytest.mark.unit
class TestModifyRequestAction:
    """Tests for modify_request action."""

    async def test_modify_with_url(self) -> None:
        from wavexis.actions.modify_request import (
            ModifyRequestAction,
            ModifyRequestParams,
        )

        backend = MockBackend()
        backend.modify_request = AsyncMock()
        params = ModifyRequestParams(
            url="https://example.com",
            pattern={"urlPattern": "*api*"},
            modifications={"headers": {"X-Custom": "value"}},
        )
        action = ModifyRequestAction(params)
        result = await action.execute(backend)

        assert result["status"] == "ok"
        assert result["pattern"] == {"urlPattern": "*api*"}

    async def test_modify_no_url(self) -> None:
        from wavexis.actions.modify_request import (
            ModifyRequestAction,
            ModifyRequestParams,
        )

        backend = MockBackend()
        backend.modify_request = AsyncMock()
        params = ModifyRequestParams(pattern={"urlPattern": "*"})
        action = ModifyRequestAction(params)
        result = await action.execute(backend)

        assert result["status"] == "ok"


@pytest.mark.unit
class TestMainModule:
    """Tests for __main__.py."""

    def test_main_entry_point(self) -> None:
        with patch("wavexis.cli.main") as mock_main:
            import wavexis.__main__ as main_mod

            main_mod.main()
            mock_main.assert_called_once()

    def test_cli_main_invokes_app(self) -> None:
        """wavexis.cli.main() should invoke the typer app with a clean prog_name."""
        with patch("wavexis.cli.app") as mock_app:
            from wavexis.cli import main

            main()
            mock_app.assert_called_once_with(prog_name="wavexis")

    def test_show_completion_uses_clean_prog_name(self) -> None:
        """Shell completion scripts must not contain spaces in env vars or command names."""
        import sys

        from wavexis.cli.app import app

        runner = CliRunner()
        # Use bash completion on non-Windows platforms (CI runs on Linux).
        shell = "powershell" if sys.platform == "win32" else "bash"
        result = runner.invoke(app, ["--show-completion", shell], prog_name="wavexis")
        assert result.exit_code == 0
        script = result.output
        assert "_PYTHON _M" not in script
        assert "python -m wavexis" not in script
        if shell == "powershell":
            assert "$Env:_WAVEXIS_COMPLETE" in script
            assert "Register-ArgumentCompleter -Native -CommandName wavexis" in script
        else:
            assert "_WAVEXIS_COMPLETE=" in script

    def test_cleanup_hook_suppresses_proactor_noise(self) -> None:
        """The unraisablehook swallows asyncio Proactor cleanup artefacts."""
        import sys
        from types import SimpleNamespace

        from wavexis.cli import _install_asyncio_cleanup_hooks

        called: list[SimpleNamespace] = []

        def fake_original(unraisable: SimpleNamespace) -> None:
            called.append(unraisable)

        old_hook = sys.unraisablehook
        try:
            sys.unraisablehook = fake_original
            _install_asyncio_cleanup_hooks()
            hook = sys.unraisablehook

            # Pattern 1: "Exception ignored while calling deallocator"
            noise_dealloc = SimpleNamespace(
                err_msg="Exception ignored while calling deallocator",
                exc_value=ValueError("I/O operation on closed pipe"),
            )
            hook(noise_dealloc)
            assert not called, "deallocator pipe noise should be suppressed"

            # Pattern 2: "Exception ignored in:"
            noise_in = SimpleNamespace(
                err_msg="Exception ignored in:",
                exc_value=ValueError("I/O operation on closed pipe"),
            )
            hook(noise_in)
            assert not called, "'Exception ignored in:' pipe noise should be suppressed"

            # Non-pipe deallocator errors should still be reported
            other = SimpleNamespace(
                err_msg="Exception ignored while calling deallocator",
                exc_value=ValueError("something else"),
            )
            hook(other)
            assert called == [other], "Other deallocator errors should still be reported"

            # Pipe errors with unrelated err_msg should be reported
            unrelated = SimpleNamespace(
                err_msg="some other context",
                exc_value=ValueError("I/O operation on closed pipe"),
            )
            hook(unrelated)
            assert called == [other, unrelated], "Unrelated pipe errors should be reported"
        finally:
            sys.unraisablehook = old_hook


@pytest.mark.unit
class TestAuthFull:
    """Tests for auth.py to cover uncovered lines."""

    async def test_apply_auth_context_with_cookies_and_headers(self) -> None:
        from wavexis.auth import AuthContext, apply_auth_context

        backend = MockBackend()
        backend.set_cookie = AsyncMock()
        backend.set_headers = AsyncMock()
        backend.navigate = AsyncMock()

        ctx = AuthContext(
            cookies=[{"name": "session", "value": "abc", "domain": "example.com", "path": "/"}],
            headers={"Authorization": "Bearer token"},
        )
        await apply_auth_context(backend, ctx, "https://example.com")

        backend.set_cookie.assert_called_once()
        assert backend.set_headers.call_count == 1
        assert backend.navigate.call_count == 2

    async def test_apply_auth_context_empty(self) -> None:
        from wavexis.auth import AuthContext, apply_auth_context

        backend = MockBackend()
        backend.navigate = AsyncMock()
        ctx = AuthContext()
        await apply_auth_context(backend, ctx, "https://example.com")
        assert backend.navigate.call_count == 1

    async def test_apply_auth_context_basic_auth(self) -> None:
        from wavexis.auth import AuthContext, apply_auth_context

        backend = MockBackend()
        backend.set_headers = AsyncMock()
        backend.set_cookie = AsyncMock()
        backend.navigate = AsyncMock()

        ctx = AuthContext(username="user", password="pass")
        await apply_auth_context(backend, ctx, "https://example.com")

        assert backend.set_headers.call_count == 1

    def test_load_auth_context_with_password_warning(self, tmp_path: Path, caplog) -> None:
        import logging

        from wavexis.auth import load_auth_context

        auth_file = tmp_path / "auth.json"
        auth_file.write_text('{"username": "admin", "password": "secret"}')

        with caplog.at_level(logging.WARNING):
            ctx = load_auth_context(str(auth_file))

        assert ctx.username == "admin"
        assert ctx.password == "secret"
        assert any("plain-text password" in r.message for r in caplog.records)

    def test_load_auth_context_no_password(self, tmp_path: Path) -> None:
        from wavexis.auth import load_auth_context

        auth_file = tmp_path / "auth.json"
        auth_file.write_text('{"username": "admin", "cookies": []}')

        ctx = load_auth_context(str(auth_file))
        assert ctx.username == "admin"
        assert ctx.password is None

    def test_load_headers_from_file(self, tmp_path: Path) -> None:
        from wavexis.auth import load_headers

        headers_file = tmp_path / "headers.json"
        headers_file.write_text('{"X-Custom": "value"}')

        headers = load_headers(str(headers_file))
        assert headers == {"X-Custom": "value"}

    def test_load_headers_file_not_found(self) -> None:
        from wavexis.auth import load_headers

        with pytest.raises(FileNotFoundError):
            load_headers("/nonexistent/path/headers.json")

    def test_load_auth_file_not_found(self) -> None:
        from wavexis.auth import load_auth_context

        with pytest.raises(FileNotFoundError):
            load_auth_context("/nonexistent/path/auth.json")


@pytest.mark.unit
class TestREPL:
    """Tests for repl.py."""

    def test_parse_command_simple(self) -> None:
        from wavexis.repl import parse_command

        cmd, args = parse_command("screenshot --url https://example.com")
        assert cmd == "screenshot"
        assert "--url" in args

    def test_parse_command_empty_raises(self) -> None:
        from wavexis.repl import parse_command

        with pytest.raises(ValueError, match="Empty command"):
            parse_command("")

    def test_parse_command_with_quotes(self) -> None:
        from wavexis.repl import parse_command

        cmd, args = parse_command('eval --expression "document.title"')
        assert cmd == "eval"
        assert len(args) == 2

    def test_help_text_contains_commands(self) -> None:
        from wavexis.repl import HELP_TEXT

        assert "screenshot" in HELP_TEXT
        assert "navigate" in HELP_TEXT
        assert "eval" in HELP_TEXT

    async def test_execute_repl_command_screenshot(self, tmp_path: Path) -> None:
        from wavexis.repl import execute_repl_command

        backend = MockBackend()
        backend.screenshot = AsyncMock(return_value=b"png-bytes")
        filename = str(tmp_path / "shot.png")
        result = await execute_repl_command(backend, "screenshot", [filename])
        assert "Screenshot saved" in result

    async def test_execute_repl_command_unknown(self) -> None:
        from wavexis.repl import execute_repl_command

        backend = MockBackend()
        with pytest.raises(ValueError, match="Unknown command"):
            await execute_repl_command(backend, "unknown_cmd", [])

    async def test_execute_repl_command_navigate(self) -> None:
        from wavexis.repl import execute_repl_command

        backend = MockBackend()
        backend.navigate = AsyncMock()
        result = await execute_repl_command(backend, "navigate", ["https://example.com"])
        assert "Navigated" in result

    async def test_execute_repl_command_exit(self) -> None:
        from wavexis.repl import execute_repl_command

        backend = MockBackend()
        result = await execute_repl_command(backend, "exit", [])
        assert result == "__EXIT__"

    async def test_execute_repl_command_quit(self) -> None:
        from wavexis.repl import execute_repl_command

        backend = MockBackend()
        result = await execute_repl_command(backend, "quit", [])
        assert result == "__EXIT__"

    async def test_execute_repl_command_eval(self) -> None:
        from wavexis.repl import execute_repl_command

        backend = MockBackend()
        backend.eval = AsyncMock(return_value="42")
        result = await execute_repl_command(backend, "eval", ["1+1"])
        assert "42" in result

    async def test_execute_repl_command_help(self) -> None:
        from wavexis.repl import HELP_TEXT, execute_repl_command

        backend = MockBackend()
        result = await execute_repl_command(backend, "help", [])
        assert result == HELP_TEXT

    async def test_execute_repl_command_click(self) -> None:
        from wavexis.repl import execute_repl_command

        backend = MockBackend()
        backend.click = AsyncMock()
        result = await execute_repl_command(backend, "click", ["#btn"])
        assert "Clicked" in result

    async def test_execute_repl_command_cookies(self) -> None:
        from wavexis.repl import execute_repl_command

        backend = MockBackend()
        backend.get_cookies = AsyncMock(return_value=[{"name": "session"}])
        result = await execute_repl_command(backend, "cookies", [])
        assert "session" in result

    async def test_execute_repl_command_url(self) -> None:
        from wavexis.repl import execute_repl_command

        backend = MockBackend()
        backend.eval = AsyncMock(return_value="https://example.com")
        result = await execute_repl_command(backend, "url", [])
        assert "example.com" in result

    async def test_execute_repl_command_title(self) -> None:
        from wavexis.repl import execute_repl_command

        backend = MockBackend()
        backend.eval = AsyncMock(return_value="My Page")
        result = await execute_repl_command(backend, "title", [])
        assert "My Page" in result

    async def test_execute_repl_command_back(self) -> None:
        from wavexis.repl import execute_repl_command

        backend = MockBackend()
        backend.go_back = AsyncMock()
        result = await execute_repl_command(backend, "back", [])
        assert "Back" in result

    async def test_execute_repl_command_reload(self) -> None:
        from wavexis.repl import execute_repl_command

        backend = MockBackend()
        backend.reload = AsyncMock()
        result = await execute_repl_command(backend, "reload", [])
        assert "Reload" in result

    async def test_execute_repl_command_wait(self) -> None:
        from wavexis.repl import execute_repl_command

        backend = MockBackend()
        backend.wait_for = AsyncMock()
        result = await execute_repl_command(backend, "wait", ["#element"])
        assert "Waited" in result

    async def test_repl_loop(self) -> None:
        from wavexis.repl import repl_loop

        backend = MockBackend()
        backend.navigate = AsyncMock()
        commands = iter(["navigate https://example.com", "help", "exit"])
        outputs: list[str] = []
        await repl_loop(backend, input_fn=lambda _: next(commands), output_fn=outputs.append)
        assert len(outputs) > 0


@pytest.mark.unit
class TestRecordAction:
    """Tests for actions/record.py to cover uncovered lines."""

    def test_events_to_yaml_click(self) -> None:
        from wavexis.actions.record import events_to_yaml

        events = [{"type": "click", "selector": "#btn"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        assert "navigate" in yaml_str
        assert "click" in yaml_str
        assert "#btn" in yaml_str

    def test_events_to_yaml_input(self) -> None:
        from wavexis.actions.record import events_to_yaml

        events = [{"type": "input", "selector": "#field", "value": "hello", "tag": "input"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        assert "type" in yaml_str
        assert "hello" in yaml_str

    def test_events_to_yaml_input_select(self) -> None:
        from wavexis.actions.record import events_to_yaml

        events = [{"type": "input", "selector": "#sel", "value": "opt", "tag": "select"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        assert "select" in yaml_str
        assert "opt" in yaml_str

    def test_events_to_yaml_keypress_enter(self) -> None:
        from wavexis.actions.record import events_to_yaml

        events = [{"type": "keypress", "selector": "#form", "key": "Enter"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        assert "click" in yaml_str

    def test_events_to_yaml_keypress_other(self) -> None:
        from wavexis.actions.record import events_to_yaml

        events = [{"type": "keypress", "selector": "#field", "key": "Tab"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        assert "Tab" in yaml_str

    def test_events_to_yaml_navigate(self) -> None:
        from wavexis.actions.record import events_to_yaml

        events = [{"type": "navigate", "url": "https://other.com"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        assert "https://other.com" in yaml_str

    def test_events_to_yaml_empty(self) -> None:
        from wavexis.actions.record import events_to_yaml

        yaml_str = events_to_yaml([], "https://example.com")
        assert "navigate" in yaml_str

    async def test_record_session(self) -> None:
        from wavexis.actions.record import record_session

        backend = MockBackend()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.eval = AsyncMock(return_value="[]")
        backend.close = AsyncMock()

        result = await record_session(backend, "https://example.com", duration=0)
        assert "navigate" in result

    async def test_record_session_collects_events_after_interrupt(self) -> None:
        """Regression: Ctrl+C must not discard recorded events."""
        from wavexis.actions.record import record_session

        backend = MockBackend()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.close = AsyncMock()

        # Simulate KeyboardInterrupt during sleep, then return events.
        recorded = json.dumps(
            [{"type": "click", "selector": "#btn", "x": 1, "y": 2}]
        )

        async def fake_eval(expr: str, await_promise: bool = False) -> Any:
            if "__wavexis_record_events" in expr:
                return recorded
            return ""

        backend.eval = AsyncMock(side_effect=fake_eval)

        with patch("wavexis.actions.record.asyncio.sleep", side_effect=KeyboardInterrupt):
            result = await record_session(backend, "https://example.com", duration=60)

        # The click event must be present even though sleep was interrupted.
        assert "#btn" in result
        assert "click" in result
