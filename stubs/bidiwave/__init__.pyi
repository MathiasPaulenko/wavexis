"""Type stubs for bidiwave package."""

from typing import Any

class BiDiClient:
    """Type stub for BiDiClient."""

    session: Any
    browsing: Any
    script: Any
    network: Any
    storage: Any
    permissions: Any
    emulation: Any
    cdp: Any
    _connection: Any

    @classmethod
    async def connect(cls, ws_url: str) -> BiDiClient: ...

    async def close(self) -> None: ...
    async def send(self, method: str, params: dict[str, Any] | None = ...) -> dict[str, Any]: ...
    async def on_log_entry(self, handler: Any) -> Any: ...
    def off(self, subscription: Any) -> None: ...


class Cookie:
    """Type stub for BiDiCookie."""

    def __init__(
        self,
        name: str = ...,
        value: str = ...,
        domain: str = ...,
        path: str = ...,
        **kwargs: Any,
    ) -> None: ...


__version__: str
