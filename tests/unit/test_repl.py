"""Unit tests for wavexis REPL module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.repl import execute_repl_command, parse_command


@pytest.mark.unit
class TestParseCommand:
    """Tests for parse_command."""

    def test_simple_command(self) -> None:
        """Test parsing a simple command."""
        cmd, args = parse_command("help")
        assert cmd == "help"
        assert args == []

    def test_command_with_args(self) -> None:
        """Test parsing command with arguments."""
        cmd, args = parse_command("navigate https://example.com")
        assert cmd == "navigate"
        assert args == ["https://example.com"]

    def test_command_with_quoted_args(self) -> None:
        """Test parsing command with quoted arguments."""
        cmd, args = parse_command('eval "document.title"')
        assert cmd == "eval"
        assert args == ["document.title"]

    def test_case_insensitive(self) -> None:
        """Test command is case-insensitive."""
        cmd, _ = parse_command("HELP")
        assert cmd == "help"

    def test_empty_line_raises(self) -> None:
        """Test empty line raises ValueError."""
        with pytest.raises(ValueError, match="Empty command"):
            parse_command("")

    def test_whitespace_only_raises(self) -> None:
        """Test whitespace-only line raises ValueError."""
        with pytest.raises(ValueError, match="Empty command"):
            parse_command("   ")


@pytest.mark.unit
class TestExecuteReplCommand:
    """Tests for execute_repl_command."""

    def _make_backend(self) -> MagicMock:
        """Create a mock backend with AsyncMock methods."""
        backend = MagicMock()
        backend.navigate = AsyncMock()
        backend.screenshot = AsyncMock(return_value=b"png-bytes")
        backend.eval = AsyncMock(return_value="result")
        backend.click = AsyncMock()
        backend.type_text = AsyncMock()
        backend.fill = AsyncMock()
        backend.hover = AsyncMock()
        backend.key_press = AsyncMock()
        backend.get_cookies = AsyncMock(return_value=[{"name": "session"}])
        backend.wait_for = AsyncMock()
        backend.close = AsyncMock()
        return backend

    async def test_navigate(self) -> None:
        """Test navigate command."""
        backend = self._make_backend()
        result = await execute_repl_command(backend, "navigate", ["https://example.com"])
        assert "Navigated to" in result
        backend.navigate.assert_called_once()

    async def test_navigate_missing_url(self) -> None:
        """Test navigate without URL raises ValueError."""
        backend = self._make_backend()
        with pytest.raises(ValueError, match="Usage: navigate"):
            await execute_repl_command(backend, "navigate", [])

    async def test_eval(self) -> None:
        """Test eval command."""
        backend = self._make_backend()
        result = await execute_repl_command(backend, "eval", ["document.title"])
        assert result == "result"
        backend.eval.assert_called_once_with("document.title", await_promise=True)

    async def test_eval_missing_expr(self) -> None:
        """Test eval without expression raises ValueError."""
        backend = self._make_backend()
        with pytest.raises(ValueError, match="Usage: eval"):
            await execute_repl_command(backend, "eval", [])

    async def test_click(self) -> None:
        """Test click command."""
        backend = self._make_backend()
        result = await execute_repl_command(backend, "click", ["#button"])
        assert "Clicked" in result
        backend.click.assert_called_once_with("#button")

    async def test_click_missing_selector(self) -> None:
        """Test click without selector raises ValueError."""
        backend = self._make_backend()
        with pytest.raises(ValueError, match="Usage: click"):
            await execute_repl_command(backend, "click", [])

    async def test_type(self) -> None:
        """Test type command."""
        backend = self._make_backend()
        result = await execute_repl_command(backend, "type", ["#input", "hello", "world"])
        assert "Typed" in result
        backend.type_text.assert_called_once_with("#input", "hello world")

    async def test_type_missing_args(self) -> None:
        """Test type with insufficient args raises ValueError."""
        backend = self._make_backend()
        with pytest.raises(ValueError, match="Usage: type"):
            await execute_repl_command(backend, "type", ["#input"])

    async def test_fill(self) -> None:
        """Test fill command."""
        backend = self._make_backend()
        result = await execute_repl_command(backend, "fill", ["#input", "value"])
        assert "Filled" in result
        backend.fill.assert_called_once_with("#input", "value")

    async def test_hover(self) -> None:
        """Test hover command."""
        backend = self._make_backend()
        result = await execute_repl_command(backend, "hover", ["#elem"])
        assert "Hovered" in result
        backend.hover.assert_called_once_with("#elem")

    async def test_key(self) -> None:
        """Test key command."""
        backend = self._make_backend()
        result = await execute_repl_command(backend, "key", ["Enter"])
        assert "Pressed" in result
        backend.key_press.assert_called_once_with("Enter")

    async def test_cookies(self) -> None:
        """Test cookies command returns JSON."""
        backend = self._make_backend()
        result = await execute_repl_command(backend, "cookies", [])
        assert "session" in result

    async def test_url(self) -> None:
        """Test url command."""
        backend = self._make_backend()
        backend.eval = AsyncMock(return_value="https://example.com/page")
        result = await execute_repl_command(backend, "url", [])
        assert result == "https://example.com/page"

    async def test_title(self) -> None:
        """Test title command."""
        backend = self._make_backend()
        backend.eval = AsyncMock(return_value="My Page")
        result = await execute_repl_command(backend, "title", [])
        assert result == "My Page"

    async def test_wait(self) -> None:
        """Test wait command."""
        backend = self._make_backend()
        result = await execute_repl_command(backend, "wait", ["#element"])
        assert "Waited" in result
        backend.wait_for.assert_called_once()

    async def test_help(self) -> None:
        """Test help command returns help text."""
        backend = self._make_backend()
        result = await execute_repl_command(backend, "help", [])
        assert "navigate" in result
        assert "screenshot" in result
        assert "eval" in result

    async def test_exit(self) -> None:
        """Test exit command returns __EXIT__."""
        backend = self._make_backend()
        result = await execute_repl_command(backend, "exit", [])
        assert result == "__EXIT__"

    async def test_quit(self) -> None:
        """Test quit command returns __EXIT__."""
        backend = self._make_backend()
        result = await execute_repl_command(backend, "quit", [])
        assert result == "__EXIT__"

    async def test_unknown_command(self) -> None:
        """Test unknown command raises ValueError."""
        backend = self._make_backend()
        with pytest.raises(ValueError, match="Unknown command"):
            await execute_repl_command(backend, "foobar", [])
