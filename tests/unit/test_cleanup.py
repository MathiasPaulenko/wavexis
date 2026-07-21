"""Unit tests for resource cleanup module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

import wavexis.cleanup as cleanup_mod
from wavexis.cleanup import (
    _cleanup_sync,
    register_backend,
    unregister_backend,
)


@pytest.mark.unit
class TestCleanup:
    """Tests for browser cleanup on crash."""

    def setup_method(self) -> None:
        """Reset cleanup state before each test."""
        cleanup_mod._cleanup_done = False
        cleanup_mod._registered_backends.clear()

    def test_register_and_unregister(self) -> None:
        backend = MagicMock()
        register_backend(backend)
        unregister_backend(backend)

    def test_cleanup_with_no_backends(self) -> None:
        _cleanup_sync()

    def test_cleanup_closes_registered_backends(self) -> None:
        backend = MagicMock()
        backend.close = AsyncMock()
        register_backend(backend)
        _cleanup_sync()
        backend.close.assert_called_once()

    def test_cleanup_is_idempotent(self) -> None:
        backend = MagicMock()
        backend.close = AsyncMock()
        register_backend(backend)
        _cleanup_sync()
        _cleanup_sync()
        backend.close.assert_called_once()

    def test_cleanup_swallows_errors(self) -> None:
        backend = MagicMock()
        backend.close = AsyncMock(side_effect=RuntimeError("boom"))
        register_backend(backend)
        _cleanup_sync()


@pytest.mark.unit
class TestSignalHandler:
    """Tests for _signal_handler and _setup_signal_handlers."""

    def setup_method(self) -> None:
        """Reset cleanup state before each test."""
        cleanup_mod._cleanup_done = False
        cleanup_mod._registered_backends.clear()

    def test_signal_handler_calls_cleanup_and_exits(self) -> None:
        """_signal_handler should run cleanup and call sys.exit with 128+signum."""
        import signal as signal_mod

        from wavexis.cleanup import _signal_handler

        backend = MagicMock()
        backend.close = AsyncMock()
        register_backend(backend)

        with pytest.raises(SystemExit) as exc_info:
            _signal_handler(signal_mod.SIGINT, None)
        assert exc_info.value.code == 128 + signal_mod.SIGINT
        # Cleanup should have closed the backend
        backend.close.assert_called_once()

    def test_signal_handler_unknown_signal_name(self) -> None:
        """_signal_handler uses str(signum) for unknown signals."""
        from wavexis.cleanup import _signal_handler

        with pytest.raises(SystemExit) as exc_info:
            _signal_handler(99, None)
        # 99 is not a standard signal name, so should use str(99)
        assert exc_info.value.code == 128 + 99

    def test_signal_handler_known_name_writes_to_stderr(self, capsys) -> None:
        """_signal_handler writes the signal name to stderr."""
        import signal as signal_mod

        from wavexis.cleanup import _signal_handler

        with pytest.raises(SystemExit):
            _signal_handler(signal_mod.SIGTERM, None)
        captured = capsys.readouterr()
        # SIGTERM should be in the message
        assert "SIGTERM" in captured.err or "15" in captured.err

    def test_setup_signal_handlers_registers_handlers(self) -> None:
        """_setup_signal_handlers should register handlers without raising."""
        from wavexis.cleanup import _setup_signal_handlers

        # Should not raise even in a test environment
        _setup_signal_handlers()
