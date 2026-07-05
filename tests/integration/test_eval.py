"""Integration tests for eval command."""

from pathlib import Path

import pytest

from browsix.actions.eval import EvalAction
from browsix.backend.manager import BackendManager
from browsix.config import BrowserOptions, EvalParams, WaitStrategy


@pytest.mark.integration
class TestEvalIntegration:
    """Integration tests for JS evaluation against real Chrome."""

    async def test_eval_expression(self):
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            params = EvalParams(
                url="https://example.com",
                expression="document.title",
                wait=WaitStrategy(strategy="load"),
            )
            action = EvalAction(params)
            result = await action.execute(backend)
            assert result == "Example Domain"
        finally:
            await backend.close()

    async def test_eval_from_file(self, tmp_path: Path):
        js_file = tmp_path / "script.js"
        js_file.write_text("document.title", encoding="utf-8")

        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            params = EvalParams(
                url="https://example.com",
                file=str(js_file),
                wait=WaitStrategy(strategy="load"),
            )
            action = EvalAction(params)
            result = await action.execute(backend)
            assert result == "Example Domain"
        finally:
            await backend.close()

    async def test_eval_await_promise(self):
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            params = EvalParams(
                url="https://example.com",
                expression="Promise.resolve(42)",
                await_promise=True,
                wait=WaitStrategy(strategy="load"),
            )
            action = EvalAction(params)
            result = await action.execute(backend)
            assert result == 42
        finally:
            await backend.close()
