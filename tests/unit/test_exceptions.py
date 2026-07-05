"""Unit tests for exceptions hierarchy."""

from browsix.exceptions import (
    ActionError,
    BackendNotAvailableError,
    BackendNotSupportedError,
    BrowsixError,
    ElementNotFoundError,
    MultiConfigError,
    NavigationError,
    WaitTimeoutError,
)


class TestExceptions:
    """Tests for browsix exception hierarchy."""

    def test_all_inherit_browsix_error(self):
        """Test all inherit browsix error."""
        for exc_cls in [
            BackendNotAvailableError,
            BackendNotSupportedError,
            NavigationError,
            WaitTimeoutError,
            ElementNotFoundError,
            ActionError,
            MultiConfigError,
        ]:
            assert issubclass(exc_cls, BrowsixError)

    def test_backend_not_available_with_name(self):
        """Test backend not available with name."""
        exc = BackendNotAvailableError("cdp")
        assert "cdp" in str(exc)

    def test_backend_not_available_without_name(self):
        """Test backend not available without name."""
        exc = BackendNotAvailableError()
        assert "No backend" in str(exc)

    def test_navigation_error(self):
        """Test navigation error."""
        exc = NavigationError("https://example.com", "timeout")
        assert "example.com" in str(exc)
        assert "timeout" in str(exc)

    def test_wait_timeout_error(self):
        """Test wait timeout error."""
        exc = WaitTimeoutError("load", 30000)
        assert "load" in str(exc)
        assert "30000" in str(exc)

    def test_element_not_found_error(self):
        """Test element not found error."""
        exc = ElementNotFoundError("#app")
        assert "#app" in str(exc)

    def test_multi_config_error(self):
        """Test multi config error."""
        exc = MultiConfigError("steps", "missing url")
        assert "steps" in str(exc)
        assert "missing url" in str(exc)
