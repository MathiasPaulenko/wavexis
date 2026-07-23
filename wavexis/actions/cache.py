"""Action caching for repeating workflows without re-analyzing pages."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheEntry:
    """A single cache entry.

    Attributes:
        value: The cached result value.
        timestamp: When the entry was created (unix epoch seconds).
        ttl: Time-to-live in seconds. 0 = no expiry.
    """

    value: Any
    timestamp: float = field(default_factory=time.time)
    ttl: float = 0.0

    def is_expired(self, now: float | None = None) -> bool:
        """Check if this entry has expired.

        Args:
            now: Current time. Defaults to time.time().

        Returns:
            True if the entry has expired (ttl > 0 and elapsed > ttl).
        """
        if self.ttl <= 0:
            return False
        current = now if now is not None else time.time()
        return (current - self.timestamp) > self.ttl


class ActionCache:
    """In-memory cache for action results.

    Caches results keyed by (url, action_type, params_hash).
    Supports per-entry TTL, invalidation by URL, and global clear.

    Attributes:
        default_ttl: Default TTL in seconds for entries. 0 = no expiry.
    """

    def __init__(self, default_ttl: float = 300.0) -> None:
        """Initialize the action cache.

        Args:
            default_ttl: Default time-to-live in seconds. Default 300 (5 min).
        """
        self._store: dict[str, CacheEntry] = {}
        self._url_index: dict[str, set[str]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self.default_ttl = default_ttl

    @staticmethod
    def _make_key(url: str, action_type: str, params: dict[str, Any]) -> str:
        """Build a cache key from url, action type, and params.

        Args:
            url: The URL the action was run against.
            action_type: The action type name (e.g. "screenshot", "dom").
            params: Action parameters dict.

        Returns:
            A unique cache key string.
        """
        params_json = json.dumps(params, sort_keys=True, default=str)
        params_hash = hashlib.sha256(params_json.encode()).hexdigest()[:16]
        return f"{url}::{action_type}::{params_hash}"

    def get(
        self,
        url: str,
        action_type: str,
        params: dict[str, Any],
    ) -> Any | None:
        """Retrieve a cached result.

        Args:
            url: The URL the action was run against.
            action_type: The action type name.
            params: Action parameters dict.

        Returns:
            The cached value, or None if not found / expired.
        """
        key = self._make_key(url, action_type, params)
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            self._remove(key)
            return None
        return entry.value

    def set(
        self,
        url: str,
        action_type: str,
        params: dict[str, Any],
        value: Any,
        ttl: float | None = None,
    ) -> None:
        """Store a result in the cache.

        Args:
            url: The URL the action was run against.
            action_type: The action type name.
            params: Action parameters dict.
            value: The result to cache.
            ttl: Optional TTL override. Defaults to self.default_ttl.
        """
        key = self._make_key(url, action_type, params)
        effective_ttl = self.default_ttl if ttl is None else ttl
        self._store[key] = CacheEntry(value=value, ttl=effective_ttl)
        if url not in self._url_index:
            self._url_index[url] = set()
        self._url_index[url].add(key)

    def invalidate_url(self, url: str) -> int:
        """Invalidate all cache entries for a given URL.

        Args:
            url: The URL to invalidate.

        Returns:
            Number of entries removed.
        """
        keys = self._url_index.pop(url, set())
        for key in keys:
            self._store.pop(key, None)
        return len(keys)

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries removed.
        """
        count = len(self._store)
        self._store.clear()
        self._url_index.clear()
        return count

    def _remove(self, key: str) -> None:
        """Remove a single entry by key.

        Args:
            key: The cache key to remove.
        """
        self._store.pop(key, None)
        for keys in self._url_index.values():
            keys.discard(key)

    @property
    def size(self) -> int:
        """Return the number of entries in the cache."""
        return len(self._store)
