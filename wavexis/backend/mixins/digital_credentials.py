"""DigitalCredentials mixin — virtual wallet behavior."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DigitalCredentialsBackend(ABC):
    """Digital credentials virtual wallet operations."""

    @abstractmethod
    async def digital_credentials_set_virtual_wallet_behavior(
        self, behavior: dict[str, Any]
    ) -> None:
        """Set the virtual wallet behavior for digital credentials."""
