"""CrashReportContext domain mixin for AbstractBackend."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any


class CrashReportContextBackend:
    """CrashReportContext domain for crash report entries."""

    @abstractmethod
    async def crash_report_context_get_entries(self) -> list[dict[str, Any]]:
        """Get crash report entries."""
