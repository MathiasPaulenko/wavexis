"""IO mixin — IO operations for blob handling."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IOBackend(ABC):
    """IO operations for reading blobs and resolving handles."""

    @abstractmethod
    async def io_read(
        self, handle: str, offset: int = 0, size: int | None = None
    ) -> dict[str, Any]:
        """Read data from a blob handle."""

    @abstractmethod
    async def io_resolve_blob(self, object_id: str) -> str:
        """Resolve a blob object ID to a UUID handle."""
