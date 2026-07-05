"""Unit tests for browsix.multi YAML parser and executor."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from browsix.exceptions import MultiConfigError
from browsix.multi import execute_actions, parse_yaml


@pytest.mark.unit
class TestParseYaml:
    def test_valid_config(self, tmp_path: Path) -> None:
        config = tmp_path / "config.yml"
        config.write_text(
            """
actions:
  - screenshot:
      url: https://example.com
      full_page: true
  - pdf:
      url: https://example.com
      paper: a4
""",
            encoding="utf-8",
        )
        actions = parse_yaml(config)
        assert len(actions) == 2
        assert "screenshot" in actions[0]
        assert actions[0]["screenshot"]["url"] == "https://example.com"
        assert "pdf" in actions[1]

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(MultiConfigError, match="file"):
            parse_yaml(tmp_path / "nonexistent.yml")

    def test_non_dict_root(self, tmp_path: Path) -> None:
        config = tmp_path / "bad.yml"
        config.write_text("- just\n- a\n- list\n", encoding="utf-8")
        with pytest.raises(MultiConfigError, match="root"):
            parse_yaml(config)

    def test_missing_actions_key(self, tmp_path: Path) -> None:
        config = tmp_path / "bad.yml"
        config.write_text("foo: bar\n", encoding="utf-8")
        with pytest.raises(MultiConfigError, match="actions"):
            parse_yaml(config)

    def test_actions_not_list(self, tmp_path: Path) -> None:
        config = tmp_path / "bad.yml"
        config.write_text("actions: notalist\n", encoding="utf-8")
        with pytest.raises(MultiConfigError, match="actions"):
            parse_yaml(config)

    def test_action_not_single_key(self, tmp_path: Path) -> None:
        config = tmp_path / "bad.yml"
        config.write_text(
            "actions:\n  - screenshot: {}\n    pdf: {}\n",
            encoding="utf-8",
        )
        with pytest.raises(MultiConfigError, match="actions"):
            parse_yaml(config)

    def test_action_params_not_dict(self, tmp_path: Path) -> None:
        config = tmp_path / "bad.yml"
        config.write_text(
            "actions:\n  - screenshot: notadict\n",
            encoding="utf-8",
        )
        with pytest.raises(MultiConfigError, match="screenshot"):
            parse_yaml(config)

    def test_empty_actions(self, tmp_path: Path) -> None:
        config = tmp_path / "empty.yml"
        config.write_text("actions: []\n", encoding="utf-8")
        actions = parse_yaml(config)
        assert actions == []


@pytest.mark.unit
class TestExecuteActions:
    async def test_execute_screenshot(self) -> None:
        backend = MagicMock()
        backend.navigate = AsyncMock()
        backend.screenshot = AsyncMock(return_value=b"png")
        actions = [{"screenshot": {"url": "https://example.com", "full_page": True}}]
        results = await execute_actions(actions, backend)
        assert len(results) == 1
        assert results[0] == b"png"

    async def test_execute_multiple(self) -> None:
        backend = MagicMock()
        backend.navigate = AsyncMock()
        backend.screenshot = AsyncMock(return_value=b"png")
        backend.eval = AsyncMock(return_value="title")
        actions = [
            {"screenshot": {"url": "https://example.com"}},
            {"eval": {"url": "https://example.com", "expression": "document.title"}},
        ]
        results = await execute_actions(actions, backend)
        assert len(results) == 2
        assert results[0] == b"png"
        assert results[1] == "title"

    async def test_execute_empty(self) -> None:
        backend = MagicMock()
        results = await execute_actions([], backend)
        assert results == []

    async def test_execute_unknown_action(self) -> None:
        backend = MagicMock()
        actions = [{"unknown_action": {"url": "https://example.com"}}]
        with pytest.raises(MultiConfigError, match="unknown_action"):
            await execute_actions(actions, backend)
