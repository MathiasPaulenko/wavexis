"""Unit tests for Output helpers."""

import csv
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import typer

from wavexis.output import Output, set_allowed_base_dir, validate_path


class TestValidatePath:
    """Tests for the shared validate_path helper."""

    def test_allows_safe_relative_path(self, tmp_path: Path):
        path = str(tmp_path / "subdir" / "file.txt")
        assert validate_path(path) == Path(path)

    def test_allows_absolute_path(self, tmp_path: Path):
        path = str(tmp_path / "file.txt")
        assert validate_path(path) == Path(path)

    def test_rejects_parent_directory_traversal(self):
        with pytest.raises(ValueError, match="Invalid path"):
            validate_path("../escape.txt")

    def test_rejects_traversal_in_middle_of_path(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Invalid path"):
            validate_path(str(tmp_path / "safe" / ".." / "escape.txt"))

    def test_rejects_null_byte(self):
        with pytest.raises(ValueError, match="Invalid path"):
            validate_path("foo\x00bar.txt")


class TestValidatePathBaseDir:
    """Regression: validate_path resolves relative paths from base_dir."""

    def test_relative_path_resolves_from_base_dir(self, tmp_path: Path):
        base = tmp_path / "base"
        base.mkdir()
        (base / "file.txt").write_text("ok")
        set_allowed_base_dir(str(base))
        try:
            resolved = validate_path("file.txt")
            assert resolved == (base / "file.txt").resolve()
        finally:
            set_allowed_base_dir(None)

    def test_relative_path_outside_base_dir_rejected(self, tmp_path: Path):
        base = tmp_path / "base"
        base.mkdir()
        outside = tmp_path / "outside.txt"
        outside.write_text("ok")
        set_allowed_base_dir(str(base))
        try:
            with pytest.raises(ValueError, match="Invalid path"):
                validate_path(str(outside))
        finally:
            set_allowed_base_dir(None)


class TestOutputPathTraversal:
    """Regression tests: Output helpers must reject traversal attempts."""

    def test_write_bytes_rejects_traversal(self):
        with pytest.raises(ValueError, match="Invalid path"):
            Output.write_bytes(b"data", "../escape.bin")

    def test_write_json_rejects_traversal(self):
        with pytest.raises(ValueError, match="Invalid path"):
            Output.write_json({"x": 1}, "../escape.json")

    def test_write_text_rejects_traversal(self):
        with pytest.raises(ValueError, match="Invalid path"):
            Output.write_text("hello", "../escape.txt")

    def test_write_csv_rejects_traversal(self):
        with pytest.raises(ValueError, match="Invalid path"):
            Output.write_csv([{"a": 1}], "../escape.csv")

    def test_write_yaml_rejects_traversal(self):
        with pytest.raises(ValueError, match="Invalid path"):
            Output.write_yaml({"a": 1}, "../escape.yaml")


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
        assert not Path(path).exists()

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

    def test_write_bytes_dash_means_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test write_bytes with path='-' writes to stdout.buffer."""
        data = b"binary data"
        Output.write_bytes(data, "-")
        captured = capsys.readouterr()
        assert "binary data" in captured.out

    def test_write_json_dash_means_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test write_json with path='-' prints to stdout."""
        data = {"key": "value"}
        Output.write_json(data, "-")
        captured = capsys.readouterr()
        assert json.loads(captured.out) == data

    def test_write_text_dash_means_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test write_text with path='-' prints to stdout."""
        text = "hello stdout"
        Output.write_text(text, "-")
        captured = capsys.readouterr()
        assert captured.out == "hello stdout\n"

    def test_write_csv_dash_means_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test write_csv with path='-' prints to stdout."""
        data = [{"name": "Alice", "age": 30}]
        Output.write_csv(data, "-")
        captured = capsys.readouterr()
        assert "name" in captured.out
        assert "Alice" in captured.out

    def test_write_yaml_to_file(self, tmp_path: Path) -> None:
        """Test write_yaml writes a YAML file to disk."""
        path = str(tmp_path / "out.yml")
        Output.write_yaml({"x": 1, "y": [1, 2, 3]}, path)
        text = Path(path).read_text(encoding="utf-8")
        assert "x: 1" in text
        assert "y:" in text

    def test_write_yaml_dash_means_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test write_yaml with path='-' prints to stdout."""
        Output.write_yaml({"x": 1}, "-")
        captured = capsys.readouterr()
        assert "x: 1" in captured.out

    def test_write_yaml_raises_when_pyyaml_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test write_yaml raises ImportError when PyYAML is not installed."""
        import wavexis.output as output_mod

        monkeypatch.setattr(output_mod, "_yaml", None)
        with pytest.raises(ImportError, match="PyYAML"):
            output_mod.Output.write_yaml({"x": 1}, None)


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

    def test_success_prints_unicode_checkmark(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Regression for bug #1: Output.success must not crash on unicode.

        On Windows consoles with a legacy codepage (cp1252/cp850), the
        checkmark glyph (U+2713) used by Rich caused
        `OSError: [Errno 22] Invalid argument`. The Output module now wraps
        stdout/stderr with a UTF-8 TextIOWrapper on Windows, so this should
        always succeed.
        """
        Output.success("unicode test \u2713 \u2139 \u00e9")
        captured = capsys.readouterr()
        assert "unicode test" in captured.out

    def test_info_prints_unicode_info_glyph(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Regression for bug #1: Output.info must not crash on unicode."""
        Output.info("info \u2139")
        captured = capsys.readouterr()
        assert "info" in captured.out


class TestOutputOSError:
    """Regression tests: Output helpers must fail cleanly on write errors."""

    @pytest.mark.parametrize(
        "method,args,write_method",
        [
            ("write_bytes", (b"data",), "write_bytes"),
            ("write_text", ("hello",), "write_text"),
            ("write_json", ({"x": 1},), "write_text"),
            ("write_yaml", ({"x": 1},), "write_text"),
            ("write_csv", ([{"a": 1}],), "open"),
        ],
    )
    def test_write_exits_on_oserror(
        self,
        method: str,
        args: tuple[Any, ...],
        write_method: str,
        tmp_path: Path,
    ) -> None:
        """A write failure should produce a clean exit, not a traceback."""
        bad_path = MagicMock()
        getattr(bad_path, write_method).side_effect = PermissionError("denied")
        with (
            patch("wavexis.output.validate_path", return_value=bad_path),
            pytest.raises(typer.Exit),
        ):
            getattr(Output, method)(*args, str(tmp_path / "out"))
