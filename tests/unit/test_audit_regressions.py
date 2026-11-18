"""Regression tests for bugs found in the stabilization audit.

Each test pins a specific defect that was repaired:
- Rich markup injection / MarkupError in Output.error/success/info
- PDF margin parsing (unit conversion, malformed input)
- WebSocket subscribe-config validation (url scheme, events type, NaN interval)
- Plugin discovery surviving load/registration failures
- Auth context rejecting non-string credential fields
- ActionCache lock pruning on entry removal / clear
- Backend close() continuing past a failing close step
- REPL surfacing parse errors instead of swallowing them
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


class TestRichMarkupEscaping:
    """Output helpers must not interpret user text as Rich markup."""

    def test_safe_markup_escapes_brackets(self) -> None:
        from wavexis.output import _escape_markup, _safe_markup

        if _escape_markup is None:
            pytest.skip("rich not installed")
        assert _safe_markup("file [/bold] missing") != "file [/bold] missing"
        assert "[/bold]" not in _safe_markup("[/bold]") or "\\" in _safe_markup("[/bold]")

    def test_error_with_malicious_markup_does_not_raise(self, capsys: Any) -> None:
        from wavexis.output import Output

        # "[/]" is an unbalanced closing tag — previously raised MarkupError
        # inside the error-reporting path itself.
        Output.error("weird value [/] not allowed")
        err = capsys.readouterr().err
        assert "weird value" in err

    def test_success_with_markup_does_not_raise(self, capsys: Any) -> None:
        from wavexis.output import Output

        Output.success("wrote [bold]not-bold[/] file")
        out = capsys.readouterr().out
        assert "not-bold" in out


class TestParseMarginInches:
    """PDF margins must honor CSS units and survive malformed input."""

    def test_inches(self) -> None:
        from wavexis.config import _parse_margin_inches

        assert _parse_margin_inches("0.4in") == pytest.approx(0.4)

    def test_millimeters_convert_to_inches(self) -> None:
        from wavexis.config import _parse_margin_inches

        assert _parse_margin_inches("10mm") == pytest.approx(10 / 25.4)

    def test_centimeters_convert_to_inches(self) -> None:
        from wavexis.config import _parse_margin_inches

        assert _parse_margin_inches("1cm") == pytest.approx(1 / 2.54)

    def test_pixels_convert_to_inches(self) -> None:
        from wavexis.config import _parse_margin_inches

        assert _parse_margin_inches("96px") == pytest.approx(1.0)

    def test_bare_number_is_inches(self) -> None:
        from wavexis.config import _parse_margin_inches

        assert _parse_margin_inches("0.5") == pytest.approx(0.5)

    @pytest.mark.parametrize("bad", ["..", "abc", "", "in", "mm"])
    def test_malformed_falls_back_to_default(self, bad: str) -> None:
        from wavexis.config import _parse_margin_inches

        assert _parse_margin_inches(bad) == pytest.approx(0.4)

    def test_malformed_does_not_raise(self) -> None:
        from wavexis.config import _parse_margin_inches

        # Previously float("1.2.3") inside pdf() raised ValueError.
        assert _parse_margin_inches("1.2.3") == pytest.approx(1.2)

    def test_non_string_falls_back(self) -> None:
        from wavexis.config import _parse_margin_inches

        assert _parse_margin_inches(None) == pytest.approx(0.4)  # type: ignore[arg-type]


class TestWebsocketConfigValidation:
    """WS subscribe config must be validated like the HTTP endpoints."""

    def _client(self) -> Any:
        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        app = create_app(api_key="test-key")
        return TestClient(TestServer(app), headers={"Authorization": "Bearer test-key"})

    async def _subscribe_and_read_error(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = self._client()
        await client.start_server()
        try:
            ws = await client.ws_connect("/ws")
            await ws.send_json(payload)
            msg = await ws.receive_json(timeout=5)
            await ws.close()
            return msg
        finally:
            await client.close()

    async def test_rejects_file_scheme_url(self) -> None:
        msg = await self._subscribe_and_read_error(
            {"url": "file:///etc/passwd", "events": ["screenshot"], "interval": 1}
        )
        assert msg["type"] == "error"

    async def test_rejects_javascript_scheme_url(self) -> None:
        msg = await self._subscribe_and_read_error(
            {"url": "javascript:alert(1)", "events": ["screenshot"], "interval": 1}
        )
        assert msg["type"] == "error"

    async def test_rejects_non_string_url(self) -> None:
        msg = await self._subscribe_and_read_error(
            {"url": 123, "events": ["screenshot"], "interval": 1}
        )
        assert msg["type"] == "error"

    async def test_rejects_nan_interval(self) -> None:
        msg = await self._subscribe_and_read_error(
            {"url": "https://example.com", "events": ["screenshot"], "interval": "nan"}
        )
        assert msg["type"] == "error"

    async def test_rejects_inf_interval(self) -> None:
        msg = await self._subscribe_and_read_error(
            {"url": "https://example.com", "events": ["screenshot"], "interval": "inf"}
        )
        assert msg["type"] == "error"

    async def test_rejects_non_list_events(self) -> None:
        msg = await self._subscribe_and_read_error(
            {"url": "https://example.com", "events": "screenshot", "interval": 1}
        )
        assert msg["type"] == "error"
        assert "events" in msg["message"]

    async def test_rejects_non_string_event_entries(self) -> None:
        msg = await self._subscribe_and_read_error(
            {"url": "https://example.com", "events": [123], "interval": 1}
        )
        assert msg["type"] == "error"


class TestPluginDiscoveryRobustness:
    """A broken plugin must not abort discovery of the rest."""

    def test_load_exception_skips_plugin(self) -> None:
        from wavexis.plugins import PluginRegistry, _discover_entry_points

        good = MagicMock()
        good.name = "good"
        good.load.return_value = MagicMock()  # unknown type → skipped cleanly

        bad = MagicMock()
        bad.name = "bad"
        bad.load.side_effect = RuntimeError("plugin exploded")

        with patch(
            "wavexis.plugins.entry_points", return_value=[bad, good]
        ):
            registry = _discover_entry_points()

        assert isinstance(registry, PluginRegistry)

    def test_hook_constructor_exception_skips_plugin(self) -> None:
        from wavexis.plugins import Plugin, _discover_entry_points

        class _ExplodingPlugin(Plugin):
            def __init__(self) -> None:
                raise RuntimeError("ctor exploded")

        ep = MagicMock()
        ep.name = "exploding"
        ep.load.return_value = _ExplodingPlugin

        with patch("wavexis.plugins.entry_points", return_value=[ep]):
            registry = _discover_entry_points()

        assert registry.hooks == []


class TestAuthContextValidation:
    """Credential fields must be strings, not arbitrary JSON values."""

    def _write(self, tmp_path: Path, payload: dict[str, Any]) -> str:
        path = tmp_path / "ctx.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return str(path)

    def test_rejects_non_string_target_origin(self, tmp_path: Path) -> None:
        from wavexis.auth import load_auth_context

        path = self._write(tmp_path, {"target_origin": {"evil": True}})
        with pytest.raises(ValueError, match="target_origin"):
            load_auth_context(path)

    def test_rejects_non_string_username(self, tmp_path: Path) -> None:
        from wavexis.auth import load_auth_context

        path = self._write(tmp_path, {"username": ["admin"], "password": "x"})
        with pytest.raises(ValueError, match="username"):
            load_auth_context(path)

    def test_rejects_non_string_password(self, tmp_path: Path) -> None:
        from wavexis.auth import load_auth_context

        path = self._write(tmp_path, {"password": 12345})
        with pytest.raises(ValueError, match="password"):
            load_auth_context(path)


class TestActionCacheLockPruning:
    """Per-key locks must not accumulate forever."""

    def test_remove_drops_unlocked_lock(self) -> None:
        from wavexis.actions.cache import ActionCache

        cache = ActionCache()
        params = {"k": "v"}
        key = cache._make_key("https://x.com", "dom", params)
        cache._locks[key] = __import__("asyncio").Lock()
        cache.set("https://x.com", "dom", params, "value")
        cache._remove(key)
        assert key not in cache._locks

    def test_remove_keeps_locked_lock(self) -> None:
        import asyncio

        from wavexis.actions.cache import ActionCache

        cache = ActionCache()
        params = {"k": "v"}
        key = cache._make_key("https://x.com", "dom", params)
        lock = asyncio.Lock()
        cache._locks[key] = lock
        cache.set("https://x.com", "dom", params, "value")

        async def _run() -> None:
            async with lock:
                cache._remove(key)

        asyncio.run(_run())
        assert key in cache._locks

    def test_clear_drops_unlocked_locks(self) -> None:
        import asyncio

        from wavexis.actions.cache import ActionCache

        cache = ActionCache()
        unlocked = asyncio.Lock()
        cache._locks["k1"] = unlocked
        cache.set("https://x.com", "dom", {}, "value")
        cache.clear()
        assert "k1" not in cache._locks


class TestBackendCloseResilience:
    """close() must attempt every resource even when a step fails."""

    async def test_cdp_close_still_closes_client_on_session_failure(self) -> None:
        from wavexis.backend.cdp import CDPBackend

        backend = CDPBackend()
        session = MagicMock()
        session.off = MagicMock()
        session.close = AsyncMock(side_effect=RuntimeError("session exploded"))
        client = MagicMock()
        client.close = AsyncMock()

        backend._session = session
        backend._client = client

        with pytest.raises(RuntimeError, match="session exploded"):
            await backend.close()

        client.close.assert_awaited_once()
        assert backend._client is None
        assert backend._session is None

    async def test_bidi_close_still_closes_client_on_context_failure(self) -> None:
        from wavexis.backend.bidi import BiDiBackend

        backend = BiDiBackend()
        client = MagicMock()
        client.off = MagicMock()
        client.browsing.close = AsyncMock(side_effect=RuntimeError("ctx exploded"))
        client.close = AsyncMock()
        backend._client = client
        backend._context = "ctx-1"

        with pytest.raises(RuntimeError, match="ctx exploded"):
            await backend.close()

        client.close.assert_awaited_once()
        assert backend._client is None


class TestReplErrorFeedback:
    """Parse errors must surface a message instead of silently ignoring input."""

    async def test_parse_error_is_reported(self) -> None:
        from wavexis.repl import repl_loop

        backend = MagicMock()
        backend.launch = AsyncMock()

        lines = iter(['click "unclosed', "exit"])
        outputs: list[str] = []

        await repl_loop(
            backend,
            input_fn=lambda _prompt: next(lines),
            output_fn=outputs.append,
        )

        assert any("Error:" in line for line in outputs)


class TestReplUnexpectedExceptions:
    """An unexpected command error must not kill the interactive loop."""

    async def test_loop_survives_type_error(self) -> None:
        from wavexis.repl import repl_loop

        backend = MagicMock()
        backend.launch = AsyncMock()

        lines = iter(["screenshot", "exit"])
        outputs: list[str] = []

        with patch(
            "wavexis.repl.execute_repl_command",
            new_callable=AsyncMock,
            side_effect=[TypeError("backend exploded"), "__EXIT__"],
        ):
            executed = await repl_loop(
                backend,
                input_fn=lambda _prompt: next(lines),
                output_fn=outputs.append,
            )

        assert any("backend exploded" in line for line in outputs)
        # The loop kept running: the error line wasn't appended, and "exit"
        # was still processed (otherwise it would hang on StopIteration).
        assert executed == []


class TestSessionDataValidation:
    """Malformed session files must raise WavexisError, not AttributeError."""

    def test_non_dict_cookie_entry_rejected(self) -> None:
        from wavexis.actions.session import SessionData
        from wavexis.exceptions import WavexisError

        with pytest.raises(WavexisError):
            SessionData.from_json('{"cookies": ["not-a-dict"]}')

    def test_non_string_storage_values_rejected(self) -> None:
        from wavexis.actions.session import SessionData
        from wavexis.exceptions import WavexisError

        with pytest.raises(WavexisError):
            SessionData.from_json('{"local_storage": {"k": 123}}')

    def test_valid_session_round_trips(self) -> None:
        from wavexis.actions.session import SessionData

        data = SessionData(
            cookies=[{"name": "a", "value": "b"}],
            local_storage={"k": "v"},
            session_storage={},
            url="https://example.com",
        )
        restored = SessionData.from_json(data.to_json())
        assert restored.cookies == data.cookies
        assert restored.local_storage == {"k": "v"}


class TestMultiConfigSizeLimit:
    """Oversized YAML configs must be rejected before reading fully."""

    def test_oversized_config_rejected(self, tmp_path: Path) -> None:
        from wavexis.exceptions import MultiConfigError
        from wavexis.multi import _MAX_CONFIG_BYTES, parse_yaml

        big = tmp_path / "big.yml"
        # Sparse write: header + a huge comment padding past the limit.
        with big.open("wb") as f:
            f.write(b"actions: []\n# ")
            f.write(b"x" * (_MAX_CONFIG_BYTES + 1))
        with pytest.raises(MultiConfigError, match="exceeds"):
            parse_yaml(big)


class TestBackendPoolSlotAccounting:
    """The pool semaphore must never leak slots, even under cancellation."""

    def _pool(self) -> Any:
        pytest.importorskip("aiohttp")
        from wavexis.serve import BackendPool

        return BackendPool(max_concurrent=1)

    async def test_cancelled_get_backend_releases_slot(self) -> None:
        import asyncio

        pool = self._pool()

        async def _slow_select(_preferred: Any = None) -> Any:
            await asyncio.sleep(10)

        with patch(
            "wavexis.serve.get_manager"
        ) as mgr:
            mgr.return_value.select_with_fallback = _slow_select
            task = asyncio.ensure_future(pool.get_backend())
            await asyncio.sleep(0.05)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        # Slot must be reusable after cancellation.
        async def _fast_select(_preferred: Any = None) -> Any:
            return MagicMock()

        with patch("wavexis.serve.get_manager") as mgr:
            mgr.return_value.select_with_fallback = _fast_select
            backend = await asyncio.wait_for(pool.get_backend(), timeout=2)
        assert backend is not None
        assert pool._created == 1

    async def test_failed_creation_releases_slot(self) -> None:
        import asyncio

        pool = self._pool()

        async def _boom(_preferred: Any = None) -> Any:
            raise RuntimeError("no browsers")

        with patch("wavexis.serve.get_manager") as mgr:
            mgr.return_value.select_with_fallback = _boom
            with pytest.raises(RuntimeError):
                await pool.get_backend()
            assert pool._created == 0

        async def _fast_select(_preferred: Any = None) -> Any:
            return MagicMock()

        with patch("wavexis.serve.get_manager") as mgr:
            mgr.return_value.select_with_fallback = _fast_select
            backend = await asyncio.wait_for(pool.get_backend(), timeout=2)
        assert backend is not None

    async def test_return_backend_releases_slot_on_sanitize_failure(
        self, monkeypatch: Any
    ) -> None:
        import asyncio

        pool = self._pool()
        backend = MagicMock()
        backend.is_connected = True

        async def _bad_sanitize(_b: Any) -> None:
            raise RuntimeError("sanitize exploded")

        monkeypatch.setattr("wavexis.serve._sanitize_backend", _bad_sanitize)

        # Acquire the only slot manually, then return the backend.
        await pool._semaphore.acquire()
        await pool.return_backend(backend)

        # The slot must be free again despite the sanitization failure —
        # wait_for raises TimeoutError if the semaphore were still held.
        await asyncio.wait_for(pool._semaphore.acquire(), timeout=2)
        assert pool._created == 0


class TestScrapeCsvRows:
    """CSV output must not 500 when scrape results aren't dicts."""

    async def test_non_dict_rows_fall_back_to_json(self) -> None:
        pytest.importorskip("aiohttp")
        from aiohttp.test_utils import TestClient, TestServer

        from wavexis.serve import create_app

        mock_backend = MagicMock()
        mock_backend.launch = AsyncMock()
        mock_backend.close = AsyncMock()
        mock_backend.navigate = AsyncMock()

        app = create_app()
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            with (
                patch(
                    "wavexis.backend.manager.BackendManager.select_with_fallback",
                    new_callable=AsyncMock,
                    return_value=mock_backend,
                ),
                patch(
                    "wavexis.actions.scrape.ScrapeAction.execute",
                    new_callable=AsyncMock,
                    return_value=["not", "dicts"],
                ),
            ):
                resp = await client.post(
                    "/scrape",
                    json={
                        "urls": ["https://example.com"],
                        "expression": "document.title",
                        "output_format": "csv",
                    },
                )
            assert resp.status == 200
            assert resp.content_type == "application/json"
        finally:
            await client.close()
