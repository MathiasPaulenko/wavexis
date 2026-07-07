"""Storage mixin — DOM storage, Cache Storage, IndexedDB."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class StorageBackend(ABC):
    """DOM storage, Cache Storage, and IndexedDB operations."""

    @abstractmethod
    async def storage_get(self, key: str, storage_type: str = "local") -> str:
        """Get a value from DOM storage (local or session).

        Args:
            key: The storage key to retrieve.
            storage_type: "local" or "session".

        Returns:
            The stored value as a string, or empty string if not found.
        """

    @abstractmethod
    async def storage_set(
        self, key: str, value: str, storage_type: str = "local"
    ) -> None:
        """Set a value in DOM storage (local or session).

        Args:
            key: The storage key.
            value: The value to store.
            storage_type: "local" or "session".
        """

    @abstractmethod
    async def storage_clear(self, storage_type: str = "local") -> None:
        """Clear all entries in DOM storage.

        Args:
            storage_type: "local" or "session".
        """

    @abstractmethod
    async def storage_list(self, storage_type: str = "local") -> dict[str, str]:
        """List all key-value pairs in DOM storage.

        Args:
            storage_type: "local" or "session".

        Returns:
            Dict mapping keys to values.
        """

    @abstractmethod
    async def cache_storage_list(self) -> list[str]:
        """List all Cache Storage cache names.

        Returns:
            List of cache names.
        """

    @abstractmethod
    async def cache_storage_entries(self, cache_name: str) -> list[dict[str, Any]]:
        """List entries in a Cache Storage cache.

        Args:
            cache_name: Name of the cache to inspect.

        Returns:
            List of cache entry dicts (url, status, etc.).
        """

    @abstractmethod
    async def cache_storage_delete(self, cache_name: str) -> None:
        """Delete a Cache Storage cache.

        Args:
            cache_name: Name of the cache to delete.
        """

    @abstractmethod
    async def indexeddb_list(self) -> list[dict[str, Any]]:
        """List all IndexedDB databases.

        Returns:
            List of database info dicts (name, version, etc.).
        """

    @abstractmethod
    async def indexeddb_get_data(
        self, database: str, store: str, key: str = ""
    ) -> Any:
        """Get data from an IndexedDB object store.

        Args:
            database: Database name.
            store: Object store name.
            key: Optional key to retrieve a specific entry. If empty, returns all.

        Returns:
            The stored data, or list of all entries if key is empty.
        """

    @abstractmethod
    async def indexeddb_clear(self, database: str, store: str) -> None:
        """Clear all entries in an IndexedDB object store.

        Args:
            database: Database name.
            store: Object store name.
        """
