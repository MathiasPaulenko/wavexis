"""Unit tests for multi-action improvements: wait, emulation, variables, parallel."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wavexis.multi import (
    _substitute_variables,
    execute_actions,
    parse_yaml,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    """Create a temporary YAML config file."""
    config = tmp_path / "config.yml"
    config.write_text(
        """
actions:
  - screenshot:
      url: https://example.com
      full_page: true
""",
        encoding="utf-8",
    )
    return config


class TestSubstituteVariables:
    """Tests for _substitute_variables."""

    def test_simple_var(self) -> None:
        result = _substitute_variables("{{url}}", {"url": "https://example.com"})
        assert result == "https://example.com"

    def test_var_in_string(self) -> None:
        result = _substitute_variables("Navigate to {{url}} now", {"url": "https://example.com"})
        assert result == "Navigate to https://example.com now"

    def test_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("API_KEY", "secret123")
        result = _substitute_variables("{{env.API_KEY}}", {})
        assert result == "secret123"

    def test_env_var_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NONEXISTENT_KEY", raising=False)
        result = _substitute_variables("{{env.NONEXISTENT_KEY}}", {})
        assert result == "{{env.NONEXISTENT_KEY}}"

    def test_multiple_vars(self) -> None:
        result = _substitute_variables(
            "{{url}} and {{selector}}",
            {"url": "https://example.com", "selector": "#btn"},
        )
        assert result == "https://example.com and #btn"

    def test_var_in_dict(self) -> None:
        result = _substitute_variables(
            {"url": "{{url}}", "selector": "#btn"},
            {"url": "https://example.com"},
        )
        assert result == {"url": "https://example.com", "selector": "#btn"}

    def test_var_in_list(self) -> None:
        result = _substitute_variables(["{{url}}", "static"], {"url": "https://example.com"})
        assert result == ["https://example.com", "static"]

    def test_no_vars(self) -> None:
        result = _substitute_variables("plain text", {})
        assert result == "plain text"

    def test_unknown_var(self) -> None:
        result = _substitute_variables("{{unknown}}", {})
        assert result == "{{unknown}}"

    def test_non_string_passthrough(self) -> None:
        assert _substitute_variables(42, {}) == 42
        assert _substitute_variables(True, {}) is True
        assert _substitute_variables(None, {}) is None


class TestParseYamlVariables:
    """Tests for variable substitution in parse_yaml."""

    def test_vars_section(self, tmp_path: Path) -> None:
        config = tmp_path / "config.yml"
        config.write_text(
            """
vars:
  target_url: https://example.com
  selector: "#main"

actions:
  - screenshot:
      url: "{{target_url}}"
      full_page: true
  - eval:
      url: "{{target_url}}"
      expression: "document.querySelector('{{selector}}').textContent"
""",
            encoding="utf-8",
        )
        actions = parse_yaml(config)
        assert actions[0]["screenshot"]["url"] == "https://example.com"
        assert actions[1]["eval"]["url"] == "https://example.com"
        assert actions[1]["eval"]["expression"] == ("document.querySelector('#main').textContent")

    def test_env_var_substitution(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TARGET_URL", "https://env.example.com")
        config = tmp_path / "config.yml"
        config.write_text(
            """
actions:
  - screenshot:
      url: "{{env.TARGET_URL}}"
""",
            encoding="utf-8",
        )
        actions = parse_yaml(config)
        assert actions[0]["screenshot"]["url"] == "https://env.example.com"

    def test_no_vars_section(self, tmp_path: Path) -> None:
        config = tmp_path / "config.yml"
        config.write_text(
            """
actions:
  - screenshot:
      url: https://example.com
""",
            encoding="utf-8",
        )
        actions = parse_yaml(config)
        assert actions[0]["screenshot"]["url"] == "https://example.com"

    def test_invalid_vars(self, tmp_path: Path) -> None:
        from wavexis.exceptions import MultiConfigError

        config = tmp_path / "config.yml"
        config.write_text(
            """
