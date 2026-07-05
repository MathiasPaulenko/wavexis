"""Unit tests for DownloadAction and ScreencastAction."""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest

from browsix.actions.download import DownloadAction
from browsix.actions.screencast import ScreencastAction
from browsix.backend.base import AbstractBackend
from browsix.config import ScreencastParams


def _make_backend() -> MagicMock:
    backend = MagicMock(spec=AbstractBackend)
    backend.launch = AsyncMock()
    backend.close = AsyncMock()
    backend.navigate = AsyncMock()
    backend.intercept_download = AsyncMock(return_value=b"file content")
    backend.screencast = AsyncMock(return_value=[b"frame1", b"frame2", b"frame3"])
    return backend


@pytest.mark.unit
class TestDownloadAction:
    async def test_intercept_download(self) -> None:
        backend = _make_backend()
        result = await DownloadAction(
            params=".*", url="https://example.com/download"
        ).execute(backend)
        backend.intercept_download.assert_called_once_with(".*")
        assert result == b"file content"

    async def test_intercept_download_no_url(self) -> None:
        backend = _make_backend()
        result = await DownloadAction(params=".*").execute(backend)
        backend.navigate.assert_not_called()
        assert result == b"file content"


@pytest.mark.unit
class TestScreencastAction:
    async def test_screencast_saves_frames(self) -> None:
        backend = _make_backend()
        params = ScreencastParams(url="https://example.com", duration=1.0)
        with tempfile.TemporaryDirectory() as tmpdir:
            action = ScreencastAction(params, output_dir=tmpdir)
            saved = await action.execute(backend)
            assert len(saved) == 3
            for fpath in saved:
                assert os.path.isfile(fpath)  # noqa: ASYNC240
                with open(fpath, "rb") as f:  # noqa: ASYNC230
                    data = f.read()
                    assert data in [b"frame1", b"frame2", b"frame3"]

    async def test_screencast_creates_dir(self) -> None:
        backend = _make_backend()
        params = ScreencastParams(url="https://example.com", duration=1.0)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "subdir", "frames")
            action = ScreencastAction(params, output_dir=output_dir)
            saved = await action.execute(backend)
            assert len(saved) == 3
            assert os.path.isdir(output_dir)  # noqa: ASYNC240
