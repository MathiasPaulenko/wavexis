"""WebSocket intercept action for capturing and mocking WS traffic."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from wavexis.actions.base import BaseAction
from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy


@dataclass
class WebSocketParams:
    """Parameters for WebSocket interception.

    Attributes:
        url: URL to navigate to.
        url_pattern: Regex pattern to filter WS URLs (empty = all).
        duration_ms: How long to capture WS frames (ms).
        mock_responses: Dict mapping request payloads to response payloads.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    url_pattern: str = ""
    duration_ms: int = 5000
    mock_responses: dict[str, str] = field(default_factory=dict)
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


class WebSocketInterceptAction(BaseAction[WebSocketParams, dict[str, Any]]):
    """Action for intercepting WebSocket frames on a page."""

    async def execute(
        self, backend: AbstractBackend
    ) -> dict[str, Any]:
        """Execute WebSocket interception on the backend.

        Args:
            backend: The browser backend to use.

        Returns:
            Dict with sent/received frames and connection info.
        """
        await backend.launch(self.params.browser)
        try:
            await backend.navigate(self.params.url, self.params.wait)

            js = f"""
                (() => {{
                    const frames = {{sent: [], received: [], errors: []}};
                    const pattern = {json.dumps(self.params.url_pattern)};
                    const regex = pattern ? new RegExp(pattern) : null;
                    const mocks = {json.dumps(self.params.mock_responses)};

                    const origWS = window.WebSocket;
                    window.WebSocket = function(url, protocols) {{
                        if (regex && !regex.test(url)) {{
                            return new origWS(url, protocols);
                        }}
                        const ws = new origWS(url, protocols);
                        frames.url = url;

                        const origSend = ws.send.bind(ws);
                        ws.send = function(data) {{
                            frames.sent.push({{timestamp: Date.now(), data: String(data)}});
                            if (mocks[String(data)]) {{
                                setTimeout(() => {{
                                    frames.received.push({{
                                        timestamp: Date.now(),
                                        data: mocks[String(data)],
                                        mocked: true,
                                    }});
                                    ws.dispatchEvent(new MessageEvent(
                                        'message', {{data: mocks[String(data)]}}
                                    ));
                                }}, 10);
                            }}
                            return origSend(data);
                        }};

                        ws.addEventListener('message', (e) => {{
                            frames.received.push({{timestamp: Date.now(), data: String(e.data)}});
                        }});
                        ws.addEventListener('error', (e) => {{
                            frames.errors.push({{timestamp: Date.now(), error: String(e)}});
                        }});
                        return ws;
                    }};
                    window.WebSocket.prototype = origWS.prototype;
                    window.WebSocket.CONNECTING = origWS.CONNECTING;
                    window.WebSocket.OPEN = origWS.OPEN;
                    window.WebSocket.CLOSING = origWS.CLOSING;
                    window.WebSocket.CLOSED = origWS.CLOSED;

                    return new Promise((resolve) => {{
                        setTimeout(() => resolve(frames), {self.params.duration_ms});
                    }});
                }})()
            """
            result = await backend.eval(js, await_promise=True)
            if isinstance(result, dict):
                return result
            return {"sent": [], "received": [], "errors": []}
        finally:
            await backend.close()
