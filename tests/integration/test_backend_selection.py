"""Integration tests for backend selection."""

from __future__ import annotations

import pytest

from browsix.backend.manager import BackendManager
from browsix.exceptions import BackendNotAvailableError


@pytest.mark.integration
class TestBackendSelectionIntegration:
    """Test suite for backendselectionintegration."""
    def test_list_available_includes_cdp(self) -> None:
        """Test list available includes cdp."""
        manager = BackendManager()
        available = manager.list_available()
        assert "cdp" in available

    def test_select_cdp(self) -> None:
        """Test select cdp."""
        manager = BackendManager()
        backend = manager.select("cdp")
        assert backend is not None

    def test_select_default_returns_cdp(self) -> None:
        """Test select default returns cdp."""
        manager = BackendManager()
        backend = manager.select()
        assert backend is not None

    def test_install_check_returns_versions(self) -> None:
        """Test install check returns versions."""
        manager = BackendManager()
        status = manager.install_check()
        assert "cdp" in status
        assert "bidi" in status
        assert status["cdp"] != "not installed"

    def test_select_unavailable_backend(self) -> None:
        """Test select unavailable backend."""
        manager = BackendManager()
        with pytest.raises(BackendNotAvailableError):
            manager.select("nonexistent")
