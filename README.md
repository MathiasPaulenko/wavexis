# browsix

[![CI](https://github.com/MathiasPaulenko/browsix/actions/workflows/ci.yml/badge.svg)](https://github.com/MathiasPaulenko/browsix/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/browsix.svg)](https://pypi.org/project/browsix/)
[![Python](https://img.shields.io/pypi/pyversions/browsix.svg)](https://pypi.org/project/browsix/)
[![Docker](https://img.shields.io/badge/Docker-ghcr.io-blue.svg)](https://github.com/MathiasPaulenko/browsix/pkgs/container/browsix)
[![License](https://img.shields.io/github/license/MathiasPaulenko/browsix.svg)](https://github.com/MathiasPaulenko/browsix/blob/main/LICENSE)
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://mathiaspaulenko.github.io/browsix/)

> Browser automation CLI — wraps cdpwave and bidiwave. No Node.js, no Chromium download. Uses your existing Chrome/Edge. 100+ commands across CDP and BiDi backends with full parity.

## Why browsix?

browsix is a command-line tool for browser automation. It wraps the [cdpwave](https://pypi.org/project/cdpwave/) (Chrome DevTools Protocol) and [bidiwave](https://pypi.org/project/bidiwave/) (WebDriver BiDi) libraries, exposing their capabilities through a single unified CLI. You don't need Node.js, Playwright, or a separate Chromium download — browsix launches your existing Chrome or Edge installation directly.

### Core concepts

- **Backend** — The browser driver that executes commands. browsix supports two backends with full feature parity: CDP (default, via cdpwave) and BiDi (via bidiwave). Both implement all 100+ methods, so you can switch with `--backend bidi` without losing functionality.
- **Action** — A single operation (screenshot, eval, click, etc.). Each action maps to a CLI command or a step in a multi-action YAML config.
- **Multi-action** — A YAML config that chains multiple actions in sequence on a single browser session. Avoids the overhead of launching a browser per action.
- **Serve mode** — An HTTP API server that exposes all browsix commands as REST endpoints with WebSocket streaming for real-time events.

## Install

```bash
pip install browsix[cdp]
```

## Docker

Serve mode in a container with Chromium pre-installed:

```bash
docker run -p 8080:8080 ghcr.io/mathiaspaulenko/browsix:latest
```

```bash
curl -X POST http://localhost:8080/screenshot \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' \
  -o screenshot.png
```

Build locally:

```bash
docker build -t browsix .
docker run -p 8080:8080 browsix
```

## Quick start

```bash
# Take a screenshot
browsix screenshot https://example.com -o out.png

# Full-page screenshot
browsix screenshot https://example.com -o full.png --full-page

# Screenshot of a specific element
browsix screenshot https://example.com -o el.png --selector "h1"

# Generate a PDF
browsix pdf https://example.com -o out.pdf --paper a4

# Evaluate JavaScript
browsix eval https://example.com -e "document.title"

# Scrape page content
browsix scrape https://example.com --selector "article"

# Emulate a device
browsix device https://example.com --preset iphone-15 -o shot.png
```

## REPL

Interactive REPL for live browser sessions. Launch a non-headless browser and execute commands in real time:

```bash
browsix repl
```

Inside the REPL:

```
browsix> navigate https://example.com
browsix> screenshot
browsix> eval document.title
browsix> click #login-button
browsix> type #username admin@example.com
browsix> cookies
browsix> url
browsix> title
browsix> wait 2
browsix> back
browsix> help
browsix> exit
```

Supported commands: `navigate`, `screenshot`, `eval`, `click`, `type`, `fill`, `hover`, `key`, `cookies`, `url`, `title`, `wait`, `back`, `forward`, `reload`, `help`, `exit`/`quit`.

## Init wizard

Generate a `browsix.yaml` config interactively from predefined templates:

```bash
browsix init
```

Or generate directly with flags:

```bash
browsix init -t multi-step -u https://example.com -s "#login" --text "admin" -o config.yaml
```

List available templates:

```bash
browsix init --list
```

Templates: `screenshot`, `pdf`, `scrape`, `eval`, `multi-step`, `cookies`, `har`.

## CI assertions

Use `--assert` with `eval` to create CI gates that pass or fail based on the result:

```bash
# Equality check — exit 0 if title matches, 1 otherwise
browsix eval https://example.com -e "document.title" --assert "== Expected Title"

# Inequality
browsix eval https://example.com -e "document.title" --assert "!= Old Title"

# Substring
browsix eval https://example.com -e "document.body.innerText" --assert "contains Welcome"

# Regex
browsix eval https://example.com -e "document.title" --assert "matches Error \\d+"
```

Output includes `assert:`, `result:`, and `status: PASS/FAIL`. Exit code 0 on pass, 1 on fail.

## Performance metrics

Capture Core Web Vitals and performance data:

```bash
# Key metrics (LCP, FCP, CLS, TTFB) with human-readable summary
browsix perf https://example.com

# CPU trace
browsix perf https://example.com -m trace -d 5000 -o trace.json

# CPU profile
browsix perf https://example.com -m profile -o profile.json

# JS code coverage
browsix perf https://example.com -m coverage -o coverage.json

# CSS coverage
browsix perf https://example.com -m css-coverage -o css-coverage.json

# Heap snapshot
browsix perf https://example.com -m heap-snapshot -o heap.json
```

Metrics: `metrics` (default), `trace`, `profile`, `heap-snapshot`, `coverage`, `css-coverage`.

## Auth

Store and use browser credentials for authenticated scraping:

```bash
# Save credentials
browsix auth save mysite --user admin --pass secret123

# Use saved credentials
browsix auth use mysite --url https://example.com/login

# List saved profiles
browsix auth list

# Delete a profile
browsix auth delete mysite
```

## Record & Replay

Record a browser session and replay it later:

```bash
# Record a session
browsix record start https://example.com -o session.json

# Replay a recorded session
browsix record replay session.json

# List recorded sessions
browsix record list
```

## Serve mode

HTTP API server powered by aiohttp with WebSocket streaming:

```bash
browsix serve --host 0.0.0.0 --port 8080
```

```bash
curl -X POST http://localhost:8080/screenshot \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' \
  -o screenshot.png
```

WebSocket endpoint at `/ws` for real-time streaming of screenshots, console events, and navigation:

```python
import aiohttp, json, asyncio

async def stream():
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect("ws://localhost:8080/ws") as ws:
            await ws.send_json({"url": "https://example.com", "events": ["screenshot"], "interval": 2.0})
            async for msg in ws:
                data = json.loads(msg.data)
                if data["type"] == "screenshot":
                    print(f"Got frame ({len(data['data'])} bytes)")

asyncio.run(stream())
```

## Multi-action

Create a YAML config and run multiple actions in sequence on a single browser session:

```yaml
# actions.yml
actions:
  - screenshot:
      url: https://example.com
      full_page: true
  - eval:
      url: https://example.com
      expression: document.title
  - pdf:
      url: https://example.com
      paper: a4
```

```bash
browsix multi actions.yml
```

### Watch mode

Re-execute the config automatically when the file changes. Useful for iterative config development:

```bash
browsix multi actions.yml --watch
```

### Dry run

Validate the config and show the planned actions without launching a browser:

```bash
browsix multi actions.yml --dry-run
```

### Supported action types

| Action | Key parameters |
|---------|------------|
| `screenshot` | `url`, `full_page`, `format` |
| `pdf` | `url`, `paper`, `landscape` |
| `eval` | `url`, `expression`, `await_promise` |
| `dom` | `url`, `action`, `selector` |
| `navigate` | `url` |
| `scrape` | `urls`, `expression` |
| `click` | `url`, `selector` |
| `type` | `url`, `selector`, `text` |
| `cookies` | `url`, `action` (get/set/delete/clear), `cookie` |
| `headers` | `url`, `action` (set-headers/set-user-agent), `headers`, `user_agent` |

### Cookies and headers in multi

```yaml
actions:
  - cookies:
      url: https://example.com
      action: get
  - headers:
      url: https://example.com
      action: set-headers
      headers:
        X-Custom-Header: my-value
  - screenshot:
      url: https://example.com
```

## Backends

browsix supports two backends with **full feature parity**:

- **CDP** (cdpwave) — default, Chrome DevTools Protocol. `pip install browsix[cdp]`
- **BiDi** (bidiwave) — WebDriver BiDi protocol, uses BiDi native + JS workarounds + CDP bridge. `pip install browsix[bidi]`

Select with `--backend`:

```bash
browsix --backend bidi screenshot https://example.com -o out.png
```

### Feature parity (v1.7.0)

Both backends implement **all** methods. BiDi uses native BiDi commands, JS workarounds
(`script.evaluate`), or the CDP bridge (`browser.cdp.sendCommand`) when needed.

| Category | Methods | BiDi impl |
|----------|---------|-----------|
| Navigation | `navigate`, `go_back`, `go_forward`, `reload`, `stop_loading`, `wait_for` | BiDi native |
| Screenshots | `screenshot`, `screenshot_selector`, `pdf`, `screencast` | BiDi + CDP |
| Tabs | `list_tabs`, `new_tab`, `close_tab`, `activate_tab` | BiDi native |
| DOM | `dom_get`, `dom_query`, `dom_set_attr`, `dom_get_attr`, `dom_remove`, `dom_focus`, `dom_scroll`, `dom_snapshot` | BiDi + JS |
| Cookies | `get_cookies`, `set_cookie`, `delete_cookie`, `clear_cookies` | BiDi native |
| Network | `set_headers`, `set_user_agent`, `block_requests`, `throttle_network`, `set_cache_disabled`, `intercept_requests`, `mock_response` | BiDi + CDP |
| Emulation | `emulate_device`, `set_viewport`, `set_geolocation`, `set_timezone`, `set_dark_mode`, `set_locale`, `set_touch_emulation`, `set_cpu_throttle`, `set_sensors` | BiDi + CDP |
| Browser | `browser_version`, `eval`, `raw`, `capture_console`, `capture_logs` | BiDi native |
| Security | `get_security_state`, `ignore_cert_errors` | CDP bridge |
| Contexts | `new_context`, `list_contexts`, `close_context`, `get_window_bounds`, `set_window_bounds` | BiDi native |
| Input | `click`, `type_text`, `fill`, `select_option`, `hover`, `key_press`, `drag`, `tap` | JS + BiDi |
| Storage | `storage_get`, `storage_set`, `storage_clear`, `storage_list` | BiDi native |
| Dialogs | `dialog_accept`, `dialog_dismiss`, `grant_permission`, `reset_permissions` | BiDi native |
| Performance | `perf_metrics`, `perf_coverage`, `perf_css_coverage`, `perf_trace`, `perf_profile`, `perf_heap_snapshot` | CDP bridge |
| CSS | `css_get_styles`, `css_get_computed`, `css_get_stylesheets`, `css_get_rules` | JS |
| Overlay | `overlay_highlight`, `overlay_clear` | JS |
| Accessibility | `a11y_tree`, `a11y_node`, `a11y_ancestors` | CDP bridge |
| Downloads | `intercept_download` | CDP bridge |
| Debug | `debug_set_breakpoint`, `debug_set_breakpoint_function`, `debug_remove_breakpoint`, `debug_step_over`, `debug_step_into`, `debug_step_out`, `debug_pause`, `debug_resume`, `debug_get_listeners` | CDP bridge |
| Cache Storage | `cache_storage_list`, `cache_storage_entries`, `cache_storage_delete` | JS |
| IndexedDB | `indexeddb_list`, `indexeddb_get_data`, `indexeddb_clear` | CDP bridge |
| Service Workers | `sw_list`, `sw_unregister`, `sw_update` | JS |
| Animations | `animation_list`, `animation_pause`, `animation_play`, `animation_seek` | JS |
| HAR | `capture_har` | CDP bridge |
| WebAuthn | `webauthn_add_virtual_authenticator`, `webauthn_remove_authenticator`, `webauthn_add_credential`, `webauthn_get_credentials` | CDP bridge |
| WebAudio | `webaudio_get_contexts`, `webaudio_get_context` | CDP bridge |
| Media | `media_get_players`, `media_get_messages` | CDP bridge |
| Cast | `cast_list`, `cast_start_tab`, `cast_stop` | CDP bridge |
| Bluetooth | `bluetooth_emulate`, `bluetooth_stop` | CDP bridge |

## Commands

browsix provides 100+ CLI commands organized into categories:

| Category | Commands |
|----------|----------|
| Capture | `screenshot`, `pdf`, `screencast`, `scrape` |
| Navigate | `navigate`, `back`, `forward`, `reload`, `stop`, `tabs` |
| Console | `console` (with `--capture`, `--format`), `logs`, `har` |
| Cookies | `cookies` (get/set/delete/clear) |
| Network | `headers`, `user-agent`, `block`, `throttle`, `cache`, `intercept`, `mock` |
| Browser | `open`, `close`, `version` |
| Emulation | `device`, `viewport`, `geolocation`, `timezone`, `dark-mode` |
| Input | `click`, `type`, `fill`, `select`, `hover`, `key`, `drag`, `tap` |
| CSS | `css-styles`, `css-computed`, `css-rules` |
| Debug | `debug-break`, `debug-step`, `debug-pause`, `debug-resume` |
| Performance | `perf` (metrics, trace, profile, coverage, heap-snapshot, css-coverage) |
| Storage | `storage` (get/set/clear/list), `indexeddb` |
| Advanced | `sw`, `animation`, `record`, `replay`, `webauthn`, `cast`, `bluetooth` |
| Auth | `auth save`, `auth use`, `auth list`, `auth delete` |
| Serve | `serve` (HTTP API server) |
| Interactive | `repl` (live browser REPL), `init` (config wizard) |
| Utility | `multi` (with `--watch`, `--dry-run`), `raw`, `backends`, `install_check`, `completions` |

Run `browsix --help` for the full list.

## Comparison

| Feature | browsix | shot-scraper | Playwright |
|---------|---------|--------------|------------|
| Language | Python | Python | Multi |
| Node.js required | No | Yes | Yes |
| Chromium download | No | Yes | Yes |
| CDP backend | Yes | Yes | Yes |
| BiDi backend | Yes | No | No |
| BiDi/CDP parity | Yes | N/A | No |
| CLI-first | Yes | Yes | No |
| Multi-action YAML | Yes | No | No |
| Device emulation | Yes | Yes | Yes |
| HAR capture | Yes | No | Yes |
| PDF generation | Yes | Yes | Yes |
| Network throttling | Yes | No | Yes |
| Cookie management | Yes | No | Yes |
| Session recording | Yes | No | No |
| Auth profiles | Yes | No | No |
| Serve mode (HTTP API) | Yes | No | No |
| Debug breakpoints | Yes | No | No |
| WebAuthn | Yes | No | No |
| Shell completions | Yes | No | No |
| Interactive REPL | Yes | No | No |
| Config wizard | Yes | No | No |
| CI assertions | Yes | No | No |
| Performance metrics | Yes | No | No |
| Watch mode | Yes | No | No |

## Documentation

Full docs at [mathiaspaulenko.github.io/browsix](https://mathiaspaulenko.github.io/browsix/).

## License

MIT