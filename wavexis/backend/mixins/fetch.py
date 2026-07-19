"""Fetch mixin — request interception and modification."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class FetchBackend(ABC):
    """Fetch domain operations for request interception."""

    @abstractmethod
    async def fetch_continue_request(
        self,
        request_id: str,
        url: str | None = None,
        method: str | None = None,
        post_data: str | None = None,
        headers: list[dict[str, Any]] | None = None,
    ) -> None:
        """Continue a paused request with optional modifications."""

    @abstractmethod
    async def fetch_continue_request_with_auth(
        self, request_id: str, auth_challenge_response: dict[str, Any]
    ) -> None:
        """Continue a paused request with authentication."""

    @abstractmethod
    async def fetch_continue_response(
        self,
        request_id: str,
        response_code: int = 200,
        response_headers: list[dict[str, Any]] | None = None,
        binary_response_headers: str | None = None,
    ) -> None:
        """Continue a paused response."""

    @abstractmethod
    async def fetch_continue_with_auth(
        self, request_id: str, auth_challenge_response: dict[str, Any]
    ) -> None:
        """Continue a paused request with auth challenge response."""

    @abstractmethod
    async def fetch_disable(self) -> None:
        """Disable the Fetch domain."""

    @abstractmethod
    async def fetch_enable(
        self, patterns: list[dict[str, Any]] | None = None, handle_auth_requests: bool = False
    ) -> None:
        """Enable the Fetch domain with optional patterns."""

    @abstractmethod
    async def fetch_fail_request(self, request_id: str, error_reason: str) -> None:
        """Fail a paused request with an error."""

    @abstractmethod
    async def fetch_fulfill_request(
        self,
        request_id: str,
        response_code: int = 200,
        response_headers: list[dict[str, Any]] | None = None,
        body: str | None = None,
    ) -> None:
        """Fulfill a paused request with a response."""

    @abstractmethod
    async def fetch_get_request_post_data(self, request_id: str) -> str:
        """Get the POST data of a paused request."""

    @abstractmethod
    async def fetch_take_response_body_as_stream(self, request_id: str) -> dict[str, Any]:
        """Take the response body of a paused request as a stream."""
