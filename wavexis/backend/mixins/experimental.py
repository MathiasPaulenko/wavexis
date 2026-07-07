"""Experimental CDP domains mixin.

Groups less-common experimental domains: WebAuthn, WebAudio, Media,
Cast, Bluetooth, WebExtensions, and browser preferences.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ExperimentalBackend(ABC):
    """Experimental browser automation features."""

    # ── WebAuthn ──────────────────────────────────────────

    @abstractmethod
    async def webauthn_add_virtual_authenticator(
        self, protocol: str, transport: str
    ) -> str:
        """Add a virtual authenticator for WebAuthn testing.

        Args:
            protocol: Authenticator protocol (e.g. "ctap2", "u2f").
            transport: Transport type (e.g. "usb", "nfc", "ble").

        Returns:
            The authenticator ID.
        """

    @abstractmethod
    async def webauthn_remove_authenticator(self, authenticator_id: str) -> None:
        """Remove a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID to remove.
        """

    @abstractmethod
    async def webauthn_add_credential(
        self, authenticator_id: str, credential: dict[str, Any]
    ) -> None:
        """Add a credential to a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID.
            credential: Credential dict.
        """

    @abstractmethod
    async def webauthn_get_credentials(self, authenticator_id: str) -> list[dict[str, Any]]:
        """Get credentials from a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID.

        Returns:
            List of credential dicts.
        """

    # ── WebAudio ──────────────────────────────────────────

    @abstractmethod
    async def webaudio_get_contexts(self) -> list[dict[str, Any]]:
        """Get all WebAudio contexts.

        Returns:
            List of audio context dicts.
        """

    @abstractmethod
    async def webaudio_get_context(self, context_id: str) -> dict[str, Any]:
        """Get a specific WebAudio context by ID.

        Args:
            context_id: The audio context ID.

        Returns:
            Audio context dict.
        """

    # ── Media ─────────────────────────────────────────────

    @abstractmethod
    async def media_get_players(self) -> list[dict[str, Any]]:
        """Get all media players.

        Returns:
            List of media player dicts.
        """

    @abstractmethod
    async def media_get_messages(self, player_id: str) -> list[dict[str, Any]]:
        """Get messages for a specific media player.

        Args:
            player_id: The media player ID.

        Returns:
            List of media message dicts.
        """

    # ── Cast ──────────────────────────────────────────────

    @abstractmethod
    async def cast_list(self) -> list[dict[str, Any]]:
        """List available cast sinks.

        Returns:
            List of cast sink dicts.
        """

    @abstractmethod
    async def cast_start_tab(self, sink_name: str) -> None:
        """Start tab mirroring to a cast sink.

        Args:
            sink_name: The cast sink name.
        """

    @abstractmethod
    async def cast_stop(self) -> None:
        """Stop active cast mirroring."""

    # ── Bluetooth ─────────────────────────────────────────

    @abstractmethod
    async def bluetooth_emulate(
        self, name: str, address: str = "00:00:00:00:00:01"
    ) -> None:
        """Emulate a Bluetooth Low Energy device.

        Args:
            name: Device name.
            address: Device address (MAC).
        """

    @abstractmethod
    async def bluetooth_stop(self) -> None:
        """Stop Bluetooth emulation."""

    # ── WebExtensions ─────────────────────────────────────

    @abstractmethod
    async def extension_install(self, path: str) -> str:
        """Install a browser extension from a .crx or unpacked directory.

        Args:
            path: Path to the .crx file or unpacked extension directory.

        Returns:
            The extension ID.
        """

    @abstractmethod
    async def extension_uninstall(self, extension_id: str) -> None:
        """Uninstall a browser extension by ID.

        Args:
            extension_id: The extension ID returned by extension_install.
        """

    @abstractmethod
    async def extension_list(self) -> list[dict[str, Any]]:
        """List installed browser extensions.

        Returns:
            List of extension dicts (id, name, version, enabled).
        """

    # ── Browser preferences ───────────────────────────────

    @abstractmethod
    async def get_pref(self, key: str) -> Any:
        """Get a browser preference value by key.

        Args:
            key: The preference key (e.g. "download.default_directory").

        Returns:
            The preference value.
        """

    @abstractmethod
    async def set_pref(self, key: str, value: Any) -> None:
        """Set a browser preference value.

        Args:
            key: The preference key.
            value: The value to set.
        """
