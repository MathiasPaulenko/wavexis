"""FedCm mixin — Federated Credential Management operations."""

from __future__ import annotations

from abc import ABC, abstractmethod


class FedCmBackend(ABC):
    """Federated Credential Management operations."""

    @abstractmethod
    async def fed_cm_click_dialog_button(self, dialog_id: str, button_index: int) -> None:
        """Click a button in a FedCm dialog."""

    @abstractmethod
    async def fed_cm_disable(self) -> None:
        """Disable the FedCm domain."""

    @abstractmethod
    async def fed_cm_dismiss_dialog(self, dialog_id: str) -> None:
        """Dismiss a FedCm dialog."""

    @abstractmethod
    async def fed_cm_enable(self) -> None:
        """Enable the FedCm domain."""

    @abstractmethod
    async def fed_cm_open_url(self, dialog_id: str, account_index: int, url: str) -> None:
        """Open a URL from a FedCm dialog."""

    @abstractmethod
    async def fed_cm_reset_cooldown(self) -> None:
        """Reset the FedCm cooldown."""

    @abstractmethod
    async def fed_cm_select_account(self, dialog_id: str, account_index: int) -> None:
        """Select an account in a FedCm dialog."""
