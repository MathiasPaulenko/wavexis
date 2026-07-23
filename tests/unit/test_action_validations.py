"""Regression tests for action-level input validation fixes."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.actions.extract import ExtractParams
from wavexis.actions.har_replay import HARReplayAction, HARReplayParams
from wavexis.actions.input import InputAction, InputParams
from wavexis.actions.visual_diff import VisualDiffAction, VisualDiffParams
from wavexis.config import EvalParams, PDFParams, ScrapeParams, ScreenshotParams
from wavexis.exceptions import ActionError, WavexisError

pytestmark = pytest.mark.unit


class TestExtractValidation:
    """Regression: ExtractParams validates schema content."""

    def test_invalid_schema_key_type(self) -> None:
        with pytest.raises(ActionError, match="schema"):
            ExtractParams(schema={1: "h1"})

    def test_invalid_schema_value_type(self) -> None:
        with pytest.raises(ActionError, match="schema"):
            ExtractParams(schema={"title": 123})

    def test_null_byte_in_selector(self) -> None:
        with pytest.raises(ActionError, match="null"):
            ExtractParams(schema={"title": "h1\x00div"})


class TestHARReplayValidation:
    """Regression: HARReplayAction must check the input file."""

    async def test_missing_har_file(self) -> None:
        backend = MagicMock()
        action = HARReplayAction(HARReplayParams(har_path="/does/not/exist.har"))
        with pytest.raises(ActionError, match="not found"):
            await action.execute(backend)


class TestInputValidation:
    """Regression: InputAction rejects oversized upload files."""

    async def test_upload_file_too_large(self, tmp_path: Path) -> None:
        from wavexis.actions.input import MAX_UPLOAD_SIZE

        upload_file = tmp_path / "big.bin"
        upload_file.write_bytes(b"x" * (MAX_UPLOAD_SIZE + 1))

        backend = MagicMock()
        backend.set_files = AsyncMock()
        params = InputParams(action="upload", selector="#file", files=[str(upload_file)])
        action = InputAction(params)
        with pytest.raises(ActionError, match="too large"):
            await action.execute(backend)


class TestVisualDiffValidation:
    """Regression: VisualDiffAction handles unreadable baseline images."""

    async def test_non_image_baseline_returns_error(self, tmp_path: Path) -> None:
        baseline = tmp_path / "baseline.png"
        baseline.write_text("not an image")

        backend = MagicMock()
        backend.navigate = AsyncMock()
        backend.screenshot = AsyncMock(return_value=b"also not an image")
        action = VisualDiffAction(
            VisualDiffParams(
                baseline_path=str(baseline),
                url="https://example.com",
            )
        )
        result = await action.execute(backend)
        assert "error" in result

    async def test_missing_baseline_image(self, tmp_path: Path) -> None:
        action = VisualDiffAction(VisualDiffParams(baseline_path=str(tmp_path / "missing.png")))
        with pytest.raises(ActionError, match="not found"):
            await action.execute(MagicMock())


class TestEvalLengthValidation:
    """Regression: EvalAction rejects expressions that are too long."""

    async def test_expression_too_long(self) -> None:
        from wavexis.actions.eval import MAX_EXPRESSION_LENGTH, EvalAction

        backend = MagicMock()
        backend.navigate = AsyncMock()
        action = EvalAction(
            EvalParams(
                url="https://example.com",
                expression="x" * (MAX_EXPRESSION_LENGTH + 1),
            )
        )
        with pytest.raises(WavexisError, match="maximum length"):
            await action.execute(backend)


class TestScrapeLengthValidation:
    """Regression: ScrapeAction rejects oversized expressions."""

    async def test_expression_too_long(self) -> None:
        from wavexis.actions.scrape import MAX_EXPRESSION_LENGTH, ScrapeAction

        backend = MagicMock()
        backend.navigate = AsyncMock()
        action = ScrapeAction(
            ScrapeParams(
                urls=["https://example.com"],
                expression="x" * (MAX_EXPRESSION_LENGTH + 1),
            )
        )
        with pytest.raises(WavexisError, match="maximum length"):
            await action.execute(backend)


class TestScreenshotLengthValidation:
    """Regression: ScreenshotAction rejects oversized js snippets."""

    async def test_js_too_long(self) -> None:
        from wavexis.actions.screenshot import MAX_JS_LENGTH, ScreenshotAction

        backend = MagicMock()
        backend.navigate = AsyncMock()
        backend.screenshot = AsyncMock(return_value=b"png")
        params = ScreenshotParams(url="https://example.com", js="x" * (MAX_JS_LENGTH + 1))
        action = ScreenshotAction(params)
        with pytest.raises(WavexisError, match="maximum length"):
            await action.execute(backend)


class TestPDFLengthValidation:
    """Regression: PDFAction rejects oversized js snippets."""

    async def test_js_too_long(self) -> None:
        from wavexis.actions.pdf import MAX_JS_LENGTH, PDFAction

        backend = MagicMock()
        backend.navigate = AsyncMock()
        backend.pdf = AsyncMock(return_value=b"pdf")
        params = PDFParams(url="https://example.com", js="x" * (MAX_JS_LENGTH + 1))
        action = PDFAction(params)
        with pytest.raises(WavexisError, match="maximum length"):
            await action.execute(backend)


class TestNavigateURLValidation:
    """Regression: backend.navigate rejects non-HTTP/HTTPS/about schemes."""

    @pytest.mark.parametrize(
        "bad_url",
        ["javascript:alert(1)", "file:///etc/passwd", "vbscript:x"],
    )
    async def test_cdp_navigate_rejects_dangerous_scheme(self, bad_url: str) -> None:
        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        with pytest.raises(ActionError, match="scheme"):
            await backend.navigate(bad_url)

    @pytest.mark.parametrize(
        "bad_url",
        ["javascript:alert(1)", "file:///etc/passwd", "vbscript:x"],
    )
    async def test_bidi_navigate_rejects_dangerous_scheme(self, bad_url: str) -> None:
        from wavexis.backend.bidi import BiDiBackend

        backend = BiDiBackend()
        with pytest.raises(ActionError, match="scheme"):
            await backend.navigate(bad_url)

    async def test_cdp_new_tab_rejects_dangerous_scheme(self) -> None:
        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        with pytest.raises(ActionError, match="scheme"):
            await backend.new_tab("javascript:alert(1)")

    async def test_bidi_new_tab_rejects_dangerous_scheme(self) -> None:
        from wavexis.backend.bidi import BiDiBackend

        backend = BiDiBackend()
        with pytest.raises(ActionError, match="scheme"):
            await backend.new_tab("javascript:alert(1)")


class TestEvalFileRegular:
    """Regression: EvalAction rejects non-regular files."""

    async def test_directory_as_expression_file(self, tmp_path: Path) -> None:
        from wavexis.actions.eval import EvalAction

        backend = MagicMock()
        backend.navigate = AsyncMock()
        action = EvalAction(EvalParams(url="https://example.com", file=str(tmp_path)))
        with pytest.raises(WavexisError, match="not a regular file"):
            await action.execute(backend)


class TestScrapeFileRegular:
    """Regression: ScrapeAction rejects non-regular files."""

    async def test_directory_as_expression_file(self, tmp_path: Path) -> None:
        from wavexis.actions.scrape import ScrapeAction

        backend = MagicMock()
        backend.navigate = AsyncMock()
        action = ScrapeAction(ScrapeParams(urls=["https://example.com"], file=str(tmp_path)))
        with pytest.raises(WavexisError, match="not a regular file"):
            await action.execute(backend)


class TestFilePathBaseDirRestriction:
    """Regression: file paths used by actions are restricted to base_dir."""

    def test_eval_params_rejects_path_outside_base_dir(self, tmp_path: Path) -> None:
        from wavexis.config import EvalParams
        from wavexis.output import set_allowed_base_dir

        set_allowed_base_dir(str(tmp_path))
        try:
            with pytest.raises(ActionError, match="Invalid file"):
                EvalParams(url="", file="/etc/passwd")
        finally:
            set_allowed_base_dir(None)

    def test_scrape_params_rejects_path_outside_base_dir(self, tmp_path: Path) -> None:
        from wavexis.config import ScrapeParams
        from wavexis.output import set_allowed_base_dir

        set_allowed_base_dir(str(tmp_path))
        try:
            with pytest.raises(ActionError, match="Invalid file"):
                ScrapeParams(file="/etc/passwd", urls=["https://example.com"])
        finally:
            set_allowed_base_dir(None)
