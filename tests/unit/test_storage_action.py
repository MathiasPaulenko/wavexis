"""Unit tests for StorageAction."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from browsix.actions.storage import StorageAction
from browsix.backend.base import AbstractBackend
from browsix.config import StorageParams


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
        backend.indexeddb_list = AsyncMock(return_value=[{"name": "db1"}])
        backend.indexeddb_get_data = AsyncMock(return_value=[{"key": "1"}])
        backend.indexeddb_clear = AsyncMock()
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
        params = StorageParams(
            url="https://example.com", action="set", key="k", value="v"
        )
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

    async def test_unknown_action_raises(self) -> None:
        """Test that unknown action raises raises an appropriate error."""
        backend = self._make_backend()
        params = StorageParams(url="https://example.com", action="unknown")
        with pytest.raises(ValueError, match="Unknown storage action"):
            await StorageAction(params).execute(backend)

    async def test_lifecycle(self) -> None:
        """Test the action lifecycle (launch, execute, close)."""
        backend = self._make_backend()
        params = StorageParams(url="https://example.com", action="list")
        await StorageAction(params).execute(backend)
        backend.launch.assert_called_once()
        backend.navigate.assert_called_once_with("https://example.com", params.wait)
        backend.close.assert_called_once()

    async def test_no_url_skips_navigate(self) -> None:
        """Test that navigation is skipped when no URL is provided."""
        backend = self._make_backend()
        params = StorageParams(action="list")
        await StorageAction(params).execute(backend)
        backend.navigate.assert_not_called()
        backend.launch.assert_called_once()
        backend.close.assert_called_once()
