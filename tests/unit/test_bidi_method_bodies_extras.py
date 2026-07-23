"""Generated unit tests for missing BiDiBackend methods used by actions/cli."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_mock_backend() -> tuple[Any, Any]:
    """Create a BiDiBackend with a mocked BiDiClient."""
    from wavexis.backend.bidi import BiDiBackend

    backend = BiDiBackend()
    backend._context = "ctx-123"

    mock_client = MagicMock()
    mock_client.cdp = MagicMock()
    mock_client.cdp.send_command = AsyncMock(return_value={})
    mock_client.cdp.on = MagicMock()
    mock_client.cdp.off = MagicMock()

    mock_client.browsing = MagicMock()
    mock_client.browsing.create_user_context = AsyncMock(
        return_value=MagicMock(user_context="uc-1")
    )

    mock_client.script = MagicMock()
    mock_client.script.evaluate = AsyncMock(return_value=MagicMock(value="result"))

    mock_client.close = AsyncMock()
    backend._client = mock_client
    return backend, mock_client


@pytest.mark.unit
class TestBiDiMethodBodiesExtras:
    """Auto-generated tests for BiDiBackend methods not covered elsewhere."""

    async def test_cache_storage_delete_cache(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.cache_storage_delete_cache("cache-1")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "CacheStorage.deleteCache"

    async def test_cache_storage_delete_entry(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.cache_storage_delete_entry("cache-1", "https://example.com/api")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "CacheStorage.deleteEntry"

    async def test_cache_storage_request_cache_names(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.cache_storage_request_cache_names("x", "https://example.com", {})
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "CacheStorage.requestCacheNames"

    async def test_cache_storage_request_cached_response(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.cache_storage_request_cached_response("cache-1", "x", [])
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "CacheStorage.requestCachedResponse"

    async def test_cache_storage_request_entries(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.cache_storage_request_entries("cache-1", 1, 1, "x")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "CacheStorage.requestEntries"

    async def test_cast_disable(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.cast_disable()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Cast.disable"

    async def test_cast_enable(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.cast_enable()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Cast.enable"

    async def test_cast_set_sink_to_use(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.cast_set_sink_to_use("Living Room")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Cast.setSinkToUse"

    async def test_cast_start_desktop_mirroring(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.cast_start_desktop_mirroring("Living Room")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Cast.startDesktopMirroring"

    async def test_cast_start_tab_mirroring(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.cast_start_tab_mirroring("Living Room")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Cast.startTabMirroring"

    async def test_cast_stop_casting(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.cast_stop_casting("Living Room")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Cast.stopCasting"

    async def test_new_user_context(self) -> None:
        backend, mock = _make_mock_backend()
        result = await backend.new_user_context()
        assert result == "uc-1"
        mock.browsing.create_user_context.assert_awaited_once()

    async def test_smart_card_disable(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.smart_card_disable()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "SmartCardEmulation.disable"

    async def test_smart_card_enable(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.smart_card_enable()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "SmartCardEmulation.enable"

    async def test_smart_card_report_begin_transaction_result(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.smart_card_report_begin_transaction_result("req-1", "0")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "SmartCardEmulation.reportBeginTransactionResult"

    async def test_smart_card_report_connect_result(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.smart_card_report_connect_result("req-1", "0", "x")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "SmartCardEmulation.reportConnectResult"

    async def test_smart_card_report_data_result(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.smart_card_report_data_result("req-1", "0", "payload")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "SmartCardEmulation.reportDataResult"

    async def test_smart_card_report_error(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.smart_card_report_error("req-1", "x")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "SmartCardEmulation.reportError"

    async def test_smart_card_report_establish_context_result(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.smart_card_report_establish_context_result("req-1", "0", 1)
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "SmartCardEmulation.reportEstablishContextResult"

    async def test_smart_card_report_get_status_change_result(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.smart_card_report_get_status_change_result("req-1", "0", ["reader-1"])
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "SmartCardEmulation.reportGetStatusChangeResult"

    async def test_smart_card_report_list_readers_result(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.smart_card_report_list_readers_result("req-1", "0", ["reader-1"])
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "SmartCardEmulation.reportListReadersResult"

    async def test_smart_card_report_plain_result(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.smart_card_report_plain_result("req-1", "0")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "SmartCardEmulation.reportPlainResult"

    async def test_smart_card_report_release_context_result(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.smart_card_report_release_context_result("req-1", "0")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "SmartCardEmulation.reportReleaseContextResult"

    async def test_smart_card_report_status_result(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.smart_card_report_status_result("req-1", "0")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "SmartCardEmulation.reportStatusResult"

    async def test_storage_clear_data_for_storage_key(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_clear_data_for_storage_key("https://example.com", "x")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.clearDataForStorageKey"

    async def test_storage_delete_storage_bucket(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_delete_storage_bucket("https://example.com", "bucket-1")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.deleteStorageBucket"

    async def test_storage_get_related_website_sets(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_get_related_website_sets()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.getRelatedWebsiteSets"

    async def test_storage_get_shared_storage_metadata(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_get_shared_storage_metadata("x")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.getSharedStorageMetadata"

    async def test_storage_get_storage_key(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_get_storage_key("x")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.getStorageKey"

    async def test_storage_get_storage_key_for_frame(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_get_storage_key_for_frame("x")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.getStorageKeyForFrame"

    async def test_storage_reset_shared_storage_budget(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_reset_shared_storage_budget("x")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.resetSharedStorageBudget"

    async def test_storage_run_bounce_tracking_mitigations(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_run_bounce_tracking_mitigations()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.runBounceTrackingMitigations"

    async def test_storage_set_cookies(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_set_cookies([{"name": "x", "value": "y"}])
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.setCookies"

    async def test_storage_set_interest_group_auction_tracking(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_set_interest_group_auction_tracking(True, 1)
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.setInterestGroupAuctionTracking"

    async def test_storage_set_interest_group_tracking(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_set_interest_group_tracking(True)
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.setInterestGroupTracking"

    async def test_storage_set_protected_audience_k_anonymity(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_set_protected_audience_k_anonymity("https://example.com", "x")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.setProtectedAudienceKAnonymity"

    async def test_storage_set_shared_storage_tracking(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_set_shared_storage_tracking(True)
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.setSharedStorageTracking"

    async def test_storage_set_storage_bucket_tracking(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_set_storage_bucket_tracking("https://example.com", "bucket-1", True)
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.setStorageBucketTracking"

    async def test_storage_track_cache_storage_for_origin(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_track_cache_storage_for_origin("https://example.com")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.trackCacheStorageForOrigin"

    async def test_storage_track_cache_storage_for_storage_key(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_track_cache_storage_for_storage_key("https://example.com")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.trackCacheStorageForStorageKey"

    async def test_storage_track_indexed_db_for_origin(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_track_indexed_db_for_origin("https://example.com")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.trackIndexedDBForOrigin"

    async def test_storage_track_indexed_db_for_storage_key(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_track_indexed_db_for_storage_key("https://example.com")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.trackIndexedDBForStorageKey"

    async def test_storage_untrack_cache_storage_for_origin(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_untrack_cache_storage_for_origin("https://example.com")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.untrackCacheStorageForOrigin"

    async def test_storage_untrack_cache_storage_for_storage_key(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_untrack_cache_storage_for_storage_key("https://example.com")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.untrackCacheStorageForStorageKey"

    async def test_storage_untrack_indexed_db_for_origin(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_untrack_indexed_db_for_origin("https://example.com")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.untrackIndexedDBForOrigin"

    async def test_storage_untrack_indexed_db_for_storage_key(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.storage_untrack_indexed_db_for_storage_key("https://example.com")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Storage.untrackIndexedDBForStorageKey"

    async def test_sw_deliver_push_message(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.sw_deliver_push_message("https://example.com", "reg-1", "payload")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "ServiceWorker.deliverPushMessage"

    async def test_sw_disable(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.sw_disable()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "ServiceWorker.disable"

    async def test_sw_dispatch_sync_event(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.sw_dispatch_sync_event("https://example.com", "reg-1", "sync-tag", True)
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "ServiceWorker.dispatchSyncEvent"

    async def test_sw_enable(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.sw_enable()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "ServiceWorker.enable"

    async def test_sw_get_messages(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.sw_get_messages("worker-1")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "ServiceWorker.getMessages"

    async def test_sw_inspect_worker(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.sw_inspect_worker("worker-1")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "ServiceWorker.inspectWorker"

    async def test_sw_skip_waiting(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.sw_skip_waiting("https://example.com")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "ServiceWorker.skipWaiting"

    async def test_sw_start_worker(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.sw_start_worker("https://example.com")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "ServiceWorker.startWorker"

    async def test_sw_stop_worker(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.sw_stop_worker("worker-1")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "ServiceWorker.stopWorker"

    async def test_system_info_get_feature_state(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.system_info_get_feature_state("default")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "SystemInfo.getFeatureState"

    async def test_system_info_get_info(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.system_info_get_info()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "SystemInfo.getInfo"

    async def test_system_info_get_process_info(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.system_info_get_process_info()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "SystemInfo.getProcessInfo"

    async def test_tethering_bind(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.tethering_bind(8080)
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Tethering.bind"

    async def test_tethering_unbind(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.tethering_unbind(8080)
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Tethering.unbind"

    async def test_tracing_end(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.tracing_end()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Tracing.end"

    async def test_tracing_get_categories(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.tracing_get_categories()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Tracing.getCategories"

    async def test_tracing_get_track_event_descriptor(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.tracing_get_track_event_descriptor("x")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Tracing.getTrackEventDescriptor"

    async def test_tracing_record_clock_sync_marker(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.tracing_record_clock_sync_marker("x")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Tracing.recordClockSyncMarker"

    async def test_tracing_request_memory_dump(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.tracing_request_memory_dump()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Tracing.requestMemoryDump"

    async def test_tracing_start(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.tracing_start("x", "x", "x")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "Tracing.start"

    async def test_web_mcp_disable(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.web_mcp_disable()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "WebMcp.disable"

    async def test_web_mcp_enable(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.web_mcp_enable()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "WebMcp.enable"

    async def test_webaudio_disable(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.webaudio_disable()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "WebAudio.disable"

    async def test_webaudio_enable(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.webaudio_enable()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "WebAudio.enable"

    async def test_webaudio_get_realtime_data(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.webaudio_get_realtime_data(1)
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "WebAudio.getRealtimeData"

    async def test_webauthn_clear_credentials(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.webauthn_clear_credentials("x")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "WebAuthn.clearCredentials"

    async def test_webauthn_disable(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.webauthn_disable()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "WebAuthn.disable"

    async def test_webauthn_enable(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.webauthn_enable()
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "WebAuthn.enable"

    async def test_webauthn_get_credential(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.webauthn_get_credential("x", "x")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "WebAuthn.getCredential"

    async def test_webauthn_remove_credential(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.webauthn_remove_credential("x", "x")
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "WebAuthn.removeCredential"

    async def test_webauthn_set_automatic_presence_simulation(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.webauthn_set_automatic_presence_simulation("x", True)
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "WebAuthn.setAutomaticPresenceSimulation"

    async def test_webauthn_set_credential_properties(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.webauthn_set_credential_properties("x", "x", True, True)
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "WebAuthn.setCredentialProperties"

    async def test_webauthn_set_response_override_bits(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.webauthn_set_response_override_bits("x", True, True, True)
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "WebAuthn.setResponseOverrideBits"

    async def test_webauthn_set_user_verified(self) -> None:
        backend, mock = _make_mock_backend()
        await backend.webauthn_set_user_verified("x", True)
        mock.cdp.send_command.assert_awaited()
        call_args = mock.cdp.send_command.call_args
        assert call_args[0][0] == "WebAuthn.setUserVerified"

