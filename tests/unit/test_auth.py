"""Unit tests for auth module."""

import json
from pathlib import Path

import pytest

from browsix.auth import AuthContext, load_auth, load_auth_context, load_headers


class TestLoadAuthContext:
    """Tests for load_auth_context."""

    @pytest.mark.unit
    def test_load_full_context(self, tmp_path: Path):
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
        path = tmp_path / "empty.json"
        path.write_text("{}", encoding="utf-8")

        ctx = load_auth_context(str(path))
        assert ctx.cookies == []
        assert ctx.headers == {}
        assert ctx.username is None
        assert ctx.password is None


class TestLoadAuth:
    """Tests for load_auth."""

    @pytest.mark.unit
    def test_load_cookies_list(self, tmp_path: Path):
        data = [{"name": "c1", "value": "v1"}]
        path = tmp_path / "cookies.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        cookies = load_auth(str(path))
        assert cookies == [{"name": "c1", "value": "v1"}]

    @pytest.mark.unit
    def test_load_cookies_from_key(self, tmp_path: Path):
        data = {"cookies": [{"name": "c2", "value": "v2"}]}
        path = tmp_path / "auth.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        cookies = load_auth(str(path))
        assert cookies == [{"name": "c2", "value": "v2"}]

    @pytest.mark.unit
    def test_load_cookies_empty(self, tmp_path: Path):
        path = tmp_path / "empty.json"
        path.write_text("{}", encoding="utf-8")

        cookies = load_auth(str(path))
        assert cookies == []


class TestLoadHeaders:
    """Tests for load_headers."""

    @pytest.mark.unit
    def test_load_headers_dict(self, tmp_path: Path):
        data = {"X-API-Key": "secret", "Authorization": "Bearer token"}
        path = tmp_path / "headers.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        headers = load_headers(str(path))
        assert headers == {"X-API-Key": "secret", "Authorization": "Bearer token"}

    @pytest.mark.unit
    def test_load_headers_from_key(self, tmp_path: Path):
        data = {"headers": {"X-Custom": "val"}}
        path = tmp_path / "config.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        headers = load_headers(str(path))
        assert headers == {"X-Custom": "val"}

    @pytest.mark.unit
    def test_load_headers_empty(self, tmp_path: Path):
        path = tmp_path / "empty.json"
        path.write_text("{}", encoding="utf-8")

        headers = load_headers(str(path))
        assert headers == {}


class TestAuthContext:
    """Tests for AuthContext dataclass."""

    @pytest.mark.unit
    def test_defaults(self):
        ctx = AuthContext()
        assert ctx.cookies == []
        assert ctx.headers == {}
        assert ctx.username is None
        assert ctx.password is None
