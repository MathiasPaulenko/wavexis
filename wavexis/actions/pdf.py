"""PDF action for generating page PDFs."""

from __future__ import annotations

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import PDFParams


class PDFAction(BaseAction[PDFParams, bytes]):
    """Action for generating a PDF of a web page.

    Navigates to the URL in params, optionally executes JS, and generates
    a PDF.
    """

    async def execute(self, backend: AbstractBackend) -> bytes:
        """Execute the PDF action.

        Args:
            backend: The browser backend to use.

        Returns:
            PDF bytes.
        """
        params = self.params
        await backend.navigate(params.url, params.wait)

        if params.js:
            await backend.eval(params.js, await_promise=True)

        return await backend.pdf(params)
