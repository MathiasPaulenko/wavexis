"""Unit tests for v2.4.x network inspection, tracing, axe, and events."""

from __future__ import annotations

import asyncio
import json
import pathlib
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.exceptions import WavexisError


def _make_cdp_backend() -> Any:
    """Create a CDPBackend with mocked session."""
    from wavexis.backend.cdp import CDPBackend

    backend = CDPBackend()
    backend._session = MagicMock()
    backend._session.runtime = MagicMock()
    backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": None}})
    backend._session.runtime.enable = AsyncMock()
    backend._session.send = AsyncMock(return_value={})
    backend._session.network = MagicMock()
    backend._session.network.enable = AsyncMock()
    backend._session.page = MagicMock()
    backend._session.page.capture_screenshot = AsyncMock(return_value="")
    return backend


def _make_bidi_backend() -> Any:
    """Create a BiDiBackend with mocked client."""
    from wavexis.backend.bidi import BiDiBackend

    backend = BiDiBackend()
    backend._client = MagicMock()
    backend._context = MagicMock()
    backend._client.script = MagicMock()
    result = MagicMock()
    result.value = None
    backend._client.script.evaluate = AsyncMock(return_value=result)
    backend._client.cdp = MagicMock()
    backend._client.cdp.send_command = AsyncMock(return_value={})
    backend._client.cdp.on = MagicMock()
    backend._client.cdp.off = MagicMock()
    backend._client.on_log_entry = AsyncMock(return_value="log-sub-1")
    backend._client.off = MagicMock()
    return backend


@pytest.mark.unit
class TestGetRequestBodyCDP:
    """Tests for get_request_body in CDP backend."""

    def test_returns_body(self) -> None:
        """Test that get_request_body returns the post data."""
        backend = _make_cdp_backend()
        backend._session.send = AsyncMock(return_value={"postData": '{"key": "value"}'})
        result = asyncio.run(backend.get_request_body("req-123"))
        assert result == '{"key": "value"}'

    def test_returns_none_on_error(self) -> None:
        """Test that get_request_body returns None on error."""
        backend = _make_cdp_backend()
        backend._session.send = AsyncMock(side_effect=Exception("fail"))
        result = asyncio.run(backend.get_request_body("req-123"))
        assert result is None


@pytest.mark.unit
class TestGetResponseBodyCDP:
    """Tests for get_response_body in CDP backend."""

    def test_returns_body(self) -> None:
        """Test that get_response_body returns the body."""
        backend = _make_cdp_backend()
        backend._session.send = AsyncMock(return_value={"body": "<html>response</html>"})
        result = asyncio.run(backend.get_response_body("req-123"))
        assert result == "<html>response</html>"

    def test_returns_none_on_error(self) -> None:
        """Test that get_response_body returns None on error."""
        backend = _make_cdp_backend()
        backend._session.send = AsyncMock(side_effect=Exception("fail"))
        result = asyncio.run(backend.get_response_body("req-123"))
        assert result is None


@pytest.mark.unit
class TestGetRequestBodyBiDi:
    """Tests for get_request_body in BiDi backend."""

    def test_returns_body(self) -> None:
        """Test that get_request_body returns the post data."""
        backend = _make_bidi_backend()
        backend._client.cdp.send_command = AsyncMock(return_value={"postData": '{"key": "value"}'})
        result = asyncio.run(backend.get_request_body("req-123"))
        assert result == '{"key": "value"}'

    def test_returns_none_on_error(self) -> None:
        """Test that get_request_body returns None on error."""
        backend = _make_bidi_backend()
        backend._client.cdp.send_command = AsyncMock(side_effect=Exception("fail"))
        result = asyncio.run(backend.get_request_body("req-123"))
        assert result is None


@pytest.mark.unit
class TestGetResponseBodyBiDi:
    """Tests for get_response_body in BiDi backend."""

    def test_returns_body(self) -> None:
        """Test that get_response_body returns the body."""
        backend = _make_bidi_backend()
        backend._client.network = MagicMock()
        backend._client.network.response_body = AsyncMock(
            return_value=MagicMock(body="<html>response</html>")
        )
        result = asyncio.run(backend.get_response_body("req-123"))
        assert result == "<html>response</html>"


