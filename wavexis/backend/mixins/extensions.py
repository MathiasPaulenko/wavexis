"""Extensions mixin — extension storage and actions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ExtensionsBackend(ABC):
    """Extension storage and action operations."""

    @abstractmethod
    async def extensions_clear_storage_items(self, id: str, storage_type: str) -> None:
        """Clear storage items for an extension."""

    @abstractmethod
    async def extensions_get_storage_items(self, id: str, storage_type: str) -> dict[str, Any]:
        """Get storage items for an extension."""

    @abstractmethod
    async def extensions_remove_storage_items(
        self, id: str, storage_type: str, keys: list[str]
    ) -> None:
        """Remove storage items from an extension."""

    @abstractmethod
    async def extensions_set_storage_items(
        self, id: str, storage_type: str, values: list[dict[str, Any]]
    ) -> None:
        """Set storage items for an extension."""

    @abstractmethod
    async def extensions_trigger_action(self, id: str, action: str) -> None:
        """Trigger an action on an extension."""
