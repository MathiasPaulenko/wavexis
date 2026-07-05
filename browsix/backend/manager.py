"""Backend manager for detecting and selecting available backends."""

from __future__ import annotations

from browsix.backend.base import AbstractBackend
from browsix.exceptions import BackendNotAvailableError, BackendNotSupportedError


class BackendManager:
    """Manages backend availability, selection, and registration.

    Backends (cdpwave, bidiwave) are optional dependencies. The manager
    detects which are installed at runtime via dynamic import.
    """

    def __init__(self) -> None:
        self._registry: dict[str, type[AbstractBackend]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register built-in backends if their dependencies are available."""
        try:
            from browsix.backend.cdp import CDPBackend

            self._registry["cdp"] = CDPBackend
        except ImportError:
            pass

        try:
            from browsix.backend.bidi import BiDiBackend

            self._registry["bidi"] = BiDiBackend
        except ImportError:
            pass

        from browsix.plugins import get_registry

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
            import cdpwave  # type: ignore[import-not-found,unused-ignore]

            result["cdp"] = getattr(cdpwave, "__version__", "installed")
        except ImportError:
            result["cdp"] = "not installed"
        try:
            import bidiwave  # type: ignore[import-not-found,unused-ignore]

            result["bidi"] = getattr(bidiwave, "__version__", "installed")
        except ImportError:
            result["bidi"] = "not installed"
        return result
