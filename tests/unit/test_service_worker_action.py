"""Unit tests for ServiceWorkerAction."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.actions.service_worker import ServiceWorkerAction, ServiceWorkerParams
from wavexis.backend.base import AbstractBackend


@pytest.mark.unit
class TestServiceWorkerAction:
    """Test suite for serviceworkeraction."""

    def _make_backend(self) -> MagicMock:
        """Create a mock backend for testing.

        Returns:
            A MagicMock backend instance.
        """
        backend = MagicMock(spec=AbstractBackend)
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.sw_list = AsyncMock(return_value=[{"id": "1", "url": "sw.js"}])
        backend.sw_unregister = AsyncMock()
        backend.sw_update = AsyncMock()
        backend.sw_enable = AsyncMock()
        backend.sw_disable = AsyncMock()
        backend.sw_deliver_push_message = AsyncMock()
        backend.sw_dispatch_sync_event = AsyncMock()
        backend.sw_get_messages = AsyncMock(return_value=[{"message": "hi"}])
        backend.sw_inspect_worker = AsyncMock()
        backend.sw_skip_waiting = AsyncMock()
        backend.sw_start_worker = AsyncMock()
        backend.sw_stop_worker = AsyncMock()
        return backend

    async def test_list_action(self) -> None:
        """Test list action."""
        backend = self._make_backend()
        params = ServiceWorkerParams(url="https://example.com", action="list")
        result = await ServiceWorkerAction(params).execute(backend)
        assert result == [{"id": "1", "url": "sw.js"}]
        backend.sw_list.assert_called_once()

    async def test_unregister_action(self) -> None:
        """Test unregister action."""
        backend = self._make_backend()
        params = ServiceWorkerParams(
            url="https://example.com", action="unregister", registration_id="reg1"
        )
        result = await ServiceWorkerAction(params).execute(backend)
        assert result is None
        backend.sw_unregister.assert_called_once_with("reg1")

    async def test_update_action(self) -> None:
        """Test update action."""
        backend = self._make_backend()
        params = ServiceWorkerParams(
            url="https://example.com", action="update", registration_id="reg1"
        )
        result = await ServiceWorkerAction(params).execute(backend)
        assert result is None
        backend.sw_update.assert_called_once_with("reg1")

    async def test_unregister_missing_id_raises(self) -> None:
        """Test that unregister missing id raises raises an appropriate error."""
        backend = self._make_backend()
        params = ServiceWorkerParams(url="https://example.com", action="unregister")
        with pytest.raises(ValueError, match="registration_id is required"):
            await ServiceWorkerAction(params).execute(backend)

    async def test_update_missing_id_raises(self) -> None:
        """Test that update missing id raises raises an appropriate error."""
        backend = self._make_backend()
        params = ServiceWorkerParams(url="https://example.com", action="update")
        with pytest.raises(ValueError, match="registration_id is required"):
            await ServiceWorkerAction(params).execute(backend)

    async def test_enable(self) -> None:
        """Test enable action."""
        backend = self._make_backend()
        params = ServiceWorkerParams(action="enable")
        await ServiceWorkerAction(params).execute(backend)
        backend.sw_enable.assert_called_once()

    async def test_disable(self) -> None:
        """Test disable action."""
        backend = self._make_backend()
        params = ServiceWorkerParams(action="disable")
        await ServiceWorkerAction(params).execute(backend)
        backend.sw_disable.assert_called_once()

    async def test_deliver_push(self) -> None:
        """Test deliver-push action."""
        backend = self._make_backend()
        params = ServiceWorkerParams(
            action="deliver-push",
            origin="https://example.com",
            registration_id="reg1",
            data="payload",
        )
        await ServiceWorkerAction(params).execute(backend)
        backend.sw_deliver_push_message.assert_called_once_with(
            "https://example.com", "reg1", "payload"
        )

    async def test_deliver_push_missing_fields_raises(self) -> None:
        """Test that deliver-push without origin raises."""
        backend = self._make_backend()
        params = ServiceWorkerParams(action="deliver-push", registration_id="reg1")
        with pytest.raises(ValueError, match="origin and registration_id are required"):
            await ServiceWorkerAction(params).execute(backend)

    async def test_dispatch_sync(self) -> None:
        """Test dispatch-sync action."""
        backend = self._make_backend()
        params = ServiceWorkerParams(
            action="dispatch-sync",
            origin="https://example.com",
            registration_id="reg1",
            tag="sync-tag",
            last_chance=True,
        )
        await ServiceWorkerAction(params).execute(backend)
        backend.sw_dispatch_sync_event.assert_called_once_with(
            "https://example.com", "reg1", "sync-tag", True
        )

    async def test_get_messages(self) -> None:
        """Test get-messages action."""
        backend = self._make_backend()
        params = ServiceWorkerParams(action="get-messages", worker_id="w1")
        result = await ServiceWorkerAction(params).execute(backend)
        assert result == [{"message": "hi"}]
        backend.sw_get_messages.assert_called_once_with("w1")

    async def test_get_messages_missing_worker_id_raises(self) -> None:
        """Test that get-messages without worker_id raises."""
        backend = self._make_backend()
        params = ServiceWorkerParams(action="get-messages")
        with pytest.raises(ValueError, match="worker_id is required"):
            await ServiceWorkerAction(params).execute(backend)

    async def test_inspect(self) -> None:
        """Test inspect action."""
        backend = self._make_backend()
        params = ServiceWorkerParams(action="inspect", worker_id="w1")
        await ServiceWorkerAction(params).execute(backend)
        backend.sw_inspect_worker.assert_called_once_with("w1")

    async def test_skip_waiting(self) -> None:
        """Test skip-waiting action."""
        backend = self._make_backend()
        params = ServiceWorkerParams(action="skip-waiting", scope_url="/")
        await ServiceWorkerAction(params).execute(backend)
        backend.sw_skip_waiting.assert_called_once_with("/")

    async def test_start_worker(self) -> None:
        """Test start-worker action."""
        backend = self._make_backend()
        params = ServiceWorkerParams(action="start-worker", scope_url="/")
        await ServiceWorkerAction(params).execute(backend)
        backend.sw_start_worker.assert_called_once_with("/")

    async def test_stop_worker(self) -> None:
        """Test stop-worker action."""
        backend = self._make_backend()
        params = ServiceWorkerParams(action="stop-worker", worker_id="w1")
        await ServiceWorkerAction(params).execute(backend)
        backend.sw_stop_worker.assert_called_once_with("w1")

    async def test_unknown_action_raises(self) -> None:
        """Test that unknown action raises raises an appropriate error."""
        backend = self._make_backend()
        params = ServiceWorkerParams(url="https://example.com", action="unknown")
        with pytest.raises(ValueError, match="Unknown service worker action"):
            await ServiceWorkerAction(params).execute(backend)

    async def test_lifecycle(self) -> None:
        """Test the action lifecycle (navigate, execute, close)."""
        backend = self._make_backend()
        params = ServiceWorkerParams(url="https://example.com", action="list")
        await ServiceWorkerAction(params).execute(backend)
        backend.navigate.assert_called_once()
        backend.sw_list.assert_called_once()
