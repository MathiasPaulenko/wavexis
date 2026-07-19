"""Exception hierarchy for wavexis."""

__all__ = [
    "ActionError",
    "BackendNotAvailableError",
    "BackendNotSupportedError",
    "ElementNotFoundError",
    "MultiConfigError",
    "NavigationError",
    "SessionNotInitializedError",
    "WaitTimeoutError",
    "WavexisError",
]


class WavexisError(Exception):
    """Base exception for all wavexis errors."""


class BackendNotAvailableError(WavexisError):
    """Raised when no backend (cdpwave/bidiwave) is installed."""

    def __init__(self, backend: str | None = None) -> None:
        """Initialize the error.

        Args:
            backend: Optional backend name that was requested but not available.
        """
        if backend:
            super().__init__(
                f"Backend '{backend}' is not installed. Run: pip install wavexis[{backend}]"
            )
        else:
            super().__init__("No backend available. Install cdpwave or bidiwave.")


class BackendNotSupportedError(WavexisError):
    """Raised when a backend doesn't support a method."""

    def __init__(self, method: str, backend: str) -> None:
        """Initialize the error.

        Args:
            method: The unsupported method name.
            backend: The backend name that doesn't support the method.
        """
        super().__init__(f"Method '{method}' is not supported by {backend} backend.")


class SessionNotInitializedError(WavexisError):
    """Raised when a backend method is called before launch()."""

    def __init__(self, msg: str | None = None) -> None:
        """Initialize the error.

        Args:
            msg: Optional custom message.
        """
        if msg:
            super().__init__(msg)
        else:
            super().__init__(
                "Browser session not initialized. Call launch() first.\n"
                "Hint: This usually means the browser failed to start. "
                "Try --headed to see the browser window, or check if Chromium is installed."
            )


class NavigationError(WavexisError):
    """Raised when navigation fails or times out."""

    def __init__(self, url: str, reason: str) -> None:
        """Initialize the error.

        Args:
            url: The URL that failed to navigate to.
            reason: The failure reason.
        """
        super().__init__(
            f"Navigation to '{url}' failed: {reason}\n"
            f"Hint: Check the URL is reachable, try --timeout 60000, "
            f"or use --proxy if behind a firewall."
        )


class WaitTimeoutError(WavexisError):
    """Raised when a wait strategy times out."""

    def __init__(self, strategy: str, timeout_ms: int) -> None:
        """Initialize the error.

        Args:
            strategy: The wait strategy name that timed out.
            timeout_ms: The timeout duration in milliseconds.
        """
        super().__init__(
            f"Wait strategy '{strategy}' timed out after {timeout_ms}ms\n"
            f"Hint: Increase timeout with --timeout {max(timeout_ms * 2, 60000)}, "
            f"or use a different wait strategy (load, domcontentloaded, networkidle)."
        )


class ElementNotFoundError(WavexisError):
    """Raised when a CSS selector matches no elements."""

    def __init__(self, selector: str) -> None:
        """Initialize the error.

        Args:
            selector: The CSS selector that matched no elements.
        """
        super().__init__(
            f"No element found matching selector: {selector}\n"
            f"Hint: Verify the selector with `wavexis dom --selector '{selector}'`, "
            f"or use `wavexis screenshot` to inspect the page visually."
        )


class ActionError(WavexisError):
    """Raised when an action fails during execution."""


class MultiConfigError(WavexisError):
    """Raised when a multi YAML config is invalid."""

    def __init__(self, field: str, reason: str) -> None:
        """Initialize the error.

        Args:
            field: The invalid config field name.
            reason: The validation failure reason.
        """
        super().__init__(f"Invalid multi config field '{field}': {reason}")
