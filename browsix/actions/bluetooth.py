"""Bluetooth action for BLE emulation (experimental)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from browsix.actions.base import BaseAction
from browsix.backend.base import AbstractBackend
from browsix.config import BrowserOptions, WaitStrategy


@dataclass
class BluetoothParams:
    """Parameters for Bluetooth emulation operations.

    Attributes:
        url: URL to navigate to before Bluetooth operations.
        action: Bluetooth action — "emulate", "stop".
        name: Device name for "emulate" action.
        address: Device MAC address for "emulate" action.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    action: str = "emulate"
    name: str | None = None
    address: str = "00:00:00:00:00:01"
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class BluetoothAction(BaseAction[BluetoothParams, Any]):
    """Action for Bluetooth emulation operations (experimental)."""

    async def execute(self, backend: AbstractBackend) -> Any:
        """Execute the Bluetooth action on the backend.

        Args:
            backend: An AbstractBackend instance.

        Returns:
            Result of the Bluetooth operation.
        """
        try:
            await backend.launch(self.params.browser)
            if self.params.url:
                await backend.navigate(self.params.url, self.params.wait)

            action = self.params.action

            if action == "emulate":
                if not self.params.name:
                    raise ValueError("name is required for emulate action")
                await backend.bluetooth_emulate(
                    self.params.name, self.params.address
                )
                return None

            if action == "stop":
                await backend.bluetooth_stop()
                return None

            raise ValueError(f"Unknown Bluetooth action: {action}")

        finally:
            await backend.close()
