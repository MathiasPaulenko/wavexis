"""Unit tests for W3-W12 enhancements: request body, modify request, HAR replay,
combined trace, axe audit, subscribe events, visual diff."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_cdp_backend() -> Any:
    """Create a CDPBackend with mocked session."""
    from wavexis.backend.cdp import CDPBackend

    backend = CDPBackend()
    backend._session = MagicMock()
    backend._session.runtime = MagicMock()
    backend._session.network = MagicMock()
    backend._session.page = MagicMock()
    backend._session.send = AsyncMock()
    return backend


def _make_bidi_backend() -> Any:
    """Create a BiDiBackend with mocked client."""
    from wavexis.backend.bidi import BiDiBackend

    backend = BiDiBackend()
    backend._client = MagicMock()
    backend._context = MagicMock()
    backend._client.cdp = MagicMock()
    backend._client.cdp.send_command = AsyncMock()
    backend._client.cdp.on = MagicMock()
    backend._client.cdp.off = MagicMock()
    backend._client.script = MagicMock()
    backend._client.script.evaluate = AsyncMock()
    backend._client.network = MagicMock()
    backend._client.network.add_intercept = AsyncMock()
    backend._client.network.continue_request = AsyncMock()
    backend._client.network.continue_response = AsyncMock()
    backend._client.network.response_body = AsyncMock(return_value=MagicMock(body="response body"))
    return backend


# ── W3: Request body capture ───────────────────────────


@pytest.mark.unit
class TestRequestBodyCapture:
    """Tests for get_request_body and get_response_body."""

    def test_cdp_get_request_body(self) -> None:
        backend = _make_cdp_backend()
        backend._session.send = AsyncMock(return_value={"postData": '{"key": "val"}'})
        result = asyncio.run(backend.get_request_body("req-123"))
        assert result == '{"key": "val"}'

    def test_cdp_get_request_body_none_on_error(self) -> None:
        backend = _make_cdp_backend()
        backend._session.send = AsyncMock(side_effect=Exception("not found"))
        result = asyncio.run(backend.get_request_body("req-missing"))
        assert result is None

    def test_cdp_get_response_body(self) -> None:
        backend = _make_cdp_backend()
        backend._session.send = AsyncMock(return_value={"body": "<html>response</html>"})
        result = asyncio.run(backend.get_response_body("req-123"))
        assert result == "<html>response</html>"

    def test_cdp_get_response_body_none_on_error(self) -> None:
        backend = _make_cdp_backend()
        backend._session.send = AsyncMock(side_effect=Exception("not found"))
        result = asyncio.run(backend.get_response_body("req-missing"))
        assert result is None

    def test_bidi_get_request_body(self) -> None:
        backend = _make_bidi_backend()
        backend._client.cdp.send_command = AsyncMock(return_value={"postData": "data=value"})
        result = asyncio.run(backend.get_request_body("req-1"))
        assert result == "data=value"

    def test_bidi_get_response_body(self) -> None:
        backend = _make_bidi_backend()
        backend._client.network.response_body = AsyncMock(
            return_value=MagicMock(body="response body")
        )
        result = asyncio.run(backend.get_response_body("req-1"))
        assert result == "response body"


# ── W6: Modify request ─────────────────────────────────


@pytest.mark.unit
class TestModifyRequest:
    """Tests for modify_request."""

    def test_cdp_modify_request_sets_up_interception(self) -> None:
        backend = _make_cdp_backend()
        pattern = {"urlPattern": "*api*", "requestStage": "Request"}
        modifications = {"headers": [{"name": "X-Custom", "value": "test"}]}
        asyncio.run(backend.modify_request(pattern, modifications))
        backend._session.send.assert_called_with("Fetch.enable", {"patterns": [pattern]})

    def test_bidi_modify_request_sets_up_interception(self) -> None:
        backend = _make_bidi_backend()
        pattern = {"urlPattern": "*api*"}
        modifications = {"method": "POST"}
        asyncio.run(backend.modify_request(pattern, modifications))
        backend._client.network.add_intercept.assert_called_once()


# ── W7: HAR replay ─────────────────────────────────────


@pytest.mark.unit
class TestHARReplay:
    """Tests for replay_har."""

    def test_cdp_replay_har_replays_entries(self) -> None:
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": 200}})
        har_data = {
            "log": {
                "entries": [
                    {
                        "request": {
                            "url": "https://api.example.com/users",
                            "method": "GET",
                            "headers": [{"name": "Accept", "value": "application/json"}],
                        }
                    },
                    {
                        "request": {
                            "url": "https://api.example.com/posts",
                            "method": "POST",
                            "headers": [],
                            "postData": {"text": '{"title": "test"}'},
                        }
                    },
                ]
            }
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".har", delete=False, encoding="utf-8"
        ) as f:
            json.dump(har_data, f)
            har_path = f.name
        try:
            asyncio.run(backend.replay_har(har_path))
            assert backend._session.runtime.evaluate.call_count == 2
        finally:
            os.unlink(har_path)

    def test_cdp_replay_har_with_url_filter(self) -> None:
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": 200}})
        har_data = {
            "log": {
                "entries": [
                    {
                        "request": {
                            "url": "https://api.example.com/users",
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
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".har", delete=False, encoding="utf-8"
        ) as f:
            json.dump(har_data, f)
            har_path = f.name
        try:
            asyncio.run(backend.replay_har(har_path, url_filter="api.example.com"))
            assert backend._session.runtime.evaluate.call_count == 1
        finally:
            os.unlink(har_path)


# ── W8: Combined trace ─────────────────────────────────


@pytest.mark.unit
class TestCombinedTrace:
    """Tests for start_combined_trace and stop_combined_trace."""

    def test_cdp_start_combined_trace_returns_id(self) -> None:
        backend = _make_cdp_backend()
        backend._session.network.enable = AsyncMock()
        backend._session.runtime.enable = AsyncMock()
        backend._session.page.capture_screenshot = AsyncMock(return_value=None)
        backend._session.send = AsyncMock()
        trace_id = asyncio.run(backend.start_combined_trace())
        assert trace_id.startswith("trace-")

    def test_cdp_stop_combined_trace_unknown_id(self) -> None:
        backend = _make_cdp_backend()
        backend._session.send = AsyncMock()
        result = asyncio.run(backend.stop_combined_trace("unknown-id"))
        assert "error" in result

    def test_cdp_start_stop_combined_trace(self) -> None:
        backend = _make_cdp_backend()
        backend._session.network.enable = AsyncMock()
        backend._session.runtime.enable = AsyncMock()
        backend._session.page.capture_screenshot = AsyncMock(return_value=None)
        backend._session.send = AsyncMock()
        trace_id = asyncio.run(
            backend.start_combined_trace(
                capture_screenshots=False,
                capture_network=False,
                capture_console=False,
            )
        )
        assert trace_id.startswith("trace-")
        result = asyncio.run(backend.stop_combined_trace(trace_id))
        assert "trace_events" in result
        assert "screenshots" in result
        assert "network" in result
        assert "console" in result


# ── W9: axe-core audit ─────────────────────────────────


@pytest.mark.unit
class TestAxeAudit:
    """Tests for axe_audit."""

    def test_cdp_axe_audit_returns_dict(self) -> None:
        backend = _make_cdp_backend()
        expected = {"violations": [], "passes": [], "incomplete": [], "inapplicable": []}
        backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": expected}})
        result = asyncio.run(backend.axe_audit())
        assert result == expected

    def test_cdp_axe_audit_returns_parsed_json(self) -> None:
        backend = _make_cdp_backend()
        expected = {"violations": [{"id": "color-contrast"}]}
        backend._session.runtime.evaluate = AsyncMock(
            return_value={"result": {"value": json.dumps(expected)}}
        )
        result = asyncio.run(backend.axe_audit())
        assert result == expected

    def test_cdp_axe_audit_error_on_invalid_result(self) -> None:
        backend = _make_cdp_backend()
        backend._session.runtime.evaluate = AsyncMock(return_value={"result": {"value": None}})
        result = asyncio.run(backend.axe_audit())
        assert "error" in result


# ── W11: Subscribe events ──────────────────────────────


@pytest.mark.unit
class TestSubscribeEvents:
    """Tests for subscribe_events and unsubscribe_events."""

    def test_cdp_subscribe_returns_id(self) -> None:
        backend = _make_cdp_backend()
        backend._session.network.enable = AsyncMock()
        backend._session.runtime.enable = AsyncMock()
        callback = MagicMock()
        sub_id = asyncio.run(backend.subscribe_events(["console", "network_request"], callback))
        assert sub_id.startswith("sub-")

    def test_cdp_unsubscribe_removes_handlers(self) -> None:
        backend = _make_cdp_backend()
        backend._session.network.enable = AsyncMock()
        backend._session.runtime.enable = AsyncMock()
        backend._session.off = MagicMock()
        callback = MagicMock()
        sub_id = asyncio.run(backend.subscribe_events(["console"], callback))
        asyncio.run(backend.unsubscribe_events(sub_id))
        assert backend._session.off.call_count >= 1

    def test_bidi_subscribe_returns_id(self) -> None:
        backend = _make_bidi_backend()
        callback = MagicMock()
        sub_id = asyncio.run(backend.subscribe_events(["network_response", "dialog"], callback))
        assert sub_id.startswith("sub-")


# ── W12: Visual diff ───────────────────────────────────


@pytest.mark.unit
class TestVisualDiff:
    """Tests for VisualDiffAction."""

    def test_visual_diff_action_import(self) -> None:
        from wavexis.actions.visual_diff import VisualDiffAction, VisualDiffParams

        params = VisualDiffParams(
            url="https://example.com",
            baseline_path="/tmp/baseline.png",
            threshold=15,
        )
        action = VisualDiffAction(params)
        assert action.params.url == "https://example.com"
        assert action.params.threshold == 15

    def test_visual_diff_compare_identical_images(self) -> None:
        from wavexis.actions.visual_diff import VisualDiffAction, VisualDiffParams

        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        img = Image.new("RGB", (10, 10), color=(255, 0, 0))
        import io

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(img_bytes)
            baseline_path = f.name

        try:
            action = VisualDiffAction(VisualDiffParams(baseline_path=baseline_path))
            result = action._compare(img_bytes, img_bytes)
            assert result["diff_count"] == 0
            assert result["diff_percentage"] == 0.0
        finally:
            os.unlink(baseline_path)

    def test_visual_diff_compare_different_images(self) -> None:
        from wavexis.actions.visual_diff import VisualDiffAction, VisualDiffParams

        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        import io

        img1 = Image.new("RGB", (10, 10), color=(255, 0, 0))
        buf1 = io.BytesIO()
        img1.save(buf1, format="PNG")

        img2 = Image.new("RGB", (10, 10), color=(0, 255, 0))
        buf2 = io.BytesIO()
        img2.save(buf2, format="PNG")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(buf1.getvalue())
            baseline_path = f.name

        try:
            action = VisualDiffAction(VisualDiffParams(baseline_path=baseline_path, threshold=5))
            result = action._compare(buf1.getvalue(), buf2.getvalue())
            assert result["diff_count"] > 0
            assert result["diff_percentage"] > 0.0
        finally:
            os.unlink(baseline_path)


# ── Action imports ─────────────────────────────────────


@pytest.mark.unit
class TestActionImports:
    """Test that all new action classes can be imported."""

    def test_modify_request_action_import(self) -> None:
        from wavexis.actions.modify_request import ModifyRequestAction, ModifyRequestParams

        params = ModifyRequestParams(
            pattern={"urlPattern": "*"},
            modifications={"method": "PUT"},
        )
        action = ModifyRequestAction(params)
        assert action.params.modifications["method"] == "PUT"

    def test_har_replay_action_import(self) -> None:
        from wavexis.actions.har_replay import HARReplayAction, HARReplayParams

        params = HARReplayParams(har_path="/tmp/test.har")
        action = HARReplayAction(params)
        assert action.params.har_path == "/tmp/test.har"

    def test_combined_trace_action_import(self) -> None:
        from wavexis.actions.combined_trace import CombinedTraceAction, CombinedTraceParams

        params = CombinedTraceParams(action="start", duration_ms=5000)
        action = CombinedTraceAction(params)
        assert action.params.duration_ms == 5000

    def test_axe_audit_action_import(self) -> None:
        from wavexis.actions.axe_audit import AxeAuditAction, AxeAuditParams

        params = AxeAuditParams(url="https://example.com")
        action = AxeAuditAction(params)
        assert action.params.url == "https://example.com"
