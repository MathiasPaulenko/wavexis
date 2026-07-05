"""Type stubs for cdpwave package."""

from typing import Any

class CDPSession:
    """Type stub for CDPSession."""

    page: Any
    dom: Any
    runtime: Any
    network: Any
    emulation: Any
    target: Any
    browser: Any
    fetch: Any
    log: Any
    security: Any
    storage: Any
    debugger: Any
    profiler: Any
    tracing: Any
    input: Any

    async def close(self) -> None: ...
    async def send(self, method: str, params: dict[str, Any] | None = ...) -> dict[str, Any]: ...
    async def wait_for_event(self, event: str, timeout: float = ...) -> None: ...
    def on(self, event: str, handler: Any) -> None: ...
    async def collect_events(
        self, event: str = ..., *, timeout: float = ...
    ) -> list[dict[str, Any]]: ...


class CDPClient:
    """Type stub for CDPClient."""

    browser: Any

    @classmethod
    async def launch(
        cls,
        headless: bool = ...,
        extra_args: list[str] | None = ...,
    ) -> CDPClient: ...

    async def new_page(self) -> CDPSession: ...
    async def close(self) -> None: ...


__version__: str
