# Serve Mode

browsix includes an HTTP API server powered by aiohttp. Start it with:

```bash
browsix serve --host 0.0.0.0 --port 8080
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/version` | browsix version |
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

Each request creates a fresh backend instance via `BackendManager.select()`. The `_run_action` helper wraps `launch()` + `action.execute()` + `close()` in a try/finally block, ensuring the browser is always cleaned up.