@pytest.mark.unit
class TestModifyRequestCDP:
    """Tests for modify_request in CDP backend."""

    def test_calls_fetch_enable(self) -> None:
        """Test that modify_request enables Fetch domain."""
        backend = _make_cdp_backend()
        backend._session.on = MagicMock()
        asyncio.run(
            backend.modify_request(
                {"urlPattern": "*/api/*"},
                {"method": "POST"},
            )
        )
        backend._session.send.assert_any_call(
            "Fetch.enable",
            {"patterns": [{"urlPattern": "*/api/*"}]},
        )


@pytest.mark.unit
class TestReplayHarCDP:
    """Tests for replay_har in CDP backend."""

    def test_replays_entries(self, tmp_path: Any) -> None:
        """Test that replay_har reads and replays HAR entries."""
        backend = _make_cdp_backend()
        har_data = {
            "log": {
                "entries": [
                    {
                        "request": {
                            "url": "https://api.example.com/data",
                            "method": "GET",
                            "headers": [{"name": "Accept", "value": "application/json"}],
                        }
                    }
                ]
            }
        }
        har_path = tmp_path / "test.har"
        har_path.write_text(json.dumps(har_data))

        asyncio.run(backend.replay_har(str(har_path)))
        backend._session.runtime.evaluate.assert_called_once()

    def test_filters_by_url(self, tmp_path: Any) -> None:
        """Test that replay_har filters entries by URL."""
        backend = _make_cdp_backend()
        har_data = {
            "log": {
                "entries": [
                    {
                        "request": {
                            "url": "https://api.example.com/data",
                            "method": "GET",
                            "headers": [],
                        }
                    },
                    {
                        "request": {
                            "url": "https://other.example.com/data",
                            "method": "GET",
                            "headers": [],
                        }
                    },
                ]
            }
        }
        har_path = tmp_path / "test.har"
        har_path.write_text(json.dumps(har_data))

        asyncio.run(backend.replay_har(str(har_path), url_filter="api.example"))
        backend._session.runtime.evaluate.assert_called_once()

    def test_unreadable_har_raises(self, tmp_path: Any, monkeypatch: Any) -> None:
        """Test that replay_har raises WavexisError when HAR file is unreadable."""
        backend = _make_cdp_backend()
        har_path = tmp_path / "test.har"
        har_path.write_text('{"log": {"entries": []}}')

        def _raise(*args: Any, **kwargs: Any) -> None:
            raise PermissionError("denied")

        monkeypatch.setattr(pathlib.Path, "read_text", _raise)

        with pytest.raises(WavexisError, match="Failed to read HAR file"):
            asyncio.run(backend.replay_har(str(har_path)))


@pytest.mark.unit
class TestCombinedTraceCDP:
    """Tests for start/stop_combined_trace in CDP backend."""

    def test_start_returns_trace_id(self) -> None:
        """Test that start_combined_trace returns a trace ID."""
        backend = _make_cdp_backend()
        backend._session.on = MagicMock()
        trace_id = asyncio.run(backend.start_combined_trace())
        assert trace_id.startswith("trace-")

    def test_stop_returns_data(self) -> None:
        """Test that stop_combined_trace returns collected data."""
        backend = _make_cdp_backend()
        backend._session.on = MagicMock()
        trace_id = asyncio.run(backend.start_combined_trace())
        result = asyncio.run(backend.stop_combined_trace(trace_id))
        assert "trace_events" in result
        assert "screenshots" in result
        assert "network" in result
        assert "console" in result

    def test_stop_unknown_trace(self) -> None:
        """Test that stop_combined_trace returns error for unknown ID."""
        backend = _make_cdp_backend()
        result = asyncio.run(backend.stop_combined_trace("unknown"))
        assert "error" in result


