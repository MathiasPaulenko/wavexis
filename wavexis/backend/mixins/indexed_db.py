"""IndexedDB mixin — IndexedDB database operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IndexedDBBackend(ABC):
    """IndexedDB operations."""

    @abstractmethod
    async def indexed_db_clear_object_store(
        self, security_origin: str, database_name: str, object_store_name: str
    ) -> None:
        """Clear all entries in an IndexedDB object store."""

    @abstractmethod
    async def indexed_db_delete_database(self, security_origin: str, database_name: str) -> None:
        """Delete an IndexedDB database."""

    @abstractmethod
    async def indexed_db_delete_object_store_entries(
        self,
        security_origin: str,
        database_name: str,
        object_store_name: str,
        key_range: dict[str, Any],
    ) -> None:
        """Delete entries in an IndexedDB object store."""

    @abstractmethod
    async def indexed_db_disable(self) -> None:
        """Disable the IndexedDB domain."""

    @abstractmethod
    async def indexed_db_enable(self) -> None:
        """Enable the IndexedDB domain."""

    @abstractmethod
    async def indexed_db_get_metadata(
        self, security_origin: str, database_name: str, object_store_name: str
    ) -> dict[str, Any]:
        """Get metadata for an IndexedDB object store."""

    @abstractmethod
    async def indexed_db_request_data(
        self,
        security_origin: str,
        database_name: str,
        object_store_name: str,
        index_name: str,
        skip_count: int = 0,
        page_size: int = 10,
        key_range: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Request data from an IndexedDB object store."""

    @abstractmethod
    async def indexed_db_request_database(
        self, security_origin: str, database_name: str
    ) -> dict[str, Any]:
        """Request an IndexedDB database with its object stores."""

    @abstractmethod
    async def indexed_db_request_database_names(self, security_origin: str) -> dict[str, Any]:
        """Request the names of all IndexedDB databases for an origin."""
