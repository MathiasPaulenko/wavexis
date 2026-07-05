"""Unit tests for ServiceWorkerAction."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from browsix.actions.service_worker import ServiceWorkerAction, ServiceWorkerParams
from browsix.backend.base import AbstractBackend


@pytest.mark.unit
class TestServiceWorkerAction:
    def _make_backend(self) -> MagicMock:
        backend = MagicMock(spec=AbstractBackend)
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.sw_list = AsyncMock(return_value=[{"id": "1", "url": "sw.js"}])
        backend.sw_unregister = AsyncMock()
        backend.sw_update = AsyncMock()
        return backend

    async def test_list_action(self) -> None:
        backend = self._make_backend()
        params = ServiceWorkerParams(url="https://example.com", action="list")
        result = await ServiceWorkerAction(params).execute(backend)
        assert result == [{"id": "1", "url": "sw.js"}]
        backend.sw_list.assert_called_once()

    async def test_unregister_action(self) -> None:
        backend = self._make_backend()
        params = ServiceWorkerParams(
            url="https://example.com", action="unregister", registration_id="reg1"
        )
        result = await ServiceWorkerAction(params).execute(backend)
        assert result is None
        backend.sw_unregister.assert_called_once_with("reg1")

    async def test_update_action(self) -> None:
        backend = self._make_backend()
        params = ServiceWorkerParams(
            url="https://example.com", action="update", registration_id="reg1"
        )
        result = await ServiceWorkerAction(params).execute(backend)
        assert result is None
        backend.sw_update.assert_called_once_with("reg1")

    async def test_unregister_missing_id_raises(self) -> None:
        backend = self._make_backend()
        params = ServiceWorkerParams(url="https://example.com", action="unregister")
        with pytest.raises(ValueError, match="registration_id is required"):
            await ServiceWorkerAction(params).execute(backend)

    async def test_update_missing_id_raises(self) -> None:
        backend = self._make_backend()
        params = ServiceWorkerParams(url="https://example.com", action="update")
        with pytest.raises(ValueError, match="registration_id is required"):
            await ServiceWorkerAction(params).execute(backend)

    async def test_unknown_action_raises(self) -> None:
        backend = self._make_backend()
        params = ServiceWorkerParams(url="https://example.com", action="unknown")
        with pytest.raises(ValueError, match="Unknown service worker action"):
            await ServiceWorkerAction(params).execute(backend)

    async def test_lifecycle(self) -> None:
        backend = self._make_backend()
        params = ServiceWorkerParams(url="https://example.com", action="list")
        await ServiceWorkerAction(params).execute(backend)
        backend.launch.assert_called_once()
        backend.navigate.assert_called_once()
        backend.close.assert_called_once()
