"""Exception hierarchy for browsix."""


class BrowsixError(Exception):
    """Base exception for all browsix errors."""


class BackendNotAvailableError(BrowsixError):
    """Raised when no backend (cdpwave/bidiwave) is installed."""

    def __init__(self, backend: str | None = None) -> None:
        if backend:
            super().__init__(
                f"Backend '{backend}' is not installed. "
                f"Run: pip install browsix[{backend}]"
            )
        else:
            super().__init__(
                "No backend available. Install cdpwave or bidiwave."
            )


class BackendNotSupportedError(BrowsixError):
    """Raised when a backend doesn't support a method."""

    def __init__(self, method: str, backend: str) -> None:
        super().__init__(f"Method '{method}' is not supported by {backend} backend.")


class NavigationError(BrowsixError):
    """Raised when navigation fails or times out."""

    def __init__(self, url: str, reason: str) -> None:
        super().__init__(f"Navigation to '{url}' failed: {reason}")


class WaitTimeoutError(BrowsixError):
    """Raised when a wait strategy times out."""

    def __init__(self, strategy: str, timeout_ms: int) -> None:
        super().__init__(
            f"Wait strategy '{strategy}' timed out after {timeout_ms}ms"
        )


class ElementNotFoundError(BrowsixError):
    """Raised when a CSS selector matches no elements."""

    def __init__(self, selector: str) -> None:
        super().__init__(f"No element found matching selector: {selector}")


class ActionError(BrowsixError):
    """Raised when an action fails during execution."""


class MultiConfigError(BrowsixError):
    """Raised when a multi YAML config is invalid."""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"Invalid multi config field '{field}': {reason}")
