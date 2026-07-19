"""Unit tests for ActionCache."""

from __future__ import annotations

import time

import pytest

from wavexis.actions.cache import ActionCache, CacheEntry


@pytest.mark.unit
class TestCacheEntry:
    """Tests for CacheEntry expiry logic."""

    def test_no_expiry(self) -> None:
        """Entry with ttl=0 never expires."""
        entry = CacheEntry(value="test", ttl=0.0)
        assert not entry.is_expired()

    def test_not_expired(self) -> None:
        """Entry within TTL is not expired."""
        entry = CacheEntry(value="test", timestamp=time.time(), ttl=10.0)
        assert not entry.is_expired()

    def test_expired(self) -> None:
        """Entry past TTL is expired."""
        entry = CacheEntry(value="test", timestamp=time.time() - 20, ttl=10.0)
        assert entry.is_expired()

    def test_expired_with_explicit_now(self) -> None:
        """Entry expiry checked against explicit now."""
        entry = CacheEntry(value="test", timestamp=100.0, ttl=5.0)
        assert entry.is_expired(now=110.0)
        assert not entry.is_expired(now=103.0)


@pytest.mark.unit
class TestActionCache:
    """Tests for ActionCache get/set/invalidate."""

    def test_set_and_get(self) -> None:
        """Setting and getting returns the cached value."""
        cache = ActionCache(default_ttl=300)
        params = {"url": "https://example.com", "format": "png"}
        cache.set("https://example.com", "screenshot", params, b"image_data")
        result = cache.get("https://example.com", "screenshot", params)
        assert result == b"image_data"

    def test_get_miss(self) -> None:
        """Getting a non-existent key returns None."""
        cache = ActionCache()
        result = cache.get("https://example.com", "screenshot", {})
        assert result is None

    def test_different_params_different_keys(self) -> None:
        """Same URL + action but different params = different cache entries."""
        cache = ActionCache()
        cache.set("https://example.com", "screenshot", {"format": "png"}, b"png")
        cache.set("https://example.com", "screenshot", {"format": "jpeg"}, b"jpeg")
        assert cache.get("https://example.com", "screenshot", {"format": "png"}) == b"png"
        assert cache.get("https://example.com", "screenshot", {"format": "jpeg"}) == b"jpeg"

    def test_different_action_different_keys(self) -> None:
        """Same URL + params but different action = different cache entries."""
        cache = ActionCache()
        params = {"url": "https://example.com"}
        cache.set("https://example.com", "screenshot", params, b"img")
        cache.set("https://example.com", "dom", params, "<html>")
        assert cache.get("https://example.com", "screenshot", params) == b"img"
        assert cache.get("https://example.com", "dom", params) == "<html>"

    def test_invalidate_url(self) -> None:
        """Invalidating by URL removes all entries for that URL."""
        cache = ActionCache()
        params = {"url": "https://example.com"}
        cache.set("https://example.com", "screenshot", params, b"img")
        cache.set("https://example.com", "dom", params, "<html>")
        cache.set("https://other.com", "screenshot", params, b"other")
        removed = cache.invalidate_url("https://example.com")
        assert removed == 2
        assert cache.get("https://example.com", "screenshot", params) is None
        assert cache.get("https://other.com", "screenshot", params) == b"other"

    def test_clear(self) -> None:
        """Clear removes all entries."""
        cache = ActionCache()
        cache.set("https://a.com", "screenshot", {}, b"a")
        cache.set("https://b.com", "dom", {}, b"b")
        removed = cache.clear()
        assert removed == 2
        assert cache.size == 0

    def test_size(self) -> None:
        """Size reflects number of entries."""
        cache = ActionCache()
        assert cache.size == 0
        cache.set("https://a.com", "screenshot", {}, b"a")
        assert cache.size == 1
        cache.set("https://b.com", "dom", {}, b"b")
        assert cache.size == 2

    def test_ttl_expiry(self) -> None:
        """Entries expire after TTL."""
        cache = ActionCache(default_ttl=0.1)
        cache.set("https://example.com", "screenshot", {}, b"img")
        assert cache.get("https://example.com", "screenshot", {}) == b"img"
        time.sleep(0.15)
        assert cache.get("https://example.com", "screenshot", {}) is None

    def test_per_entry_ttl_override(self) -> None:
        """Per-entry TTL overrides default."""
        cache = ActionCache(default_ttl=300)
        cache.set("https://example.com", "screenshot", {}, b"img", ttl=0.1)
        assert cache.get("https://example.com", "screenshot", {}) == b"img"
        time.sleep(0.15)
        assert cache.get("https://example.com", "screenshot", {}) is None

    def test_invalidate_nonexistent_url(self) -> None:
        """Invalidating a URL with no entries returns 0."""
        cache = ActionCache()
        removed = cache.invalidate_url("https://nonexistent.com")
        assert removed == 0
