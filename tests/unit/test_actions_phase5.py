"""Unit tests for accessibility, dialog, permissions, and security actions."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from browsix.actions.accessibility import AccessibilityAction
from browsix.actions.dialog import DialogAction
from browsix.actions.permissions import PermissionsAction
from browsix.actions.security import SecurityAction
from browsix.backend.base import AbstractBackend


def _make_backend() -> MagicMock:
    """Create a mock backend for testing.

        Returns:
            A MagicMock backend instance.
        """
    backend = MagicMock(spec=AbstractBackend)
    backend.launch = AsyncMock()
    backend.close = AsyncMock()
    backend.navigate = AsyncMock()
    backend.a11y_tree = AsyncMock(return_value={"nodes": []})
    backend.a11y_node = AsyncMock(return_value={"nodeId": "1"})
    backend.a11y_ancestors = AsyncMock(return_value=[{"nodeId": "0"}])
    backend.dialog_accept = AsyncMock()
    backend.dialog_dismiss = AsyncMock()
    backend.grant_permission = AsyncMock()
    backend.reset_permissions = AsyncMock()
    backend.get_security_state = AsyncMock(return_value={"secure": True})
    backend.ignore_cert_errors = AsyncMock()
    return backend


@pytest.mark.unit
class TestAccessibilityAction:
    """Test suite for accessibilityaction."""
    async def test_tree(self) -> None:
        """Test tree."""
        backend = _make_backend()
        result = await AccessibilityAction(
            params=None, action="tree", url="https://example.com"
        ).execute(backend)
        backend.a11y_tree.assert_called_once()
        assert result == {"nodes": []}

    async def test_node(self) -> None:
        """Test node."""
        backend = _make_backend()
        result = await AccessibilityAction(
            params=None, action="node", node_id="1", url="https://example.com"
        ).execute(backend)
        backend.a11y_node.assert_called_once_with("1")
        assert result == {"nodeId": "1"}

    async def test_ancestors(self) -> None:
        """Test ancestors."""
        backend = _make_backend()
        result = await AccessibilityAction(
            params=None, action="ancestors", node_id="1", url="https://example.com"
        ).execute(backend)
        backend.a11y_ancestors.assert_called_once_with("1")
        assert result == [{"nodeId": "0"}]

    async def test_unknown_action_raises(self) -> None:
        """Test that unknown action raises raises an appropriate error."""
        backend = _make_backend()
        with pytest.raises(ValueError, match="Unknown a11y action"):
            await AccessibilityAction(
                params=None, action="bad", url="https://example.com"
            ).execute(backend)


@pytest.mark.unit
class TestDialogAction:
    """Test suite for dialogaction."""
    async def test_accept(self) -> None:
        """Test accept."""
        backend = _make_backend()
        await DialogAction(
            params="", action="accept", url="https://example.com"
        ).execute(backend)
        backend.dialog_accept.assert_called_once_with(None)

    async def test_accept_with_text(self) -> None:
        """Test accept with text."""
        backend = _make_backend()
        await DialogAction(
            params="", action="accept", prompt_text="yes", url="https://example.com"
        ).execute(backend)
        backend.dialog_accept.assert_called_once_with("yes")

    async def test_dismiss(self) -> None:
        """Test dismiss."""
        backend = _make_backend()
        await DialogAction(
            params="", action="dismiss", url="https://example.com"
        ).execute(backend)
        backend.dialog_dismiss.assert_called_once()

    async def test_unknown_action_raises(self) -> None:
        """Test that unknown action raises raises an appropriate error."""
        backend = _make_backend()
        with pytest.raises(ValueError, match="Unknown dialog action"):
            await DialogAction(
                params="", action="bad", url="https://example.com"
            ).execute(backend)


@pytest.mark.unit
class TestPermissionsAction:
    """Test suite for permissionsaction."""
    async def test_grant(self) -> None:
        """Test grant."""
        backend = _make_backend()
        await PermissionsAction(
            params="", action="grant", permission="geolocation", url="https://example.com"
        ).execute(backend)
        backend.grant_permission.assert_called_once_with("geolocation")

    async def test_reset(self) -> None:
        """Test reset."""
        backend = _make_backend()
        await PermissionsAction(
            params="", action="reset", url="https://example.com"
        ).execute(backend)
        backend.reset_permissions.assert_called_once()

    async def test_unknown_action_raises(self) -> None:
        """Test that unknown action raises raises an appropriate error."""
        backend = _make_backend()
        with pytest.raises(ValueError, match="Unknown permissions action"):
            await PermissionsAction(
                params="", action="bad", url="https://example.com"
            ).execute(backend)


@pytest.mark.unit
class TestSecurityAction:
    """Test suite for securityaction."""
    async def test_state(self) -> None:
        """Test state."""
        backend = _make_backend()
        result = await SecurityAction(
            params="", action="state", url="https://example.com"
        ).execute(backend)
        backend.get_security_state.assert_called_once()
        assert result == {"secure": True}

    async def test_ignore_cert(self) -> None:
        """Test ignore cert."""
        backend = _make_backend()
        result = await SecurityAction(
            params="", action="ignore_cert", ignore=True, url="https://example.com"
        ).execute(backend)
        backend.ignore_cert_errors.assert_called_once_with(True)
        assert result is None

    async def test_unknown_action_raises(self) -> None:
        """Test that unknown action raises raises an appropriate error."""
        backend = _make_backend()
        with pytest.raises(ValueError, match="Unknown security action"):
            await SecurityAction(
                params="", action="bad", url="https://example.com"
            ).execute(backend)
