"""Unit tests for wavexis.multi YAML parser and executor."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wavexis.exceptions import MultiConfigError
from wavexis.multi import execute_actions, parse_yaml


@pytest.mark.unit
class TestParseYaml:
    """Test suite for parseyaml."""

    def test_valid_config(self, tmp_path: Path) -> None:
        """Test valid config."""
        config = tmp_path / "config.yml"
        config.write_text(
            """
actions:
  - screenshot:
      url: https://example.com
      full_page: true
  - pdf:
      url: https://example.com
      paper: a4
""",
            encoding="utf-8",
        )
        actions = parse_yaml(config)
        assert len(actions) == 2
        assert "screenshot" in actions[0]
        assert actions[0]["screenshot"]["url"] == "https://example.com"
        assert "pdf" in actions[1]

    def test_missing_file(self, tmp_path: Path) -> None:
        """Test that missing file raises an appropriate error."""
        with pytest.raises(MultiConfigError, match="file"):
            parse_yaml(tmp_path / "nonexistent.yml")

    def test_unreadable_file(self, tmp_path: Path) -> None:
        """An existing but unreadable config file should raise MultiConfigError."""
        config = tmp_path / "config.yml"
        config.write_text("actions:\n  - screenshot:\n      url: https://example.com\n")
        with (
            patch("pathlib.Path.read_text", side_effect=PermissionError("denied")),
            pytest.raises(MultiConfigError, match="unreadable"),
        ):
            parse_yaml(config)

    def test_non_dict_root(self, tmp_path: Path) -> None:
        """Test non dict root."""
        config = tmp_path / "bad.yml"
        config.write_text("- just\n- a\n- list\n", encoding="utf-8")
        with pytest.raises(MultiConfigError, match="root"):
            parse_yaml(config)

    def test_missing_actions_key(self, tmp_path: Path) -> None:
        """Test that missing actions key raises an appropriate error."""
        config = tmp_path / "bad.yml"
        config.write_text("foo: bar\n", encoding="utf-8")
        with pytest.raises(MultiConfigError, match="actions"):
            parse_yaml(config)

    def test_actions_not_list(self, tmp_path: Path) -> None:
        """Test actions not list."""
        config = tmp_path / "bad.yml"
        config.write_text("actions: notalist\n", encoding="utf-8")
        with pytest.raises(MultiConfigError, match="actions"):
            parse_yaml(config)

    def test_action_not_single_key(self, tmp_path: Path) -> None:
        """Test action not single key."""
        config = tmp_path / "bad.yml"
        config.write_text(
            "actions:\n  - screenshot: {}\n    pdf: {}\n",
            encoding="utf-8",
        )
        with pytest.raises(MultiConfigError, match="actions"):
            parse_yaml(config)

    def test_action_params_not_dict(self, tmp_path: Path) -> None:
        """Test action params not dict."""
        config = tmp_path / "bad.yml"
        config.write_text(
            "actions:\n  - screenshot: notadict\n",
            encoding="utf-8",
        )
        with pytest.raises(MultiConfigError, match="screenshot"):
            parse_yaml(config)

    def test_empty_actions(self, tmp_path: Path) -> None:
        """Test empty actions."""
        config = tmp_path / "empty.yml"
        config.write_text("actions: []\n", encoding="utf-8")
        actions = parse_yaml(config)
        assert actions == []

    def test_non_string_variable_substitution(self, tmp_path: Path) -> None:
        """Regression: non-string vars (int/bool) must be coerced to str."""
        config = tmp_path / "vars.yml"
        config.write_text(
            """
vars:
  count: 5
  flag: true
actions:
  - eval:
      url: "https://example.com/page?n={{count}}&f={{flag}}"
""",
            encoding="utf-8",
        )
        actions = parse_yaml(config)
        url = actions[0]["eval"]["url"]
        assert "n=5" in url
        assert "f=True" in url

    def test_env_variable_substitution(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """{{env.KEY}} should resolve from os.environ."""
        monkeypatch.setenv("WAVERXIS_TEST_TOKEN", "secret123")
        config = tmp_path / "env.yml"
        config.write_text(
            """
