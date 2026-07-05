"""Integration tests for multi command."""

from __future__ import annotations

from pathlib import Path

import pytest

from browsix.backend.cdp import CDPBackend
from browsix.config import BrowserOptions
from browsix.exceptions import MultiConfigError
from browsix.multi import execute_actions, parse_yaml


@pytest.mark.integration
class TestMultiIntegration:
    def test_parse_valid_config(self, tmp_path: Path) -> None:
        config = tmp_path / "shots.yml"
        config.write_text(
            """
actions:
  - screenshot:
      url: https://example.com
      full_page: true
  - eval:
      url: https://example.com
      expression: document.title
""",
            encoding="utf-8",
        )
        actions = parse_yaml(config)
        assert len(actions) == 2
        assert "screenshot" in actions[0]
        assert "eval" in actions[1]

    def test_parse_invalid_config(self, tmp_path: Path) -> None:
        config = tmp_path / "bad.yml"
        config.write_text("not_a_mapping\n", encoding="utf-8")
        with pytest.raises(MultiConfigError):
            parse_yaml(config)

    async def test_execute_screenshot_and_eval(self) -> None:
        backend = CDPBackend()
        await backend.launch(BrowserOptions())
        try:
            actions = [
                {"screenshot": {"url": "https://example.com", "full_page": True}},
                {"eval": {"url": "https://example.com", "expression": "document.title"}},
            ]
            results = await execute_actions(actions, backend)
            assert len(results) == 2
            assert isinstance(results[0], bytes)
            assert isinstance(results[1], str)
        finally:
            await backend.close()
