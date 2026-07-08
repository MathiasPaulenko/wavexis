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
            "add-credential", "get-credentials".
        protocol: Authenticator protocol (e.g. "ctap2", "u2f").
        transport: Transport type (e.g. "usb", "nfc", "ble").
        authenticator_id: Authenticator ID for operations requiring it.
        credential: Credential dict for add-credential.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    action: str = "add-virtual-authenticator"
    protocol: str = "ctap2"
    transport: str = "usb"
    authenticator_id: str | None = None
    credential: dict[str, Any] | None = None
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
                raise ValueError(
                    "authenticator_id is required for remove-authenticator"
                )
            await backend.webauthn_remove_authenticator(
                self.params.authenticator_id
            )
            return None

        if action == "add-credential":
            if not self.params.authenticator_id or not self.params.credential:
                raise ValueError(
                    "authenticator_id and credential are required "
                    "for add-credential"
                )
            await backend.webauthn_add_credential(
                self.params.authenticator_id, self.params.credential
            )
            return None

        if action == "get-credentials":
            if not self.params.authenticator_id:
                raise ValueError(
                    "authenticator_id is required for get-credentials"
                )
            return await backend.webauthn_get_credentials(
                self.params.authenticator_id
            )

        raise ValueError(f"Unknown WebAuthn action: {action}")
