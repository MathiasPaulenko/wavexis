"""FileSystem mixin — file system operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class FileSystemBackend(ABC):
    """File system operations."""

    @abstractmethod
    async def file_system_get_directory(
        self, storage_key: str, path_components: list[str], bucket_name: str = ""
    ) -> dict[str, Any]:
        """Get a file system directory by storage key and path components."""
