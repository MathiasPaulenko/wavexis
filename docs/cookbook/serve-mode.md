# Serve Mode

wavexis includes an HTTP API server powered by aiohttp. Start it with:

```bash
wavexis serve --host 0.0.0.0 --port 8080
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/version` | wavexis version |
| GET | `/backends` | Available backends |
| POST | `/screenshot` | Take a screenshot |
| POST | `/pdf` | Generate a PDF |
| POST | `/eval` | Evaluate JavaScript |
| POST | `/scrape` | Scrape multiple URLs |
| POST | `/dom/get` | Get DOM HTML |
| POST | `/dom/query` | Query DOM elements |
| POST | `/navigate` | Navigate to URL |
| POST | `/har` | Capture HAR data |
| POST | `/cookies/get` | Get cookies |
| POST | `/cookies/set` | Set a cookie |
| POST | `/input/click` | Click an element |
| POST | `/input/type` | Type text into an element |
| POST | `/perf/metrics` | Get performance metrics |
| POST | `/perf/trace` | Capture performance trace |
| POST | `/cwv` | Core Web Vitals scoring (LCP, CLS, INP) |
| POST | `/modify-request` | Modify requests in-flight |
| POST | `/modify-response` | Modify responses in-flight |
| POST | `/multi` | Run multiple actions |
| GET | `/plugins` | List discovered plugins |

## Rate limiting

Protect the HTTP API from abuse with `--rate-limit`:

```bash
wavexis serve --rate-limit 60
```

This allows up to 60 requests per minute using a token bucket algorithm.
When the limit is exceeded, the server responds with `429 Too Many Requests`
and a `Retry-After` header indicating when to retry.

## Backend degradation

wavexis automatically falls back from the preferred backend to an alternative
if it cannot be created (e.g. cdpwave not installed). Use `--backend` to set
a preference:

```bash
wavexis serve --backend cdp    # prefers cdp, falls back to bidi
wavexis serve --backend bidi   # prefers bidi, falls back to cdp
```

## Core Web Vitals

Measure LCP, CLS, INP with scoring via the `/cwv` endpoint:

```bash
curl -X POST http://localhost:8080/cwv \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "budgets": {"lcp_ms": 2500}}'
```

## Examples

### Screenshot

```bash
curl -X POST http://localhost:8080/screenshot \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' \
  -o screenshot.png
```

### Eval

```bash
curl -X POST http://localhost:8080/eval \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "expression": "document.title"}'
```

### Navigate

```bash
curl -X POST http://localhost:8080/navigate \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## Architecture

Each request creates a fresh backend instance via `BackendManager.select_with_fallback()`. If the preferred backend fails to initialize, wavexis automatically tries the next available backend. The `_run_action` helper wraps `action.execute()` + `close()` in a try/finally block, ensuring the browser is always cleaned up.

## WebSocket streaming

The `/ws` endpoint provides real-time streaming of browser events via WebSocket.

### Subscribe

Connect to `ws://localhost:8080/ws` and send a JSON subscribe message:

```json
{
    "url": "https://example.com",
    "events": ["screenshot", "console", "navigation", "dom_mutation", "perf_metrics"],
    "interval": 1.0,
    "format": "png",
    "quality": 80
}
```

### Streamed events

The server sends JSON messages with a `type` field:

| Type | Description |
|------|-------------|
| `ready` | Server is ready, browser launched and navigated |
| `screenshot` | Base64-encoded screenshot image |
| `console` | Console message (deduplicated) |
| `navigation` | URL change detected |
| `dom_mutation` | DOM content change detected (polled) |
| `perf_metrics` | Performance metrics snapshot (LCP, FCP, CLS, etc.) |
| `network_request` | Network request intercepted |
| `network_response` | Network response intercepted |
| `dialog` | JavaScript dialog event |
| `navigated` | Confirmation of client-initiated navigation |
| `eval_result` | Result of a client-initiated eval |
| `error` | Error from a stream source |

### Client commands

Send JSON commands to control the browser:

```json
{"action": "navigate", "url": "https://example.org"}
{"action": "eval", "expression": "document.title"}
{"action": "screenshot"}
{"action": "close"}
```

### Available event types

| Event | Description | Streaming method |
|-------|-------------|-----------------|
| `screenshot` | Periodic screenshots (base64) | Polling |
| `console` | Console messages (deduplicated) | Polling |
| `navigation` | URL changes | Polling |
| `dom_mutation` | DOM content changes | Polling |
| `perf_metrics` | Performance metrics snapshots | Polling |
| `network_request` | Network requests | Event subscription |
| `network_response` | Network responses | Event subscription |
| `dialog` | JavaScript dialogs | Event subscription |

### Python client example

```python
import asyncio
import json
import aiohttp

async def stream():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect("ws://localhost:8080/ws") as ws:
            await ws.send_json({
                "url": "https://example.com",
                "events": ["screenshot", "console"],
                "interval": 2.0,
            })
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data["type"] == "screenshot":
                        print(f"Got screenshot ({len(data['data'])} bytes)")
                    elif data["type"] == "console":
                        print(f"Console: {data['data']}")
                    elif data["type"] == "ready":
                        print(f"Ready: {data['url']}")

asyncio.run(stream())
```

### JavaScript client example

```javascript
const ws = new WebSocket("ws://localhost:8080/ws");
ws.onopen = () => {
    ws.send(JSON.stringify({
        url: "https://example.com",
        events: ["screenshot", "console", "navigation"],
        interval: 1.0,
    }));
};
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "screenshot") {
        console.log(`Screenshot: ${data.data.length} chars`);
    } else if (data.type === "console") {
        console.log("Console:", data.data);
    } else if (data.type === "navigation") {
        console.log("Navigated to:", data.url);
    }
};
```
