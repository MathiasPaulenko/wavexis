"""Unit tests for SmartCardEmulationAction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.actions.smart_card_emulation import (
    SmartCardEmulationAction,
    SmartCardEmulationParams,
)


@pytest.mark.unit
class TestSmartCardEmulationAction:
    """Test suite for SmartCardEmulationAction."""

    def _make_backend(self) -> MagicMock:
        """Create a mock backend for testing.

        Returns:
            A MagicMock backend instance.
        """
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.close = AsyncMock()
        backend.smart_card_enable = AsyncMock()
        backend.smart_card_disable = AsyncMock()
        backend.smart_card_report_error = AsyncMock()
        backend.smart_card_report_plain_result = AsyncMock()
        backend.smart_card_report_connect_result = AsyncMock()
        backend.smart_card_report_data_result = AsyncMock()
        backend.smart_card_report_status_result = AsyncMock()
        backend.smart_card_report_begin_transaction_result = AsyncMock()
        backend.smart_card_report_establish_context_result = AsyncMock()
        backend.smart_card_report_release_context_result = AsyncMock()
        backend.smart_card_report_list_readers_result = AsyncMock()
        backend.smart_card_report_get_status_change_result = AsyncMock()
        return backend

    async def test_enable(self) -> None:
        """Test enable action."""
        backend = self._make_backend()
        params = SmartCardEmulationParams(action="enable")
        result = await SmartCardEmulationAction(params).execute(backend)
        assert result is None
        backend.smart_card_enable.assert_called_once()

    async def test_disable(self) -> None:
        """Test disable action."""
        backend = self._make_backend()
        params = SmartCardEmulationParams(action="disable")
        result = await SmartCardEmulationAction(params).execute(backend)
        assert result is None
        backend.smart_card_disable.assert_called_once()

    async def test_report_error(self) -> None:
        """Test report-error action."""
        backend = self._make_backend()
        params = SmartCardEmulationParams(
            action="report-error", request_id="req1", error="E_TIMEOUT"
        )
        await SmartCardEmulationAction(params).execute(backend)
        backend.smart_card_report_error.assert_called_once_with("req1", "E_TIMEOUT")

    async def test_report_error_missing_fields_raises(self) -> None:
        """Test that report-error without request_id raises."""
        backend = self._make_backend()
        params = SmartCardEmulationParams(action="report-error", error="E_FAIL")
        with pytest.raises(ValueError, match="request_id and error are required"):
            await SmartCardEmulationAction(params).execute(backend)

    async def test_report_plain(self) -> None:
        """Test report-plain action."""
        backend = self._make_backend()
        params = SmartCardEmulationParams(action="report-plain", request_id="req2", result_code=0)
        await SmartCardEmulationAction(params).execute(backend)
        backend.smart_card_report_plain_result.assert_called_once_with("req2", 0)

    async def test_report_connect(self) -> None:
        """Test report-connect action."""
        backend = self._make_backend()
        params = SmartCardEmulationParams(
            action="report-connect",
            request_id="req3",
            result_code=0,
            connection_id="conn1",
        )
        await SmartCardEmulationAction(params).execute(backend)
        backend.smart_card_report_connect_result.assert_called_once_with("req3", 0, "conn1")

    async def test_report_data(self) -> None:
        """Test report-data action."""
        backend = self._make_backend()
        params = SmartCardEmulationParams(
            action="report-data",
            request_id="req4",
            result_code=0,
            data="deadbeef",
        )
        await SmartCardEmulationAction(params).execute(backend)
        backend.smart_card_report_data_result.assert_called_once_with("req4", 0, "deadbeef")

    async def test_report_status(self) -> None:
        """Test report-status action."""
        backend = self._make_backend()
        params = SmartCardEmulationParams(action="report-status", request_id="req5", status="ready")
        await SmartCardEmulationAction(params).execute(backend)
        backend.smart_card_report_status_result.assert_called_once_with("req5", "ready")

    async def test_report_begin_transaction(self) -> None:
        """Test report-begin-transaction action."""
        backend = self._make_backend()
        params = SmartCardEmulationParams(
            action="report-begin-transaction", request_id="req6", result_code=0
        )
        await SmartCardEmulationAction(params).execute(backend)
        backend.smart_card_report_begin_transaction_result.assert_called_once_with("req6", 0)

    async def test_report_establish_context(self) -> None:
        """Test report-establish-context action."""
        backend = self._make_backend()
        params = SmartCardEmulationParams(
            action="report-establish-context",
            request_id="req7",
            result_code=0,
            context_id="ctx1",
        )
        await SmartCardEmulationAction(params).execute(backend)
        backend.smart_card_report_establish_context_result.assert_called_once_with(
            "req7", 0, "ctx1"
        )

    async def test_report_release_context(self) -> None:
        """Test report-release-context action."""
        backend = self._make_backend()
        params = SmartCardEmulationParams(
            action="report-release-context", request_id="req8", result_code=0
        )
        await SmartCardEmulationAction(params).execute(backend)
        backend.smart_card_report_release_context_result.assert_called_once_with("req8", 0)

    async def test_report_list_readers(self) -> None:
        """Test report-list-readers action."""
        backend = self._make_backend()
        readers = [{"name": "Reader 1", "id": "r1"}]
        params = SmartCardEmulationParams(
            action="report-list-readers",
            request_id="req9",
            result_code=0,
            readers=readers,
        )
        await SmartCardEmulationAction(params).execute(backend)
        backend.smart_card_report_list_readers_result.assert_called_once_with("req9", 0, readers)

    async def test_report_get_status_change(self) -> None:
        """Test report-get-status-change action."""
        backend = self._make_backend()
        readers = [{"name": "Reader 1", "state": "empty"}]
        params = SmartCardEmulationParams(
            action="report-get-status-change",
            request_id="req10",
            result_code=0,
            readers=readers,
        )
        await SmartCardEmulationAction(params).execute(backend)
        backend.smart_card_report_get_status_change_result.assert_called_once_with(
            "req10", 0, readers
        )

    async def test_unknown_action_raises(self) -> None:
        """Test that unknown action raises ValueError."""
        backend = self._make_backend()
        params = SmartCardEmulationParams(action="invalid")
        with pytest.raises(ValueError, match="Unknown SmartCardEmulation action"):
            await SmartCardEmulationAction(params).execute(backend)

    async def test_lifecycle(self) -> None:
        """Test the action lifecycle (navigate, execute, close)."""
        backend = self._make_backend()
        params = SmartCardEmulationParams(url="https://example.com", action="enable")
        await SmartCardEmulationAction(params).execute(backend)
        backend.navigate.assert_called_once()
        backend.smart_card_enable.assert_called_once()
