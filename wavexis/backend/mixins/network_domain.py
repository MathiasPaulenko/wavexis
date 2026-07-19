"""Network domain mixin for AbstractBackend (additional CDP Network methods)."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any


class NetworkDomainBackend:
    """Additional CDP Network domain methods not covered by NetworkBackend."""

    @abstractmethod
    async def network_clear_accepted_encodings_override(self) -> None:
        """Clear the accepted encodings override."""

    @abstractmethod
    async def network_configure_durable_messages(self, options: dict[str, Any]) -> None:
        """Configure durable messages."""

    @abstractmethod
    async def network_delete_device_bound_session(self, session_id: str) -> None:
        """Delete a device-bound session."""

    @abstractmethod
    async def network_disable(self) -> None:
        """Disable the Network domain."""

    @abstractmethod
    async def network_emulate_network_conditions_by_rule(
        self,
        download_throughput: float = 0,
        upload_throughput: float = 0,
        offline: bool = False,
        latency: float = 0,
        connection_type: str = "",
    ) -> None:
        """Emulate network conditions by rule."""

    @abstractmethod
    async def network_enable(
        self, max_total_buffer_size: int = 0, max_resource_buffer_size: int = 0
    ) -> None:
        """Enable the Network domain."""

    @abstractmethod
    async def network_enable_device_bound_sessions(self) -> None:
        """Enable device-bound sessions."""

    @abstractmethod
    async def network_enable_reporting_api(self, enable: bool) -> None:
        """Enable or disable the Reporting API."""

    @abstractmethod
    async def network_fetch_schemeful_site(self, request_id: str) -> dict[str, Any]:
        """Fetch the schemeful site for a request."""

    @abstractmethod
    async def network_get_certificate(self, origin: str) -> dict[str, Any]:
        """Get the certificate for an origin."""

    @abstractmethod
    async def network_get_request_post_data(self, request_id: str) -> str:
        """Get the POST data for a request."""

    @abstractmethod
    async def network_get_response_body_for_interception(self, interception_id: str) -> str:
        """Get the response body for an interception."""

    @abstractmethod
    async def network_get_security_isolation_status(self, frame_id: str = "") -> dict[str, Any]:
        """Get the security isolation status."""

    @abstractmethod
    async def network_override_network_state(self, state: dict[str, Any]) -> None:
        """Override the network state."""

    @abstractmethod
    async def network_search_in_response_body(
        self, request_id: str, query: str, case_sensitive: bool = False, is_regex: bool = False
    ) -> dict[str, Any]:
        """Search in a response body."""

    @abstractmethod
    async def network_set_accepted_encodings(self, encodings: list[str]) -> None:
        """Set accepted encodings."""

    @abstractmethod
    async def network_set_attach_debug_stack(self, enabled: bool) -> None:
        """Set whether to attach debug stack to network requests."""

    @abstractmethod
    async def network_set_cookies(self, cookies: list[dict[str, Any]]) -> None:
        """Set cookies."""

    @abstractmethod
    async def network_stream_resource_content(self, request_id: str) -> dict[str, Any]:
        """Stream resource content for a request."""

    @abstractmethod
    async def network_take_response_body_for_interception_as_stream(
        self, interception_id: str
    ) -> dict[str, Any]:
        """Take the response body for an interception as a stream."""
