"""Unit tests for Output helpers."""

import csv
import json
from pathlib import Path

import pytest

from browsix.output import Output


class TestOutput:
    """Tests for Output static methods."""

    def test_write_bytes_to_file(self, tmp_path: Path):
        """Test write bytes to file."""
        data = b"\x89PNG\r\n\x1a\n"
        path = str(tmp_path / "test.bin")
        Output.write_bytes(data, path)
        assert Path(path).read_bytes() == data

    def test_write_json_to_file(self, tmp_path: Path):
        """Test write json to file."""
        data = {"key": "value", "num": 42}
        path = str(tmp_path / "test.json")
        Output.write_json(data, path)
        loaded = json.loads(Path(path).read_text(encoding="utf-8"))
        assert loaded == data

    def test_write_text_to_file(self, tmp_path: Path):
        """Test write text to file."""
        text = "hello world"
        path = str(tmp_path / "test.txt")
        Output.write_text(text, path)
        assert Path(path).read_text(encoding="utf-8") == text

    def test_write_csv_to_file(self, tmp_path: Path):
        """Test write csv to file."""
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        path = str(tmp_path / "output.csv")
        Output.write_csv(data, path)
        with Path(path).open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["name"] == "Alice"
        assert rows[0]["age"] == "30"
        assert rows[1]["name"] == "Bob"

    def test_write_csv_empty(self, tmp_path: Path):
        """Test write csv empty."""
        path = str(tmp_path / "empty.csv")
        Output.write_csv([], path)
        assert Path(path).read_text(encoding="utf-8") == ""

    def test_write_csv_different_keys(self, tmp_path: Path):
        """Test write csv different keys."""
        data = [
            {"a": 1, "b": 2},
            {"a": 3, "c": 4},
        ]
        path = str(tmp_path / "multi.csv")
        Output.write_csv(data, path)
        with Path(path).open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert "a" in rows[0]
        assert "b" in rows[0]
        assert "c" in rows[0]
        assert rows[1]["c"] == "4"


@pytest.mark.unit
class TestOutputRichFallback:
    """Tests for Output.error/success/info with and without rich."""

    def test_error_without_rich(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test error without rich."""
        Output.error("test error message")
        captured = capsys.readouterr()
        assert "test error message" in captured.err

    def test_success_without_rich(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test success without rich."""
        Output.success("test success message")
        captured = capsys.readouterr()
        assert "test success message" in captured.out

    def test_info_without_rich(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test info without rich."""
        Output.info("test info message")
        captured = capsys.readouterr()
        assert "test info message" in captured.out
