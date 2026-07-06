"""Base action class for wavexis actions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from wavexis.backend.base import AbstractBackend

P = TypeVar("P")
R = TypeVar("R")


class BaseAction(ABC, Generic[P, R]):
    """Abstract base class for all wavexis actions.

    An action encapsulates a single operation (e.g. screenshot, eval, pdf)
    that is executed against a backend.
    """

    def __init__(self, params: P) -> None:
        """Initialize the action with parameters.

        Args:
            params: Action-specific parameters.
        """
        self.params = params

    @abstractmethod
    async def execute(self, backend: AbstractBackend) -> R:
        """Execute the action against the given backend."""
