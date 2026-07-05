"""Unit tests for DebugAction."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from browsix.actions.debug import DebugAction, DebugActionParams
from browsix.backend.base import AbstractBackend


@pytest.mark.unit
class TestDebugAction:
    """Test suite for debugaction."""
    def _make_backend(self) -> MagicMock:
        """Create a mock backend for testing.

            Returns:
                A MagicMock backend instance.
            """
        backend = MagicMock(spec=AbstractBackend)
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.debug_set_breakpoint = AsyncMock(return_value="bp-1")
        backend.debug_set_breakpoint_function = AsyncMock(return_value="bp-func-1")
        backend.debug_remove_breakpoint = AsyncMock()
        backend.debug_step_over = AsyncMock()
        backend.debug_step_into = AsyncMock()
        backend.debug_step_out = AsyncMock()
        backend.debug_pause = AsyncMock()
        backend.debug_resume = AsyncMock()
        backend.debug_get_listeners = AsyncMock(
            return_value=[{"type": "click", "useCapture": False, "passive": False}]
        )
        return backend

    async def test_breakpoint_action(self) -> None:
        """Test breakpoint action."""
        backend = self._make_backend()
        params = DebugActionParams(
            url="https://example.com",
            action="breakpoint",
            script_url="https://example.com/app.js",
            line=42,
        )
        result = await DebugAction(params).execute(backend)
        backend.debug_set_breakpoint.assert_called_once_with(
            "https://example.com/app.js", 42, None
        )
        assert result == "bp-1"

    async def test_breakpoint_with_condition(self) -> None:
        """Test breakpoint with condition."""
        backend = self._make_backend()
        params = DebugActionParams(
            url="https://example.com",
            action="breakpoint",
            script_url="https://example.com/app.js",
            line=10,
            condition="x > 5",
        )
        result = await DebugAction(params).execute(backend)
        backend.debug_set_breakpoint.assert_called_once_with(
            "https://example.com/app.js", 10, "x > 5"
        )
        assert result == "bp-1"

    async def test_function_breakpoint_action(self) -> None:
        """Test function breakpoint action."""
        backend = self._make_backend()
        params = DebugActionParams(
            url="https://example.com",
            action="function_breakpoint",
            function_name="myFunc",
        )
        result = await DebugAction(params).execute(backend)
        backend.debug_set_breakpoint_function.assert_called_once_with("myFunc")
        assert result == "bp-func-1"

    async def test_remove_breakpoint_action(self) -> None:
        """Test remove breakpoint action."""
        backend = self._make_backend()
        params = DebugActionParams(
            url="https://example.com",
            action="remove_breakpoint",
            breakpoint_id="bp-1",
        )
        result = await DebugAction(params).execute(backend)
        backend.debug_remove_breakpoint.assert_called_once_with("bp-1")
        assert result is None

    async def test_step_over_action(self) -> None:
        """Test step over action."""
        backend = self._make_backend()
        params = DebugActionParams(url="https://example.com", action="step_over")
        await DebugAction(params).execute(backend)
        backend.debug_step_over.assert_called_once()

    async def test_step_into_action(self) -> None:
        """Test step into action."""
        backend = self._make_backend()
        params = DebugActionParams(url="https://example.com", action="step_into")
        await DebugAction(params).execute(backend)
        backend.debug_step_into.assert_called_once()

    async def test_step_out_action(self) -> None:
        """Test step out action."""
        backend = self._make_backend()
        params = DebugActionParams(url="https://example.com", action="step_out")
        await DebugAction(params).execute(backend)
        backend.debug_step_out.assert_called_once()

    async def test_pause_action(self) -> None:
        """Test pause action."""
        backend = self._make_backend()
        params = DebugActionParams(url="https://example.com", action="pause")
        await DebugAction(params).execute(backend)
        backend.debug_pause.assert_called_once()

    async def test_resume_action(self) -> None:
        """Test resume action."""
        backend = self._make_backend()
        params = DebugActionParams(url="https://example.com", action="resume")
        await DebugAction(params).execute(backend)
        backend.debug_resume.assert_called_once()

    async def test_listeners_action(self) -> None:
        """Test listeners action."""
        backend = self._make_backend()
        params = DebugActionParams(
            url="https://example.com", action="listeners", selector="#btn"
        )
        result = await DebugAction(params).execute(backend)
        backend.debug_get_listeners.assert_called_once_with("#btn")
        assert isinstance(result, list)
        assert result[0]["type"] == "click"

    async def test_breakpoint_missing_script_url_raises(self) -> None:
        """Test that breakpoint missing script url raises raises an appropriate error."""
        backend = self._make_backend()
        params = DebugActionParams(
            url="https://example.com", action="breakpoint", line=42
        )
        with pytest.raises(ValueError, match="script_url and line are required"):
            await DebugAction(params).execute(backend)

    async def test_breakpoint_missing_line_raises(self) -> None:
        """Test that breakpoint missing line raises raises an appropriate error."""
        backend = self._make_backend()
        params = DebugActionParams(
            url="https://example.com", action="breakpoint",
            script_url="https://example.com/app.js",
        )
        with pytest.raises(ValueError, match="script_url and line are required"):
            await DebugAction(params).execute(backend)

    async def test_unknown_action_raises(self) -> None:
        """Test that unknown action raises raises an appropriate error."""
        backend = self._make_backend()
        params = DebugActionParams(url="https://example.com", action="unknown")
        with pytest.raises(ValueError, match="Unknown debug action"):
            await DebugAction(params).execute(backend)

    async def test_close_called_on_error(self) -> None:
        """Test close called on error."""
        backend = self._make_backend()
        backend.debug_pause = AsyncMock(side_effect=RuntimeError("boom"))
        params = DebugActionParams(url="https://example.com", action="pause")
        with pytest.raises(RuntimeError, match="boom"):
            await DebugAction(params).execute(backend)
        backend.close.assert_called_once()

    def test_params_defaults(self) -> None:
        """Test params defaults."""
        params = DebugActionParams()
        assert params.action == "breakpoint"
        assert params.url is None
