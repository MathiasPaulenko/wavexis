"""Unit tests for global CLI options: --headed, --timeout, --proxy, config."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import wavexis.cli.app  # noqa: F401 — ensure module is loaded
from wavexis.config import BrowserOptions

pytestmark = pytest.mark.unit

_cli = sys.modules["wavexis.cli.app"]


class TestBrowserOptions:
    """Tests for BrowserOptions with proxy and timeout fields."""

    def test_defaults(self) -> None:
        opts = BrowserOptions()
        assert opts.headless is True
        assert opts.proxy is None
        assert opts.timeout == 30000

    def test_with_proxy(self) -> None:
        opts = BrowserOptions(proxy="http://proxy:8080")
        assert opts.proxy == "http://proxy:8080"

    def test_with_timeout(self) -> None:
        opts = BrowserOptions(timeout=60000)
        assert opts.timeout == 60000

    def test_headed(self) -> None:
        opts = BrowserOptions(headless=False)
        assert opts.headless is False

    def test_socks_proxy(self) -> None:
        opts = BrowserOptions(proxy="socks5://proxy:1080")
        assert opts.proxy == "socks5://proxy:1080"


class TestBrowserOptionsHelper:
    """Tests for _browser_options() CLI helper."""

    def test_default_options(self) -> None:
        _cli._headless = True
        _cli._timeout = 30000
        _cli._proxy = None
        opts = _cli._browser_options()
        assert opts.headless is True
        assert opts.timeout == 30000
        assert opts.proxy is None

    def test_headed_options(self) -> None:
        _cli._headless = False
        _cli._timeout = 30000
        _cli._proxy = None
        opts = _cli._browser_options()
        assert opts.headless is False

    def test_proxy_options(self) -> None:
        _cli._headless = True
        _cli._timeout = 30000
        _cli._proxy = "http://proxy:8080"
        opts = _cli._browser_options()
        assert opts.proxy == "http://proxy:8080"

    def test_timeout_options(self) -> None:
        _cli._headless = True
        _cli._timeout = 60000
        _cli._proxy = None
        opts = _cli._browser_options()
        assert opts.timeout == 60000


class TestLoadGlobalConfig:
    """Tests for _load_global_config."""

    def test_no_config_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: Path("/nonexistent_home_12345"))
        _cli._preferred_backend = None
        _cli._headless = True
        _cli._timeout = 30000
        _cli._proxy = None
        _cli._load_global_config()
        assert _cli._preferred_backend is None
        assert _cli._headless is True
        assert _cli._timeout == 30000
        assert _cli._proxy is None

    def test_loads_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_dir = tmp_path / ".wavexis"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text(
            "backend: bidi\nheadless: false\ntimeout: 60000\nproxy: http://proxy:9090\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        _cli._preferred_backend = None
        _cli._headless = True
        _cli._timeout = 30000
        _cli._proxy = None
        _cli._load_global_config()

        assert _cli._preferred_backend == "bidi"
        assert _cli._headless is False
        assert _cli._timeout == 60000
        assert _cli._proxy == "http://proxy:9090"

    def test_cli_overrides_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_dir = tmp_path / ".wavexis"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text("backend: bidi\ntimeout: 60000\n", encoding="utf-8")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        _cli._preferred_backend = "cdp"
        _cli._headless = True
        _cli._timeout = 30000
        _cli._proxy = None
        _cli._load_global_config()

        assert _cli._preferred_backend == "cdp"
        assert _cli._timeout == 60000


class TestConfigCommand:
    """Tests for wavexis config command."""

    def test_config_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(_cli.app, ["config", "path"])
        assert result.exit_code == 0
        assert str(tmp_path / ".wavexis" / "config.yml") in result.output

    def test_config_init(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(_cli.app, ["config", "init"])
        assert result.exit_code == 0
        config_path = tmp_path / ".wavexis" / "config.yml"
        assert config_path.exists()
        import yaml

        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert "backend" in data
        assert "headless" in data
        assert "timeout" in data

    def test_config_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(
            _cli.app, ["config", "set", "--key", "timeout", "--value", "45000"]
        )
        assert result.exit_code == 0
        config_path = tmp_path / ".wavexis" / "config.yml"
        import yaml

        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert data["timeout"] == 45000

    def test_config_set_headless(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(
            _cli.app, ["config", "set", "--key", "headless", "--value", "false"]
        )
        assert result.exit_code == 0
        config_path = tmp_path / ".wavexis" / "config.yml"
        import yaml

        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert data["headless"] is False

    def test_config_show_no_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(_cli.app, ["config", "show"])
        assert result.exit_code == 0
        assert "No config file found" in result.output

    def test_config_show(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_dir = tmp_path / ".wavexis"
        config_dir.mkdir()
        (config_dir / "config.yml").write_text(
            "backend: cdp\ntimeout: 30000\n", encoding="utf-8"
        )
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(_cli.app, ["config", "show"])
        assert result.exit_code == 0
        assert "backend: cdp" in result.output