vars: "not a dict"
actions:
  - screenshot:
      url: https://example.com
""",
            encoding="utf-8",
        )
        with pytest.raises(MultiConfigError, match="vars"):
            parse_yaml(config)


class TestWaitDispatch:
    """Tests for wait action dispatch in multi."""

    async def test_wait_action_dispatched(self) -> None:
        backend = MagicMock()
        backend.wait_for = AsyncMock(return_value=None)
        actions = [{"wait": {"strategy": "selector", "selector": "#loaded", "timeout": 5000}}]
        await execute_actions(actions, backend)
        backend.wait_for.assert_called_once()
        ws_arg = backend.wait_for.call_args[0][0]
        assert ws_arg.strategy == "selector"
        assert ws_arg.selector == "#loaded"
        assert ws_arg.timeout == 5000

    async def test_wait_default_strategy(self) -> None:
        backend = MagicMock()
        backend.wait_for = AsyncMock(return_value=None)
        actions = [{"wait": {}}]
        await execute_actions(actions, backend)
        ws_arg = backend.wait_for.call_args[0][0]
        assert ws_arg.strategy == "load"
        assert ws_arg.timeout == 30000


class TestEmulationDispatch:
    """Tests for emulation action dispatch in multi."""

    async def test_emulation_device(self) -> None:
        backend = MagicMock()
        backend.emulate_device = AsyncMock(return_value=None)
        actions = [{"emulation": {"action": "device", "device": "iphone-15"}}]
        await execute_actions(actions, backend)
        backend.emulate_device.assert_called_once_with("iphone-15")

    async def test_emulation_viewport(self) -> None:
        backend = MagicMock()
        backend.set_viewport = AsyncMock(return_value=None)
        actions = [{"emulation": {"action": "viewport", "width": 1920, "height": 1080}}]
        await execute_actions(actions, backend)
        backend.set_viewport.assert_called_once_with(1920, 1080, 1.0)

    async def test_emulation_timezone(self) -> None:
        backend = MagicMock()
        backend.set_timezone = AsyncMock(return_value=None)
        actions = [{"emulation": {"action": "timezone", "timezone": "America/New_York"}}]
        await execute_actions(actions, backend)
        backend.set_timezone.assert_called_once_with("America/New_York")

    async def test_emulation_dark_mode(self) -> None:
        backend = MagicMock()
        backend.set_dark_mode = AsyncMock(return_value=None)
        actions = [{"emulation": {"action": "dark_mode", "dark_mode": True}}]
        await execute_actions(actions, backend)
        backend.set_dark_mode.assert_called_once_with(True)


class TestParallelExecution:
    """Tests for --parallel flag in execute_actions."""

    async def test_parallel_executes_all(self) -> None:
        backend = MagicMock()
        tab_mock = AsyncMock()
        tab_mock.close = AsyncMock()
        backend.new_tab_handle = AsyncMock(return_value=tab_mock)

        async def fake_dispatch(
            action_type: str, params: dict, backend: Any, cache: Any = None
        ) -> Any:
            if action_type == "navigate":
                return "nav-result"
            return b"screenshot-data"

        with patch("wavexis.multi._dispatch", side_effect=fake_dispatch):
            actions = [
                {"navigate": {"url": "https://example.com"}},
                {"screenshot": {"url": "https://example.com"}},
            ]
            results = await execute_actions(actions, backend, parallel=True)
            assert len(results) == 2

    async def test_sequential_default(self) -> None:
        backend = MagicMock()
        call_order: list[str] = []

        async def fake_dispatch(
            action_type: str, params: dict, backend: Any, cache: Any = None
        ) -> Any:
            call_order.append(action_type)
            return "result"

        with patch("wavexis.multi._dispatch", side_effect=fake_dispatch):
            actions = [
                {"navigate": {"url": "https://a.com"}},
                {"screenshot": {"url": "https://b.com"}},
            ]
            results = await execute_actions(actions, backend)
            assert len(results) == 2
            assert call_order == ["navigate", "screenshot"]
