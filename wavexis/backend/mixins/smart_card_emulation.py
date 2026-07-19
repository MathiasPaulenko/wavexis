"""SmartCardEmulation mixin — smart card reader emulation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SmartCardEmulationBackend(ABC):
    """Smart card reader emulation operations."""

    @abstractmethod
    async def smart_card_enable(self) -> None:
        """Enable the SmartCardEmulation domain."""

    @abstractmethod
    async def smart_card_disable(self) -> None:
        """Disable the SmartCardEmulation domain."""

    @abstractmethod
    async def smart_card_report_error(self, request_id: str, error: str) -> None:
        """Report an error for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            error: Error code string.
        """

    @abstractmethod
    async def smart_card_report_plain_result(self, request_id: str, result_code: int) -> None:
        """Report a plain result for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
        """

    @abstractmethod
    async def smart_card_report_connect_result(
        self, request_id: str, result_code: int, connection_id: str
    ) -> None:
        """Report a connect result for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
            connection_id: Established connection identifier.
        """

    @abstractmethod
    async def smart_card_report_data_result(
        self, request_id: str, result_code: int, data: str
    ) -> None:
        """Report a data result for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
            data: Response data (hex-encoded).
        """

    @abstractmethod
    async def smart_card_report_status_result(self, request_id: str, status: str) -> None:
        """Report a status result for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            status: Status string.
        """

    @abstractmethod
    async def smart_card_report_begin_transaction_result(
        self, request_id: str, result_code: int
    ) -> None:
        """Report a begin-transaction result for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
        """

    @abstractmethod
    async def smart_card_report_establish_context_result(
        self, request_id: str, result_code: int, context_id: str
    ) -> None:
        """Report an establish-context result for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
            context_id: Established context identifier.
        """

    @abstractmethod
    async def smart_card_report_release_context_result(
        self, request_id: str, result_code: int
    ) -> None:
        """Report a release-context result for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
        """

    @abstractmethod
    async def smart_card_report_list_readers_result(
        self, request_id: str, result_code: int, readers: list[dict[str, Any]]
    ) -> None:
        """Report a list-readers result for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
            readers: List of reader dicts.
        """

    @abstractmethod
    async def smart_card_report_get_status_change_result(
        self, request_id: str, result_code: int, readers: list[dict[str, Any]]
    ) -> None:
        """Report a get-status-change result for a pending smart card request.

        Args:
            request_id: The pending request identifier.
            result_code: Smart card result code.
            readers: List of reader status dicts.
        """
