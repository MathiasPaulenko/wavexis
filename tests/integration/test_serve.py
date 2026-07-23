"""Integration tests for serve mode against a real HTTP server."""

import aiohttp
import pytest

from wavexis.serve import create_app

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


async def test_serve_health() -> None:
    """Test serve health."""
    app = create_app()
    async with aiohttp.test_utils.TestServer(app) as server, aiohttp.ClientSession() as session:  # noqa: SIM117
        async with session.get(f"http://127.0.0.1:{server.port}/health") as resp:
            assert resp.status == 200
            data = await resp.json()
            assert data == {"status": "ok"}


async def test_serve_version() -> None:
    """Test serve version."""
    app = create_app()
    async with aiohttp.test_utils.TestServer(app) as server, aiohttp.ClientSession() as session:  # noqa: SIM117
        async with session.get(f"http://127.0.0.1:{server.port}/version") as resp:
            assert resp.status == 200
            data = await resp.json()
            assert "version" in data


async def test_serve_backends() -> None:
    """Test serve backends."""
    app = create_app()
    async with aiohttp.test_utils.TestServer(app) as server, aiohttp.ClientSession() as session:  # noqa: SIM117
        async with session.get(f"http://127.0.0.1:{server.port}/backends") as resp:
            assert resp.status == 200
            data = await resp.json()
            assert "cdp" in data
            assert "bidi" in data


async def test_serve_screenshot() -> None:
    """Test serve screenshot."""
    app = create_app()
    async with aiohttp.test_utils.TestServer(app) as server, aiohttp.ClientSession() as session:  # noqa: SIM117
        async with session.post(
            f"http://127.0.0.1:{server.port}/screenshot",
            json={"url": "https://example.com"},
        ) as resp:
            assert resp.status == 200
            assert resp.content_type == "image/png"
            data = await resp.read()
            assert len(data) > 0
            assert data[:4] == b"\x89PNG"


async def test_serve_eval() -> None:
    """Test serve eval with an API key."""
    app = create_app(api_key="test-key")
    async with aiohttp.test_utils.TestServer(app) as server, aiohttp.ClientSession() as session:  # noqa: SIM117
        async with session.post(
            f"http://127.0.0.1:{server.port}/eval",
            headers={"X-API-Key": "test-key"},
            json={
                "url": "https://example.com",
                "expression": "document.title",
            },
        ) as resp:
            assert resp.status == 200
            data = await resp.json()
            assert "result" in data


async def test_serve_perf_metrics() -> None:
    """Test serve perf metrics."""
    app = create_app()
    async with aiohttp.test_utils.TestServer(app) as server, aiohttp.ClientSession() as session:  # noqa: SIM117
        async with session.post(
            f"http://127.0.0.1:{server.port}/perf/metrics",
            json={"url": "https://example.com"},
        ) as resp:
            assert resp.status == 200
            data = await resp.json()
            assert isinstance(data, dict)
