"""PWA mixin — Progressive Web App operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PwaBackend(ABC):
    """Progressive Web App operations for installation and management."""

    @abstractmethod
    async def pwa_change_app_user_settings(
        self, app_id: str, user_settings: dict[str, Any]
    ) -> None:
        """Change PWA user settings.

        Args:
            app_id: The app ID.
            user_settings: Dictionary of user settings to change.
        """

    @abstractmethod
    async def pwa_get_os_app_state(self, app_id: str) -> dict[str, Any]:
        """Get the OS-level state of a PWA.

        Args:
            app_id: The app ID.

        Returns:
            Dict containing the app state.
        """

    @abstractmethod
    async def pwa_install(self, manifest_id: str, install_url: str | None = None) -> None:
        """Install a PWA.

        Args:
            manifest_id: The manifest ID of the PWA.
            install_url: Optional install URL.
        """

    @abstractmethod
    async def pwa_launch_files_in_app(self, app_id: str, files: list[str]) -> dict[str, Any]:
        """Launch files in a PWA.

        Args:
            app_id: The app ID.
            files: List of file paths to launch.

        Returns:
            Dict containing the launch result.
        """

    @abstractmethod
    async def pwa_open_current_page_in_app(self, app_id: str) -> dict[str, Any]:
        """Open the current page in a PWA.

        Args:
            app_id: The app ID.

        Returns:
            Dict containing the target info.
        """

    @abstractmethod
    async def pwa_uninstall(self, app_id: str) -> None:
        """Uninstall a PWA.

        Args:
            app_id: The app ID.
        """
