"""Unit tests for DOMSnapshotAction."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.actions.dom_snapshot import DOMSnapshotAction, DOMSnapshotParams
from wavexis.backend.base import AbstractBackend


@pytest.mark.unit
class TestDOMSnapshotAction:
    """Test suite for domsnapshotaction."""

    def _make_backend(self) -> MagicMock:
        """Create a mock backend for testing.

        Returns:
            A MagicMock backend instance.
        """
        backend = MagicMock(spec=AbstractBackend)
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.dom_snapshot = AsyncMock(return_value={"documents": [], "strings": []})
        return backend

    async def test_dom_snapshot_action(self) -> None:
        """Test dom snapshot action."""
        backend = self._make_backend()
        params = DOMSnapshotParams(url="https://example.com")
        result = await DOMSnapshotAction(params).execute(backend)
        backend.dom_snapshot.assert_called_once()
        assert "documents" in result

    async def test_launch_and_close_called(self) -> None:
        """Test launch and close called."""
        backend = self._make_backend()
        params = DOMSnapshotParams(url="https://example.com")
        await DOMSnapshotAction(params).execute(backend)
        backend.navigate.assert_called_once()

    async def test_close_called_on_error(self) -> None:
        """Test close called on error."""
        backend = self._make_backend()
        backend.dom_snapshot = AsyncMock(side_effect=RuntimeError("boom"))
        params = DOMSnapshotParams(url="https://example.com")
        with pytest.raises(RuntimeError, match="boom"):
            await DOMSnapshotAction(params).execute(backend)

    def test_params_defaults(self) -> None:
        """Test params defaults."""
        params = DOMSnapshotParams()
        assert params.url == ""
