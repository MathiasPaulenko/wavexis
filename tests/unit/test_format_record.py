"""Unit tests for --format output and record events_to_yaml."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest
import yaml

from browsix.actions.record import events_to_yaml
from browsix.output import Output


@pytest.mark.unit
class TestOutputWriteFormatted:
    """Tests for Output.write_formatted."""

    def test_json_format_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test JSON format outputs to stdout."""
        data = {"key": "value", "num": 42}
        Output.write_formatted(data, "json")
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result == data

    def test_yaml_format_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test YAML format outputs to stdout."""
        data = {"key": "value", "num": 42}
        Output.write_formatted(data, "yaml")
        captured = capsys.readouterr()
        result = yaml.safe_load(captured.out)
        assert result == data

    def test_csv_format_with_list(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test CSV format with list of dicts."""
        data = [{"name": "a", "value": 1}, {"name": "b", "value": 2}]
        Output.write_formatted(data, "csv")
        captured = capsys.readouterr()
        reader = csv.DictReader(io.StringIO(captured.out))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["name"] == "a"

    def test_csv_format_with_scalar(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test CSV format wraps scalar into value column."""
        Output.write_formatted("hello", "csv")
        captured = capsys.readouterr()
        reader = csv.DictReader(io.StringIO(captured.out))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["value"] == "hello"

    def test_csv_format_with_dict(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test CSV format with single dict wraps into list."""
        data = {"name": "test", "value": 99}
        Output.write_formatted(data, "csv")
        captured = capsys.readouterr()
        reader = csv.DictReader(io.StringIO(captured.out))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["name"] == "test"

    def test_json_format_to_file(self, tmp_path: Path) -> None:
        """Test JSON format writes to file."""
        data = {"key": "value"}
        filepath = str(tmp_path / "out.json")
        Output.write_formatted(data, "json", filepath)
        result = json.loads(Path(filepath).read_text())
        assert result == data

    def test_yaml_format_to_file(self, tmp_path: Path) -> None:
        """Test YAML format writes to file."""
        data = {"key": "value"}
        filepath = str(tmp_path / "out.yaml")
        Output.write_formatted(data, "yaml", filepath)
        result = yaml.safe_load(Path(filepath).read_text())
        assert result == data

    def test_unsupported_format_raises(self) -> None:
        """Test unsupported format raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported format"):
            Output.write_formatted({}, "xml")


@pytest.mark.unit
class TestEventsToYaml:
    """Tests for events_to_yaml."""

    def test_empty_events(self) -> None:
        """Test empty events produces just navigate action."""
        yaml_str = events_to_yaml([], "https://example.com")
        config = yaml.safe_load(yaml_str)
        assert config["actions"] == [{"navigate": {"url": "https://example.com"}}]

    def test_click_event(self) -> None:
        """Test click event converts to click action."""
        events = [{"type": "click", "selector": "#button", "x": 10, "y": 20}]
        yaml_str = events_to_yaml(events, "https://example.com")
        config = yaml.safe_load(yaml_str)
        assert config["actions"][1] == {"click": {"selector": "#button"}}

    def test_input_event(self) -> None:
        """Test input event converts to type action."""
        events = [{"type": "input", "selector": "#search", "value": "hello", "tag": "input"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        config = yaml.safe_load(yaml_str)
        assert config["actions"][1] == {"type": {"selector": "#search", "text": "hello"}}

    def test_keypress_enter(self) -> None:
        """Test Enter keypress converts to click action."""
        events = [{"type": "keypress", "selector": "#submit", "key": "Enter"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        config = yaml.safe_load(yaml_str)
        assert config["actions"][1] == {"click": {"selector": "#submit"}}

    def test_keypress_other(self) -> None:
        """Test non-Enter keypress converts to keypress action."""
        events = [{"type": "keypress", "selector": "#field", "key": "Tab"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        config = yaml.safe_load(yaml_str)
        assert config["actions"][1] == {"keypress": {"key": "Tab"}}

    def test_navigate_event(self) -> None:
        """Test navigate event converts to navigate action."""
        events = [{"type": "navigate", "url": "https://example.com/page2"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        config = yaml.safe_load(yaml_str)
        assert config["actions"][1] == {"navigate": {"url": "https://example.com/page2"}}

    def test_mixed_events(self) -> None:
        """Test mixed events produce correct action sequence."""
        events = [
            {"type": "click", "selector": "#login", "x": 5, "y": 5},
            {"type": "input", "selector": "#user", "value": "admin", "tag": "input"},
            {"type": "input", "selector": "#pass", "value": "secret", "tag": "input"},
            {"type": "keypress", "selector": "#submit", "key": "Enter"},
        ]
        yaml_str = events_to_yaml(events, "https://example.com")
        config = yaml.safe_load(yaml_str)
        actions = config["actions"]
        assert len(actions) == 5
        assert actions[0] == {"navigate": {"url": "https://example.com"}}
        assert actions[1] == {"click": {"selector": "#login"}}
        assert actions[2] == {"type": {"selector": "#user", "text": "admin"}}
        assert actions[3] == {"type": {"selector": "#pass", "text": "secret"}}
        assert actions[4] == {"click": {"selector": "#submit"}}
