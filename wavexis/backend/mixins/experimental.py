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
    async def webauthn_add_virtual_authenticator(self, protocol: str, transport: str) -> str:
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

    @abstractmethod
    async def webauthn_enable(self) -> None:
        """Enable the WebAuthn domain."""

    @abstractmethod
    async def webauthn_disable(self) -> None:
        """Disable the WebAuthn domain."""

    @abstractmethod
    async def webauthn_get_credential(
        self, authenticator_id: str, credential_id: str
    ) -> dict[str, Any]:
        """Get a specific credential from a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID.
            credential_id: The credential ID.

        Returns:
            Credential dict.
        """

    @abstractmethod
    async def webauthn_remove_credential(self, authenticator_id: str, credential_id: str) -> None:
        """Remove a credential from a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID.
            credential_id: The credential ID.
        """

    @abstractmethod
    async def webauthn_clear_credentials(self, authenticator_id: str) -> None:
        """Clear all credentials from a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID.
        """

    @abstractmethod
    async def webauthn_set_user_verified(
        self, authenticator_id: str, is_user_verified: bool
    ) -> None:
        """Set the user-verified flag on a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID.
            is_user_verified: Whether the user is verified.
        """

    @abstractmethod
    async def webauthn_set_automatic_presence_simulation(
        self, authenticator_id: str, enabled: bool
    ) -> None:
        """Set automatic presence simulation on a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID.
            enabled: Whether to enable presence simulation.
        """

    @abstractmethod
    async def webauthn_set_credential_properties(
        self,
        authenticator_id: str,
        credential_id: str,
        backup_state: bool = False,
        backup_eligibility: bool = False,
    ) -> None:
        """Set credential properties on a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID.
            credential_id: The credential ID.
            backup_state: The backup state.
            backup_eligibility: The backup eligibility.
        """

    @abstractmethod
    async def webauthn_set_response_override_bits(
        self,
        authenticator_id: str,
        is_bogus_signature: bool = False,
        is_bad_uv: bool = False,
        is_bad_up: bool = False,
    ) -> None:
        """Set response override bits on a virtual authenticator.

        Args:
            authenticator_id: The authenticator ID.
            is_bogus_signature: Whether to return bogus signatures.
            is_bad_uv: Whether to return bad UV responses.
            is_bad_up: Whether to return bad UP responses.
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

    @abstractmethod
    async def webaudio_enable(self) -> None:
        """Enable the WebAudio domain."""

    @abstractmethod
    async def webaudio_disable(self) -> None:
        """Disable the WebAudio domain."""

    @abstractmethod
    async def webaudio_get_realtime_data(self, context_id: str) -> dict[str, Any]:
        """Get realtime data for a WebAudio context.

        Args:
            context_id: The audio context ID.

        Returns:
            Dict with realtime audio data.
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

    @abstractmethod
    async def cast_enable(self) -> None:
        """Enable the Cast domain."""

    @abstractmethod
    async def cast_disable(self) -> None:
        """Disable the Cast domain."""

    @abstractmethod
    async def cast_set_sink_to_use(self, sink_name: str) -> None:
        """Set a sink to use for cast.

        Args:
            sink_name: The cast sink name.
        """

    @abstractmethod
    async def cast_start_desktop_mirroring(self, sink_name: str) -> None:
        """Start desktop mirroring to a cast sink.

        Args:
            sink_name: The cast sink name.
        """

    @abstractmethod
    async def cast_start_tab_mirroring(self, sink_name: str) -> None:
        """Start tab mirroring to a cast sink.

        Args:
            sink_name: The cast sink name.
        """

    @abstractmethod
    async def cast_stop_casting(self, sink_name: str) -> None:
        """Stop casting to a specific sink.

        Args:
            sink_name: The cast sink name.
        """

    # ── Bluetooth ─────────────────────────────────────────

    @abstractmethod
    async def bluetooth_emulate(self, name: str, address: str = "00:00:00:00:00:01") -> None:
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

    # ── Tethering ─────────────────────────────────────────

    @abstractmethod
    async def tethering_bind(self, port: int) -> None:
        """Bind a port for tethering (accept incoming connections).

        Args:
            port: The port number to bind.
        """

    @abstractmethod
    async def tethering_unbind(self, port: int) -> None:
        """Unbind a port from tethering.

        Args:
            port: The port number to unbind.
        """

    # ── WebMcp ────────────────────────────────────────────

    @abstractmethod
    async def web_mcp_enable(self) -> None:
        """Enable the WebMcp domain."""

    @abstractmethod
    async def web_mcp_disable(self) -> None:
        """Disable the WebMcp domain."""
