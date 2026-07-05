"""Unit tests for WebAuthnAction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from browsix.actions.webauthn import WebAuthnAction, WebAuthnParams


@pytest.mark.unit
class TestWebAuthnAction:
    def _make_backend(self) -> MagicMock:
        backend = MagicMock()
        backend.launch = AsyncMock()
        backend.navigate = AsyncMock()
        backend.close = AsyncMock()
        backend.webauthn_add_virtual_authenticator = AsyncMock(
            return_value="auth-id-123"
        )
        backend.webauthn_remove_authenticator = AsyncMock()
        backend.webauthn_add_credential = AsyncMock()
        backend.webauthn_get_credentials = AsyncMock(
            return_value=[{"credentialId": "cred1"}]
        )
        return backend

    async def test_add_virtual_authenticator(self) -> None:
        backend = self._make_backend()
        params = WebAuthnParams(
            url="https://example.com",
            action="add-virtual-authenticator",
            protocol="ctap2",
            transport="usb",
        )
        result = await WebAuthnAction(params).execute(backend)
        assert result == "auth-id-123"
        backend.webauthn_add_virtual_authenticator.assert_called_once_with(
            "ctap2", "usb"
        )

    async def test_remove_authenticator(self) -> None:
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
        backend = self._make_backend()
        params = WebAuthnParams(
            url="https://example.com",
            action="remove-authenticator",
        )
        with pytest.raises(ValueError, match="authenticator_id is required"):
            await WebAuthnAction(params).execute(backend)

    async def test_add_credential(self) -> None:
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
        backend = self._make_backend()
        params = WebAuthnParams(
            url="https://example.com",
            action="add-credential",
        )
        with pytest.raises(ValueError, match="authenticator_id and credential"):
            await WebAuthnAction(params).execute(backend)

    async def test_get_credentials(self) -> None:
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
        backend = self._make_backend()
        params = WebAuthnParams(
            url="https://example.com",
            action="get-credentials",
        )
        with pytest.raises(ValueError, match="authenticator_id is required"):
            await WebAuthnAction(params).execute(backend)

    async def test_unknown_action_raises(self) -> None:
        backend = self._make_backend()
        params = WebAuthnParams(
            url="https://example.com",
            action="invalid",
        )
        with pytest.raises(ValueError, match="Unknown WebAuthn action"):
            await WebAuthnAction(params).execute(backend)

    async def test_lifecycle(self) -> None:
        backend = self._make_backend()
        params = WebAuthnParams(url="https://example.com", action="add-virtual-authenticator")
        await WebAuthnAction(params).execute(backend)
        backend.launch.assert_called_once()
        backend.navigate.assert_called_once()
        backend.close.assert_called_once()

    async def test_no_url_skips_navigate(self) -> None:
        backend = self._make_backend()
        params = WebAuthnParams(url="", action="add-virtual-authenticator")
        await WebAuthnAction(params).execute(backend)
        backend.launch.assert_called_once()
        backend.navigate.assert_not_called()
        backend.close.assert_called_once()
