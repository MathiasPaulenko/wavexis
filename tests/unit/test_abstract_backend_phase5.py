"""Unit tests for AbstractBackend Phase 5 abstract methods."""

import inspect

import pytest

from browsix.backend.base import AbstractBackend


@pytest.mark.unit
class TestAbstractBackendPhase5:
    def _get_abstract_methods(self) -> list[str]:
        return [
            name
            for name, val in vars(AbstractBackend).items()
            if getattr(val, "__isabstractmethod__", False)
        ]

    def test_input_methods_exist(self) -> None:
        methods = self._get_abstract_methods()
        for name in [
            "click", "type_text", "fill", "select_option",
            "hover", "key_press", "drag", "tap",
        ]:
            assert name in methods, f"{name} should be an abstract method"

    def test_network_advanced_methods_exist(self) -> None:
        methods = self._get_abstract_methods()
        for name in [
            "block_requests", "throttle_network", "set_cache_disabled",
            "intercept_requests", "mock_response",
        ]:
            assert name in methods, f"{name} should be an abstract method"

    def test_a11y_methods_exist(self) -> None:
        methods = self._get_abstract_methods()
        for name in ["a11y_tree", "a11y_node", "a11y_ancestors"]:
            assert name in methods, f"{name} should be an abstract method"

    def test_download_method_exists(self) -> None:
        assert "intercept_download" in self._get_abstract_methods()

    def test_dialog_methods_exist(self) -> None:
        methods = self._get_abstract_methods()
        assert "dialog_accept" in methods
        assert "dialog_dismiss" in methods

    def test_permissions_methods_exist(self) -> None:
        methods = self._get_abstract_methods()
        assert "grant_permission" in methods
        assert "reset_permissions" in methods

    def test_security_methods_exist(self) -> None:
        methods = self._get_abstract_methods()
        assert "get_security_state" in methods
        assert "ignore_cert_errors" in methods

    def test_emulation_advanced_methods_exist(self) -> None:
        methods = self._get_abstract_methods()
        for name in ["set_locale", "set_cpu_throttle", "set_touch_emulation", "set_sensors"]:
            assert name in methods, f"{name} should be an abstract method"

    def test_click_signature(self) -> None:
        sig = inspect.signature(AbstractBackend.click)
        params = list(sig.parameters.keys())
        assert "selector" in params
        assert "button" in params
        assert "click_count" in params

    def test_type_text_signature(self) -> None:
        sig = inspect.signature(AbstractBackend.type_text)
        params = list(sig.parameters.keys())
        assert "selector" in params
        assert "text" in params
        assert "delay" in params
