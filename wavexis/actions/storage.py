"""Storage action for DOM storage, Cache Storage, and IndexedDB operations."""

from __future__ import annotations

from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import StorageParams


class StorageAction(BaseAction[StorageParams, Any]):
    """Action for storage operations (DOM, Cache, IndexedDB)."""

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the storage action on the backend.

        Args:
            backend: An AbstractBackend instance.

        Returns:
            Result of the storage operation.
        """
        if self.params.url:
            await backend.navigate(self.params.url, self.params.wait)

        action = self.params.action

        if action == "get":
            if not self.params.key:
                raise ValueError("key is required for get action")
            return await backend.storage_get(
                self.params.key, self.params.storage_type
            )

        if action == "set":
            if not self.params.key or self.params.value is None:
                raise ValueError("key and value are required for set action")
            await backend.storage_set(
                self.params.key,
                self.params.value,
                self.params.storage_type,
            )
            return None

        if action == "clear":
            await backend.storage_clear(self.params.storage_type)
            return None

        if action == "list":
            return await backend.storage_list(self.params.storage_type)

        if action == "cache-list":
            return await backend.cache_storage_list()

        if action == "cache-entries":
            if not self.params.cache_name:
                raise ValueError("cache_name is required for cache-entries action")
            return await backend.cache_storage_entries(self.params.cache_name)

        if action == "cache-delete":
            if not self.params.cache_name:
                raise ValueError("cache_name is required for cache-delete action")
            await backend.cache_storage_delete(self.params.cache_name)
            return None

        if action == "indexeddb-list":
            return await backend.indexeddb_list()

        if action == "indexeddb-get":
            if not self.params.database or not self.params.store:
                raise ValueError(
                    "database and store are required for indexeddb-get action"
                )
            return await backend.indexeddb_get_data(
                self.params.database, self.params.store
            )

        if action == "indexeddb-clear":
            if not self.params.database or not self.params.store:
                raise ValueError(
                    "database and store are required for indexeddb-clear action"
                )
            await backend.indexeddb_clear(self.params.database, self.params.store)
            return None

        raise ValueError(f"Unknown storage action: {action}")
