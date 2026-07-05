"""Integration tests for PDF command."""

import pytest

from browsix.actions.pdf import PDFAction
from browsix.backend.manager import BackendManager
from browsix.config import BrowserOptions, PDFParams, WaitStrategy


@pytest.mark.integration
class TestPDFIntegration:
    """Integration tests for PDF generation against real Chrome."""

    async def test_pdf_letter(self):
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            params = PDFParams(
                url="https://example.com",
                paper="letter",
                wait=WaitStrategy(strategy="load"),
            )
            action = PDFAction(params)
            result = await action.execute(backend)
            assert len(result) > 0
            assert result[:4] == b"%PDF"
        finally:
            await backend.close()

    async def test_pdf_a4(self):
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            params = PDFParams(
                url="https://example.com",
                paper="a4",
                wait=WaitStrategy(strategy="load"),
            )
            action = PDFAction(params)
            result = await action.execute(backend)
            assert len(result) > 0
            assert result[:4] == b"%PDF"
        finally:
            await backend.close()

    async def test_pdf_landscape(self):
        manager = BackendManager()
        backend = manager.select()
        try:
            await backend.launch(BrowserOptions())
            params = PDFParams(
                url="https://example.com",
                paper="a4",
                landscape=True,
                wait=WaitStrategy(strategy="load"),
            )
            action = PDFAction(params)
            result = await action.execute(backend)
            assert len(result) > 0
            assert result[:4] == b"%PDF"
        finally:
            await backend.close()
