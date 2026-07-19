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
    async def storage_set(self, key: str, value: str, storage_type: str = "local") -> None:
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
    async def cache_storage_delete_cache(self, cache_id: str) -> None:
        """Delete a cache by its CDP cache ID.

        Args:
            cache_id: The CDP cache identifier.
        """

    @abstractmethod
    async def cache_storage_delete_entry(self, cache_id: str, request: str) -> None:
        """Delete a specific entry from a cache.

        Args:
            cache_id: The CDP cache identifier.
            request: The request URL of the entry to delete.
        """

    @abstractmethod
    async def cache_storage_request_cache_names(
        self, security_origin: str | None = None
    ) -> list[dict[str, Any]]:
        """Request cache names for a security origin.

        Args:
            security_origin: Optional security origin. If None, uses the current page.

        Returns:
            List of cache info dicts with cacheId and cacheName.
        """

    @abstractmethod
    async def cache_storage_request_cached_response(
        self, cache_id: str, request_url: str, request_headers: list[dict[str, str]] | None = None
    ) -> dict[str, Any]:
        """Request a cached response for a specific request.

        Args:
            cache_id: The CDP cache identifier.
            request_url: The request URL.
            request_headers: Optional list of request header dicts.

        Returns:
            The cached response dict.
        """

    @abstractmethod
    async def cache_storage_request_entries(
        self, cache_id: str, skip_count: int = 0, page_size: int = 100
    ) -> list[dict[str, Any]]:
        """Request entries from a cache.

        Args:
            cache_id: The CDP cache identifier.
            skip_count: Number of entries to skip.
            page_size: Maximum number of entries to return.

        Returns:
            List of cache entry dicts.
        """

    @abstractmethod
    async def indexeddb_list(self) -> list[dict[str, Any]]:
        """List all IndexedDB databases.

        Returns:
            List of database info dicts (name, version, etc.).
        """

    @abstractmethod
    async def indexeddb_get_data(self, database: str, store: str, key: str = "") -> Any:
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

    @abstractmethod
    async def storage_clear_data_for_origin(self, origin: str, storage_types: str = "all") -> None:
        """Clear storage data for a given origin."""

    @abstractmethod
    async def storage_get_usage_and_quota(self, origin: str) -> dict[str, Any]:
        """Get usage and quota for a given origin."""

    @abstractmethod
    async def storage_get_trust_tokens(self) -> list[dict[str, Any]]:
        """Get all trust tokens for the current origin."""

    @abstractmethod
    async def storage_clear_trust_tokens(self, origin: str) -> None:
        """Clear trust tokens for a given origin."""

    @abstractmethod
    async def storage_get_shared_storage_entries(self, owner_origin: str) -> list[dict[str, Any]]:
        """Get shared storage entries for an owner origin."""

    @abstractmethod
    async def storage_set_shared_storage_entry(
        self, owner_origin: str, key: str, value: str
    ) -> None:
        """Set a shared storage entry."""

    @abstractmethod
    async def storage_delete_shared_storage_entry(self, owner_origin: str, key: str) -> None:
        """Delete a shared storage entry."""

    @abstractmethod
    async def storage_clear_shared_storage_entries(self, owner_origin: str) -> None:
        """Clear all shared storage entries for an owner origin."""

    @abstractmethod
    async def storage_get_interest_group_details(
        self, owner_origin: str, name: str
    ) -> dict[str, Any]:
        """Get interest group details."""

    @abstractmethod
    async def storage_override_quota_for_origin(
        self, origin: str, quota_size: float | None = None
    ) -> None:
        """Override quota for a given origin. Pass None to reset."""

    @abstractmethod
    async def storage_clear_data_for_storage_key(
        self, storage_key: str, storage_types: str = "all"
    ) -> None:
        """Clear storage data for a given storage key.

        Args:
            storage_key: The storage key.
            storage_types: Comma-separated storage types to clear.
        """

    @abstractmethod
    async def storage_delete_storage_bucket(self, storage_key: str, bucket_name: str) -> None:
        """Delete a storage bucket.

        Args:
            storage_key: The storage key.
            bucket_name: The bucket name.
        """

    @abstractmethod
    async def storage_get_related_website_sets(self) -> list[dict[str, Any]]:
        """Get related website sets.

        Returns:
            List of related website set dicts.
        """

    @abstractmethod
    async def storage_get_shared_storage_metadata(self, owner_origin: str) -> dict[str, Any]:
        """Get shared storage metadata for an owner origin.

        Args:
            owner_origin: The owner origin.

        Returns:
            Metadata dict.
        """

    @abstractmethod
    async def storage_get_storage_key(self, frame_id: str) -> str:
        """Get storage key for a frame.

        Args:
            frame_id: The frame ID.

        Returns:
            The storage key string.
        """

    @abstractmethod
    async def storage_get_storage_key_for_frame(self, frame_id: str) -> str:
        """Get storage key for a frame (alternative endpoint).

        Args:
            frame_id: The frame ID.

        Returns:
            The storage key string.
        """

    @abstractmethod
    async def storage_reset_shared_storage_budget(self, owner_origin: str) -> None:
        """Reset shared storage budget for an owner origin.

        Args:
            owner_origin: The owner origin.
        """

    @abstractmethod
    async def storage_run_bounce_tracking_mitigations(self) -> None:
        """Run bounce tracking mitigations."""

    @abstractmethod
    async def storage_set_cookies(self, cookies: list[dict[str, Any]]) -> None:
        """Set cookies.

        Args:
            cookies: List of cookie dicts.
        """

    @abstractmethod
    async def storage_set_interest_group_auction_tracking(
        self, enable: bool, context_id: int | None = None
    ) -> None:
        """Set interest group auction tracking.

        Args:
            enable: Whether to enable tracking.
            context_id: Optional auction context ID.
        """

    @abstractmethod
    async def storage_set_interest_group_tracking(self, enable: bool) -> None:
        """Set interest group tracking.

        Args:
            enable: Whether to enable tracking.
        """

    @abstractmethod
    async def storage_set_protected_audience_k_anonymity(
        self, storage_key: str, hashed_mac_key: str
    ) -> None:
        """Set protected audience k-anonymity.

        Args:
            storage_key: The storage key.
            hashed_mac_key: The hashed MAC key.
        """

    @abstractmethod
    async def storage_set_shared_storage_tracking(self, enable: bool) -> None:
        """Set shared storage tracking.

        Args:
            enable: Whether to enable tracking.
        """

    @abstractmethod
    async def storage_set_storage_bucket_tracking(
        self, storage_key: str, bucket_name: str, enable: bool
    ) -> None:
        """Set storage bucket tracking.

        Args:
            storage_key: The storage key.
            bucket_name: The bucket name.
            enable: Whether to enable tracking.
        """

    @abstractmethod
    async def storage_track_cache_storage_for_origin(self, origin: str) -> None:
        """Track cache storage for an origin.

        Args:
            origin: The origin to track.
        """

    @abstractmethod
    async def storage_track_cache_storage_for_storage_key(self, storage_key: str) -> None:
        """Track cache storage for a storage key.

        Args:
            storage_key: The storage key to track.
        """

    @abstractmethod
    async def storage_track_indexed_db_for_origin(self, origin: str) -> None:
        """Track IndexedDB for an origin.

        Args:
            origin: The origin to track.
        """

    @abstractmethod
    async def storage_track_indexed_db_for_storage_key(self, storage_key: str) -> None:
        """Track IndexedDB for a storage key.

        Args:
            storage_key: The storage key to track.
        """

    @abstractmethod
    async def storage_untrack_cache_storage_for_origin(self, origin: str) -> None:
        """Untrack cache storage for an origin.

        Args:
            origin: The origin to untrack.
        """

    @abstractmethod
    async def storage_untrack_cache_storage_for_storage_key(self, storage_key: str) -> None:
        """Untrack cache storage for a storage key.

        Args:
            storage_key: The storage key to untrack.
        """

    @abstractmethod
    async def storage_untrack_indexed_db_for_origin(self, origin: str) -> None:
        """Untrack IndexedDB for an origin.

        Args:
            origin: The origin to untrack.
        """

    @abstractmethod
    async def storage_untrack_indexed_db_for_storage_key(self, storage_key: str) -> None:
        """Untrack IndexedDB for a storage key.

        Args:
            storage_key: The storage key to untrack.
        """
