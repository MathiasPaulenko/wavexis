"""Type stubs for cdpwave package (v3.3.0)."""

from collections.abc import Awaitable, Callable
from typing import Any

class Subscription:
    """Type stub for event subscription handle."""

    event_name: str

class BrowserContext:
    """Type stub for BrowserContext."""

    context_id: str
    is_closed: bool

    async def close(self) -> None: ...
    async def new_page(
        self, url: str = ..., auto_attach: bool = False
    ) -> CDPSession: ...

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
    css: Any
    overlay: Any
    animation: Any
    web_authn: Any
    media: Any
    accessibility: Any
    audits: Any
    console: Any
    device_access: Any
    device_orientation: Any
    dom_debugger: Any
    dom_snapshot: Any
    dom_storage: Any
    event_breakpoints: Any
    extensions: Any
    heap_profiler: Any
    indexed_db: Any
    inspector: Any
    io: Any
    layer_tree: Any

    target_id: str
    session_id: str
    is_closed: bool

    async def close(self) -> None: ...
    async def send(self, method: str, params: dict[str, Any] | None = ...) -> dict[str, Any]: ...
    async def wait_for_event(self, event: str, timeout: float = ...) -> dict[str, Any]: ...
    def on(self, event: str, handler: Callable[..., Any]) -> Subscription: ...
    def off(self, event: str, handler: Callable[..., Any]) -> None: ...
    async def collect_events(
        self, event: str = ..., *, timeout: float = ...
    ) -> list[dict[str, Any]]: ...
    async def wait_for_load_state(
        self, state: str = ..., timeout: float = ...
    ) -> dict[str, Any]: ...
    async def wait_for_navigation(
        self, url: str | None = ..., timeout: float = ...
    ) -> dict[str, Any]: ...
    async def wait_for_network_idle(
        self, idle_time: float = ..., timeout: float = ...
    ) -> None: ...
    async def wait_for_selector(
        self,
        selector: str,
        root_node_id: int = ...,
        timeout: float = ...,
        poll_interval: float = ...,
    ) -> int: ...


class CDPClient:
    """Type stub for CDPClient.

    ``launch`` and ``connect`` return an awaitable launch context
    (awaitable -> CDPClient, also usable as an async context manager).
    """

    browser: Any
    is_closed: bool
    is_connected: bool
    sessions: list[CDPSession]

    @classmethod
    def launch(
        cls,
        headless: bool = ...,
        browser_path: str | None = ...,
        port: int = ...,
        user_data_dir: str | None = ...,
        extra_args: list[str] | None = ...,
        timeout: float = ...,
        max_retries: int = ...,
        backoff_base: float = ...,
        backoff_max: float = ...,
        pipe: bool = ...,
    ) -> Awaitable[CDPClient]: ...

    @classmethod
    def connect(
        cls,
        host: str = ...,
        port: int = ...,
        ws_url: str | None = ...,
        max_retries: int = ...,
        backoff_base: float = ...,
        backoff_max: float = ...,
    ) -> Awaitable[CDPClient]: ...

    async def new_page(
        self, url: str = ..., auto_attach: bool = False
    ) -> CDPSession: ...
    async def new_context(self) -> BrowserContext: ...
    async def connect_to_page(self, target_id: str) -> CDPSession: ...
    async def get_pages(self) -> list[Any]: ...
    async def close(self) -> None: ...
    async def send(self, method: str, params: dict[str, Any] | None = ...) -> dict[str, Any]: ...
    def on(self, event: str, handler: Callable[..., Any]) -> Subscription: ...
    def off(self, event: str, handler: Callable[..., Any]) -> None: ...


__version__: str
