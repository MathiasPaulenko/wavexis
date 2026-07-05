"""Integration tests for console and logs commands."""

import pytest

from browsix.actions.console import ConsoleAction, ConsoleParams
from browsix.backend.manager import BackendManager
from browsix.config import BrowserOptions, WaitStrategy


@pytest.mark.integration
class TestConsoleIntegration:
    """Integration tests for console capture against real Chrome."""

    async def test_capture_console(self):
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            params = ConsoleParams(
                url="https://example.com",
                capture="console",
                wait=WaitStrategy(strategy="load"),
            )
            action = ConsoleAction(params)
            result = await action.execute(backend)
            assert "console" in result
            assert isinstance(result["console"], list)
        finally:
            await backend.close()

    async def test_capture_logs(self):
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            params = ConsoleParams(
                url="https://example.com",
                capture="logs",
                wait=WaitStrategy(strategy="load"),
            )
            action = ConsoleAction(params)
            result = await action.execute(backend)
            assert "logs" in result
            assert isinstance(result["logs"], list)
        finally:
            await backend.close()
