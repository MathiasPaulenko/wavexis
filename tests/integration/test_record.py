"""Integration tests for record/replay against a real Chrome browser."""

from pathlib import Path

import pytest

from wavexis.backend.cdp import CDPBackend
from wavexis.config import BrowserOptions
from wavexis.record import record_to_yaml, replay_from_yaml

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


@pytest.fixture
def backend() -> CDPBackend:
    """Backend."""
    return CDPBackend()


@pytest.fixture
def browser_opts() -> BrowserOptions:
    """Browser opts."""
    return BrowserOptions(headless=True)


async def test_record_and_replay(
    backend: CDPBackend, browser_opts: BrowserOptions, tmp_path: Path
) -> None:
    """Test record and replay."""
    actions = [
        {"eval": {"url": "https://example.com", "expression": "1 + 1"}},
    ]
    yaml_path = tmp_path / "session.yml"
    record_to_yaml(actions, yaml_path)
    assert yaml_path.exists()

    await backend.launch(browser_opts)
    try:
        results = await replay_from_yaml(yaml_path, backend)
        assert len(results) == 1
    finally:
        await backend.close()


async def test_replay_multi_action(
    backend: CDPBackend, browser_opts: BrowserOptions, tmp_path: Path
) -> None:
    """Test replay multi action."""
    actions = [
        {"eval": {"url": "https://example.com", "expression": "document.title"}},
        {"screenshot": {"url": "https://example.com", "output": "out.png"}},
    ]
    yaml_path = tmp_path / "multi.yml"
    record_to_yaml(actions, yaml_path)

    await backend.launch(browser_opts)
    try:
        results = await replay_from_yaml(yaml_path, backend)
        assert len(results) == 2
    finally:
        await backend.close()
