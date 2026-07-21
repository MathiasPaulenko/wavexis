"""Unit tests for record/replay system."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from wavexis.actions.record import events_to_yaml
from wavexis.backend.base import AbstractBackend
from wavexis.exceptions import WavexisError
from wavexis.record import Recorder, record_to_yaml, replay_from_yaml


@pytest.mark.unit
class TestRecorder:
    """Test suite for recorder."""

    def test_init(self) -> None:
        """Test init."""
        backend = MagicMock(spec=AbstractBackend)
        recorder = Recorder(backend)
        assert recorder.actions == []

    def test_record_manual(self) -> None:
        """Test record manual."""
        backend = MagicMock(spec=AbstractBackend)
        recorder = Recorder(backend)
        recorder.record("screenshot", {"url": "https://example.com"})
        assert len(recorder.actions) == 1
        assert recorder.actions[0] == {"screenshot": {"url": "https://example.com"}}

    def test_record_multiple(self) -> None:
        """Test record multiple."""
        backend = MagicMock(spec=AbstractBackend)
        recorder = Recorder(backend)
        recorder.record("screenshot", {"url": "https://example.com"})
        recorder.record("eval", {"expression": "document.title"})
        assert len(recorder.actions) == 2
        assert "screenshot" in recorder.actions[0]
        assert "eval" in recorder.actions[1]

    def test_getattr_skips_lifecycle_methods(self) -> None:
        """Lifecycle methods (launch, close) should not be recorded."""
        backend = MagicMock(spec=AbstractBackend)
        recorder = Recorder(backend)
        # Accessing launch should return the original attribute without recording
        _ = recorder.launch
        assert recorder.actions == []
        _ = recorder.close
        assert recorder.actions == []

    def test_getattr_skips_internal_methods(self) -> None:
        """Internal methods (_get_origin, _get_session, _send) should not be recorded."""
        backend = MagicMock()
        recorder = Recorder(backend)
        _ = recorder._get_origin
        _ = recorder._get_session
        _ = recorder._send
        assert recorder.actions == []

    def test_getattr_records_callable_methods(self) -> None:
        """Callable methods should be wrapped to record calls."""
        backend = MagicMock(spec=AbstractBackend)
        backend.screenshot = MagicMock(return_value=b"png")
        recorder = Recorder(backend)
        result = recorder.screenshot(url="https://example.com")
        assert result == b"png"
        assert len(recorder.actions) == 1
        assert "screenshot" in recorder.actions[0]
        assert recorder.actions[0]["screenshot"]["url"] == "https://example.com"

    def test_getattr_records_args(self) -> None:
        """Positional args should be recorded in _args list, kwargs as keys."""
        backend = MagicMock(spec=AbstractBackend)
        backend.eval = MagicMock(return_value="title")
        recorder = Recorder(backend)
        result = recorder.eval("document.title", await_promise=False)
        assert result == "title"
        assert len(recorder.actions) == 1
        assert "eval" in recorder.actions[0]
        assert recorder.actions[0]["eval"]["_args"] == ["document.title"]
        assert recorder.actions[0]["eval"]["await_promise"] is False

    def test_getattr_returns_non_callable_attributes(self) -> None:
        """Non-callable attributes should be returned directly without recording."""
        backend = MagicMock(spec=AbstractBackend)
        backend.some_property = "value"
        recorder = Recorder(backend)
        result = recorder.some_property
        assert result == "value"
        assert recorder.actions == []


@pytest.mark.unit
class TestRecordToYaml:
    """Test suite for recordtoyaml."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Test save and load."""
        actions = [
            {"screenshot": {"url": "https://example.com", "output": "out.png"}},
            {"eval": {"url": "https://example.com", "expression": "1+1"}},
        ]
        path = tmp_path / "session.yml"
        record_to_yaml(actions, path)
        assert path.exists()
        data = yaml.safe_load(path.read_text())
        assert "actions" in data
        assert len(data["actions"]) == 2
        assert "screenshot" in data["actions"][0]

    def test_empty_actions(self, tmp_path: Path) -> None:
        """Test empty actions."""
        path = tmp_path / "empty.yml"
        record_to_yaml([], path)
        data = yaml.safe_load(path.read_text())
        assert data["actions"] == []

    def test_write_error(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test that record_to_yaml raises WavexisError on write failure."""
        from pathlib import Path

        def _raise(*args: Any, **kwargs: Any) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(Path, "write_text", _raise)

        path = tmp_path / "session.yml"
        with pytest.raises(WavexisError, match="Failed to write recorded config"):
            record_to_yaml([{"navigate": {"url": "https://example.com"}}], path)


@pytest.mark.unit
class TestReplayFromYaml:
    """Test suite for replayfromyaml."""

    async def test_replay_valid(self, tmp_path: Path) -> None:
        """Test replay valid."""
        actions = [
            {"screenshot": {"url": "https://example.com", "output": "out.png"}},
        ]
        path = tmp_path / "session.yml"
        record_to_yaml(actions, path)

        backend = MagicMock(spec=AbstractBackend)
        backend.screenshot = AsyncMock(return_value=b"png_data")

        results = await replay_from_yaml(path, backend)
        assert len(results) == 1

    async def test_replay_empty(self, tmp_path: Path) -> None:
        """Test replay empty."""
        path = tmp_path / "empty.yml"
        record_to_yaml([], path)

        backend = MagicMock(spec=AbstractBackend)
        results = await replay_from_yaml(path, backend)
        assert results == []


@pytest.mark.unit
class TestEventsToYaml:
    """Test suite for events_to_yaml conversion."""

    def test_click_event(self) -> None:
        """Test click event conversion."""
        events = [{"type": "click", "selector": "#button"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        data = yaml.safe_load(yaml_str)
        assert data["actions"][0] == {"navigate": {"url": "https://example.com"}}
        assert data["actions"][1] == {"click": {"selector": "#button"}}

    def test_input_event_input_tag(self) -> None:
        """Test input event with input tag converts to type action."""
        events = [{"type": "input", "selector": "#field", "value": "hello", "tag": "input"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        data = yaml.safe_load(yaml_str)
        assert data["actions"][1] == {"type": {"selector": "#field", "text": "hello"}}

    def test_input_event_select_tag(self) -> None:
        """Test input event with select tag converts to select action."""
        events = [{"type": "input", "selector": "#sel", "value": "opt1", "tag": "select"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        data = yaml.safe_load(yaml_str)
        assert data["actions"][1] == {"select": {"selector": "#sel", "value": "opt1"}}

    def test_keypress_enter_with_selector(self) -> None:
        """Test Enter keypress with selector converts to click."""
        events = [{"type": "keypress", "selector": "#submit", "key": "Enter"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        data = yaml.safe_load(yaml_str)
        assert data["actions"][1] == {"click": {"selector": "#submit"}}

    def test_keypress_non_enter(self) -> None:
        """Test non-Enter keypress converts to keypress action."""
        events = [{"type": "keypress", "selector": "#field", "key": "Tab"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        data = yaml.safe_load(yaml_str)
        assert data["actions"][1] == {"keypress": {"key": "Tab"}}

    def test_navigate_event(self) -> None:
        """Test navigate event conversion."""
        events = [{"type": "navigate", "url": "https://example.com/page2"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        data = yaml.safe_load(yaml_str)
        assert data["actions"][1] == {"navigate": {"url": "https://example.com/page2"}}

    def test_empty_events(self) -> None:
        """Test empty events list still includes initial navigate."""
        yaml_str = events_to_yaml([], "https://example.com")
        data = yaml.safe_load(yaml_str)
        assert len(data["actions"]) == 1
        assert data["actions"][0] == {"navigate": {"url": "https://example.com"}}

    def test_event_missing_selector_does_not_raise(self) -> None:
        """Events with missing selector should be skipped, not raise KeyError."""
        events = [{"type": "click"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        data = yaml.safe_load(yaml_str)
        # Only the initial navigate action should be present
        assert len(data["actions"]) == 1

    def test_event_missing_value_uses_empty_default(self) -> None:
        """Input events with missing value should use empty string."""
        events = [{"type": "input", "selector": "#field", "tag": "input"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        data = yaml.safe_load(yaml_str)
        assert data["actions"][1] == {"type": {"selector": "#field", "text": ""}}

    def test_navigate_event_missing_url_skipped(self) -> None:
        """Navigate events with missing url should be skipped."""
        events = [{"type": "navigate"}]
        yaml_str = events_to_yaml(events, "https://example.com")
        data = yaml.safe_load(yaml_str)
        assert len(data["actions"]) == 1

    def test_unknown_event_type_skipped(self) -> None:
        """Unknown event types should be skipped silently."""
        events = [{"type": "scroll", "x": 100, "y": 200}]
        yaml_str = events_to_yaml(events, "https://example.com")
        data = yaml.safe_load(yaml_str)
        assert len(data["actions"]) == 1
