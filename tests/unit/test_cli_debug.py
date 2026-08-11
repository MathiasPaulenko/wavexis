"""Unit tests for wavexis.cli._debug commands."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from wavexis.cli.app import app

runner = CliRunner()


def _make_backend() -> AsyncMock:
    """Return a mock backend for debug CLI tests."""
    backend = AsyncMock()
    backend.launch = AsyncMock()
    backend.close = AsyncMock()
    backend.navigate = AsyncMock()
    backend.dom_get_document = AsyncMock(return_value={"nodeId": 1})
    backend.runtime_evaluate = AsyncMock(return_value={"result": 1})
    backend.target_get_targets = AsyncMock(return_value=[])
    return backend


@pytest.fixture
def backend() -> AsyncMock:
    """Provide a mock backend."""
    return _make_backend()


def _run_with_action(args: list[str], module_path: str, result: Any, backend: AsyncMock) -> Any:
    """Invoke a debug command with the given Action class patched."""
    with patch(module_path) as mock_action:
        mock_action.return_value.execute = AsyncMock(return_value=result)
        with patch("wavexis.cli._debug._get_backend", return_value=backend):
            return runner.invoke(app, args)


@pytest.mark.unit
class TestDebugCSSCommands:
    """Tests for debug css subcommands."""

    def test_css_styles(self, backend: AsyncMock) -> None:
        result = _run_with_action(
            ["css", "styles", "https://example.com", "-s", "body"],
            "wavexis.actions.css.CSSAction",
            {"inlineStyles": []},
            backend,
        )
        assert result.exit_code == 0

    def test_css_stylesheets(self, backend: AsyncMock) -> None:
        result = _run_with_action(
            ["css", "stylesheets", "https://example.com"],
            "wavexis.actions.css.CSSAction",
            [],
            backend,
        )
        assert result.exit_code == 0

    def test_css_computed(self, backend: AsyncMock) -> None:
        result = _run_with_action(
            ["css", "computed", "https://example.com", "-s", "body"],
            "wavexis.actions.css.CSSAction",
            {"color": "black"},
            backend,
        )
        assert result.exit_code == 0


@pytest.mark.unit
class TestDebugDebuggerCommands:
    """Tests for debug debug subcommands."""

    def test_debug_pause(self, backend: AsyncMock) -> None:
        result = _run_with_action(
            ["debug", "pause", "https://example.com"],
            "wavexis.actions.debug.DebugAction",
            None,
            backend,
        )
        assert result.exit_code == 0
        assert "Paused" in result.output

    def test_debug_resume(self, backend: AsyncMock) -> None:
        result = _run_with_action(
            ["debug", "resume", "https://example.com"],
            "wavexis.actions.debug.DebugAction",
            None,
            backend,
        )
        assert result.exit_code == 0
        assert "Resumed" in result.output

    def test_debug_listeners(self, backend: AsyncMock) -> None:
        result = _run_with_action(
            ["debug", "listeners", "https://example.com", "-s", "body"],
            "wavexis.actions.debug.DebugAction",
            [],
            backend,
        )
        assert result.exit_code == 0


@pytest.mark.unit
class TestDebugOverlayCommands:
    """Tests for debug overlay subcommands."""

    def test_overlay_highlight(self, backend: AsyncMock) -> None:
        result = _run_with_action(
            ["overlay", "highlight", "https://example.com", "-s", "body"],
            "wavexis.actions.overlay.OverlayAction",
            None,
            backend,
        )
        assert result.exit_code == 0

    def test_overlay_clear(self, backend: AsyncMock) -> None:
        result = _run_with_action(
            ["overlay", "clear", "https://example.com"],
            "wavexis.actions.overlay.OverlayAction",
            None,
            backend,
        )
        assert result.exit_code == 0


@pytest.mark.unit
class TestDebugDirectCommands:
    """Tests for debug commands that call backend methods directly."""

    def test_dom_document(self, backend: AsyncMock) -> None:
        with patch("wavexis.cli._debug._get_backend", return_value=backend):
            result = runner.invoke(app, ["dom", "document", "https://example.com"])
        assert result.exit_code == 0
        assert backend.dom_get_document.await_count == 2

    def test_runtime_evaluate(self, backend: AsyncMock) -> None:
        with patch("wavexis.cli._debug._get_backend", return_value=backend):
            result = runner.invoke(app, ["runtime", "evaluate", "https://example.com", "1+1"])
        assert result.exit_code == 0
        backend.runtime_evaluate.assert_awaited_once_with("1+1", False, False)

    def test_target_list(self, backend: AsyncMock) -> None:
        with patch("wavexis.cli._debug._get_backend", return_value=backend):
            result = runner.invoke(app, ["target", "list"])
        assert result.exit_code == 0
        backend.target_get_targets.assert_awaited_once()

    def test_css_direct_passes_wait_strategy(self, backend: AsyncMock) -> None:
        """Regression: _css_direct must pass _wait_strategy() to navigate."""
        with patch("wavexis.cli._debug._get_backend", return_value=backend):
            result = runner.invoke(
                app, ["css", "enable", "https://example.com"]
            )
        assert result.exit_code == 0
        backend.navigate.assert_awaited_once()
        call_args = backend.navigate.call_args
        assert len(call_args.args) >= 2 or "wait" in call_args.kwargs
        wait_arg = call_args.args[1] if len(call_args.args) >= 2 else call_args.kwargs.get("wait")
        assert wait_arg is not None

    def test_debug_direct_passes_wait_strategy(self, backend: AsyncMock) -> None:
        """Regression: _debug_direct must pass _wait_strategy() to navigate."""
        with patch("wavexis.cli._debug._get_backend", return_value=backend):
            result = runner.invoke(
                app, ["runtime", "evaluate", "https://example.com", "1+1"]
            )
        assert result.exit_code == 0
        backend.navigate.assert_awaited_once()
        call_args = backend.navigate.call_args
        assert len(call_args.args) >= 2 or "wait" in call_args.kwargs
        wait_arg = call_args.args[1] if len(call_args.args) >= 2 else call_args.kwargs.get("wait")
        assert wait_arg is not None

    def test_dom_direct_passes_wait_strategy(self, backend: AsyncMock) -> None:
        """Regression: _dom_node_direct must pass _wait_strategy() to navigate."""
        with patch("wavexis.cli._debug._get_backend", return_value=backend):
            result = runner.invoke(
                app, ["dom", "document", "https://example.com"]
            )
        assert result.exit_code == 0
        backend.navigate.assert_awaited_once()
        call_args = backend.navigate.call_args
        assert len(call_args.args) >= 2 or "wait" in call_args.kwargs
        wait_arg = call_args.args[1] if len(call_args.args) >= 2 else call_args.kwargs.get("wait")
        assert wait_arg is not None
