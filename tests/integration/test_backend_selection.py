"""Integration tests for backend selection."""

from __future__ import annotations

import pytest

from browsix.backend.manager import BackendManager
from browsix.exceptions import BackendNotAvailableError


@pytest.mark.integration
class TestBackendSelectionIntegration:
    def test_list_available_includes_cdp(self) -> None:
        manager = BackendManager()
        available = manager.list_available()
        assert "cdp" in available

    def test_select_cdp(self) -> None:
        manager = BackendManager()
        backend = manager.select("cdp")
        assert backend is not None

    def test_select_default_returns_cdp(self) -> None:
        manager = BackendManager()
        backend = manager.select()
        assert backend is not None

    def test_install_check_returns_versions(self) -> None:
        manager = BackendManager()
        status = manager.install_check()
        assert "cdp" in status
        assert "bidi" in status
        assert status["cdp"] != "not installed"

    def test_select_unavailable_backend(self) -> None:
        manager = BackendManager()
        with pytest.raises(BackendNotAvailableError):
            manager.select("nonexistent")
