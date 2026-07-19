"""SmartCardEmulation action for smart card reader emulation (experimental)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy


@dataclass
class SmartCardEmulationParams:
    """Parameters for smart card emulation operations.

    Attributes:
        url: URL to navigate to before smart card operations.
        action: Smart card action — "enable", "disable", "report-error",
            "report-plain", "report-connect", "report-data",
            "report-status", "report-begin-transaction",
            "report-establish-context", "report-release-context",
            "report-list-readers", "report-get-status-change".
        request_id: Pending request identifier (required for report-* actions).
        result_code: Smart card result code (required for most report-* actions).
        error: Error code string (required for report-error).
        connection_id: Connection identifier (required for report-connect).
        context_id: Context identifier (required for report-establish-context).
        data: Response data hex string (required for report-data).
        status: Status string (required for report-status).
        readers: List of reader dicts (required for report-list-readers
            and report-get-status-change).
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    action: str = "enable"
    request_id: str | None = None
    result_code: int = 0
    error: str | None = None
    connection_id: str | None = None
    context_id: str | None = None
    data: str | None = None
    status: str | None = None
    readers: list[dict[str, Any]] | None = None
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class SmartCardEmulationAction(BaseAction[SmartCardEmulationParams, Any]):
    """Action for smart card reader emulation operations (experimental)."""

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the smart card emulation action on the backend.

        Args:
            backend: An AbstractBackend instance.

        Returns:
            Result of the smart card emulation operation.
        """
        if self.params.url:
            await backend.navigate(self.params.url, self.params.wait)

        action = self.params.action

        if action == "enable":
            await backend.smart_card_enable()
            return None

        if action == "disable":
            await backend.smart_card_disable()
            return None

        if action == "report-error":
            if not self.params.request_id or not self.params.error:
                raise ValueError("request_id and error are required for report-error")
            await backend.smart_card_report_error(self.params.request_id, self.params.error)
            return None

        if action == "report-plain":
            if not self.params.request_id:
                raise ValueError("request_id is required for report-plain")
            await backend.smart_card_report_plain_result(
                self.params.request_id, self.params.result_code
            )
            return None

        if action == "report-connect":
            if not self.params.request_id or not self.params.connection_id:
                raise ValueError("request_id and connection_id are required for report-connect")
            await backend.smart_card_report_connect_result(
                self.params.request_id,
                self.params.result_code,
                self.params.connection_id,
            )
            return None

        if action == "report-data":
            if not self.params.request_id or self.params.data is None:
                raise ValueError("request_id and data are required for report-data")
            await backend.smart_card_report_data_result(
                self.params.request_id,
                self.params.result_code,
                self.params.data,
            )
            return None

        if action == "report-status":
            if not self.params.request_id or not self.params.status:
                raise ValueError("request_id and status are required for report-status")
            await backend.smart_card_report_status_result(
                self.params.request_id, self.params.status
            )
            return None

        if action == "report-begin-transaction":
            if not self.params.request_id:
                raise ValueError("request_id is required for report-begin-transaction")
            await backend.smart_card_report_begin_transaction_result(
                self.params.request_id, self.params.result_code
            )
            return None

        if action == "report-establish-context":
            if not self.params.request_id or not self.params.context_id:
                raise ValueError(
                    "request_id and context_id are required for report-establish-context"
                )
            await backend.smart_card_report_establish_context_result(
                self.params.request_id,
                self.params.result_code,
                self.params.context_id,
            )
            return None

        if action == "report-release-context":
            if not self.params.request_id:
                raise ValueError("request_id is required for report-release-context")
            await backend.smart_card_report_release_context_result(
                self.params.request_id, self.params.result_code
            )
            return None

        if action == "report-list-readers":
            if not self.params.request_id or self.params.readers is None:
                raise ValueError("request_id and readers are required for report-list-readers")
            await backend.smart_card_report_list_readers_result(
                self.params.request_id,
                self.params.result_code,
                self.params.readers,
            )
            return None

        if action == "report-get-status-change":
            if not self.params.request_id or self.params.readers is None:
                raise ValueError("request_id and readers are required for report-get-status-change")
            await backend.smart_card_report_get_status_change_result(
                self.params.request_id,
                self.params.result_code,
                self.params.readers,
            )
            return None

        raise ValueError(f"Unknown SmartCardEmulation action: {action}")
