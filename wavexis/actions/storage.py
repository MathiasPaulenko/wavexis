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
            return await backend.storage_get(self.params.key, self.params.storage_type)

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

        if action == "cache-delete-cache":
            if not self.params.cache_id:
                raise ValueError("cache_id is required for cache-delete-cache action")
            await backend.cache_storage_delete_cache(self.params.cache_id)
            return None

        if action == "cache-delete-entry":
            if not self.params.cache_id or not self.params.request_url:
                raise ValueError("cache_id and request_url are required for cache-delete-entry")
            await backend.cache_storage_delete_entry(self.params.cache_id, self.params.request_url)
            return None

        if action == "cache-request-names":
            return await backend.cache_storage_request_cache_names(self.params.origin)

        if action == "cache-cached-response":
            if not self.params.cache_id or not self.params.request_url:
                raise ValueError("cache_id and request_url are required for cache-cached-response")
            return await backend.cache_storage_request_cached_response(
                self.params.cache_id,
                self.params.request_url,
                self.params.request_headers,
            )

        if action == "cache-request-entries":
            if not self.params.cache_id:
                raise ValueError("cache_id is required for cache-request-entries")
            return await backend.cache_storage_request_entries(
                self.params.cache_id,
                self.params.skip_count,
                self.params.page_size,
            )

        if action == "indexeddb-list":
            return await backend.indexeddb_list()

        if action == "indexeddb-get":
            if not self.params.database or not self.params.store:
                raise ValueError("database and store are required for indexeddb-get action")
            return await backend.indexeddb_get_data(self.params.database, self.params.store)

        if action == "indexeddb-clear":
            if not self.params.database or not self.params.store:
                raise ValueError("database and store are required for indexeddb-clear action")
            await backend.indexeddb_clear(self.params.database, self.params.store)
            return None

        if action == "clear-data-for-storage-key":
            if not self.params.storage_key:
                raise ValueError("storage_key is required for clear-data-for-storage-key")
            await backend.storage_clear_data_for_storage_key(
                self.params.storage_key, self.params.storage_types
            )
            return None

        if action == "delete-bucket":
            if not self.params.storage_key or not self.params.bucket_name:
                raise ValueError("storage_key and bucket_name are required for delete-bucket")
            await backend.storage_delete_storage_bucket(
                self.params.storage_key, self.params.bucket_name
            )
            return None

        if action == "related-website-sets":
            return await backend.storage_get_related_website_sets()

        if action == "shared-storage-metadata":
            if not self.params.owner_origin:
                raise ValueError("owner_origin is required for shared-storage-metadata")
            return await backend.storage_get_shared_storage_metadata(self.params.owner_origin)

        if action == "get-storage-key":
            if not self.params.frame_id:
                raise ValueError("frame_id is required for get-storage-key")
            return await backend.storage_get_storage_key(self.params.frame_id)

        if action == "get-storage-key-for-frame":
            if not self.params.frame_id:
                raise ValueError("frame_id is required for get-storage-key-for-frame")
            return await backend.storage_get_storage_key_for_frame(self.params.frame_id)

        if action == "reset-shared-storage-budget":
            if not self.params.owner_origin:
                raise ValueError("owner_origin is required for reset-shared-storage-budget")
            await backend.storage_reset_shared_storage_budget(self.params.owner_origin)
            return None

        if action == "run-bounce-tracking":
            await backend.storage_run_bounce_tracking_mitigations()
            return None

        if action == "set-cookies":
            if self.params.cookies is None:
                raise ValueError("cookies is required for set-cookies")
            await backend.storage_set_cookies(self.params.cookies)
            return None

        if action == "set-ig-auction-tracking":
            await backend.storage_set_interest_group_auction_tracking(
                self.params.enable, self.params.context_id
            )
            return None

        if action == "set-ig-tracking":
            await backend.storage_set_interest_group_tracking(self.params.enable)
            return None

        if action == "set-protected-audience-k-anonymity":
            if not self.params.storage_key or not self.params.hashed_mac_key:
                raise ValueError(
                    "storage_key and hashed_mac_key are required "
                    "for set-protected-audience-k-anonymity"
                )
            await backend.storage_set_protected_audience_k_anonymity(
                self.params.storage_key, self.params.hashed_mac_key
            )
            return None

        if action == "set-shared-storage-tracking":
            await backend.storage_set_shared_storage_tracking(self.params.enable)
            return None

        if action == "set-bucket-tracking":
            if not self.params.storage_key or not self.params.bucket_name:
                raise ValueError("storage_key and bucket_name are required for set-bucket-tracking")
            await backend.storage_set_storage_bucket_tracking(
                self.params.storage_key,
                self.params.bucket_name,
                self.params.enable,
            )
            return None

        if action == "track-cache-origin":
            if not self.params.origin:
                raise ValueError("origin is required for track-cache-origin")
            await backend.storage_track_cache_storage_for_origin(self.params.origin)
            return None

        if action == "track-cache-key":
            if not self.params.storage_key:
                raise ValueError("storage_key is required for track-cache-key")
            await backend.storage_track_cache_storage_for_storage_key(self.params.storage_key)
            return None

        if action == "track-idb-origin":
            if not self.params.origin:
                raise ValueError("origin is required for track-idb-origin")
            await backend.storage_track_indexed_db_for_origin(self.params.origin)
            return None

        if action == "track-idb-key":
            if not self.params.storage_key:
                raise ValueError("storage_key is required for track-idb-key")
            await backend.storage_track_indexed_db_for_storage_key(self.params.storage_key)
            return None

        if action == "untrack-cache-origin":
            if not self.params.origin:
                raise ValueError("origin is required for untrack-cache-origin")
            await backend.storage_untrack_cache_storage_for_origin(self.params.origin)
            return None

        if action == "untrack-cache-key":
            if not self.params.storage_key:
                raise ValueError("storage_key is required for untrack-cache-key")
            await backend.storage_untrack_cache_storage_for_storage_key(self.params.storage_key)
            return None

        if action == "untrack-idb-origin":
            if not self.params.origin:
                raise ValueError("origin is required for untrack-idb-origin")
            await backend.storage_untrack_indexed_db_for_origin(self.params.origin)
            return None

        if action == "untrack-idb-key":
            if not self.params.storage_key:
                raise ValueError("storage_key is required for untrack-idb-key")
            await backend.storage_untrack_indexed_db_for_storage_key(self.params.storage_key)
            return None

        raise ValueError(f"Unknown storage action: {action}")
