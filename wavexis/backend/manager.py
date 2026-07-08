"""Backend manager for detecting and selecting available backends."""

from __future__ import annotations

import logging

from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions
from wavexis.exceptions import (
    BackendNotAvailableError,
    BackendNotSupportedError,
)

logger = logging.getLogger(__name__)

_manager: BackendManager | None = None


def get_manager() -> BackendManager:
    """Return the singleton BackendManager instance.

    Returns:
        The shared BackendManager, created on first call.
    """
    global _manager
    if _manager is None:
        _manager = BackendManager()
    return _manager


def reset_manager() -> None:
    """Reset the singleton manager (useful for tests)."""
    global _manager
    _manager = None


class BackendManager:
    """Manages backend availability, selection, and registration.

    Backends (cdpwave, bidiwave) are optional dependencies. The manager
    detects which are installed at runtime via dynamic import.
    """

    def __init__(self) -> None:
        """Initialize the manager and register built-in backends."""
        self._registry: dict[str, type[AbstractBackend]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register built-in backends if their dependencies are available."""
        try:
            from wavexis.backend.cdp import CDPBackend

            self._registry["cdp"] = CDPBackend
        except ImportError:
            pass

        try:
            from wavexis.backend.bidi import BiDiBackend

            self._registry["bidi"] = BiDiBackend
        except ImportError:
            pass

        from wavexis.plugins import get_registry

        for name, backend_cls in get_registry().backends.items():
            self._registry[name] = backend_cls

    def list_available(self) -> list[str]:
        """Return a list of available backend names.

        Returns:
            List of backend names (e.g. ["cdp", "bidi"]).
        """
        return list(self._registry.keys())

    def select(self, preferred: str | None = None) -> AbstractBackend:
        """Select a backend by preference or availability.

        Args:
            preferred: Preferred backend name. If None or unavailable,
                falls back to the first available backend.

        Returns:
            An instance of the selected backend.

        Raises:
            BackendNotAvailableError: If no backend is available.
        """
        available = self.list_available()
        if not available:
            raise BackendNotAvailableError()

        if preferred and preferred in available:
            return self.create(preferred)

        if preferred and preferred not in available:
            raise BackendNotAvailableError(preferred)

        return self.create(available[0])

    async def select_with_fallback(
        self,
        preferred: str | None = None,
        options: BrowserOptions | None = None,
    ) -> AbstractBackend:
        """Select a backend, falling back if the preferred one cannot be created.

        Tries the preferred backend first. If its constructor raises
        (e.g. dependency import fails), tries each remaining available
        backend until one is created successfully.

        Args:
            preferred: Preferred backend name. If None, tries all in order.
            options: Unused (kept for API compatibility). Launch is left to callers.

        Returns:
            A backend instance (not yet launched).

        Raises:
            BackendNotAvailableError: If no backend can be created.
        """
        return self.select_with_fallback_sync(preferred)

    def select_with_fallback_sync(
        self,
        preferred: str | None = None,
        options: BrowserOptions | None = None,
    ) -> AbstractBackend:
        """Synchronous version of select_with_fallback.

        Args:
            preferred: Preferred backend name. If None, tries all in order.
            options: Unused (kept for API compatibility).

        Returns:
            A backend instance (not yet launched).

        Raises:
            BackendNotAvailableError: If no backend can be created.
        """
        available = self.list_available()
        if not available:
            raise BackendNotAvailableError()

        ordered: list[str] = []
        if preferred and preferred in available:
            ordered.append(preferred)
        ordered.extend(b for b in available if b not in ordered)

        last_error: Exception | None = None
        for name in ordered:
            try:
                backend = self.create(name)
                logger.info("Backend '%s' created successfully", name)
                return backend
            except Exception as exc:
                last_error = exc
                logger.warning("Backend '%s' could not be created: %s", name, exc)
                continue

        raise BackendNotAvailableError(
            f"All backends failed to initialize. Last error: {last_error}"
        )

    def create(self, name: str) -> AbstractBackend:
        """Create an instance of a specific backend by name.

        Args:
            name: Backend name (e.g. "cdp", "bidi").

        Returns:
            An instance of the backend.

        Raises:
            BackendNotSupportedError: If the backend name is not registered.
        """
        backend_cls = self._registry.get(name)
        if backend_cls is None:
            raise BackendNotSupportedError(name, "BackendManager")
        return backend_cls()

    def register(self, name: str, backend_cls: type[AbstractBackend]) -> None:
        """Register a custom backend.

        Args:
            name: Backend name to register.
            backend_cls: A class implementing AbstractBackend.
        """
        self._registry[name] = backend_cls

    def install_check(self) -> dict[str, str]:
        """Check which backends are installed and return their versions.

        Returns:
            Dict mapping backend names to version strings or 'not installed'.
        """
        result: dict[str, str] = {}
        try:
            import cdpwave

            result["cdp"] = getattr(cdpwave, "__version__", "installed")
        except ImportError:
            result["cdp"] = "not installed"
        try:
            import bidiwave

            result["bidi"] = getattr(bidiwave, "__version__", "installed")
        except ImportError:
            result["bidi"] = "not installed"
        return result
