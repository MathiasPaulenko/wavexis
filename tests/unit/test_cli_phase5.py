"""Unit tests for CLI Phase 5 commands."""


import pytest
from typer.testing import CliRunner

from wavexis.cli.app import app

runner = CliRunner()


@pytest.mark.unit
class TestCLIInputCommands:
    """Test suite for cliinputcommands."""
    def test_input_click_help(self) -> None:
        """Test input click help."""
        result = runner.invoke(app, ["input", "click", "--help"])
        assert result.exit_code == 0
        assert "Click" in result.stdout

    def test_input_type_help(self) -> None:
        """Test input type help."""
        result = runner.invoke(app, ["input", "type", "--help"])
        assert result.exit_code == 0
        assert "Type" in result.stdout

    def test_input_fill_help(self) -> None:
        """Test input fill help."""
        result = runner.invoke(app, ["input", "fill", "--help"])
        assert result.exit_code == 0
        assert "Fill" in result.stdout

    def test_input_tap_help(self) -> None:
        """Test input tap help."""
        result = runner.invoke(app, ["input", "tap", "--help"])
        assert result.exit_code == 0
        assert "Tap" in result.stdout


@pytest.mark.unit
class TestCLINetworkCommands:
    """Test suite for clinetworkcommands."""
    def test_network_block_help(self) -> None:
        """Test network block help."""
        result = runner.invoke(app, ["network", "block", "--help"])
        assert result.exit_code == 0
        assert "Block" in result.stdout

    def test_network_throttle_help(self) -> None:
        """Test network throttle help."""
        result = runner.invoke(app, ["network", "throttle", "--help"])
        assert result.exit_code == 0
        assert "Throttle" in result.stdout

    def test_network_mock_help(self) -> None:
        """Test network mock help."""
        result = runner.invoke(app, ["network", "mock", "--help"])
        assert result.exit_code == 0
        assert "Mock" in result.stdout


@pytest.mark.unit
class TestCLIA11yCommand:
    """Test suite for clia11ycommand."""
    def test_a11y_help(self) -> None:
        """Test a11y help."""
        result = runner.invoke(app, ["a11y", "--help"])
        assert result.exit_code == 0
        assert "accessibility" in result.stdout.lower()


@pytest.mark.unit
class TestCLIDialogCommand:
    """Test suite for clidialogcommand."""
    def test_dialog_help(self) -> None:
        """Test dialog help."""
        result = runner.invoke(app, ["dialog", "--help"])
        assert result.exit_code == 0
        assert "dialog" in result.stdout.lower()


@pytest.mark.unit
class TestCLIPermissionsCommand:
    """Test suite for clipermissionscommand."""
    def test_permissions_help(self) -> None:
        """Test permissions help."""
        result = runner.invoke(app, ["permissions", "--help"])
        assert result.exit_code == 0
        assert "permissions" in result.stdout.lower()


@pytest.mark.unit
class TestCLISecurityCommand:
    """Test suite for clisecuritycommand."""
    def test_security_help(self) -> None:
        """Test security help."""
        result = runner.invoke(app, ["security", "--help"])
        assert result.exit_code == 0
        assert "security" in result.stdout.lower()


@pytest.mark.unit
class TestCLIScreencastCommand:
    """Test suite for cliscreencastcommand."""
    def test_screencast_help(self) -> None:
        """Test screencast help."""
        result = runner.invoke(app, ["screencast", "--help"])
        assert result.exit_code == 0
        assert "screencast" in result.stdout.lower()


@pytest.mark.unit
class TestCLIDownloadCommand:
    """Test suite for clidownloadcommand."""
    def test_download_help(self) -> None:
        """Test download help."""
        result = runner.invoke(app, ["download", "--help"])
        assert result.exit_code == 0
        assert "download" in result.stdout.lower()
