"""Unit tests for record/replay system."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from wavexis.backend.base import AbstractBackend
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
