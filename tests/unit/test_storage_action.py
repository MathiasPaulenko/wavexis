"""Unit tests for StorageAction."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.actions.storage import StorageAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import StorageParams


@pytest.mark.unit
class TestStorageAction:
    """Test suite for storageaction."""

    def _make_backend(self) -> MagicMock:
        """Create a mock backend for testing.

        Returns:
            A MagicMock backend instance.
        """
        backend = MagicMock(spec=AbstractBackend)
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.storage_get = AsyncMock(return_value="test_value")
        backend.storage_set = AsyncMock()
        backend.storage_clear = AsyncMock()
        backend.storage_list = AsyncMock(return_value={"k1": "v1"})
        backend.cache_storage_list = AsyncMock(return_value=["cache1"])
        backend.cache_storage_entries = AsyncMock(return_value=[{"url": "https://example.com"}])
        backend.cache_storage_delete = AsyncMock()
        backend.cache_storage_delete_cache = AsyncMock()
        backend.cache_storage_delete_entry = AsyncMock()
        backend.cache_storage_request_cache_names = AsyncMock(
            return_value=[{"cacheId": "c1", "cacheName": "cache1"}]
        )
        backend.cache_storage_request_cached_response = AsyncMock(return_value={"body": "resp"})
        backend.cache_storage_request_entries = AsyncMock(
            return_value=[{"url": "https://example.com"}]
        )
        backend.indexeddb_list = AsyncMock(return_value=[{"name": "db1"}])
        backend.indexeddb_get_data = AsyncMock(return_value=[{"key": "1"}])
        backend.indexeddb_clear = AsyncMock()
        backend.storage_clear_data_for_storage_key = AsyncMock()
        backend.storage_delete_storage_bucket = AsyncMock()
        backend.storage_get_related_website_sets = AsyncMock(return_value=[{"set": "s1"}])
        backend.storage_get_shared_storage_metadata = AsyncMock(return_value={"length": 0})
        backend.storage_get_storage_key = AsyncMock(return_value="key1")
        backend.storage_get_storage_key_for_frame = AsyncMock(return_value="key1")
        backend.storage_reset_shared_storage_budget = AsyncMock()
        backend.storage_run_bounce_tracking_mitigations = AsyncMock()
        backend.storage_set_cookies = AsyncMock()
        backend.storage_set_interest_group_auction_tracking = AsyncMock()
        backend.storage_set_interest_group_tracking = AsyncMock()
        backend.storage_set_protected_audience_k_anonymity = AsyncMock()
        backend.storage_set_shared_storage_tracking = AsyncMock()
        backend.storage_set_storage_bucket_tracking = AsyncMock()
        backend.storage_track_cache_storage_for_origin = AsyncMock()
        backend.storage_track_cache_storage_for_storage_key = AsyncMock()
        backend.storage_track_indexed_db_for_origin = AsyncMock()
        backend.storage_track_indexed_db_for_storage_key = AsyncMock()
        backend.storage_untrack_cache_storage_for_origin = AsyncMock()
        backend.storage_untrack_cache_storage_for_storage_key = AsyncMock()
        backend.storage_untrack_indexed_db_for_origin = AsyncMock()
        backend.storage_untrack_indexed_db_for_storage_key = AsyncMock()
        return backend

    async def test_get_action(self) -> None:
        """Test get action."""
        backend = self._make_backend()
        params = StorageParams(url="https://example.com", action="get", key="test_key")
        result = await StorageAction(params).execute(backend)
        assert result == "test_value"
        backend.storage_get.assert_called_once_with("test_key", "local")

    async def test_set_action(self) -> None:
        """Test set action."""
        backend = self._make_backend()
        params = StorageParams(url="https://example.com", action="set", key="k", value="v")
        result = await StorageAction(params).execute(backend)
        assert result is None
        backend.storage_set.assert_called_once_with("k", "v", "local")

    async def test_clear_action(self) -> None:
        """Test clear action."""
        backend = self._make_backend()
        params = StorageParams(url="https://example.com", action="clear")
        result = await StorageAction(params).execute(backend)
        assert result is None
        backend.storage_clear.assert_called_once_with("local")

    async def test_list_action(self) -> None:
        """Test list action."""
        backend = self._make_backend()
        params = StorageParams(url="https://example.com", action="list")
        result = await StorageAction(params).execute(backend)
        assert result == {"k1": "v1"}
        backend.storage_list.assert_called_once_with("local")

    async def test_cache_list_action(self) -> None:
        """Test cache list action."""
        backend = self._make_backend()
        params = StorageParams(url="https://example.com", action="cache-list")
        result = await StorageAction(params).execute(backend)
        assert result == ["cache1"]
        backend.cache_storage_list.assert_called_once()

    async def test_cache_entries_action(self) -> None:
        """Test cache entries action."""
        backend = self._make_backend()
        params = StorageParams(
            url="https://example.com", action="cache-entries", cache_name="mycache"
        )
        result = await StorageAction(params).execute(backend)
        assert len(result) == 1
        backend.cache_storage_entries.assert_called_once_with("mycache")

    async def test_cache_delete_action(self) -> None:
        """Test cache delete action."""
        backend = self._make_backend()
        params = StorageParams(
            url="https://example.com", action="cache-delete", cache_name="mycache"
        )
        result = await StorageAction(params).execute(backend)
        assert result is None
        backend.cache_storage_delete.assert_called_once_with("mycache")

    async def test_indexeddb_list_action(self) -> None:
        """Test indexeddb list action."""
        backend = self._make_backend()
        params = StorageParams(url="https://example.com", action="indexeddb-list")
        result = await StorageAction(params).execute(backend)
        assert result == [{"name": "db1"}]
        backend.indexeddb_list.assert_called_once()

    async def test_indexeddb_get_action(self) -> None:
        """Test indexeddb get action."""
        backend = self._make_backend()
        params = StorageParams(
            url="https://example.com",
            action="indexeddb-get",
            database="mydb",
            store="mystore",
        )
        await StorageAction(params).execute(backend)
        backend.indexeddb_get_data.assert_called_once_with("mydb", "mystore")

    async def test_indexeddb_clear_action(self) -> None:
        """Test indexeddb clear action."""
        backend = self._make_backend()
        params = StorageParams(
            url="https://example.com",
            action="indexeddb-clear",
            database="mydb",
            store="mystore",
        )
        result = await StorageAction(params).execute(backend)
        assert result is None
        backend.indexeddb_clear.assert_called_once_with("mydb", "mystore")

    async def test_get_missing_key_raises(self) -> None:
        """Test that get missing key raises raises an appropriate error."""
        backend = self._make_backend()
        params = StorageParams(url="https://example.com", action="get")
        with pytest.raises(ValueError, match="key is required"):
            await StorageAction(params).execute(backend)

    async def test_set_missing_value_raises(self) -> None:
        """Test that set missing value raises raises an appropriate error."""
        backend = self._make_backend()
        params = StorageParams(url="https://example.com", action="set", key="k")
        with pytest.raises(ValueError, match="key and value are required"):
            await StorageAction(params).execute(backend)

    async def test_clear_data_for_storage_key(self) -> None:
        """Test clear-data-for-storage-key action."""
        backend = self._make_backend()
        params = StorageParams(action="clear-data-for-storage-key", storage_key="sk1")
        await StorageAction(params).execute(backend)
        backend.storage_clear_data_for_storage_key.assert_called_once_with("sk1", "all")

    async def test_delete_bucket(self) -> None:
        """Test delete-bucket action."""
        backend = self._make_backend()
        params = StorageParams(action="delete-bucket", storage_key="sk1", bucket_name="b1")
        await StorageAction(params).execute(backend)
        backend.storage_delete_storage_bucket.assert_called_once_with("sk1", "b1")

    async def test_related_website_sets(self) -> None:
        """Test related-website-sets action."""
        backend = self._make_backend()
        params = StorageParams(action="related-website-sets")
        result = await StorageAction(params).execute(backend)
        assert result == [{"set": "s1"}]
        backend.storage_get_related_website_sets.assert_called_once()

    async def test_shared_storage_metadata(self) -> None:
        """Test shared-storage-metadata action."""
        backend = self._make_backend()
        params = StorageParams(action="shared-storage-metadata", owner_origin="https://a.com")
        result = await StorageAction(params).execute(backend)
        assert result == {"length": 0}
        backend.storage_get_shared_storage_metadata.assert_called_once_with("https://a.com")

    async def test_get_storage_key(self) -> None:
        """Test get-storage-key action."""
        backend = self._make_backend()
        params = StorageParams(action="get-storage-key", frame_id="f1")
        result = await StorageAction(params).execute(backend)
        assert result == "key1"
        backend.storage_get_storage_key.assert_called_once_with("f1")

    async def test_get_storage_key_for_frame(self) -> None:
        """Test get-storage-key-for-frame action."""
        backend = self._make_backend()
        params = StorageParams(action="get-storage-key-for-frame", frame_id="f1")
        result = await StorageAction(params).execute(backend)
        assert result == "key1"
        backend.storage_get_storage_key_for_frame.assert_called_once_with("f1")

    async def test_reset_shared_storage_budget(self) -> None:
        """Test reset-shared-storage-budget action."""
        backend = self._make_backend()
        params = StorageParams(action="reset-shared-storage-budget", owner_origin="https://a.com")
        await StorageAction(params).execute(backend)
        backend.storage_reset_shared_storage_budget.assert_called_once_with("https://a.com")

    async def test_run_bounce_tracking(self) -> None:
        """Test run-bounce-tracking action."""
        backend = self._make_backend()
        params = StorageParams(action="run-bounce-tracking")
        await StorageAction(params).execute(backend)
        backend.storage_run_bounce_tracking_mitigations.assert_called_once()

    async def test_set_cookies(self) -> None:
        """Test set-cookies action."""
        backend = self._make_backend()
        params = StorageParams(action="set-cookies", cookies=[{"name": "c1"}])
        await StorageAction(params).execute(backend)
        backend.storage_set_cookies.assert_called_once_with([{"name": "c1"}])

    async def test_set_ig_auction_tracking(self) -> None:
        """Test set-ig-auction-tracking action."""
        backend = self._make_backend()
        params = StorageParams(action="set-ig-auction-tracking", enable=True, context_id=42)
        await StorageAction(params).execute(backend)
        backend.storage_set_interest_group_auction_tracking.assert_called_once_with(True, 42)

    async def test_set_ig_tracking(self) -> None:
        """Test set-ig-tracking action."""
        backend = self._make_backend()
        params = StorageParams(action="set-ig-tracking", enable=True)
        await StorageAction(params).execute(backend)
        backend.storage_set_interest_group_tracking.assert_called_once_with(True)

    async def test_set_protected_audience_k_anonymity(self) -> None:
        """Test set-protected-audience-k-anonymity action."""
        backend = self._make_backend()
        params = StorageParams(
            action="set-protected-audience-k-anonymity",
            storage_key="sk1",
            hashed_mac_key="hmk1",
        )
        await StorageAction(params).execute(backend)
        backend.storage_set_protected_audience_k_anonymity.assert_called_once_with("sk1", "hmk1")

    async def test_set_shared_storage_tracking(self) -> None:
        """Test set-shared-storage-tracking action."""
        backend = self._make_backend()
        params = StorageParams(action="set-shared-storage-tracking", enable=True)
        await StorageAction(params).execute(backend)
        backend.storage_set_shared_storage_tracking.assert_called_once_with(True)

    async def test_set_bucket_tracking(self) -> None:
        """Test set-bucket-tracking action."""
        backend = self._make_backend()
        params = StorageParams(
            action="set-bucket-tracking", storage_key="sk1", bucket_name="b1", enable=True
        )
        await StorageAction(params).execute(backend)
        backend.storage_set_storage_bucket_tracking.assert_called_once_with("sk1", "b1", True)

    async def test_track_cache_origin(self) -> None:
        """Test track-cache-origin action."""
        backend = self._make_backend()
        params = StorageParams(action="track-cache-origin", origin="https://a.com")
        await StorageAction(params).execute(backend)
        backend.storage_track_cache_storage_for_origin.assert_called_once_with("https://a.com")

    async def test_track_cache_key(self) -> None:
        """Test track-cache-key action."""
        backend = self._make_backend()
        params = StorageParams(action="track-cache-key", storage_key="sk1")
        await StorageAction(params).execute(backend)
        backend.storage_track_cache_storage_for_storage_key.assert_called_once_with("sk1")

    async def test_track_idb_origin(self) -> None:
        """Test track-idb-origin action."""
        backend = self._make_backend()
        params = StorageParams(action="track-idb-origin", origin="https://a.com")
        await StorageAction(params).execute(backend)
        backend.storage_track_indexed_db_for_origin.assert_called_once_with("https://a.com")

    async def test_track_idb_key(self) -> None:
        """Test track-idb-key action."""
        backend = self._make_backend()
        params = StorageParams(action="track-idb-key", storage_key="sk1")
        await StorageAction(params).execute(backend)
        backend.storage_track_indexed_db_for_storage_key.assert_called_once_with("sk1")

    async def test_untrack_cache_origin(self) -> None:
        """Test untrack-cache-origin action."""
        backend = self._make_backend()
        params = StorageParams(action="untrack-cache-origin", origin="https://a.com")
        await StorageAction(params).execute(backend)
        backend.storage_untrack_cache_storage_for_origin.assert_called_once_with("https://a.com")

    async def test_untrack_cache_key(self) -> None:
        """Test untrack-cache-key action."""
        backend = self._make_backend()
        params = StorageParams(action="untrack-cache-key", storage_key="sk1")
        await StorageAction(params).execute(backend)
        backend.storage_untrack_cache_storage_for_storage_key.assert_called_once_with("sk1")

    async def test_untrack_idb_origin(self) -> None:
        """Test untrack-idb-origin action."""
        backend = self._make_backend()
        params = StorageParams(action="untrack-idb-origin", origin="https://a.com")
        await StorageAction(params).execute(backend)
        backend.storage_untrack_indexed_db_for_origin.assert_called_once_with("https://a.com")

    async def test_untrack_idb_key(self) -> None:
        """Test untrack-idb-key action."""
        backend = self._make_backend()
        params = StorageParams(action="untrack-idb-key", storage_key="sk1")
        await StorageAction(params).execute(backend)
        backend.storage_untrack_indexed_db_for_storage_key.assert_called_once_with("sk1")

    async def test_unknown_action_raises(self) -> None:
        """Test that unknown action raises raises an appropriate error."""
        backend = self._make_backend()
        params = StorageParams(url="https://example.com", action="unknown")
        with pytest.raises(ValueError, match="Unknown storage action"):
            await StorageAction(params).execute(backend)

    async def test_cache_delete_cache(self) -> None:
        """Test cache-delete-cache action."""
        backend = self._make_backend()
        params = StorageParams(action="cache-delete-cache", cache_id="c1")
        await StorageAction(params).execute(backend)
        backend.cache_storage_delete_cache.assert_called_once_with("c1")

    async def test_cache_delete_cache_missing_id_raises(self) -> None:
        """Test that cache-delete-cache without cache_id raises."""
        backend = self._make_backend()
        params = StorageParams(action="cache-delete-cache")
        with pytest.raises(ValueError, match="cache_id is required for cache-delete-cache"):
            await StorageAction(params).execute(backend)

    async def test_cache_delete_entry(self) -> None:
        """Test cache-delete-entry action."""
        backend = self._make_backend()
        params = StorageParams(
            action="cache-delete-entry", cache_id="c1", request_url="https://x.com"
        )
        await StorageAction(params).execute(backend)
        backend.cache_storage_delete_entry.assert_called_once_with("c1", "https://x.com")

    async def test_cache_delete_entry_missing_fields_raises(self) -> None:
        """Test that cache-delete-entry without cache_id/request_url raises."""
        backend = self._make_backend()
        params = StorageParams(action="cache-delete-entry", cache_id="c1")
        with pytest.raises(ValueError, match="cache_id and request_url are required"):
            await StorageAction(params).execute(backend)

    async def test_cache_request_names(self) -> None:
        """Test cache-request-names action."""
        backend = self._make_backend()
        params = StorageParams(action="cache-request-names", origin="https://a.com")
        result = await StorageAction(params).execute(backend)
        assert result == [{"cacheId": "c1", "cacheName": "cache1"}]
        backend.cache_storage_request_cache_names.assert_called_once_with("https://a.com")

    async def test_cache_cached_response(self) -> None:
        """Test cache-cached-response action."""
        backend = self._make_backend()
        params = StorageParams(
            action="cache-cached-response", cache_id="c1", request_url="https://x.com"
        )
        result = await StorageAction(params).execute(backend)
        assert result == {"body": "resp"}
        backend.cache_storage_request_cached_response.assert_called_once_with(
            "c1", "https://x.com", None
        )

    async def test_cache_cached_response_missing_fields_raises(self) -> None:
        """Test that cache-cached-response without cache_id/request_url raises."""
        backend = self._make_backend()
        params = StorageParams(action="cache-cached-response", cache_id="c1")
        with pytest.raises(ValueError, match="cache_id and request_url are required"):
            await StorageAction(params).execute(backend)

    async def test_cache_request_entries(self) -> None:
        """Test cache-request-entries action."""
        backend = self._make_backend()
        params = StorageParams(
            action="cache-request-entries", cache_id="c1", skip_count=5, page_size=50
        )
        result = await StorageAction(params).execute(backend)
        assert result == [{"url": "https://example.com"}]
        backend.cache_storage_request_entries.assert_called_once_with("c1", 5, 50)

    async def test_cache_request_entries_missing_id_raises(self) -> None:
        """Test that cache-request-entries without cache_id raises."""
        backend = self._make_backend()
        params = StorageParams(action="cache-request-entries")
        with pytest.raises(ValueError, match="cache_id is required for cache-request-entries"):
            await StorageAction(params).execute(backend)

    async def test_lifecycle(self) -> None:
        """Test the action lifecycle (navigate, execute)."""
        backend = self._make_backend()
        params = StorageParams(url="https://example.com", action="list")
        await StorageAction(params).execute(backend)
        backend.navigate.assert_called_once_with("https://example.com", params.wait)
        backend.storage_list.assert_called_once()

    async def test_no_url_skips_navigate(self) -> None:
        """Test that navigation is skipped when no URL is provided."""
        backend = self._make_backend()
        params = StorageParams(action="list")
        await StorageAction(params).execute(backend)
        backend.navigate.assert_not_called()
        backend.storage_list.assert_called_once()
