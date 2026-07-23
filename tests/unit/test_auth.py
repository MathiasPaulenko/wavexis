"""Unit tests for auth module."""

import json
from pathlib import Path

import pytest

from wavexis.auth import AuthContext, load_auth, load_auth_context, load_headers


class TestLoadAuthContext:
    """Tests for load_auth_context."""

    @pytest.mark.unit
    def test_load_full_context(self, tmp_path: Path):
        """Test load full context."""
        data = {
            "cookies": [{"name": "session", "value": "abc"}],
            "headers": {"X-Custom": "value"},
            "username": "user",
            "password": "pass",
        }
        path = tmp_path / "auth.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        ctx = load_auth_context(str(path))
        assert ctx.cookies == [{"name": "session", "value": "abc"}]
        assert ctx.headers == {"X-Custom": "value"}
        assert ctx.username == "user"
        assert ctx.password == "pass"

    @pytest.mark.unit
    def test_load_empty_context(self, tmp_path: Path):
        """Test load empty context."""
        path = tmp_path / "empty.json"
        path.write_text("{}", encoding="utf-8")

        ctx = load_auth_context(str(path))
        assert ctx.cookies == []
        assert ctx.headers == {}
        assert ctx.username is None
        assert ctx.password is None

    @pytest.mark.unit
    def test_load_invalid_top_level_raises(self, tmp_path: Path):
        """Reject non-object auth context files."""
        path = tmp_path / "bad.json"
        path.write_text('"not-an-object"', encoding="utf-8")

        with pytest.raises(ValueError):
            load_auth_context(str(path))

    @pytest.mark.unit
    def test_load_oversized_file_raises(self, tmp_path: Path):
        """Reject auth files that exceed the size guard."""
        path = tmp_path / "huge.json"
        # Create a file that is just over the 1 MB guard
        path.write_bytes(b'{"x": "' + b"0" * (1_000_001) + b'"}')

        with pytest.raises(ValueError, match="exceeds maximum size"):
            load_auth_context(str(path))

    @pytest.mark.unit
    def test_load_invalid_cookie_raises(self, tmp_path: Path):
        """Reject cookies missing required name/value keys."""
        data = {"cookies": [{"name": "session"}, {"value": "abc"}]}
        path = tmp_path / "bad_cookies.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        with pytest.raises(ValueError, match="'name' and 'value'"):
            load_auth_context(str(path))


class TestLoadAuth:
    """Tests for load_auth."""

    @pytest.mark.unit
    def test_load_cookies_list(self, tmp_path: Path):
        """Test load cookies list."""
        data = [{"name": "c1", "value": "v1"}]
        path = tmp_path / "cookies.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        cookies = load_auth(str(path))
        assert cookies == [{"name": "c1", "value": "v1"}]

    @pytest.mark.unit
    def test_load_cookies_from_key(self, tmp_path: Path):
        """Test load cookies from key."""
        data = {"cookies": [{"name": "c2", "value": "v2"}]}
        path = tmp_path / "auth.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        cookies = load_auth(str(path))
        assert cookies == [{"name": "c2", "value": "v2"}]

    @pytest.mark.unit
    def test_load_cookies_empty(self, tmp_path: Path):
        """Test load cookies empty."""
        path = tmp_path / "empty.json"
        path.write_text("{}", encoding="utf-8")

        cookies = load_auth(str(path))
        assert cookies == []

    @pytest.mark.unit
    def test_load_invalid_top_level_raises(self, tmp_path: Path):
        """Reject JSON values that are neither a list nor an object."""
        path = tmp_path / "bad.json"
        path.write_text("42", encoding="utf-8")

        with pytest.raises(ValueError):
            load_auth(str(path))


class TestLoadHeaders:
    """Tests for load_headers."""

    @pytest.mark.unit
    def test_load_headers_dict(self, tmp_path: Path):
        """Test load headers dict."""
        data = {"X-API-Key": "secret", "Authorization": "Bearer token"}
        path = tmp_path / "headers.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        headers = load_headers(str(path))
        assert headers == {"X-API-Key": "secret", "Authorization": "Bearer token"}

    @pytest.mark.unit
    def test_load_headers_from_key(self, tmp_path: Path):
        """Test load headers from key."""
        data = {"headers": {"X-Custom": "val"}}
        path = tmp_path / "config.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        headers = load_headers(str(path))
        assert headers == {"X-Custom": "val"}

    @pytest.mark.unit
    def test_load_headers_empty(self, tmp_path: Path):
        """Test load headers empty."""
        path = tmp_path / "empty.json"
        path.write_text("{}", encoding="utf-8")

        headers = load_headers(str(path))
        assert headers == {}

    @pytest.mark.unit
    def test_load_invalid_top_level_raises(self, tmp_path: Path):
        """Reject non-object headers files."""
        path = tmp_path / "bad.json"
        path.write_text('["not-an-object"]', encoding="utf-8")

        with pytest.raises(ValueError):
            load_headers(str(path))


class TestAuthContext:
    """Tests for AuthContext dataclass."""

    @pytest.mark.unit
    def test_defaults(self):
        """Test defaults."""
        ctx = AuthContext()
        assert ctx.cookies == []
        assert ctx.headers == {}
        assert ctx.username is None
        assert ctx.password is None
        assert ctx.target_origin is None

    @pytest.mark.unit
    async def test_target_origin_ignores_cookie_domains(self):
        """When target_origin is set, cookie domains must not bypass it."""
        from wavexis.auth import apply_auth_context
        from wavexis.exceptions import WavexisError

        class _FakeBackend:
            async def set_headers(self, headers): ...
            async def set_cookie(self, cookie): ...
            async def navigate(self, url, wait=None): ...

        ctx = AuthContext(
            target_origin="https://example.com",
            cookies=[{"name": "session", "value": "x", "domain": "evil.com"}],
        )
        with pytest.raises(WavexisError, match="required target_origin"):
            await apply_auth_context(_FakeBackend(), ctx, "https://evil.com")

    @pytest.mark.unit
    async def test_rejects_data_url(self):
        """data: URLs cannot carry auth credentials."""
        from wavexis.auth import apply_auth_context
        from wavexis.exceptions import WavexisError

        class _FakeBackend:
            async def set_headers(self, headers): ...
            async def set_cookie(self, cookie): ...
            async def navigate(self, url, wait=None): ...

        ctx = AuthContext(target_origin="data:text/html,<html></html>")
        data_url = "data:text/html,<script>alert(1)</script>"
        with pytest.raises(WavexisError, match="cannot be applied"):
            await apply_auth_context(_FakeBackend(), ctx, data_url)

    @pytest.mark.unit
    async def test_rejects_cookie_domain_with_scheme(self):
        """Cookie domains must be plain hosts, not origins."""
        from wavexis.auth import apply_auth_context
        from wavexis.exceptions import WavexisError

        class _FakeBackend:
            async def set_headers(self, headers): ...
            async def set_cookie(self, cookie): ...
            async def navigate(self, url, wait=None): ...

        ctx = AuthContext(cookies=[{"name": "session", "value": "x", "domain": "https://evil.com"}])
        with pytest.raises(WavexisError, match="plain host"):
            await apply_auth_context(_FakeBackend(), ctx, "https://example.com")
