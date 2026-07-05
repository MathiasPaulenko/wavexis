"""Pytest configuration and fixtures for browsix tests."""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: fast isolated tests with mocks")
    config.addinivalue_line("markers", "integration: tests against a real Chrome browser")
    config.addinivalue_line("markers", "slow: tests that take more than 5 seconds")
    config.addinivalue_line("markers", "chrome: tests that require Chrome specifically")
