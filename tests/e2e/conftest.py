"""E2E test configuration — launches the real wavexis CLI as a subprocess.

These tests invoke ``python -m wavexis <command>`` against a real Chrome
browser.  They are skipped automatically when cdpwave or Chrome is not
available.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


def _chrome_available() -> bool:
    """Return True if a Chrome/Chromium binary can be found."""
    for name in ("chrome", "chromium", "google-chrome", "chromium-browser"):
        if shutil.which(name):
            return True
    # On Windows the registry / common install paths
    for candidate in (
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
    ):
        if candidate.exists():
            return True
    return False


def _cdpwave_available() -> bool:
    """Return True if cdpwave is importable."""
    try:
        import cdpwave  # noqa: F401
    except ImportError:
        return False
    return True


def pytest_configure(config: pytest.Config) -> None:
    """Register the e2e marker."""
    config.addinivalue_line("markers", "e2e: end-to-end CLI tests against a real browser")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip e2e tests when prerequisites are missing."""
    skip_e2e = not _cdpwave_available() or not _chrome_available()
    skip_marker = pytest.mark.skip(reason="cdpwave or Chrome not available — skipping e2e tests")
    for item in items:
        if "e2e" in item.keywords and skip_e2e:
            item.add_marker(skip_marker)


@pytest.fixture
def cli() -> CLIRunner:
    """Return a helper that runs the wavexis CLI as a real subprocess."""
    return CLIRunner()


class CLIRunner:
    """Run ``python -m wavexis`` as a subprocess and capture the result."""

    def __init__(self) -> None:
        self._base_cmd: list[str] = [sys.executable, "-m", "wavexis"]

    def run(
        self,
        args: list[str],
        *,
        timeout: int = 60,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
    ) -> CLIResult:
        """Execute ``python -m wavexis <args>`` and return a CLIResult.

        Args:
            args: Extra CLI arguments (e.g. ``["screenshot", "https://example.com"]``).
            timeout: Subprocess timeout in seconds.
            cwd: Working directory for the subprocess.
            env: Optional environment overrides.

        Returns:
            A CLIResult with exit code, stdout, and stderr.
        """
        cmd = self._base_cmd + args
        run_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        if env:
            run_env.update(env)
        completed = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
            env=run_env,
        )
        # Decode explicitly: the default text mode uses the system codec
        # (e.g. cp1252 on Windows), which chokes on box-drawing characters
        # in --help output and JSON escapes.
        completed.stdout = completed.stdout.decode("utf-8", errors="replace")
        completed.stderr = completed.stderr.decode("utf-8", errors="replace")
        return CLIResult(completed)


class CLIResult:
    """Wrapper around subprocess.CompletedProcess with assertion helpers."""

    def __init__(self, completed: subprocess.CompletedProcess[str]) -> None:
        self.exit_code: int = completed.returncode
        self.stdout: str = completed.stdout
        self.stderr: str = completed.stderr

    def assert_success(self) -> CLIResult:
        """Assert the command exited with code 0."""
        assert self.exit_code == 0, (
            f"Expected exit code 0, got {self.exit_code}.\n"
            f"stdout: {self.stdout}\nstderr: {self.stderr}"
        )
        return self

    def assert_exit_code(self, code: int) -> CLIResult:
        """Assert the command exited with a specific code."""
        assert self.exit_code == code, (
            f"Expected exit code {code}, got {self.exit_code}.\n"
            f"stdout: {self.stdout}\nstderr: {self.stderr}"
        )
        return self

    def assert_stdout_contains(self, substring: str) -> CLIResult:
        """Assert that stdout contains a substring."""
        assert substring in self.stdout, f"Expected '{substring}' in stdout, got:\n{self.stdout}"
        return self

    def assert_file_exists(self, path: str | Path) -> CLIResult:
        """Assert that a file was created at the given path."""
        p = Path(path)
        assert p.exists(), f"Expected file at {path}, but it does not exist."
        assert p.stat().st_size > 0, f"File {path} exists but is empty."
        return self

    def parse_stdout_json(self) -> Any:
        """Parse stdout as JSON."""
        import json

        return json.loads(self.stdout.strip())
