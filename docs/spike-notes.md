# Spike Notes — Phase 0

## Environment

- **OS**: Windows 11
- **Python**: 3.11+
- **Browser**: Chrome (system-installed)
- **cdpwave**: 2.0.1

## Pipeline Tested

1. `BackendManager()` → detected `["cdp"]`
2. `manager.select("cdp")` → `CDPBackend` instance
3. `backend.launch(BrowserOptions(headless=True))` → Chrome headless launched
4. `backend.navigate("https://example.com")` → waited for `Page.loadEventFired`
5. `backend.screenshot(ScreenshotParams(...))` → base64-decoded PNG bytes
6. Saved to `spike.png`
7. `backend.eval("document.title")` → `"Example Domain"`
8. `backend.close()` → browser process terminated

## cdpwave API Used

- `CDPClient.launch(headless=True, extra_args=[...])` — classmethod, returns connected client
- `client.new_page()` — creates a new tab, returns `CDPSession`
- `session.page.enable()` — enable Page domain events
- `session.page.navigate(url)` — navigate to URL
- `session.page.capture_screenshot(format, quality, capture_beyond_viewport)` — returns `{"data": "<base64>"}`
- `session.runtime.evaluate(expression, await_promise)` — returns `{"result": {"value": ...}}`
- `session.wait_for_event("Page.loadEventFired", timeout)` — waits for load event
- `client.close()` — closes all sessions, connection, and browser process

## Findings

- **Startup time**: ~1-2s (Chrome launch + WebSocket connect)
- **Navigate time**: ~0.5-1s (depends on network)
- **Screenshot size**: ~50-100KB for example.com full page PNG
- **No issues encountered**: cdpwave API is clean and straightforward

## Notes for Future Phases

- `BrowserOptions.width/height` are passed via `--window-size` Chrome arg, not via CDP Emulation
- `capture_beyond_viewport=True` is needed for full-page screenshots
- `Page.loadEventFired` is the simplest wait strategy; `networkidle` will need Network domain idle tracking
- `screenshot_selector` uses DOM.getBoxModel + clip — works but could be optimized
