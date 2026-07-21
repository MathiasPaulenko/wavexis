<p align="center">
  <img src="docs/assets/images/logo-wide.svg" alt="wavexis" width="480">
</p>

<h3 align="center">Browser automation CLI — wraps cdpwave and bidiwave</h3>

---

[![CI](https://github.com/MathiasPaulenko/wavexis/actions/workflows/ci.yml/badge.svg)](https://github.com/MathiasPaulenko/wavexis/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/wavexis.svg)](https://pypi.org/project/wavexis/)
[![Python](https://img.shields.io/pypi/pyversions/wavexis.svg)](https://pypi.org/project/wavexis/)
[![Docker](https://img.shields.io/badge/Docker-ghcr.io-blue.svg)](https://github.com/MathiasPaulenko/wavexis/pkgs/container/wavexis)
[![License](https://img.shields.io/github/license/MathiasPaulenko/wavexis.svg)](https://github.com/MathiasPaulenko/wavexis/blob/main/LICENSE)
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://mathiaspaulenko.github.io/wavexis/)

> Browser automation CLI — wraps cdpwave and bidiwave. No Node.js, no Chromium download. Uses your existing Chrome/Edge. 117 CLI commands, 743 backend methods, full CDP + BiDi parity.

## Why wavexis?

wavexis is a command-line tool for browser automation. It wraps the [cdpwave](https://pypi.org/project/cdpwave/) (Chrome DevTools Protocol) and [bidiwave](https://pypi.org/project/bidiwave/) (WebDriver BiDi) libraries, exposing their capabilities through a single unified CLI. You don't need Node.js, Playwright, or a separate Chromium download — wavexis launches your existing Chrome or Edge installation directly.

### Core concepts

- **Backend** — The browser driver that executes commands. wavexis supports two backends with full feature parity: CDP (default, via cdpwave) and BiDi (via bidiwave). Both implement all 743 methods across 60 CDP domains and 12 BiDi modules, so you can switch with `--backend bidi` without losing functionality.
- **Action** — A single operation (screenshot, eval, click, etc.). Each action maps to a CLI command or a step in a multi-action YAML config.
- **Multi-action** — A YAML config that chains multiple actions in sequence on a single browser session. Avoids the overhead of launching a browser per action.
- **Serve mode** — An HTTP API server that exposes all wavexis commands as REST endpoints with WebSocket streaming for real-time events.

## Install

```bash
pip install wavexis[cdp]
```

## Docker

Serve mode in a container with Chromium pre-installed:

```bash
docker run -p 8080:8080 ghcr.io/mathiaspaulenko/wavexis:latest
```

```bash
curl -X POST http://localhost:8080/screenshot \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' \
  -o screenshot.png
```

Build locally:

```bash
docker build -t wavexis .
docker run -p 8080:8080 wavexis
```

## Quick start

```bash
# Take a screenshot
wavexis screenshot https://example.com -o out.png

# Full-page screenshot
wavexis screenshot https://example.com -o full.png --full-page

# Screenshot of a specific element
wavexis screenshot https://example.com -o el.png --selector "h1"

# Generate a PDF
wavexis pdf https://example.com -o out.pdf --paper a4

# Evaluate JavaScript
wavexis eval https://example.com -e "document.title"

# Scrape page content
wavexis scrape https://example.com --selector "article"

# Emulate a device
wavexis emulation device https://example.com --device iphone-15 -o shot.png
```

## REPL

Interactive REPL for live browser sessions. Launch a non-headless browser and execute commands in real time:

```bash
wavexis repl
```

Inside the REPL:

```
wavexis> navigate https://example.com
wavexis> screenshot
wavexis> eval document.title
wavexis> click #login-button
wavexis> type #username admin@example.com
wavexis> cookies
wavexis> url
wavexis> title
wavexis> wait 2
wavexis> back
wavexis> help
wavexis> exit
```

Supported commands: `navigate`, `screenshot`, `eval`, `click`, `type`, `fill`, `hover`, `key`, `cookies`, `url`, `title`, `wait`, `back`, `forward`, `reload`, `help`, `exit`/`quit`.

## Init wizard

Generate a `wavexis.yaml` config interactively from predefined templates:

```bash
wavexis init
```

Or generate directly with flags:

```bash
wavexis init -t multi-step -u https://example.com -s "#login" --text "admin" -o config.yaml
```

List available templates:

```bash
wavexis init --list
```

Templates: `screenshot`, `pdf`, `scrape`, `eval`, `multi-step`, `cookies`, `har`.

## CI assertions

Use `--assert` with `eval` to create CI gates that pass or fail based on the result:

```bash
# Equality check — exit 0 if title matches, 1 otherwise
wavexis eval https://example.com -e "document.title" --assert "== Expected Title"

# Inequality
wavexis eval https://example.com -e "document.title" --assert "!= Old Title"

# Substring
wavexis eval https://example.com -e "document.body.innerText" --assert "contains Welcome"

# Regex
wavexis eval https://example.com -e "document.title" --assert "matches Error \\d+"
```

Output includes `assert:`, `result:`, and `status: PASS/FAIL`. Exit code 0 on pass, 1 on fail.

## Stealth mode

Enable anti-bot stealth mode to hide headless browser indicators. Useful for scraping protected sites:

```bash
# Global flag — applies to all commands
wavexis --stealth screenshot https://example.com -o out.png
wavexis --stealth scrape https://protected-site.com --selector "article"
```

Stealth mode hides `navigator.webdriver`, fakes plugins, languages, chrome runtime, WebGL vendor/renderer, permissions API, `navigator.connection`, `hardwareConcurrency`, `deviceMemory`, and `platform`. Works with both CDP and BiDi backends.

## Action caching

Cache action results to avoid re-analyzing pages when running multi-action workflows repeatedly:

```bash
# Cache results for 60 seconds
wavexis multi actions.yml --cache-ttl 60
```

Cacheable actions: `screenshot`, `dom`, `scrape`, `eval`, `cookies`, `headers`. Cache is keyed by URL, action type, and params hash.

## WebExtension management

Install, uninstall, and list browser extensions:

```bash
# Install an unpacked extension directory
wavexis extension-install /path/to/extension/

# Install a .crx file
wavexis extension-install /path/to/extension.crx

# List installed extensions
wavexis extension-list

# Uninstall by extension ID
wavexis extension-uninstall <extension-id>
```

## Browser preferences

Get and set browser preferences programmatically:

```bash
# Get a preference
wavexis pref-get download.default_directory

# Set a preference
wavexis pref-set download.default_directory /tmp/downloads
```

## Performance metrics

Capture Core Web Vitals and performance data:

```bash
# Key metrics (LCP, FCP, CLS, TTFB) with human-readable summary
wavexis perf https://example.com

# CPU trace
wavexis perf https://example.com -m trace -d 5000 -o trace.json

# CPU profile
wavexis perf https://example.com -m profile -o profile.json

# JS code coverage
wavexis perf https://example.com -m coverage -o coverage.json

# CSS coverage
wavexis perf https://example.com -m css-coverage -o css-coverage.json

# Heap snapshot
wavexis perf https://example.com -m heap-snapshot -o heap.json
```

Metrics: `metrics` (default), `trace`, `profile`, `heap-snapshot`, `coverage`, `css-coverage`.

## Core Web Vitals scoring

Measure LCP, CLS, INP with actionable ratings and a 0-100 score:

```bash
# Basic measurement
wavexis cwv https://example.com

# With CI budgets (fails if thresholds exceeded)
wavexis cwv https://example.com --budget '{"lcp_ms":2500,"cls":0.1,"inp_ms":200}'

# Save report to file
wavexis cwv https://example.com -o cwv-report.json
```

Ratings: **good** / **needs-improvement** / **poor** based on official Google thresholds.

| Metric | Good | Poor |
|--------|------|------|
| LCP | < 2500ms | > 4000ms |
| CLS | < 0.1 | > 0.25 |
| INP | < 200ms | > 500ms |

## Request modification

Intercept and modify network requests and responses in-flight:

```bash
# Modify request headers for matching URLs
wavexis modify https://example.com -p "*/api/*" --header "X-Custom: value"

# Modify response body
wavexis modify-response https://example.com -p "*/api/*" -b '{"modified":true}' -s 200

# Keep browser open for interception
wavexis modify https://example.com -p "*/api/*" --wait 10
```

## Auth

Apply an auth context (cookies, headers, basic auth) from a JSON file and navigate to a URL:

```bash
# Apply auth context and print page title
wavexis auth context.json https://example.com/login

# Apply auth context and save a screenshot
wavexis auth context.json https://example.com/login --screenshot -o authed.png
```

The auth context JSON file supports `cookies`, `headers`, `username`, and `password` fields. See `wavexis auth --help` for details.

## Record & Replay

Record a browsing session to YAML and replay it later:

```bash
# Generate a YAML session from action types (non-interactive)
wavexis record https://example.com -o session.yml --actions "screenshot,eval"

# Record real interactions in a visible browser window
wavexis record https://example.com --interactive --duration 60 -o session.yml

# Replay a recorded session
wavexis replay session.yml
```

## Serve mode

HTTP API server powered by aiohttp with WebSocket streaming:

```bash
wavexis serve --host 0.0.0.0 --port 8080

# With rate limiting (60 requests/min)
wavexis serve --host 0.0.0.0 --port 8080 --rate-limit 60
```

```bash
curl -X POST http://localhost:8080/screenshot \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' \
  -o screenshot.png
```

WebSocket endpoint at `/ws` for real-time streaming of screenshots, console events, navigation, DOM mutations, and performance metrics:

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
wavexis multi actions.yml
```

### Watch mode

Re-execute the config automatically when the file changes. Useful for iterative config development:

```bash
wavexis multi actions.yml --watch
```

### Dry run

Validate the config and show the planned actions without launching a browser:

```bash
wavexis multi actions.yml --dry-run
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

wavexis supports two backends with **full feature parity**:

- **CDP** (cdpwave) — default, Chrome DevTools Protocol. `pip install wavexis[cdp]`
- **BiDi** (bidiwave) — WebDriver BiDi protocol, uses BiDi native + JS workarounds + CDP bridge. `pip install wavexis[bidi]`

Select with `--backend`:

```bash
wavexis --backend bidi screenshot https://example.com -o out.png
```

### Graceful backend degradation

If the preferred backend fails to initialize (e.g. dependency not installed), wavexis
automatically falls back to the next available backend:

```bash
# Prefers CDP, falls back to BiDi if cdpwave is not installed
wavexis screenshot https://example.com -o out.png

# Prefers BiDi, falls back to CDP if bidiwave is not installed
wavexis --backend bidi screenshot https://example.com -o out.png
```

### Feature parity (v2.13.0)

Both backends implement **all** 743 methods across 60 CDP domains and 12 BiDi modules. BiDi uses native BiDi commands, JS workarounds
(`script.evaluate`), or the CDP bridge (`browser.cdp.sendCommand`) when needed. Zero uncovered methods.

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
| Extensions | `extension_install`, `extension_uninstall`, `extension_list` | CDP bridge |
| Preferences | `get_pref`, `set_pref` | CDP bridge |
| Stealth | `stealth` JS injection on launch | JS |
| Debugger | `debugger_pause`, `debugger_resume`, `debugger_step_into`, `debugger_step_over`, `debugger_step_out`, `debugger_set_breakpoint`, +27 more | CDP bridge |
| Heap Profiler | `heap_profiler_take_heap_snapshot`, `heap_profiler_start_sampling`, +10 more | CDP bridge |
| DOM Debugger | `dom_debugger_get_event_listeners`, `dom_debugger_set_breakpoint`, +8 more | CDP bridge |
| DOM Storage | `dom_storage_clear`, `dom_storage_get_items`, +5 more | CDP bridge |
| Event Breakpoints | `event_breakpoints_set`, `event_breakpoints_clear`, +2 more | CDP bridge |
| FedCM | `fedcm_enable`, `fedcm_disable`, +5 more | CDP bridge |
| Fetch | `fetch_enable`, `fetch_disable`, `fetch_continue_request`, +8 more | CDP bridge |
| File System | `file_system_get_directory` | CDP bridge |
| Headless | `headless_begin_frame`, `headless_disable`, `headless_enable` | CDP bridge |
| IO | `io_read`, `io_write`, `io_close` | CDP bridge |
| Layer Tree | `layer_tree_enable`, `layer_tree_disable`, +7 more | CDP bridge |
| Log | `log_enable`, `log_disable`, `log_clear`, `log_start_violations`, `log_stop_violations` | CDP bridge |
| Memory | `memory_get_sampling_profile`, `memory_start_sampling`, +9 more | CDP bridge |
| Page | `page_enable`, `page_disable`, `page_reload`, +62 more | CDP bridge |
| Profiler | `profiler_start`, `profiler_stop`, `profiler_get_profile`, +6 more | CDP bridge |
| Runtime | `runtime_evaluate`, `runtime_compile_script`, `runtime_run_script`, +21 more | CDP bridge |
| Schema | `schema_get_domains` | CDP bridge |
| Sensor | `sensor_set_sensor_reading_enabled`, +3 more | CDP bridge |
| Smart Card | `smart_card_emulation_enable`, `smart_card_emulation_disable`, +10 more | CDP bridge |
| System Info | `system_info_get_info`, `system_info_get_process_info`, `system_info_get_feature_state` | CDP bridge |
| Target | `target_create_target`, `target_close_target`, `target_get_targets`, +16 more | CDP bridge |
| Tethering | `tethering_bind`, `tethering_unbind` | CDP bridge |
| Tracing | `tracing_start`, `tracing_end`, `tracing_get_categories`, +3 more | CDP bridge |
| WebMCP | `web_mcp_enable`, `web_mcp_disable` | CDP bridge |
| Worker | `worker_created`, `worker_disconnected` | CDP bridge |
| Crash Report | `crash_report_context_get_entries` | CDP bridge |
| Device Access | `device_access_enable`, `device_access_disable`, `device_access_select_device`, `device_access_cancel_prompt` | CDP bridge |
| Device Orientation | `device_orientation_set_orientation`, `device_orientation_clear_orientation` | CDP bridge |
| Digital Credentials | `digital_credentials_get_credentials` | CDP bridge |
| Inspector | `inspector_enable`, `inspector_disable` | CDP bridge |
| Performance Timeline | `performance_timeline_enable` | CDP bridge |
| Preload | `preload_enable`, `preload_disable` | CDP bridge |
| PWA | `pwa_get_install_state`, `pwa_install`, `pwa_uninstall`, +4 more | CDP bridge |

## Commands

wavexis provides 130+ top-level CLI commands plus 480+ sub-commands organized into categories:

| Category | Commands |
|----------|----------|
| Capture | `screenshot`, `pdf`, `screencast`, `scrape` |
| Navigate | `navigate`, `back`, `forward`, `reload`, `stop`, `tabs` |
| Console | `console` (with `--capture`, `--format`), `logs`, `har` |
| Cookies | `cookies` (get/set/delete/clear) |
| Network | `headers`, `user-agent`, `block`, `throttle`, `cache`, `intercept`, `mock` |
| Browser | `open`, `close`, `version` |
| Emulation | `emulation device`, `emulation viewport`, `emulation geolocation`, `emulation timezone`, `emulation dark-mode`, `emulation media`, `emulation vision-deficiency`, `emulation idle-override`, `emulation disable-js`, `emulation visible-size`, `devices` |
| Input | `click`, `type`, `fill`, `select`, `hover`, `key`, `drag`, `tap` |
| CSS | `css get-styles`, `css get-computed`, `css get-rules` |
| Debug | `debug break`, `debug step`, `debug pause`, `debug resume` |
| Performance | `perf metrics`, `perf trace`, `perf profile`, `perf coverage`, `perf heap-snapshot`, `perf css-coverage`, `cwv` (Core Web Vitals scoring) |
| Storage | `storage get`, `storage set`, `storage clear`, `storage list`, `indexeddb` |
| Advanced | `sw`, `animation`, `record`, `replay`, `webauthn`, `cast`, `bluetooth`, `extension-install`, `extension-uninstall`, `extension-list`, `lighthouse`, `a11y`, `download`, `dialog`, `permissions`, `security` |
| Preferences | `pref-get`, `pref-set` |
| Auth | `auth` (apply auth context from JSON file) |
| Serve | `serve` (HTTP API server) |
| Interactive | `repl` (live browser REPL), `init` (config wizard) |
| Network inspection | `inspect`, `modify`, `modify-response`, `har-replay` |
| Tracing | `trace` (start/stop unified tracing) |
| Accessibility | `axe` (accessibility audit) |
| Events | `events` (subscribe/unsubscribe to browser events) |
| Natural language | `nl` (click/fill/find using natural language selectors) |
| Shadow DOM | `shadow` (click/fill/eval inside shadow roots) |
| Batch | `batch` (process multiple URLs from file) |
| Crawl | `crawl` (crawl website collecting titles and links) |
| Utility | `multi` (with `--watch`, `--dry-run`, `--parallel`, `--cache-ttl`), `raw`, `backends`, `install_check`, `completions`, `plugins` |

Run `wavexis --help` for the full list.

## Comparison

| Feature | wavexis | shot-scraper | Playwright |
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
| Action caching | Yes | No | No |
| Stealth mode | Yes | No | No |
| WebExtension management | Yes | No | No |
| Browser preferences | Yes | No | No |
| Live event streaming | Yes | No | No |
| Core Web Vitals scoring | Yes | No | No |
| Request modification | Yes | No | No |
| Rate limiting (serve) | Yes | No | No |
| Backend degradation | Yes | No | No |
| Site crawling | Yes | No | No |
| Accessibility audit | Yes | No | No |
| WebSocket inspection | Yes | No | No |
| Visual diff | Yes | No | No |
| Full CDP domain coverage (60 domains) | Yes | No | No |
| Heap profiler | Yes | No | No |
| Smart card emulation | Yes | No | No |
| System info | Yes | No | No |
| Tethering | Yes | No | No |
| WebMCP | Yes | No | No |

## Documentation

Full docs at [mathiaspaulenko.github.io/wavexis](https://mathiaspaulenko.github.io/wavexis/).

## License

MIT