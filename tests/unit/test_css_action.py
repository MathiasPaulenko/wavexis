"""Unit tests for CSSAction."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from browsix.actions.css import CSSAction, CSSActionParams
from browsix.backend.base import AbstractBackend


@pytest.mark.unit
class TestCSSAction:
    """Test suite for cssaction."""
    def _make_backend(self) -> MagicMock:
        """Create a mock backend for testing.

            Returns:
                A MagicMock backend instance.
            """
        backend = MagicMock(spec=AbstractBackend)
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.css_get_styles = AsyncMock(
            return_value={"inlineStyles": {"cssText": "color: red"}, "matchedStyles": {}}
        )
        backend.css_get_stylesheets = AsyncMock(
            return_value=[{"styleSheetId": "1", "origin": "regular", "sourceURL": "style.css"}]
        )
        backend.css_get_rules = AsyncMock(
            return_value=[{"selectorText": "body", "cssText": "margin: 0"}]
        )
        backend.css_get_computed = AsyncMock(
            return_value={"color": "rgb(255, 0, 0)", "display": "block"}
        )
        return backend

    async def test_styles_action(self) -> None:
        """Test styles action."""
        backend = self._make_backend()
        params = CSSActionParams(
            url="https://example.com", action="styles", selector="body"
        )
        result = await CSSAction(params).execute(backend)
        backend.css_get_styles.assert_called_once_with("body")
        assert "inlineStyles" in result

    async def test_stylesheets_action(self) -> None:
        """Test stylesheets action."""
        backend = self._make_backend()
        params = CSSActionParams(url="https://example.com", action="stylesheets")
        result = await CSSAction(params).execute(backend)
        backend.css_get_stylesheets.assert_called_once()
        assert isinstance(result, list)
        assert len(result) == 1

    async def test_rules_action(self) -> None:
        """Test rules action."""
        backend = self._make_backend()
        params = CSSActionParams(
            url="https://example.com", action="rules", stylesheet_id="sheet-1"
        )
        result = await CSSAction(params).execute(backend)
        backend.css_get_rules.assert_called_once_with("sheet-1")
        assert isinstance(result, list)

    async def test_computed_action(self) -> None:
        """Test computed action."""
        backend = self._make_backend()
        params = CSSActionParams(
            url="https://example.com", action="computed", selector="#hero"
        )
        result = await CSSAction(params).execute(backend)
        backend.css_get_computed.assert_called_once_with("#hero")
        assert "color" in result

    async def test_styles_missing_selector_raises(self) -> None:
        """Test that styles missing selector raises raises an appropriate error."""
        backend = self._make_backend()
        params = CSSActionParams(url="https://example.com", action="styles")
        with pytest.raises(ValueError, match="selector is required"):
            await CSSAction(params).execute(backend)

    async def test_rules_missing_stylesheet_id_raises(self) -> None:
        """Test that rules missing stylesheet id raises raises an appropriate error."""
        backend = self._make_backend()
        params = CSSActionParams(url="https://example.com", action="rules")
        with pytest.raises(ValueError, match="stylesheet_id is required"):
            await CSSAction(params).execute(backend)

    async def test_unknown_action_raises(self) -> None:
        """Test that unknown action raises raises an appropriate error."""
        backend = self._make_backend()
        params = CSSActionParams(url="https://example.com", action="unknown")
        with pytest.raises(ValueError, match="Unknown CSS action"):
            await CSSAction(params).execute(backend)

    async def test_launch_and_close_called(self) -> None:
        """Test launch and close called."""
        backend = self._make_backend()
        params = CSSActionParams(
            url="https://example.com", action="stylesheets"
        )
        await CSSAction(params).execute(backend)
        backend.launch.assert_called_once()
        backend.close.assert_called_once()

    async def test_close_called_on_error(self) -> None:
        """Test close called on error."""
        backend = self._make_backend()
        backend.css_get_stylesheets = AsyncMock(side_effect=RuntimeError("boom"))
        params = CSSActionParams(url="https://example.com", action="stylesheets")
        with pytest.raises(RuntimeError, match="boom"):
            await CSSAction(params).execute(backend)
        backend.close.assert_called_once()

    def test_params_defaults(self) -> None:
        """Test params defaults."""
        params = CSSActionParams()
        assert params.action == "styles"
        assert params.url == ""
        assert params.selector is None
