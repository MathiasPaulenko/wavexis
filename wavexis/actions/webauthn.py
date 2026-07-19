"""WebAuthn action for virtual authenticator management (experimental)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy


@dataclass
class WebAuthnParams:
    """Parameters for WebAuthn operations.

    Attributes:
        url: URL to navigate to before WebAuthn operations.
        action: WebAuthn action — "add-virtual-authenticator", "remove-authenticator",
            "add-credential", "get-credentials", "enable", "disable",
            "get-credential", "remove-credential", "clear-credentials",
            "set-user-verified", "set-automatic-presence-simulation",
            "set-credential-properties", "set-response-override-bits".
        protocol: Authenticator protocol (e.g. "ctap2", "u2f").
        transport: Transport type (e.g. "usb", "nfc", "ble").
        authenticator_id: Authenticator ID for operations requiring it.
        credential: Credential dict for add-credential.
        credential_id: Credential ID for operations requiring it.
        is_user_verified: User verified flag for set-user-verified.
        enabled: Enabled flag for set-automatic-presence-simulation.
        backup_state: Backup state for set-credential-properties.
        backup_eligibility: Backup eligibility for set-credential-properties.
        is_bogus_signature: Bogus signature flag for set-response-override-bits.
        is_bad_uv: Bad UV flag for set-response-override-bits.
        is_bad_up: Bad UP flag for set-response-override-bits.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    action: str = "add-virtual-authenticator"
    protocol: str = "ctap2"
    transport: str = "usb"
    authenticator_id: str | None = None
    credential: dict[str, Any] | None = None
    credential_id: str | None = None
    is_user_verified: bool = False
    enabled: bool = False
    backup_state: bool = False
    backup_eligibility: bool = False
    is_bogus_signature: bool = False
    is_bad_uv: bool = False
    is_bad_up: bool = False
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class WebAuthnAction(BaseAction[WebAuthnParams, Any]):
    """Action for WebAuthn virtual authenticator operations (experimental)."""

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the WebAuthn action on the backend.

        Args:
            backend: An AbstractBackend instance.

        Returns:
            Result of the WebAuthn operation.
        """
        if self.params.url:
            await backend.navigate(self.params.url, self.params.wait)

        action = self.params.action

        if action == "add-virtual-authenticator":
            return await backend.webauthn_add_virtual_authenticator(
                self.params.protocol, self.params.transport
            )

        if action == "remove-authenticator":
            if not self.params.authenticator_id:
                raise ValueError("authenticator_id is required for remove-authenticator")
            await backend.webauthn_remove_authenticator(self.params.authenticator_id)
            return None

        if action == "add-credential":
            if not self.params.authenticator_id or not self.params.credential:
                raise ValueError("authenticator_id and credential are required for add-credential")
            await backend.webauthn_add_credential(
                self.params.authenticator_id, self.params.credential
            )
            return None

        if action == "get-credentials":
            if not self.params.authenticator_id:
                raise ValueError("authenticator_id is required for get-credentials")
            return await backend.webauthn_get_credentials(self.params.authenticator_id)

        if action == "enable":
            await backend.webauthn_enable()
            return None

        if action == "disable":
            await backend.webauthn_disable()
            return None

        if action == "get-credential":
            if not self.params.authenticator_id or not self.params.credential_id:
                raise ValueError(
                    "authenticator_id and credential_id are required for get-credential"
                )
            return await backend.webauthn_get_credential(
                self.params.authenticator_id, self.params.credential_id
            )

        if action == "remove-credential":
            if not self.params.authenticator_id or not self.params.credential_id:
                raise ValueError(
                    "authenticator_id and credential_id are required for remove-credential"
                )
            await backend.webauthn_remove_credential(
                self.params.authenticator_id, self.params.credential_id
            )
            return None

        if action == "clear-credentials":
            if not self.params.authenticator_id:
                raise ValueError("authenticator_id is required for clear-credentials")
            await backend.webauthn_clear_credentials(self.params.authenticator_id)
            return None

        if action == "set-user-verified":
            if not self.params.authenticator_id:
                raise ValueError("authenticator_id is required for set-user-verified")
            await backend.webauthn_set_user_verified(
                self.params.authenticator_id, self.params.is_user_verified
            )
            return None

        if action == "set-automatic-presence-simulation":
            if not self.params.authenticator_id:
                raise ValueError(
                    "authenticator_id is required for set-automatic-presence-simulation"
                )
            await backend.webauthn_set_automatic_presence_simulation(
                self.params.authenticator_id, self.params.enabled
            )
            return None

        if action == "set-credential-properties":
            if not self.params.authenticator_id or not self.params.credential_id:
                raise ValueError(
                    "authenticator_id and credential_id are required for set-credential-properties"
                )
            await backend.webauthn_set_credential_properties(
                self.params.authenticator_id,
                self.params.credential_id,
                self.params.backup_state,
                self.params.backup_eligibility,
            )
            return None

        if action == "set-response-override-bits":
            if not self.params.authenticator_id:
                raise ValueError("authenticator_id is required for set-response-override-bits")
            await backend.webauthn_set_response_override_bits(
                self.params.authenticator_id,
                self.params.is_bogus_signature,
                self.params.is_bad_uv,
                self.params.is_bad_up,
            )
            return None

        raise ValueError(f"Unknown WebAuthn action: {action}")
