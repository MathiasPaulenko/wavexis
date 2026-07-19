"""Unit tests for CLI error handling and exit codes."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from wavexis.cli.app import (
    EXIT_BACKEND_ERROR,
    EXIT_BROWSER_ERROR,
    EXIT_CONFIG_ERROR,
    EXIT_SUCCESS,
    app,
)
from wavexis.exceptions import (
    BackendNotAvailableError,
    ElementNotFoundError,
    MultiConfigError,
    NavigationError,
    WaitTimeoutError,
    WavexisError,
)

runner = CliRunner()


@pytest.mark.unit
class TestExitCodes:
    """Test suite for exitcodes."""

    def test_exit_code_constants(self) -> None:
        """Test exit code constants."""
        assert EXIT_SUCCESS == 0
        assert EXIT_BROWSER_ERROR == 1
        assert EXIT_CONFIG_ERROR == 2
        assert EXIT_BACKEND_ERROR == 3


@pytest.mark.unit
class TestVersionFlag:
    """Test suite for versionflag."""

    def test_version_flag(self) -> None:
        """Test version flag."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == EXIT_SUCCESS
        assert "wavexis v" in result.stdout


@pytest.mark.unit
class TestErrorHandling:
    """Test suite for errorhandling."""

    def test_backend_not_available_error(self) -> None:
        """Test backend not available error."""
        with patch(
            "wavexis.cli._capture._get_backend",
            side_effect=BackendNotAvailableError(),
        ):
            result = runner.invoke(app, ["screenshot", "https://example.com"])
            assert result.exit_code == EXIT_BACKEND_ERROR

    def test_navigation_error(self) -> None:
        """Test navigation error."""
        with patch(
            "wavexis.cli._capture._get_backend",
            side_effect=NavigationError("https://example.com", "timeout"),
        ):
            result = runner.invoke(app, ["screenshot", "https://example.com"])
            assert result.exit_code == EXIT_BROWSER_ERROR

    def test_wait_timeout_error(self) -> None:
        """Test wait timeout error."""
        with patch(
            "wavexis.cli._capture._get_backend",
            side_effect=WaitTimeoutError("load", 30000),
        ):
            result = runner.invoke(app, ["screenshot", "https://example.com"])
            assert result.exit_code == EXIT_BROWSER_ERROR

    def test_element_not_found_error(self) -> None:
        """Test element not found error."""
        with patch(
            "wavexis.cli._capture._get_backend",
            side_effect=ElementNotFoundError("#nonexistent"),
        ):
            result = runner.invoke(app, ["screenshot", "https://example.com"])
            assert result.exit_code == EXIT_BROWSER_ERROR

    def test_multi_config_error(self) -> None:
        """Test multi config error."""
        with patch(
            "wavexis.cli._workflow._get_backend",
            side_effect=MultiConfigError("actions", "missing key"),
        ):
            result = runner.invoke(app, ["multi", "config.yml"])
            assert result.exit_code == EXIT_CONFIG_ERROR

    def test_generic_wavexis_error(self) -> None:
        """Test generic wavexis error."""
        with patch(
            "wavexis.cli._capture._get_backend",
            side_effect=WavexisError("something went wrong"),
        ):
            result = runner.invoke(app, ["screenshot", "https://example.com"])
            assert result.exit_code == EXIT_BROWSER_ERROR
