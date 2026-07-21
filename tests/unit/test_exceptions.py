"""Unit tests for exceptions hierarchy."""

from wavexis.exceptions import (
    ActionError,
    BackendNotAvailableError,
    BackendNotSupportedError,
    ElementNotFoundError,
    MultiConfigError,
    NavigationError,
    SessionNotInitializedError,
    WaitTimeoutError,
    WavexisError,
)


class TestExceptions:
    """Tests for wavexis exception hierarchy."""

    def test_all_inherit_wavexis_error(self):
        """Test all inherit wavexis error."""
        for exc_cls in [
            BackendNotAvailableError,
            BackendNotSupportedError,
            NavigationError,
            WaitTimeoutError,
            ElementNotFoundError,
            ActionError,
            MultiConfigError,
            SessionNotInitializedError,
        ]:
            assert issubclass(exc_cls, WavexisError)

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

    def test_session_not_initialized_default_message(self):
        """Test session not initialized default message."""
        exc = SessionNotInitializedError()
        assert "launch()" in str(exc)
        assert "Hint" in str(exc)

    def test_session_not_initialized_custom_message(self):
        """Test session not initialized custom message."""
        exc = SessionNotInitializedError("custom reason")
        assert "custom reason" in str(exc)

    def test_backend_not_supported_error(self):
        """Test backend not supported error."""
        exc = BackendNotSupportedError("some_method", "my_backend")
        assert "some_method" in str(exc)
        assert "my_backend" in str(exc)

    def test_action_error_is_value_error(self):
        """Test that ActionError is also a ValueError."""
        assert issubclass(ActionError, ValueError)
        exc = ActionError("bad action")
        assert isinstance(exc, ValueError)
        assert "bad action" in str(exc)
