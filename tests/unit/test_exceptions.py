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
        exc = BackendNotAvailableError("cdp")
        assert "cdp" in str(exc)

    def test_backend_not_available_without_name(self):
        exc = BackendNotAvailableError()
        assert "No backend" in str(exc)

    def test_navigation_error(self):
        exc = NavigationError("https://example.com", "timeout")
        assert "example.com" in str(exc)
        assert "timeout" in str(exc)

    def test_wait_timeout_error(self):
        exc = WaitTimeoutError("load", 30000)
        assert "load" in str(exc)
        assert "30000" in str(exc)

    def test_element_not_found_error(self):
        exc = ElementNotFoundError("#app")
        assert "#app" in str(exc)

    def test_multi_config_error(self):
        exc = MultiConfigError("steps", "missing url")
        assert "steps" in str(exc)
        assert "missing url" in str(exc)
