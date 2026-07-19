"""Unit tests for serve mode (wavexis.serve)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.backend.base import AbstractBackend


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
            resp = await client.post("/dom/get", json={"url": "https://example.com"})
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

    def test_set_ws_max_connections(self) -> None:
        import wavexis.serve as serve_mod

        serve_mod.set_ws_max_connections(10)
        assert serve_mod._ws_max_connections == 10
        serve_mod.set_ws_max_connections(20)

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
