"""Target mixin — browser target management (tabs, contexts, attachments)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class TargetBackend(ABC):
    """Browser target management: tabs, contexts, and auto-attach."""

    @abstractmethod
    async def target_get_targets(self) -> list[dict[str, Any]]:
        """Get all available targets.

        Returns:
            List of target info dicts.
        """

    @abstractmethod
    async def target_create_target(self, url: str) -> str:
        """Create a new target (tab) with the given URL.

        Args:
            url: The initial URL for the new target.

        Returns:
            The target ID of the new target.
        """

    @abstractmethod
    async def target_close_target(self, target_id: str) -> None:
        """Close a target by ID.

        Args:
            target_id: The target ID to close.
        """

    @abstractmethod
    async def target_activate_target(self, target_id: str) -> None:
        """Activate (focus) a target by ID.

        Args:
            target_id: The target ID to activate.
        """

    @abstractmethod
    async def target_attach_to_target(self, target_id: str, flatten: bool = True) -> str:
        """Attach to a target by ID.

        Args:
            target_id: The target ID to attach to.
            flatten: Whether to flatten the session.

        Returns:
            The session ID of the attachment.
        """

    @abstractmethod
    async def target_detach_from_target(self, session_id: str) -> None:
        """Detach from a target by session ID.

        Args:
            session_id: The session ID to detach.
        """

    @abstractmethod
    async def target_set_auto_attach(
        self, auto_attach: bool, wait_for_debugger_on_start: bool = False
    ) -> None:
        """Set auto-attach for new targets.

        Args:
            auto_attach: Whether to auto-attach to new targets.
            wait_for_debugger_on_start: Whether to wait for debugger on start.
        """

    @abstractmethod
    async def target_set_discover_targets(self, discover: bool) -> None:
        """Enable or disable target discovery.

        Args:
            discover: Whether to discover targets.
        """

    @abstractmethod
    async def target_get_target_info(self, target_id: str) -> dict[str, Any]:
        """Get info about a specific target.

        Args:
            target_id: The target ID to query.

        Returns:
            Target info dict.
        """

    @abstractmethod
    async def target_create_browser_context(self) -> str:
        """Create a new browser context.

        Returns:
            The browser context ID.
        """

    @abstractmethod
    async def target_attach_to_browser_target(self) -> str:
        """Attach to the browser target.

        Returns:
            The session ID of the attachment.
        """

    @abstractmethod
    async def target_auto_attach_related(
        self, target_id: str, wait_for_debugger_on_start: bool = False
    ) -> None:
        """Auto-attach to related targets of a given target.

        Args:
            target_id: The target ID to auto-attach related targets for.
            wait_for_debugger_on_start: Whether to wait for debugger on start.
        """

    @abstractmethod
    async def target_dispose_browser_context(self, browser_context_id: str) -> None:
        """Dispose a browser context by ID.

        Args:
            browser_context_id: The browser context ID to dispose.
        """

    @abstractmethod
    async def target_expose_dev_tools_protocol(self, target_id: str, binding_name: str) -> None:
        """Expose DevTools protocol API to the target.

        Args:
            target_id: The target ID to expose the protocol to.
            binding_name: The binding name to use.
        """

    @abstractmethod
    async def target_get_browser_contexts(self) -> list[str]:
        """Get all browser contexts.

        Returns:
            List of browser context IDs.
        """

    @abstractmethod
    async def target_get_dev_tools_target(self, target_id: str) -> str:
        """Get the DevTools target for a given target.

        Args:
            target_id: The target ID to query.

        Returns:
            The DevTools target ID.
        """

    @abstractmethod
    async def target_open_dev_tools(self, target_id: str) -> None:
        """Open DevTools for a target.

        Args:
            target_id: The target ID to open DevTools for.
        """

    @abstractmethod
    async def target_send_message_to_target(self, session_id: str, message: str) -> None:
        """Send a message to a target via session ID.

        Args:
            session_id: The session ID to send the message to.
            message: The message to send.
        """

    @abstractmethod
    async def target_set_remote_locations(self, locations: list[dict[str, str]]) -> None:
        """Set remote locations for target discovery.

        Args:
            locations: List of location dicts with host and port keys.
        """
