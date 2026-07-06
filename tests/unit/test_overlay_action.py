"""Unit tests for OverlayAction."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.actions.overlay import OverlayAction, OverlayParams
from wavexis.backend.base import AbstractBackend


@pytest.mark.unit
class TestOverlayAction:
    """Test suite for overlayaction."""
    def _make_backend(self) -> MagicMock:
        """Create a mock backend for testing.

            Returns:
                A MagicMock backend instance.
            """
        backend = MagicMock(spec=AbstractBackend)
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.overlay_highlight = AsyncMock()
        backend.overlay_clear = AsyncMock()
        return backend

    async def test_highlight_action(self) -> None:
        """Test highlight action."""
        backend = self._make_backend()
        params = OverlayParams(
            url="https://example.com", action="highlight", selector="#hero"
        )
        await OverlayAction(params).execute(backend)
        backend.overlay_highlight.assert_called_once_with(
            "#hero", "rgba(255,0,0,0.5)"
        )

    async def test_highlight_custom_color(self) -> None:
        """Test highlight custom color."""
        backend = self._make_backend()
        params = OverlayParams(
            url="https://example.com",
            action="highlight",
            selector="#hero",
            color="rgba(0,255,0,0.3)",
        )
        await OverlayAction(params).execute(backend)
        backend.overlay_highlight.assert_called_once_with(
            "#hero", "rgba(0,255,0,0.3)"
        )

    async def test_clear_action(self) -> None:
        """Test clear action."""
        backend = self._make_backend()
        params = OverlayParams(url="https://example.com", action="clear")
        await OverlayAction(params).execute(backend)
        backend.overlay_clear.assert_called_once()

    async def test_highlight_missing_selector_raises(self) -> None:
        """Test that highlight missing selector raises raises an appropriate error."""
        backend = self._make_backend()
        params = OverlayParams(url="https://example.com", action="highlight")
        with pytest.raises(ValueError, match="selector is required"):
            await OverlayAction(params).execute(backend)

    async def test_unknown_action_raises(self) -> None:
        """Test that unknown action raises raises an appropriate error."""
        backend = self._make_backend()
        params = OverlayParams(url="https://example.com", action="unknown")
        with pytest.raises(ValueError, match="Unknown overlay action"):
            await OverlayAction(params).execute(backend)

    async def test_launch_and_close_called(self) -> None:
        """Test launch and close called."""
        backend = self._make_backend()
        params = OverlayParams(url="https://example.com", action="clear")
        await OverlayAction(params).execute(backend)
        backend.launch.assert_called_once()
        backend.close.assert_called_once()

    async def test_close_called_on_error(self) -> None:
        """Test close called on error."""
        backend = self._make_backend()
        backend.overlay_clear = AsyncMock(side_effect=RuntimeError("boom"))
        params = OverlayParams(url="https://example.com", action="clear")
        with pytest.raises(RuntimeError, match="boom"):
            await OverlayAction(params).execute(backend)
        backend.close.assert_called_once()

    def test_params_defaults(self) -> None:
        """Test params defaults."""
        params = OverlayParams()
        assert params.action == "highlight"
        assert params.color == "rgba(255,0,0,0.5)"
        assert params.url == ""
