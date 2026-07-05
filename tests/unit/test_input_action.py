"""Unit tests for InputAction."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from browsix.actions.input import InputAction
from browsix.backend.base import AbstractBackend
from browsix.config import InputParams


@pytest.mark.unit
class TestInputAction:
    def _make_backend(self) -> MagicMock:
        backend = MagicMock(spec=AbstractBackend)
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.click = AsyncMock()
        backend.type_text = AsyncMock()
        backend.fill = AsyncMock()
        backend.select_option = AsyncMock()
        backend.hover = AsyncMock()
        backend.key_press = AsyncMock()
        backend.drag = AsyncMock()
        backend.tap = AsyncMock()
        return backend

    async def test_click_action(self) -> None:
        backend = self._make_backend()
        params = InputParams(url="https://example.com", selector="#btn", action="click")
        await InputAction(params).execute(backend)
        backend.navigate.assert_called_once()
        backend.click.assert_called_once_with("#btn", button="left", click_count=1)

    async def test_type_action(self) -> None:
        backend = self._make_backend()
        params = InputParams(
            url="https://example.com", selector="#input",
            action="type", text="hello", delay=10,
        )
        await InputAction(params).execute(backend)
        backend.type_text.assert_called_once_with("#input", "hello", delay=10)

    async def test_fill_action(self) -> None:
        backend = self._make_backend()
        params = InputParams(
            url="https://example.com", selector="#input",
            action="fill", value="test",
        )
        await InputAction(params).execute(backend)
        backend.fill.assert_called_once_with("#input", "test")

    async def test_select_action(self) -> None:
        backend = self._make_backend()
        params = InputParams(
            url="https://example.com", selector="select",
            action="select", value="opt1",
        )
        await InputAction(params).execute(backend)
        backend.select_option.assert_called_once_with("select", "opt1")

    async def test_hover_action(self) -> None:
        backend = self._make_backend()
        params = InputParams(url="https://example.com", selector="#el", action="hover")
        await InputAction(params).execute(backend)
        backend.hover.assert_called_once_with("#el")

    async def test_key_action(self) -> None:
        backend = self._make_backend()
        params = InputParams(url="https://example.com", action="key", key="Enter")
        await InputAction(params).execute(backend)
        backend.key_press.assert_called_once_with("Enter")

    async def test_drag_action(self) -> None:
        backend = self._make_backend()
        params = InputParams(url="https://example.com", action="drag", source="#src", target="#tgt")
        await InputAction(params).execute(backend)
        backend.drag.assert_called_once_with("#src", "#tgt")

    async def test_tap_action(self) -> None:
        backend = self._make_backend()
        params = InputParams(url="https://example.com", selector="#el", action="tap")
        await InputAction(params).execute(backend)
        backend.tap.assert_called_once_with("#el")

    async def test_unknown_action_raises(self) -> None:
        backend = self._make_backend()
        params = InputParams(url="https://example.com", action="unknown")
        with pytest.raises(ValueError, match="Unknown input action"):
            await InputAction(params).execute(backend)
