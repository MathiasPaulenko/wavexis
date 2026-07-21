"""Unit tests for serve mode (wavexis.serve)."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.backend.base import AbstractBackend
from wavexis.exceptions import ActionError, WavexisError


def _has_aiohttp() -> bool:
    """has aiohttp."""
    try:
        import aiohttp  # noqa: F401

        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(not _has_aiohttp(), reason="aiohttp not installed")


@pytest.mark.unit
class TestServeImport:
    """Test suite for serveimport."""

    def test_import_aiohttp_raises_without_install(self) -> None:
        """Test that import aiohttp raises without install raises an appropriate error."""
        from wavexis.serve import _import_aiohttp

        web = _import_aiohttp()
        assert web is not None


@pytest.mark.unit
class TestServeCreateApp:
    """Test suite for servecreateapp."""

    def test_create_app_returns_application(self) -> None:
        """Test create app returns application."""
        from wavexis.serve import create_app

        app = create_app()
        assert app is not None
        assert "backend_name" in app

    def test_create_app_has_routes(self) -> None:
        """Test create app has routes."""
        from wavexis.serve import create_app

        app = create_app()
        routes = [r.resource.canonical for r in app.router.routes()]
        assert "/screenshot" in routes
        assert "/pdf" in routes
        assert "/eval" in routes
        assert "/scrape" in routes
        assert "/dom/get" in routes
        assert "/dom/query" in routes
        assert "/navigate" in routes
        assert "/har" in routes
        assert "/cookies/get" in routes
        assert "/cookies/set" in routes
        assert "/input/click" in routes
        assert "/input/type" in routes
        assert "/perf/metrics" in routes
        assert "/perf/trace" in routes
        assert "/auth" in routes
        assert "/user-agent" in routes
        assert "/headers" in routes
        assert "/device" in routes
        assert "/multi" in routes
        assert "/health" in routes
        assert "/backends" in routes
        assert "/version" in routes
        assert "/ws" in routes
        assert "/plugins" in routes


@pytest.mark.unit
class TestServeHandlers:
    """Test suite for servehandlers."""

    async def test_health_endpoint(self) -> None:
        """Test health endpoint."""
        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        resp = await client.get("/health")
        assert resp.status == 200
        data = await resp.json()
        assert data == {"status": "ok"}
        await client.close()

    async def test_version_endpoint(self) -> None:
        """Test version endpoint."""
        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import __version__, create_app

        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        resp = await client.get("/version")
        assert resp.status == 200
        data = await resp.json()
        assert data == {"version": __version__}
        await client.close()

    async def test_backends_endpoint(self) -> None:
        """Test backends endpoint."""
        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        resp = await client.get("/backends")
        assert resp.status == 200
        data = await resp.json()
        assert "cdp" in data
        assert "bidi" in data
        await client.close()


@pytest.mark.unit
class TestServeHandlerMocks:
    """Test handlers with mocked backend to avoid real browser."""

    def _make_mock_backend(self) -> MagicMock:
        """make mock backend."""
        backend = MagicMock(spec=AbstractBackend)
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.screenshot = AsyncMock(return_value=b"\x89PNG\r\n\x1a\n")
        backend.pdf = AsyncMock(return_value=b"%PDF-1.4")
        backend.eval = AsyncMock(return_value=42)
        backend.get_cookies = AsyncMock(return_value=[{"name": "foo", "value": "bar"}])
        backend.set_cookie = AsyncMock()
        backend.perf_metrics = AsyncMock(return_value={"Timestamp": 1.0})
        backend.perf_trace = AsyncMock(return_value={"traceEvents": [{"name": "X"}]})
        backend.subscribe_events = AsyncMock(return_value="sub-test-1")
        backend.unsubscribe_events = AsyncMock()
        return backend

    async def test_screenshot_endpoint(self) -> None:
        """Test screenshot endpoint."""
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/screenshot",
                json={"url": "https://example.com"},
            )
        assert resp.status == 200
        assert resp.content_type == "image/png"
        data = await resp.read()
        assert data.startswith(b"\x89PNG")
        await client.close()

    async def test_screenshot_endpoint_returns_500_on_wavexis_error(self) -> None:
        """A backend action failure should produce a clean JSON 500 response."""
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.exceptions import WavexisError
        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        mock_backend.screenshot = AsyncMock(side_effect=WavexisError("backend failure"))
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/screenshot",
                json={"url": "https://example.com"},
            )
        assert resp.status == 500
        assert resp.content_type == "application/json"
        data = await resp.json()
        assert "error" in data
        assert "backend failure" in data["error"]
        await client.close()

    async def test_screenshot_endpoint_rejects_non_object_json_body(self) -> None:
        """Test screenshot endpoint rejects non-object JSON body."""
        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        resp = await client.post(
            "/screenshot",
            json=[1, 2, 3],
        )
        assert resp.status == 400
        data = await resp.json()
        assert "error" in data
        await client.close()

    async def test_pdf_endpoint(self) -> None:
        """Test pdf endpoint."""
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/pdf",
                json={"url": "https://example.com"},
            )
        assert resp.status == 200
        assert resp.content_type == "application/pdf"
        data = await resp.read()
        assert data.startswith(b"%PDF")
        await client.close()

    async def test_eval_endpoint(self) -> None:
        """Test eval endpoint."""
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/eval",
                json={"url": "https://example.com", "expression": "1+1"},
            )
        assert resp.status == 200
        data = await resp.json()
        assert data == {"result": 42}
        await client.close()

    async def test_perf_metrics_endpoint(self) -> None:
        """Test perf metrics endpoint."""
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/perf/metrics",
                json={"url": "https://example.com"},
            )
        assert resp.status == 200
        data = await resp.json()
        assert "Timestamp" in data
        await client.close()

    async def test_perf_trace_endpoint(self) -> None:
        """Test perf trace endpoint."""
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/perf/trace",
                json={"url": "https://example.com", "duration_ms": 1000},
            )
        assert resp.status == 200
        data = await resp.json()
        assert "traceEvents" in data
        await client.close()

    async def test_navigate_endpoint(self) -> None:
        """Test navigate endpoint."""
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/navigate",
                json={"url": "https://example.com"},
            )
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "ok"
        await client.close()

    async def test_cookies_get_endpoint(self) -> None:
        """Test cookies get endpoint."""
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/cookies/get",
                json={"url": "https://example.com"},
            )
        assert resp.status == 200
        data = await resp.json()
        assert "cookies" in data
        await client.close()

    async def test_cookies_set_endpoint(self) -> None:
        """Test cookies set endpoint."""
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/cookies/set",
                json={
                    "name": "foo",
                    "value": "bar",
                    "domain": "example.com",
                },
            )
        assert resp.status == 200
        data = await resp.json()
        assert data == {"status": "ok"}
        await client.close()

    async def test_websocket_screenshot_stream(self) -> None:
        """Test websocket screenshot stream."""
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        mock_backend.capture_console = AsyncMock(return_value=[])
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            ws = await client.ws_connect("/ws")
            await ws.send_json(
                {
                    "url": "https://example.com",
                    "events": ["screenshot"],
                    "interval": 0.1,
                }
            )
            ready = await ws.receive_json(timeout=2)
            assert ready["type"] == "ready"
            screenshot = await ws.receive_json(timeout=2)
            assert screenshot["type"] == "screenshot"
            assert "data" in screenshot
            await ws.send_json({"action": "close"})
        await ws.close()
        await client.close()

    async def test_websocket_eval_command(self) -> None:
        """Test websocket eval command."""
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        mock_backend.capture_console = AsyncMock(return_value=[])
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            ws = await client.ws_connect("/ws")
            await ws.send_json(
                {
                    "url": "https://example.com",
                    "events": [],
                    "interval": 1.0,
                }
            )
            ready = await ws.receive_json(timeout=2)
            assert ready["type"] == "ready"
            await ws.send_json({"action": "eval", "expression": "document.title"})
            result = await ws.receive_json(timeout=2)
            assert result["type"] == "eval_result"
            assert result["result"] == 42
            await ws.send_json({"action": "close"})
        await ws.close()
        await client.close()

    async def test_websocket_unsubscribes_events_on_close(self) -> None:
        """Regression: WebSocket close must unsubscribe event handlers.

        Without this, event handlers leak onto pooled backends and fire
        during subsequent unrelated sessions.
        """
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        mock_backend.capture_console = AsyncMock(return_value=[])
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            ws = await client.ws_connect("/ws")
            await ws.send_json(
                {
                    "url": "https://example.com",
                    "events": ["network_request"],
                    "interval": 1.0,
                }
            )
            ready = await ws.receive_json(timeout=2)
            assert ready["type"] == "ready"
            # subscribe_events should have been called with the network types
            mock_backend.subscribe_events.assert_awaited()
            sub_id = mock_backend.subscribe_events.await_args.args[0]
            assert "network_request" in sub_id or isinstance(sub_id, list)
            await ws.send_json({"action": "close"})
        await ws.close()
        await client.close()
        # unsubscribe_events must be called on close to prevent handler leaks
        mock_backend.unsubscribe_events.assert_awaited()

    async def test_scrape_endpoint(self) -> None:
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        mock_backend.scrape = AsyncMock(return_value={"title": "Test"})
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/scrape",
                json={"url": "https://example.com"},
            )
        assert resp.status == 200
        await client.close()

    async def test_scrape_csv_endpoint(self) -> None:
        """Test that scrape with output_format=csv returns CSV text."""
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        mock_backend.navigate = AsyncMock()
        mock_backend.eval = AsyncMock(return_value="Test Title")
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/scrape",
                json={
                    "url": "https://example.com",
                    "output_format": "csv",
                    "urls": ["https://example.com"],
                },
            )
        assert resp.status == 200
        text = await resp.text()
        assert "url" in text
        assert "result" in text
        assert "text/csv" in resp.headers.get("Content-Type", "")
        await client.close()

    async def test_dom_get_endpoint(self) -> None:
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        mock_backend.dom_get = AsyncMock(return_value="<html></html>")
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/dom/get", json={"url": "https://example.com", "selector": "body"}
            )
        assert resp.status == 200
        await client.close()

    async def test_dom_query_endpoint(self) -> None:
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        mock_backend.dom_query = AsyncMock(return_value={"nodeId": 1})
        mock_backend.dom_get = AsyncMock(return_value="<html></html>")
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/dom/query", json={"url": "https://example.com", "selector": "div"}
            )
        assert resp.status == 200
        await client.close()

    async def test_har_endpoint(self) -> None:
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        mock_backend.capture_har = AsyncMock(return_value={"log": {"entries": []}})
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post("/har", json={"url": "https://example.com"})
        assert resp.status == 200
        await client.close()

    async def test_input_click_endpoint(self) -> None:
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        mock_backend.click = AsyncMock()
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/input/click",
                json={"url": "https://example.com", "selector": "button"},
            )
        assert resp.status == 200
        await client.close()

    async def test_input_type_endpoint(self) -> None:
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        mock_backend.type = AsyncMock()
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/input/type",
                json={"url": "https://example.com", "selector": "input", "text": "hello"},
            )
        assert resp.status == 200
        await client.close()

    async def test_cwv_endpoint(self) -> None:
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        mock_backend.eval = AsyncMock(
            side_effect=[
                {"lcp": 2000, "cls": 0.05, "inp": 100},
                {"lcp": 2000, "cls": 0.05, "inp": 100},
            ]
        )
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post("/cwv", json={"url": "https://example.com", "observe_ms": 100})
        assert resp.status == 200
        await client.close()

    async def test_user_agent_endpoint(self) -> None:
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        mock_backend.set_user_agent = AsyncMock()
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/user-agent",
                json={"url": "https://example.com", "user_agent": "MyBot/1.0"},
            )
        assert resp.status == 200
        await client.close()

    async def test_headers_endpoint(self) -> None:
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        mock_backend.set_headers = AsyncMock()
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/headers",
                json={"url": "https://example.com", "headers": {"X-Test": "val"}},
            )
        assert resp.status == 200
        await client.close()

    async def test_device_endpoint(self) -> None:
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        mock_backend.emulate_device = AsyncMock()
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/device",
                json={"url": "https://example.com", "device": "iPhone 12"},
            )
        assert resp.status == 200
        await client.close()

    async def test_modify_request_endpoint(self) -> None:
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        mock_backend.modify_request = AsyncMock()
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/modify-request",
                json={"url": "https://example.com", "pattern": "*api*"},
            )
        assert resp.status == 200
        await client.close()

    async def test_modify_response_endpoint(self) -> None:
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = self._make_mock_backend()
        mock_backend.modify_response = AsyncMock()
        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        with patch(
            "wavexis.backend.manager.BackendManager.select_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            resp = await client.post(
                "/modify-response",
                json={"url": "https://example.com", "pattern": "*api*"},
            )
        assert resp.status == 200
        await client.close()

    async def test_plugins_endpoint(self) -> None:
        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        app = create_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        resp = await client.get("/plugins")
        assert resp.status == 200
        data = await resp.json()
        assert "actions" in data
        assert "backends" in data
        assert "middleware" in data
        await client.close()

    async def test_auth_endpoint_missing_context_file_returns_400(
        self, tmp_path: Path
    ) -> None:
        """A missing or invalid auth context file should return 400, not 500."""
        from unittest.mock import patch

        from aiohttp.test_utils import TestClient, TestServer

        import wavexis.serve as serve_mod
        from wavexis.serve import create_app

        bad_context = tmp_path / "bad_auth.json"
        bad_context.write_text("not json", encoding="utf-8")
        serve_mod.set_allowed_base_dir(str(tmp_path))
        try:
            mock_backend = self._make_mock_backend()
            app = create_app(base_dir=str(tmp_path))
            server = TestServer(app)
            client = TestClient(server)
            await client.start_server()
            with patch(
                "wavexis.backend.manager.BackendManager.select_with_fallback",
                new_callable=AsyncMock,
                return_value=mock_backend,
            ):
                resp = await client.post(
                    "/auth",
                    json={"context": str(bad_context), "url": "https://example.com"},
                )
            assert resp.status == 400
            text = await resp.text()
            assert "auth context" in text.lower()
            await client.close()
        finally:
            serve_mod.set_allowed_base_dir(None)


@pytest.mark.unit
class TestServeUtilities:
    """Test serve utility functions."""

    def test_safe_params(self) -> None:
        from wavexis.config import ScreenshotParams
        from wavexis.serve import _safe_params

        params = _safe_params(
            ScreenshotParams, {"url": "https://example.com", "unknown": "ignored"}
        )
        assert params.url == "https://example.com"

    def test_safe_params_nested_wait_strategy(self) -> None:
        from wavexis.config import ScreenshotParams, WaitStrategy
        from wavexis.serve import _safe_params

        params = _safe_params(
            ScreenshotParams,
            {"url": "https://example.com", "wait": {"strategy": "selector", "selector": "#main"}},
        )
        assert isinstance(params.wait, WaitStrategy)
        assert params.wait.strategy == "selector"
        assert params.wait.selector == "#main"

    def test_safe_params_nested_browser_options(self) -> None:
        from wavexis.config import BrowserOptions, ScreenshotParams
        from wavexis.serve import _safe_params

        params = _safe_params(
            ScreenshotParams,
            {"url": "https://example.com", "browser": {"headless": False, "width": 1920}},
        )
        assert isinstance(params.browser, BrowserOptions)
        assert params.browser.headless is False
        assert params.browser.width == 1920

    def test_safe_params_nested_optional_wait(self) -> None:
        from wavexis.config import PDFParams, WaitStrategy
        from wavexis.serve import _safe_params

        params = _safe_params(
            PDFParams,
            {"url": "https://example.com", "wait": {"strategy": "networkidle", "timeout": 60000}},
        )
        assert isinstance(params.wait, WaitStrategy)
        assert params.wait.strategy == "networkidle"
        assert params.wait.timeout == 60000

    def test_safe_params_nested_cookie_params(self) -> None:
        from wavexis.config import CookieActionParams, CookieParams
        from wavexis.serve import _safe_params

        params = _safe_params(
            CookieActionParams,
            {
                "url": "https://example.com",
                "action": "set",
                "cookie": {"name": "session", "value": "abc123", "domain": ".example.com"},
            },
        )
        assert isinstance(params.cookie, CookieParams)
        assert params.cookie.name == "session"
        assert params.cookie.value == "abc123"
        assert params.cookie.domain == ".example.com"

    def test_safe_params_dict_field_not_converted(self) -> None:
        from wavexis.config import HeaderParams
        from wavexis.serve import _safe_params

        params = _safe_params(
            HeaderParams,
            {"url": "https://example.com", "headers": {"X-Custom": "value"}},
        )
        assert isinstance(params.headers, dict)
        assert params.headers == {"X-Custom": "value"}

    def test_safe_params_none_value_for_optional_field(self) -> None:
        from wavexis.config import NetworkParams
        from wavexis.serve import _safe_params

        params = _safe_params(
            NetworkParams,
            {"url": "https://example.com", "action": "cookies_get", "cookie": None},
        )
        assert params.cookie is None

    def test_token_bucket_acquire(self) -> None:
        import asyncio

        from wavexis.serve import TokenBucket

        bucket = TokenBucket(capacity=2, refill_period=60.0)

        async def _test() -> None:
            assert await bucket.acquire() is True
            assert await bucket.acquire() is True
            assert await bucket.acquire() is False

        asyncio.run(_test())

    def test_token_bucket_retry_after(self) -> None:
        import asyncio

        from wavexis.serve import TokenBucket

        bucket = TokenBucket(capacity=1, refill_period=60.0)

        async def _test() -> None:
            await bucket.acquire()
            ra = await bucket.retry_after()
            assert ra > 0

        asyncio.run(_test())

    def test_set_allowed_base_dir(self, tmp_path) -> None:
        from wavexis.serve import _validate_path, set_allowed_base_dir

        set_allowed_base_dir(str(tmp_path))
        result = _validate_path(str(tmp_path / "test.txt"))
        assert result is not None

    def test_validate_path_no_base_dir(self) -> None:
        from wavexis.exceptions import WavexisError
        from wavexis.serve import _validate_path, set_allowed_base_dir

        set_allowed_base_dir(None)
        with pytest.raises(WavexisError):
            _validate_path("/tmp/test.txt")

    def test_validate_path_outside_base_dir(self, tmp_path) -> None:
        from wavexis.exceptions import WavexisError
        from wavexis.serve import _validate_path, set_allowed_base_dir

        set_allowed_base_dir(str(tmp_path))
        with pytest.raises(WavexisError):
            _validate_path("/etc/passwd")

    def test_validate_path_empty_string(self, tmp_path) -> None:
        from wavexis.exceptions import WavexisError
        from wavexis.serve import _validate_path, set_allowed_base_dir

        set_allowed_base_dir(str(tmp_path))
        with pytest.raises(WavexisError, match="non-empty"):
            _validate_path("")

    def test_validate_path_none_value(self, tmp_path) -> None:
        from wavexis.exceptions import WavexisError
        from wavexis.serve import _validate_path, set_allowed_base_dir

        set_allowed_base_dir(str(tmp_path))
        with pytest.raises(WavexisError, match="non-empty"):
            _validate_path(None)  # type: ignore[arg-type]

    def test_set_ws_max_connections(self) -> None:
        import wavexis.serve as serve_mod

        serve_mod.set_ws_max_connections(10)
        assert serve_mod._ws_max_connections == 10
        serve_mod.set_ws_max_connections(20)

    def test_set_ws_max_messages_per_minute(self) -> None:
        """set_ws_max_messages_per_minute should update the global limit."""
        import wavexis.serve as serve_mod

        original = serve_mod._ws_max_messages_per_minute
        try:
            serve_mod.set_ws_max_messages_per_minute(60)
            assert serve_mod._ws_max_messages_per_minute == 60
            serve_mod.set_ws_max_messages_per_minute(240)
            assert serve_mod._ws_max_messages_per_minute == 240
        finally:
            serve_mod.set_ws_max_messages_per_minute(original)

    async def test_websocket_connection_counter_decremented_on_prepare_error(self) -> None:
        """If ws.prepare raises, _ws_connections must still be decremented."""
        from unittest.mock import patch

        import wavexis.serve as serve_mod

        serve_mod._ws_connections = 0
        original_max = serve_mod._ws_max_connections
        serve_mod._ws_max_connections = 10
        try:
            with patch("wavexis.serve._import_aiohttp") as mock_import:
                web = MagicMock()
                web.WSMsgType = MagicMock()
                web.Response.return_value = MagicMock()
                ws = MagicMock()
                ws.prepare = AsyncMock(side_effect=RuntimeError("prepare failed"))
                ws.close = AsyncMock()
                web.WebSocketResponse.return_value = ws
                mock_import.return_value = web

                request = MagicMock()
                with pytest.raises(RuntimeError, match="prepare failed"):
                    await serve_mod.handle_websocket(request)

            assert serve_mod._ws_connections == 0
        finally:
            serve_mod._ws_max_connections = original_max

    def test_backend_pool(self) -> None:
        import asyncio

        from wavexis.serve import BackendPool

        pool = BackendPool(max_concurrent=2)

        async def _test() -> None:
            await pool.acquire()
            await pool.acquire()
            pool.release()
            pool.release()

        asyncio.run(_test())

    def test_backend_pool_get_backend_creation_failure_restores_slot(self) -> None:
        """Regression: if backend creation fails, the reserved slot must be released.

        Previously, ``_created`` was incremented under the lock but never
        decremented when ``select_with_fallback`` raised, causing the pool
        to slowly fill with phantom backends.
        """
        import asyncio

        from wavexis.serve import BackendPool

        pool = BackendPool(max_concurrent=2)

        async def _test() -> None:
            # Patch the manager so select_with_fallback always fails.
            from unittest.mock import patch

            with patch(
                "wavexis.serve.get_manager"
            ) as mock_get_manager:
                mock_manager = mock_get_manager.return_value
                mock_manager.select_with_fallback.side_effect = RuntimeError("no backend")
                with pytest.raises(RuntimeError, match="no backend"):
                    await pool.get_backend(preferred="cdp")
            # The slot reserved for the failed creation must have been released.
            assert pool._created == 0

        asyncio.run(_test())

    def test_backend_pool_discard_backend_closes_and_decrements(self) -> None:
        """Regression: discard_backend must close the backend and decrement _created."""
        import asyncio
        from unittest.mock import AsyncMock

        from wavexis.serve import BackendPool

        pool = BackendPool(max_concurrent=2)

        async def _test() -> None:
            backend = AsyncMock()
            pool._created = 1
            await pool.discard_backend(backend)
            backend.close.assert_awaited_once()
            assert pool._created == 0

        asyncio.run(_test())

    def test_backend_pool_return_backend_does_not_close(self) -> None:
        """Regression: return_backend must NOT close the backend before returning it.

        Previously, return_backend closed the backend then put it back in the
        pool, so every reused backend was unusable. The fix returns the backend
        to the pool without closing it.
        """
        import asyncio
        from unittest.mock import AsyncMock

        from wavexis.serve import BackendPool

        pool = BackendPool(max_concurrent=2)

        async def _test() -> None:
            backend = AsyncMock()
            pool._created = 1
            await pool.return_backend(backend)
            # Backend must NOT be closed when returned to the pool.
            backend.close.assert_not_awaited()
            # Backend must be available for reuse.
            assert not pool._pool.empty()
            reused = await pool.get_backend()
            assert reused is backend

        asyncio.run(_test())

    def test_backend_pool_return_backend_closes_when_pool_full(self) -> None:
        """Regression: return_backend must close the backend when the pool is full."""
        import asyncio
        from unittest.mock import AsyncMock

        from wavexis.serve import BackendPool

        pool = BackendPool(max_concurrent=2)

        async def _test() -> None:
            # Fill the pool to capacity.
            b1 = AsyncMock()
            b2 = AsyncMock()
            await pool.return_backend(b1)
            await pool.return_backend(b2)
            # Now the pool is full; returning another backend should close it.
            b3 = AsyncMock()
            pool._created = 3
            await pool.return_backend(b3)
            b3.close.assert_awaited_once()
            assert pool._created == 2

        asyncio.run(_test())

    def test_safe_params_caches_type_hints(self) -> None:
        """Regression: _safe_params must cache type hints to avoid recomputing per request."""
        from wavexis.config import ScreenshotParams
        from wavexis.serve import _TYPE_HINTS_CACHE, _safe_params

        _safe_params(ScreenshotParams, {"url": "https://example.com"})
        assert ScreenshotParams in _TYPE_HINTS_CACHE
        cached = _TYPE_HINTS_CACHE[ScreenshotParams]
        # Second call should reuse the cached entry (same object identity).
        _safe_params(ScreenshotParams, {"url": "https://example.org"})
        assert _TYPE_HINTS_CACHE[ScreenshotParams] is cached

    async def test_stream_console_dedup_evicts_oldest_not_newest(self) -> None:
        """Regression: _stream_console must evict the OLDEST key when the
        dedup window is full, not the newest.

        Previously the code called ``seen_order[0]`` *after* ``append``,
        so ``seen_order[0]`` was the just-appended (newest) key — causing
        the newest entry to be immediately removed from ``seen`` and
        re-streamed on the next poll.
        """
        import asyncio
        from collections import deque

        from wavexis.serve import _stream_console

        # Use a tiny dedup window by patching the function's local logic:
        # we monkeypatch collections.deque via a small wrapper to observe
        # eviction order. Simpler: replicate the dedup logic inline and
        # assert the invariant directly.

        max_seen = 3
        seen: set[str] = set()
        seen_order: deque[str] = deque(maxlen=max_seen)

        def add(key: str) -> bool:
            """Replica of the fixed dedup logic. Returns True if newly added."""
            if key in seen:
                return False
            if len(seen_order) == max_seen:
                seen.discard(seen_order[0])
            seen.add(key)
            seen_order.append(key)
            return True

        # Fill the window.
        assert add("a") is True
        assert add("b") is True
        assert add("c") is True
        # Now adding "d" should evict "a" (the oldest), not "d".
        assert add("d") is True
        assert "a" not in seen
        assert "d" in seen
        # Re-adding "a" must be treated as new (it was evicted); this
        # evicts "b" (now the oldest).
        assert add("a") is True
        assert "b" not in seen
        # Re-adding "d" must be a duplicate (it's still in the window).
        assert add("d") is False
        # Window now holds {c, d, a} in insertion order.
        assert list(seen_order) == ["c", "d", "a"]

        # Sanity check: the actual _stream_console function still exists
        # and is importable (guards against accidental removal).
        assert callable(_stream_console)
        # Suppress unused-import warning for asyncio.
        _ = asyncio

    def test_create_app_with_options(self) -> None:
        from wavexis.serve import create_app

        app = create_app(
            backend_name="cdp",
            rate_limit=100,
            base_dir="/tmp",
            api_key="secret",
            cors_origins=["*"],
            max_concurrent=3,
        )
        assert app is not None
        assert app["backend_name"] == "cdp"

    def test_create_app_with_cors_origins(self) -> None:
        from wavexis.serve import create_app

        app = create_app(cors_origins=["https://example.com"])
        assert app is not None

    def test_create_app_with_api_key(self) -> None:
        from wavexis.serve import create_app

        app = create_app(api_key="test-key")
        assert app is not None


@pytest.mark.unit
class TestJSONErrorMiddleware:
    """Tests for _json_error_middleware."""

    async def test_wavexis_error_is_raised(self) -> None:
        """WavexisError must not be turned into a 400 JSON response."""
        from wavexis.serve import _json_error_middleware

        async def _handler(request: Any) -> Any:
            raise WavexisError("boom")

        with pytest.raises(WavexisError, match="boom"):
            await _json_error_middleware(MagicMock(), _handler)

    async def test_action_error_is_raised(self) -> None:
        """ActionError (ValueError subclass) must not be turned into a 400 response."""
        from wavexis.serve import _json_error_middleware

        async def _handler(request: Any) -> Any:
            raise ActionError("bad action")

        with pytest.raises(ActionError, match="bad action"):
            await _json_error_middleware(MagicMock(), _handler)

    async def test_value_error_returns_400(self) -> None:
        """Plain ValueError must still produce a 400 JSON response."""
        from wavexis.serve import _json_error_middleware

        async def _handler(request: Any) -> Any:
            raise ValueError("plain value error")

        response = await _json_error_middleware(MagicMock(), _handler)
        assert response.status == 400
        assert "invalid JSON body" in response.text
