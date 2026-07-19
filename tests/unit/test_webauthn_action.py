"""Unit tests for WebAuthnAction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from wavexis.actions.webauthn import WebAuthnAction, WebAuthnParams


@pytest.mark.unit
class TestWebAuthnAction:
    """Test suite for webauthnaction."""

    def _make_backend(self) -> MagicMock:
        """Create a mock backend for testing.

        Returns:
            A MagicMock backend instance.
        """
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.close = AsyncMock()
        backend.webauthn_add_virtual_authenticator = AsyncMock(return_value="auth-id-123")
        backend.webauthn_remove_authenticator = AsyncMock()
        backend.webauthn_add_credential = AsyncMock()
        backend.webauthn_get_credentials = AsyncMock(return_value=[{"credentialId": "cred1"}])
        backend.webauthn_enable = AsyncMock()
        backend.webauthn_disable = AsyncMock()
        backend.webauthn_get_credential = AsyncMock(
            return_value={"credentialId": "cred1", "isRpScoped": False}
        )
        backend.webauthn_remove_credential = AsyncMock()
        backend.webauthn_clear_credentials = AsyncMock()
        backend.webauthn_set_user_verified = AsyncMock()
        backend.webauthn_set_automatic_presence_simulation = AsyncMock()
        backend.webauthn_set_credential_properties = AsyncMock()
        backend.webauthn_set_response_override_bits = AsyncMock()
        return backend

    async def test_add_virtual_authenticator(self) -> None:
        """Test add virtual authenticator."""
        backend = self._make_backend()
        params = WebAuthnParams(
            url="https://example.com",
            action="add-virtual-authenticator",
            protocol="ctap2",
            transport="usb",
        )
        result = await WebAuthnAction(params).execute(backend)
        assert result == "auth-id-123"
        backend.webauthn_add_virtual_authenticator.assert_called_once_with("ctap2", "usb")

    async def test_remove_authenticator(self) -> None:
        """Test remove authenticator."""
        backend = self._make_backend()
        params = WebAuthnParams(
            url="https://example.com",
            action="remove-authenticator",
            authenticator_id="auth-123",
        )
        result = await WebAuthnAction(params).execute(backend)
        assert result is None
        backend.webauthn_remove_authenticator.assert_called_once_with("auth-123")

    async def test_remove_authenticator_missing_id_raises(self) -> None:
        """Test that remove authenticator missing id raises raises an appropriate error."""
        backend = self._make_backend()
        params = WebAuthnParams(
            url="https://example.com",
            action="remove-authenticator",
        )
        with pytest.raises(ValueError, match="authenticator_id is required"):
            await WebAuthnAction(params).execute(backend)

    async def test_add_credential(self) -> None:
        """Test add credential."""
        backend = self._make_backend()
        cred = {"credentialId": "cred1", "isRpScoped": False}
        params = WebAuthnParams(
            url="https://example.com",
            action="add-credential",
            authenticator_id="auth-123",
            credential=cred,
        )
        result = await WebAuthnAction(params).execute(backend)
        assert result is None
        backend.webauthn_add_credential.assert_called_once_with("auth-123", cred)

    async def test_add_credential_missing_fields_raises(self) -> None:
        """Test that add credential missing fields raises raises an appropriate error."""
        backend = self._make_backend()
        params = WebAuthnParams(
            url="https://example.com",
            action="add-credential",
        )
        with pytest.raises(ValueError, match="authenticator_id and credential"):
            await WebAuthnAction(params).execute(backend)

    async def test_get_credentials(self) -> None:
        """Test get credentials."""
        backend = self._make_backend()
        params = WebAuthnParams(
            url="https://example.com",
            action="get-credentials",
            authenticator_id="auth-123",
        )
        result = await WebAuthnAction(params).execute(backend)
        assert result == [{"credentialId": "cred1"}]
        backend.webauthn_get_credentials.assert_called_once_with("auth-123")

    async def test_get_credentials_missing_id_raises(self) -> None:
        """Test that get credentials missing id raises raises an appropriate error."""
        backend = self._make_backend()
        params = WebAuthnParams(
            url="https://example.com",
            action="get-credentials",
        )
        with pytest.raises(ValueError, match="authenticator_id is required"):
            await WebAuthnAction(params).execute(backend)

    async def test_unknown_action_raises(self) -> None:
        """Test that unknown action raises raises an appropriate error."""
        backend = self._make_backend()
        params = WebAuthnParams(
            url="https://example.com",
            action="invalid",
        )
        with pytest.raises(ValueError, match="Unknown WebAuthn action"):
            await WebAuthnAction(params).execute(backend)

    async def test_lifecycle(self) -> None:
        """Test the action lifecycle (navigate, execute)."""
        backend = self._make_backend()
        params = WebAuthnParams(url="https://example.com", action="add-virtual-authenticator")
        await WebAuthnAction(params).execute(backend)
        backend.navigate.assert_called_once()
        backend.webauthn_add_virtual_authenticator.assert_called_once()

    async def test_no_url_skips_navigate(self) -> None:
        """Test that navigation is skipped when no URL is provided."""
        backend = self._make_backend()
        params = WebAuthnParams(url="", action="add-virtual-authenticator")
        await WebAuthnAction(params).execute(backend)
        backend.navigate.assert_not_called()
        backend.webauthn_add_virtual_authenticator.assert_called_once()

    async def test_enable(self) -> None:
        """Test enable action."""
        backend = self._make_backend()
        params = WebAuthnParams(action="enable")
        result = await WebAuthnAction(params).execute(backend)
        assert result is None
        backend.webauthn_enable.assert_called_once()

    async def test_disable(self) -> None:
        """Test disable action."""
        backend = self._make_backend()
        params = WebAuthnParams(action="disable")
        result = await WebAuthnAction(params).execute(backend)
        assert result is None
        backend.webauthn_disable.assert_called_once()

    async def test_get_credential(self) -> None:
        """Test get-credential action."""
        backend = self._make_backend()
        params = WebAuthnParams(
            action="get-credential", authenticator_id="auth-1", credential_id="cred-1"
        )
        result = await WebAuthnAction(params).execute(backend)
        assert result["credentialId"] == "cred1"
        backend.webauthn_get_credential.assert_called_once_with("auth-1", "cred-1")

    async def test_get_credential_missing_fields_raises(self) -> None:
        """Test that get-credential without ids raises."""
        backend = self._make_backend()
        params = WebAuthnParams(action="get-credential")
        with pytest.raises(ValueError, match="authenticator_id and credential_id"):
            await WebAuthnAction(params).execute(backend)

    async def test_remove_credential(self) -> None:
        """Test remove-credential action."""
        backend = self._make_backend()
        params = WebAuthnParams(
            action="remove-credential", authenticator_id="auth-1", credential_id="cred-1"
        )
        result = await WebAuthnAction(params).execute(backend)
        assert result is None
        backend.webauthn_remove_credential.assert_called_once_with("auth-1", "cred-1")

    async def test_clear_credentials(self) -> None:
        """Test clear-credentials action."""
        backend = self._make_backend()
        params = WebAuthnParams(action="clear-credentials", authenticator_id="auth-1")
        result = await WebAuthnAction(params).execute(backend)
        assert result is None
        backend.webauthn_clear_credentials.assert_called_once_with("auth-1")

    async def test_set_user_verified(self) -> None:
        """Test set-user-verified action."""
        backend = self._make_backend()
        params = WebAuthnParams(
            action="set-user-verified", authenticator_id="auth-1", is_user_verified=True
        )
        result = await WebAuthnAction(params).execute(backend)
        assert result is None
        backend.webauthn_set_user_verified.assert_called_once_with("auth-1", True)

    async def test_set_automatic_presence_simulation(self) -> None:
        """Test set-automatic-presence-simulation action."""
        backend = self._make_backend()
        params = WebAuthnParams(
            action="set-automatic-presence-simulation", authenticator_id="auth-1", enabled=True
        )
        result = await WebAuthnAction(params).execute(backend)
        assert result is None
        backend.webauthn_set_automatic_presence_simulation.assert_called_once_with("auth-1", True)

    async def test_set_credential_properties(self) -> None:
        """Test set-credential-properties action."""
        backend = self._make_backend()
        params = WebAuthnParams(
            action="set-credential-properties",
            authenticator_id="auth-1",
            credential_id="cred-1",
            backup_state=True,
        )
        result = await WebAuthnAction(params).execute(backend)
        assert result is None
        backend.webauthn_set_credential_properties.assert_called_once_with(
            "auth-1", "cred-1", True, False
        )

    async def test_set_response_override_bits(self) -> None:
        """Test set-response-override-bits action."""
        backend = self._make_backend()
        params = WebAuthnParams(
            action="set-response-override-bits", authenticator_id="auth-1", is_bogus_signature=True
        )
        result = await WebAuthnAction(params).execute(backend)
        assert result is None
        backend.webauthn_set_response_override_bits.assert_called_once_with(
            "auth-1", True, False, False
        )
