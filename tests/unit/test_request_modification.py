"""Unit tests for request/response modification in-flight (modify_request, modify_response)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCDPModifyRequest:
    """Tests for CDPBackend.modify_request."""

    @pytest.mark.asyncio
    async def test_modify_request_sets_up_fetch_handler(self) -> None:
        """modify_request should enable Fetch domain and register a handler."""
        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        session = MagicMock()
        session.send = AsyncMock()
        session.on = MagicMock()
        backend._session = session

        pattern = {"urlPattern": "*/api/*"}
        modifications = {"method": "POST", "post_data": '{"key":"val"}'}

        await backend.modify_request(pattern, modifications)

        session.on.assert_called_once()
        assert session.on.call_args[0][0] == "Fetch.requestPaused"
        session.send.assert_called_once_with("Fetch.enable", {"patterns": [pattern]})

    @pytest.mark.asyncio
    async def test_modify_request_handler_continues_with_modifications(self) -> None:
        """The Fetch.requestPaused handler should call Fetch.continueRequest with mods."""
        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        session = MagicMock()
        session.send = AsyncMock()
        session.on = MagicMock()
        backend._session = session

        modifications = {"method": "PUT", "post_data": "data"}
        await backend.modify_request({"urlPattern": "*"}, modifications)

        handler = session.on.call_args[0][1]
        event_params = {
            "requestId": "req-123",
            "request": {"url": "https://example.com/api", "method": "GET"},
        }
        await handler(event_params)

        send_call = session.send.call_args
        assert send_call[0][0] == "Fetch.continueRequest"
        params = send_call[0][1]
        assert params["requestId"] == "req-123"
        assert params["method"] == "PUT"
        assert params["postData"] == "data"


class TestCDPModifyResponse:
    """Tests for CDPBackend.modify_response."""

    @pytest.mark.asyncio
    async def test_modify_response_sets_up_fetch_handler(self) -> None:
        """modify_response should enable Fetch domain with Response stage."""
        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        session = MagicMock()
        session.send = AsyncMock()
        session.on = MagicMock()
        backend._session = session

        pattern = {"urlPattern": "*/api/*"}
        modifications = {"status": 404, "body": "Not Found"}

        await backend.modify_response(pattern, modifications)

        session.on.assert_called_once()
        assert session.on.call_args[0][0] == "Fetch.requestPaused"
        send_call = session.send.call_args
        assert send_call[0][0] == "Fetch.enable"
        patterns = send_call[0][1]["patterns"]
        assert patterns[0]["requestStage"] == "Response"

    @pytest.mark.asyncio
    async def test_modify_response_handler_fulfills(self) -> None:
        """The handler should call Fetch.fulfillRequest with modified body."""
        import base64

        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        session = MagicMock()
        session.send = AsyncMock()
        session.on = MagicMock()
        backend._session = session

        modifications = {"status": 200, "body": '{"modified":true}'}
        await backend.modify_response({"urlPattern": "*"}, modifications)

        handler = session.on.call_args[0][1]
        event_params = {"requestId": "req-456"}
        await handler(event_params)

        send_call = session.send.call_args
        assert send_call[0][0] == "Fetch.fulfillRequest"
        params = send_call[0][1]
        assert params["requestId"] == "req-456"
        assert params["responseCode"] == 200
        decoded = base64.b64decode(params["body"]).decode("utf-8")
        assert decoded == '{"modified":true}'

    @pytest.mark.asyncio
    async def test_modify_response_defaults_to_response_stage(self) -> None:
        """modify_response should default requestStage to 'Response'."""
        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        session = MagicMock()
        session.send = AsyncMock()
        session.on = MagicMock()
        backend._session = session

        await backend.modify_response({"urlPattern": "*"}, {"body": "test"})

        patterns = session.send.call_args[0][1]["patterns"]
        assert patterns[0]["requestStage"] == "Response"

    @pytest.mark.asyncio
    async def test_modify_response_serializes_dict_body(self) -> None:
        """modify_response should JSON-serialize dict/list bodies."""
        import base64

        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        session = MagicMock()
        session.send = AsyncMock()
        session.on = MagicMock()
        backend._session = session

        modifications = {"body": {"key": "value"}}
        await backend.modify_response({"urlPattern": "*"}, modifications)

        handler = session.on.call_args[0][1]
        await handler({"requestId": "r1"})

        params = session.send.call_args[0][1]
        decoded = base64.b64decode(params["body"]).decode("utf-8")
        assert '"key"' in decoded
        assert '"value"' in decoded


class TestBiDiModifyResponse:
    """Tests for BiDiBackend.modify_response."""

    @pytest.mark.asyncio
    async def test_bidi_modify_response_uses_cdp_bridge(self) -> None:
        """BiDiBackend.modify_response should use network.add_intercept."""
        from wavexis.backend.bidi import BiDiBackend

        backend = BiDiBackend()
        client = MagicMock()
        client.network = MagicMock()
        client.network.add_intercept = AsyncMock()
        client.network.continue_response = AsyncMock()
        backend._client = client
        backend._context = "ctx-1"

        modifications = {"status": 500, "body": "error"}
        await backend.modify_response({"urlPattern": "*"}, modifications)

        client.network.add_intercept.assert_called_once()


class TestCLIModify:
    """Tests for CLI modify and modify-response commands."""

    @pytest.mark.asyncio
    async def test_modify_stays_open_with_wait(self) -> None:
        """_modify should keep browser open for wait seconds."""
        from wavexis.cli._network_inspect import _modify

        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.modify_request = AsyncMock()

        with (
            patch("wavexis.cli._network_inspect._get_backend", return_value=backend),
            patch("wavexis.cli._network_inspect._browser_options", return_value=MagicMock()),
        ):
            await _modify(
                "https://example.com",
                "*/api/*",
                {"method": "POST"},
                wait=0.01,
            )

            backend.modify_request.assert_called_once()
            backend.navigate.assert_called_once()
            backend.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_modify_response_stays_open_with_wait(self) -> None:
        """_modify_response should keep browser open for wait seconds."""
        from wavexis.cli._network_inspect import _modify_response

        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.modify_response = AsyncMock()

        with (
            patch("wavexis.cli._network_inspect._get_backend", return_value=backend),
            patch("wavexis.cli._network_inspect._browser_options", return_value=MagicMock()),
        ):
            await _modify_response(
                "https://example.com",
                "*/api/*",
                {"status": 404, "body": "Not Found"},
                wait=0.01,
            )

            backend.modify_response.assert_called_once()
            backend.navigate.assert_called_once()
            backend.close.assert_called_once()


class TestServeModifyEndpoints:
    """Tests for serve.py modify-request and modify-response endpoints."""

    @pytest.mark.asyncio
    async def test_handle_modify_request(self) -> None:
        """handle_modify_request should call backend.modify_request."""
        from wavexis.serve import handle_modify_request

        request = MagicMock()
        request.json = AsyncMock(
            return_value={
                "url": "https://example.com",
                "pattern": "*/api/*",
                "modifications": {"method": "POST"},
            }
        )

        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.modify_request = AsyncMock()

        pool = MagicMock()
        pool.acquire = AsyncMock()
        pool.release = MagicMock()
        pool.get_backend = AsyncMock(return_value=backend)
        pool.return_backend = AsyncMock()

        with (
            patch("wavexis.serve._import_aiohttp"),
            patch("wavexis.serve._get_pool", return_value=pool),
        ):
            await handle_modify_request(request)

            backend.modify_request.assert_called_once()
            backend.navigate.assert_called_once()
            pool.return_backend.assert_called_once_with(backend)
            pool.release.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_modify_response(self) -> None:
        """handle_modify_response should call backend.modify_response."""
        from wavexis.serve import handle_modify_response

        request = MagicMock()
        request.json = AsyncMock(
            return_value={
                "url": "https://example.com",
                "pattern": "*/api/*",
                "modifications": {"status": 200, "body": "modified"},
            }
        )

        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.close = AsyncMock()
        backend.navigate = AsyncMock()
        backend.modify_response = AsyncMock()

        pool = MagicMock()
        pool.acquire = AsyncMock()
        pool.release = MagicMock()
        pool.get_backend = AsyncMock(return_value=backend)
        pool.return_backend = AsyncMock()

        with (
            patch("wavexis.serve._import_aiohttp"),
            patch("wavexis.serve._get_pool", return_value=pool),
        ):
            await handle_modify_response(request)

            backend.modify_response.assert_called_once()
            backend.navigate.assert_called_once()
            pool.return_backend.assert_called_once_with(backend)
            pool.release.assert_called_once()