@pytest.mark.unit
class TestAxeAuditCDP:
    """Tests for axe_audit in CDP backend."""

    def test_returns_violations(self) -> None:
        """Test that axe_audit returns audit results."""
        backend = _make_cdp_backend()
        audit_result = {
            "violations": [{"id": "color-contrast"}],
            "passes": [],
            "incomplete": [],
            "inapplicable": [],
        }
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": audit_result}}
        )
        result = asyncio.run(backend.axe_audit())
        assert "violations" in result
        assert len(result["violations"]) == 1

    def test_returns_error_on_failure(self) -> None:
        """Test that axe_audit returns error dict on failure."""
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": None}})
        result = asyncio.run(backend.axe_audit())
        assert "error" in result


@pytest.mark.unit
class TestSubscribeEventsCDP:
    """Tests for subscribe/unsubscribe_events in CDP backend."""

    def test_subscribe_returns_id(self) -> None:
        """Test that subscribe_events returns a subscription ID."""
        backend = _make_cdp_backend()
        backend._session.on = MagicMock()
        sub_id = asyncio.run(backend.subscribe_events(["console"], lambda e: None))
        assert sub_id.startswith("sub-")

    def test_unsubscribe_removes_handlers(self) -> None:
        """Test that unsubscribe_events removes handlers."""
        backend = _make_cdp_backend()
        backend._session.on = MagicMock()
        backend._session.off = MagicMock()
        sub_id = asyncio.run(backend.subscribe_events(["console"], lambda e: None))
        asyncio.run(backend.unsubscribe_events(sub_id))
        backend._session.off.assert_called()

    def test_subscribe_rolls_back_on_enable_failure(self) -> None:
        """Registered handlers are removed if domain enable() fails."""
        backend = _make_cdp_backend()
        backend._session.on = MagicMock()
        backend._session.off = MagicMock()
        backend._session.runtime.enable = MagicMock(side_effect=RuntimeError("boom"))
        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(backend.subscribe_events(["console"], lambda e: None))
        backend._session.off.assert_called_once()


@pytest.mark.unit
class TestCombinedTraceBiDi:
    """Tests for combined trace in BiDi backend."""

    def test_start_returns_trace_id(self) -> None:
        """Test that start_combined_trace returns a trace ID."""
        backend = _make_bidi_backend()
        trace_id = asyncio.run(backend.start_combined_trace())
        assert trace_id.startswith("trace-")

    def test_stop_returns_data(self) -> None:
        """Test that stop_combined_trace returns collected data."""
        backend = _make_bidi_backend()
        trace_id = asyncio.run(backend.start_combined_trace())
        result = asyncio.run(backend.stop_combined_trace(trace_id))
        assert "trace_events" in result
        assert "network" in result


@pytest.mark.unit
class TestAxeAuditBiDi:
    """Tests for axe_audit in BiDi backend."""

    def test_returns_violations(self) -> None:
        """Test that axe_audit returns audit results."""
        backend = _make_bidi_backend()
        audit_result = {
            "violations": [{"id": "color-contrast"}],
            "passes": [],
            "incomplete": [],
            "inapplicable": [],
        }
        result_mock = MagicMock()
        result_mock.value = audit_result
        backend._client.script.evaluate = AsyncMock(return_value=result_mock)
        result = asyncio.run(backend.axe_audit())
        assert "violations" in result


@pytest.mark.unit
class TestSubscribeEventsBiDi:
    """Tests for subscribe_events in BiDi backend."""

    def test_subscribe_returns_id(self) -> None:
        """Test that subscribe_events returns a subscription ID."""
        backend = _make_bidi_backend()
        sub_id = asyncio.run(backend.subscribe_events(["console"], lambda e: None))
        assert sub_id.startswith("sub-")

    def test_unsubscribe_removes_handlers(self) -> None:
        """Test that unsubscribe_events removes handlers."""
        backend = _make_bidi_backend()
        sub_id = asyncio.run(backend.subscribe_events(["console"], lambda e: None))
        asyncio.run(backend.unsubscribe_events(sub_id))
        backend._client.off.assert_called()

    def test_subscribe_rolls_back_on_failure(self) -> None:
        """Registered handlers are removed if a later subscription fails."""
        backend = _make_bidi_backend()
        backend._client.on_request = MagicMock(side_effect=RuntimeError("boom"))
        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(backend.subscribe_events(["console", "network_request"], lambda e: None))
        backend._client.off.assert_called_once_with("log-sub-1")