actions:
  - eval:
      url: "https://example.com?t={{env.WAVERXIS_TEST_TOKEN}}"
""",
            encoding="utf-8",
        )
        actions = parse_yaml(config)
        assert actions[0]["eval"]["url"] == "https://example.com?t=secret123"

    def test_undefined_variable_preserved(self, tmp_path: Path) -> None:
        """Undefined {{var}} should be left intact."""
        config = tmp_path / "undef.yml"
        config.write_text(
            """
actions:
  - eval:
      url: "https://example.com/{{missing}}"
""",
            encoding="utf-8",
        )
        actions = parse_yaml(config)
        assert actions[0]["eval"]["url"] == "https://example.com/{{missing}}"


@pytest.mark.unit
class TestExecuteActions:
    """Test suite for executeactions."""

    async def test_execute_screenshot(self) -> None:
        """Test execute screenshot."""
        backend = MagicMock()
        backend.navigate = AsyncMock()
        backend.screenshot = AsyncMock(return_value=b"png")
        actions = [{"screenshot": {"url": "https://example.com", "full_page": True}}]
        results = await execute_actions(actions, backend)
        assert len(results) == 1
        assert results[0] == b"png"

    async def test_execute_multiple(self) -> None:
        """Test execute multiple."""
        backend = MagicMock()
        backend.navigate = AsyncMock()
        backend.screenshot = AsyncMock(return_value=b"png")
        backend.eval = AsyncMock(return_value="title")
        actions = [
            {"screenshot": {"url": "https://example.com"}},
            {"eval": {"url": "https://example.com", "expression": "document.title"}},
        ]
        results = await execute_actions(actions, backend)
        assert len(results) == 2
        assert results[0] == b"png"
        assert results[1] == "title"

    async def test_execute_empty(self) -> None:
        """Test execute empty."""
        backend = MagicMock()
        results = await execute_actions([], backend)
        assert results == []

    async def test_execute_unknown_action(self) -> None:
        """Test execute unknown action."""
        backend = MagicMock()
        actions = [{"unknown_action": {"url": "https://example.com"}}]
        with pytest.raises(MultiConfigError, match="unknown_action"):
            await execute_actions(actions, backend)

    async def test_parallel_returns_exceptions_without_aborting(self) -> None:
        """One failing action should not abort other parallel actions."""
        from wavexis.exceptions import WavexisError

        backend = MagicMock()
        tab_mock = MagicMock()
        tab_mock.close = AsyncMock()
        backend.new_tab_handle = AsyncMock(return_value=tab_mock)

        async def mixed_dispatch(
            action_type: str, params: dict, backend: Any, cache: Any = None
        ) -> Any:
            if action_type == "screenshot":
                return b"png"
            raise ValueError("intentional")

        with (
            pytest.raises(WavexisError, match="intentional"),
            patch("wavexis.multi._dispatch", side_effect=mixed_dispatch),
        ):
            await execute_actions(
                [
                    {"screenshot": {"url": "https://example.com"}},
                    {"eval": {"url": "https://example.com", "expression": "1"}},
                ],
                backend,
                parallel=True,
            )


@pytest.mark.unit
class TestActionRegistry:
    """Regression tests for the multi-action registry.

    Recorded sessions (from wavexis record) emit action types like
    `keypress` and `select`. These must be present in the registry so
    that `wavexis multi` can replay them.
    """

    def test_registry_contains_recorded_action_types(self) -> None:
        """All action types emitted by events_to_yaml must be registered."""
        from wavexis.multi import _ACTION_REGISTRY

        required = {"navigate", "click", "type", "select", "keypress"}
        missing = required - set(_ACTION_REGISTRY)
        assert not missing, f"Missing registered actions: {missing}"

    def test_registry_contains_template_action_types(self) -> None:
        """All action types referenced in init.py templates must be registered."""
        from wavexis.init import TEMPLATES
        from wavexis.multi import _ACTION_REGISTRY

        referenced: set[str] = set()
        for template in TEMPLATES.values():
            for action_dict in template["actions"]:
                referenced.add(next(iter(action_dict)))
        missing = referenced - set(_ACTION_REGISTRY)
        assert not missing, f"Template actions missing from registry: {missing}"

    def test_registry_contains_common_input_actions(self) -> None:
        """Common input actions should be replayable via multi YAML."""
        from wavexis.multi import _ACTION_REGISTRY

        expected = {
            "click",
            "type",
            "fill",
            "select",
            "hover",
            "keypress",
            "right_click",
            "double_click",
            "drag",
            "tap",
            "scroll",
            "upload",
        }
        missing = expected - set(_ACTION_REGISTRY)
        assert not missing, f"Missing input actions in registry: {missing}"

    async def test_keypress_action_dispatches_to_input(self) -> None:
        """A keypress action should dispatch to InputAction with action='key'."""
        from unittest.mock import patch

        backend = MagicMock()
        captured: dict[str, Any] = {}

        async def fake_execute(self: Any, b: Any) -> Any:
            captured["action"] = self.params.action
            captured["key"] = self.params.key
            return None

        with patch("wavexis.actions.input.InputAction.execute", fake_execute):
            await execute_actions(
                [{"keypress": {"key": "Tab"}}],
                backend,
            )

        assert captured["action"] == "key"
        assert captured["key"] == "Tab"

    async def test_select_action_dispatches_to_input(self) -> None:
        """A select action should dispatch to InputAction with action='select'."""
        from unittest.mock import patch

        backend = MagicMock()
        captured: dict[str, Any] = {}

        async def fake_execute(self: Any, b: Any) -> Any:
            captured["action"] = self.params.action
            captured["selector"] = self.params.selector
            captured["value"] = self.params.value
            return None

        with patch("wavexis.actions.input.InputAction.execute", fake_execute):
            await execute_actions(
                [{"select": {"selector": "#country", "value": "US"}}],
                backend,
            )

        assert captured["action"] == "select"
        assert captured["selector"] == "#country"
        assert captured["value"] == "US"

    async def test_har_action_dispatches_to_haraction(self) -> None:
        """A har action should dispatch to HARAction with the configured params."""
        from unittest.mock import patch

        backend = MagicMock()
        captured: dict[str, Any] = {}

        async def fake_execute(self: Any, b: Any) -> Any:
            captured["url"] = self.params.url
            captured["filter"] = self.params.filter
            captured["timeout"] = self.params.timeout
            return {"log": {"entries": []}}

        with patch("wavexis.actions.har.HARAction.execute", fake_execute):
            result = await execute_actions(
                [{"har": {"url": "https://example.com", "timeout": 2000, "filter": "api"}}],
                backend,
            )

        assert captured["url"] == "https://example.com"
        assert captured["filter"] == "api"
        assert captured["timeout"] == 2000
        assert result == [{"log": {"entries": []}}]


@pytest.mark.unit
class TestActionFactories:
    """Test suite for the _*_factory functions in wavexis.multi.

    These tests verify that each factory builds the correct action
    instance with the correct parameter mapping. The factories are
    internal but are the bridge between YAML config and action classes,
    so regressions here would break multi-action workflows silently.
    """

    def test_navigate_factory(self) -> None:
        """_navigate_factory builds a NavigateAction with the url."""
        from wavexis.actions.navigate import NavigateAction
        from wavexis.multi import _navigate_factory

        action = _navigate_factory({"url": "https://example.com"})
        assert isinstance(action, NavigateAction)
        assert action.params.url == "https://example.com"

    def test_navigate_factory_default_url(self) -> None:
        """_navigate_factory defaults to empty url when missing."""
        from wavexis.multi import _navigate_factory

        action = _navigate_factory({})
        assert action.params.url == ""

    def test_click_factory(self) -> None:
        """_click_factory builds an InputAction with action='click'."""
        from wavexis.actions.input import InputAction
        from wavexis.multi import _click_factory

        action = _click_factory({"selector": "#btn", "url": "https://x.com"})
        assert isinstance(action, InputAction)
        assert action.params.action == "click"
        assert action.params.selector == "#btn"
        assert action.params.url == "https://x.com"

    def test_type_factory(self) -> None:
        """_type_factory builds an InputAction with action='type'."""
        from wavexis.actions.input import InputAction
        from wavexis.multi import _type_factory

        action = _type_factory({"selector": "#input", "text": "hello"})
        assert isinstance(action, InputAction)
        assert action.params.action == "type"
        assert action.params.selector == "#input"
        assert action.params.text == "hello"

    def test_fill_factory(self) -> None:
        """_fill_factory builds an InputAction with action='fill'."""
        from wavexis.multi import _fill_factory

        action = _fill_factory({"selector": "#input", "value": "filled"})
        assert action.params.action == "fill"
        assert action.params.selector == "#input"
        assert action.params.value == "filled"

    def test_select_factory(self) -> None:
        """_select_factory builds an InputAction with action='select'."""
        from wavexis.multi import _select_factory

        action = _select_factory({"selector": "#sel", "value": "US"})
        assert action.params.action == "select"
        assert action.params.selector == "#sel"
        assert action.params.value == "US"

    def test_hover_factory(self) -> None:
        """_hover_factory builds an InputAction with action='hover'."""
        from wavexis.multi import _hover_factory

        action = _hover_factory({"selector": "#hover"})
        assert action.params.action == "hover"
        assert action.params.selector == "#hover"

    def test_keypress_factory_default_key(self) -> None:
        """_keypress_factory defaults to 'Enter' when key is missing."""
        from wavexis.multi import _keypress_factory

        action = _keypress_factory({})
        assert action.params.action == "key"
        assert action.params.key == "Enter"

    def test_keypress_factory_custom_key(self) -> None:
        """_keypress_factory uses the provided key."""
        from wavexis.multi import _keypress_factory

        action = _keypress_factory({"key": "Tab"})
        assert action.params.key == "Tab"

    def test_right_click_factory(self) -> None:
        """_right_click_factory builds an InputAction with action='right_click'."""
        from wavexis.multi import _right_click_factory

        action = _right_click_factory({"selector": "#btn"})
        assert action.params.action == "right_click"
        assert action.params.selector == "#btn"

    def test_double_click_factory(self) -> None:
        """_double_click_factory builds an InputAction with action='double_click'."""
        from wavexis.multi import _double_click_factory

        action = _double_click_factory({"selector": "#btn"})
        assert action.params.action == "double_click"
        assert action.params.selector == "#btn"

    def test_drag_factory(self) -> None:
        """_drag_factory builds an InputAction with action='drag'."""
        from wavexis.multi import _drag_factory

        action = _drag_factory({"source": "#src", "target": "#dst"})
        assert action.params.action == "drag"
        assert action.params.source == "#src"
        assert action.params.target == "#dst"

    def test_tap_factory(self) -> None:
        """_tap_factory builds an InputAction with action='tap'."""
        from wavexis.multi import _tap_factory

        action = _tap_factory({"selector": "#btn"})
        assert action.params.action == "tap"
        assert action.params.selector == "#btn"

    def test_scrape_factory_with_urls(self) -> None:
        """_scrape_factory builds a ScrapeAction with a list of urls."""
        from wavexis.actions.scrape import ScrapeAction
        from wavexis.multi import _scrape_factory

        action = _scrape_factory({"urls": ["https://a.com", "https://b.com"]})
        assert isinstance(action, ScrapeAction)
        assert action.params.urls == ["https://a.com", "https://b.com"]

    def test_scrape_factory_with_single_url(self) -> None:
        """_scrape_factory falls back to 'url' key when 'urls' is missing."""
        from wavexis.multi import _scrape_factory

        action = _scrape_factory({"url": "https://single.com"})
        assert action.params.urls == ["https://single.com"]

    def test_scrape_factory_default_expression(self) -> None:
        """_scrape_factory defaults expression to 'document.title'."""
        from wavexis.multi import _scrape_factory

        action = _scrape_factory({"url": "https://x.com"})
        assert action.params.expression == "document.title"

    def test_scrape_factory_custom_expression(self) -> None:
        """_scrape_factory uses the provided expression."""
        from wavexis.multi import _scrape_factory

        action = _scrape_factory({"url": "https://x.com", "expression": "document.body.innerText"})
        assert action.params.expression == "document.body.innerText"

    def test_eval_factory(self) -> None:
        """_eval_factory builds an EvalAction with url and expression."""
        from wavexis.actions.eval import EvalAction
        from wavexis.multi import _eval_factory

        action = _eval_factory({"url": "https://x.com", "expression": "document.title"})
        assert isinstance(action, EvalAction)
        assert action.params.url == "https://x.com"
        assert action.params.expression == "document.title"

    def test_upload_factory_with_list(self) -> None:
        """_upload_factory accepts a list of file paths."""
        from wavexis.multi import _upload_factory

        action = _upload_factory({"selector": "#file", "files": ["/a.txt", "/b.txt"]})
        assert action.params.action == "upload"
        assert action.params.selector == "#file"
        assert action.params.files == ["/a.txt", "/b.txt"]

    def test_upload_factory_with_string(self) -> None:
        """_upload_factory converts a single string file into a list."""
        from wavexis.multi import _upload_factory

        action = _upload_factory({"selector": "#file", "files": "/single.txt"})
        assert action.params.action == "upload"
        assert action.params.files == ["/single.txt"]

    def test_upload_factory_default_empty_files(self) -> None:
        """_upload_factory defaults to empty files list."""
        from wavexis.multi import _upload_factory

        action = _upload_factory({"selector": "#file"})
        assert action.params.files == []

    def test_cookies_factory_with_cookie_dict(self) -> None:
        """_cookies_factory builds a CookieAction with a cookie dict."""
        from wavexis.actions.cookies import CookieAction
        from wavexis.multi import _cookies_factory

        action = _cookies_factory(
            {
                "action": "set",
                "cookie": {
                    "name": "session",
                    "value": "abc",
                    "domain": "example.com",
                    "path": "/",
                },
            }
        )
        assert isinstance(action, CookieAction)
        assert action.params.action == "set"
        assert action.params.cookie.name == "session"
        assert action.params.cookie.value == "abc"
        assert action.params.cookie.domain == "example.com"
        assert action.params.cookie.path == "/"

    def test_cookies_factory_without_cookie_dict(self) -> None:
        """_cookies_factory builds a CookieAction with default cookie when no dict."""
        from wavexis.multi import _cookies_factory

        action = _cookies_factory({"action": "get"})
        assert action.params.action == "get"
        # Default cookie has empty fields
        assert action.params.cookie.name == ""
        assert action.params.cookie.value == ""

    def test_cookies_factory_with_name_and_domain(self) -> None:
        """_cookies_factory passes name and domain for delete action."""
        from wavexis.multi import _cookies_factory

        action = _cookies_factory(
            {"action": "delete", "name": "old", "domain": "example.com"}
        )
        assert action.params.action == "delete"
        assert action.params.name == "old"
        assert action.params.domain == "example.com"

    def test_scroll_factory(self) -> None:
        """_scroll_factory builds an InputAction with action='scroll'."""
        from wavexis.multi import _scroll_factory

        action = _scroll_factory({"x": 100, "y": 200})
        assert action.params.action == "scroll"
        assert action.params.scroll_x == 100
        assert action.params.scroll_y == 200

    def test_scroll_factory_defaults(self) -> None:
        """_scroll_factory defaults x and y to 0."""
        from wavexis.multi import _scroll_factory

        action = _scroll_factory({})
        assert action.params.action == "scroll"
        assert action.params.scroll_x == 0
        assert action.params.scroll_y == 0
