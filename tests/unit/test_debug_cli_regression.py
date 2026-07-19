"""Regression tests for bugs found in _debug.py and _experimental.py CLI modules.

Bugs fixed:
1. smartcard command in _experimental.py hardcoded "-" as output instead of using
   the --output flag value.
2. Dozens of unguarded json.loads() calls in _debug.py that would crash with
   an unhandled JSONDecodeError traceback on invalid user input.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from wavexis.cli.app import app

runner = CliRunner()


def _make_mock_backend() -> AsyncMock:
    """Create a mock backend suitable for debug/experimental commands."""
    backend = AsyncMock()
    backend.launch = AsyncMock()
    backend.close = AsyncMock()
    backend.navigate = AsyncMock()
    backend.raw = AsyncMock(return_value={"result": {}})
    return backend


@pytest.mark.unit
class TestSmartcardOutputFlag:
    """Regression: smartcard command ignored --output flag and always wrote to stdout."""

    def test_smartcard_output_to_file(self, tmp_path: Path) -> None:
        """--output flag should write result to the specified file, not stdout."""
        backend = _make_mock_backend()
        # SmartCardEmulationAction.execute returns a dict result
        with patch(
            "wavexis.cli._experimental.SmartCardEmulationAction"
        ) as mock_action_cls:
            mock_action = mock_action_cls.return_value
            mock_action.execute = AsyncMock(
                return_value={"status": "ok", "data": "test"}
            )
            with patch(
                "wavexis.cli._experimental._get_backend", return_value=backend
            ):
                out = str(tmp_path / "smartcard_out.json")
                result = runner.invoke(
                    app,
                    [
                        "smartcard",
                        "enable",
                        "https://example.com",
                        "-o",
                        out,
                    ],
                )
        assert result.exit_code == 0
        assert Path(out).exists()
        saved = json.loads(Path(out).read_text(encoding="utf-8"))
        assert saved["status"] == "ok"


@pytest.mark.unit
class TestDebugJsonLoadsSafety:
    """Regression: unguarded json.loads in _debug.py crashed with tracebacks."""

    def test_css_force_starting_style_invalid_json(self) -> None:
        """Invalid JSON for starting_style_id should exit with code 2, not crash."""
        backend = _make_mock_backend()
        with patch("wavexis.cli._debug._get_backend", return_value=backend):
            result = runner.invoke(
                app,
                [
                    "css",
                    "force-starting-style",
                    "https://example.com",
                    "1",
                    "not-valid-json",
                ],
            )
        assert result.exit_code == 2
        assert "invalid" in result.output.lower()

    def test_debug_blackbox_contexts_invalid_json(self) -> None:
        """Invalid JSON for unique_ids should exit with code 2, not crash."""
        backend = _make_mock_backend()
        with patch("wavexis.cli._debug._get_backend", return_value=backend):
            result = runner.invoke(
                app,
                [
                    "debug",
                    "blackbox-contexts",
                    "https://example.com",
                    "not-valid-json",
                ],
            )
        assert result.exit_code == 2
        assert "invalid" in result.output.lower()

    def test_overlay_highlight_quad_invalid_json(self) -> None:
        """Invalid JSON for quad should exit with code 2, not crash."""
        backend = _make_mock_backend()
        with patch("wavexis.cli._debug._get_backend", return_value=backend):
            result = runner.invoke(
                app,
                [
                    "overlay",
                    "highlight-quad",
                    "https://example.com",
                    "--quad",
                    "not-valid-json",
                ],
            )
        assert result.exit_code == 2
        assert "invalid" in result.output.lower()

    def test_dom_highlight_node_invalid_json(self) -> None:
        """Invalid JSON for highlight_config should exit with code 2, not crash."""
        backend = _make_mock_backend()
        with patch("wavexis.cli._debug._get_backend", return_value=backend):
            result = runner.invoke(
                app,
                [
                    "dom",
                    "highlight-node",
                    "https://example.com",
                    "1",
                    "not-valid-json",
                ],
            )
        assert result.exit_code == 2
        assert "invalid" in result.output.lower()

    def test_emulation_add_screen_invalid_json(self) -> None:
        """Invalid JSON for screen_json should exit with code 2, not crash."""
        backend = _make_mock_backend()
        with patch("wavexis.cli._debug._get_backend", return_value=backend):
            result = runner.invoke(
                app,
                [
                    "emulation",
                    "add-screen",
                    "https://example.com",
                    "not-valid-json",
                ],
            )
        assert result.exit_code == 2
        assert "invalid" in result.output.lower()

    def test_dom_storage_clear_invalid_json(self) -> None:
        """Invalid JSON for storage_id should exit with code 2, not crash."""
        backend = _make_mock_backend()
        with patch("wavexis.cli._debug._get_backend", return_value=backend):
            result = runner.invoke(
                app,
                [
                    "dom-storage",
                    "clear",
                    "https://example.com",
                    "not-valid-json",
                ],
            )
        assert result.exit_code == 2
        assert "invalid" in result.output.lower()

    def test_network_set_cookies_invalid_json(self) -> None:
        """Invalid JSON for cookies should exit with code 2, not crash."""
        backend = _make_mock_backend()
        with patch("wavexis.cli._debug._get_backend", return_value=backend):
            result = runner.invoke(
                app,
                [
                    "network-domain",
                    "set-cookies",
                    "https://example.com",
                    "--cookies",
                    "not-valid-json",
                ],
            )
        assert result.exit_code == 2
        assert "invalid" in result.output.lower()

    def test_input_dispatch_touch_event_invalid_json(self) -> None:
        """Invalid JSON for touch_points should exit with code 2, not crash."""
        backend = _make_mock_backend()
        with patch("wavexis.cli._debug._get_backend", return_value=backend):
            result = runner.invoke(
                app,
                [
                    "input-domain",
                    "dispatch-touch-event",
                    "https://example.com",
                    "--type",
                    "touchStart",
                    "--touch-points",
                    "not-valid-json",
                ],
            )
        assert result.exit_code == 2
        assert "invalid" in result.output.lower()
