# Changelog

All notable changes to wavexis are documented in this file.

## v2.14.0 — 2026-07-19

### Bug Fixes

- **`smartcard` CLI command missing `--output` option** — The command hardcoded `"-"` in `_write_json_output()` and had no `output` parameter, so users could never save results to a file. Added the standard `-o`/`--output` option.
- **~46 unguarded `json.loads()` in `_debug.py`** — Across CSS, debug, overlay, DOM, emulation, digital-credentials, DOM-storage, extensions, fetch, preload, PWA, IndexedDB, layer-tree, log, input-domain, and network-domain subcommands — all would crash with an unhandled `JSONDecodeError` traceback on invalid user input. Added `_safe_json_loads()` helper that catches `JSONDecodeError` and exits with a user-friendly error message (exit code 2).

### Testing

- **2083 unit tests passing** — Added 9 regression tests in `test_debug_cli_regression.py` covering the smartcard output flag and JSON safety across 8 subcommand groups.

## v2.13.0 — 2026-07-19

### Full CDP & BiDi Coverage

- **Complete cdpwave coverage** — All 689 methods across 60 CDP domain classes now have direct wrappers in `AbstractBackend`, `CDPBackend`, and `BiDiBackend` (via CDP bridge). Zero uncovered methods.
- **Complete bidiwave coverage** — All 78 methods across 12 BiDi module classes plus 6 non-event `BiDiClient` methods now have direct wrappers in `BiDiBackend`. Zero uncovered methods.
- **40+ new backend mixins** — Added domain-specific mixins for console, crash report, device access, device orientation, digital credentials, DOM debugger, DOM snapshot, DOM storage, event breakpoints, extensions, FedCM, fetch, file system, headless experimental, heap profiler, indexed DB, input, inspector, IO, layer tree, log, media, memory, network domain, overlay, page, performance timeline, preload, profiler, PWA, runtime, schema, security, sensor, smart card emulation, system info, and target.
- **New action modules** — Added `smart_card_emulation`, `system_info`, `target`, `tethering`, `tracing`, and `web_mcp` actions.

### Bug Fixes

- **`_build_shadow_pierce_js` single-quote escaping** — `json.dumps` doesn't escape single quotes; selectors containing `'` were injected into single-quoted JS strings, breaking the script. Now single quotes are properly escaped with `\\'`.
- **Duplicate `dom_snapshot_capture_snapshot` / `dom_snapshot_get_snapshot`** — Second definitions in `bidi.py` had required positional arguments that conflicted with the earlier definitions. Made `computed_styles` / `computed_style_whitelist` optional with `None` defaults.

### Testing

- **2068 unit tests passing** — Fixed all 49 previously failing tests:
  - Replaced `MagicMock` with `AsyncMock` for all awaited client methods (browsing, network, script, CDP).
  - Fixed action lifecycle tests — actions call `navigate`, not `launch`/`close`.
  - Fixed CLI execution tests for `dom`, `console`, `media`, `security`, `logs` commands after subcommand group refactoring.
  - Fixed `FakeBackend`/`DummyBackend` — removed `AbstractBackend` inheritance (incomplete implementations).
  - Fixed `get_response_body` / `modify_request` / `modify_response` tests to use `network.*` mocks instead of CDP bridge.
  - Fixed `test_apply_auth_context_empty` — empty auth context navigates once, not twice.
  - Fixed `test_events_to_yaml_input_select` — input with `tag=select` generates `select` action, not `type`.
  - Fixed `test_write_csv_empty` — `write_csv([])` returns early without creating a file.
  - Fixed `test_unsubscribe_removes_handlers` — `unsubscribe_events` calls `client.off`, not `client.cdp.off`.

## v2.11.5 — 2026-07-08

### Testing

- **CDP backend coverage** — Added 154 comprehensive async unit tests for `CDPBackend` method bodies with fully mocked `CDPSession`/`CDPClient`, covering navigation, screenshots, DOM, network, input, storage, CSS, debugger, WebAuthn, media, tracing, accessibility, and more.
- **BiDi backend coverage** — Added 159 comprehensive async unit tests for `BiDiBackend` method bodies with mocked `BiDiClient`, covering navigation, screenshots, DOM, network, input, contexts, and more.
- **Coverage restored to 84%** — Overall test coverage increased from 70% to 84% after removing the `cdp.py` and `bidi.py` coverage exclusions, exceeding the 80% CI threshold.

### Code Quality

- **Ruff lint compliance** — Fixed all E501 (line length) and N806 (variable naming) errors in test files to pass CI lint checks.

## v2.11.4 — 2026-07-08

### Code Quality & Cleanup

- **`unregister_backend` now called after close** — New `_close_backend()` helper in `cli/_shared.py` calls `unregister_backend()` after `backend.close()`, preventing stale backends from lingering in the cleanup registry. All 59 `backend.close()` call sites across 14 CLI modules updated.
- **BiDi launch-check deduplication** — Extracted `_require_launched()` helper in `BiDiBackend`, replacing 80+ repetitions of the 3-line `if self._client is None or self._context is None: raise` boilerplate with a single method call.
- **Non-deterministic `hash()` in `_stream_console`** — Replaced `hash(json.dumps(...))` (randomized per process via `PYTHONHASHSEED`) with the raw JSON string as the deduplication set key.
- **Watch mode debounce** — Added 500ms debounce to watch mode: after detecting a file change, waits 500ms and re-checks mtime before executing, preventing 2-3 redundant executions on rapid saves.
- **Coverage exclusion removed** — Removed `cdp.py` and `bidi.py` from the coverage `omit` list in `pyproject.toml`, enabling coverage reporting for core backends.
- **Structured logging for serve mode** — New `_request_logging_middleware` assigns `X-Request-ID` headers and logs JSON-structured request info (method, path, status, elapsed_ms). `serve()` configures JSON log format for production correlation.

## v2.11.3 — 2026-07-08

### Security

- **JSON parse error handling** — New `_json_error_middleware` catches `json.JSONDecodeError` and returns 400 instead of unhandled 500 on invalid JSON bodies.
- **API key timing attack** — `serve.py` now uses `hmac.compare_digest()` instead of `!=` for API key comparison, preventing timing side-channel attacks.
- **CORS `*` warning** — `create_app()` now emits a warning when `--cors-origins *` is combined with `--api-key`, alerting about the security risk.
- **WebSocket rate limiting** — Each WebSocket connection now has a per-connection `TokenBucket` (120 msgs/min). Messages exceeding the limit receive an error response.
- **`_ws_connections` race condition** — WebSocket connection counter now protected by `asyncio.Lock`, preventing concurrent connections from exceeding the limit.

### Refactored

- **`@with_backend` decorator** — New decorator centralizes backend lifecycle (acquire → launch → handler → release) with consistent error handling. 10 handlers refactored to eliminate ~100 lines of boilerplate.
- **`handle_navigate` error handling** — Now uses `@with_backend()` which catches exceptions and returns JSON 500 instead of raw traceback.
- **`BackendPool` connection reuse** — Pool now maintains a queue of idle backends. `_run_action` and `_release_backend` return backends to the pool instead of closing them, enabling browser reuse across requests.

### Fixed

- **`select_with_fallback` misleading async** — Removed unused `options` parameter from async wrapper to clarify it delegates to sync.
- **`BackendNotAvailableError` message corruption** — `select_with_fallback_sync` now raises `WavexisError` instead of `BackendNotAvailableError` when all backends fail, avoiding confusing `Backend 'All backends failed...' is not installed` messages.

## v2.11.2 — 2026-07-08

### Fixed

- **Version mismatch (recurrent)** — Synced `wavexis/__init__.py` with `pyproject.toml` (was `2.11.0` vs `2.11.1`).
- **JS injection in `record` command** — `cli/_workflow.py` now escapes single quotes in `selector` and `text` before interpolating into JS expressions, preventing breakage and injection.
- **BiDi backend ignores browser options** — `backend/bidi.py` `launch()` now applies `browser_url`, `width`/`height` (viewport), `user_agent`, `extra_headers`, and `proxy` after connecting, matching CDP backend behavior.
- **BiDi uses `RuntimeError` instead of `SessionNotInitializedError`** — All 38+ `raise RuntimeError("BiDiBackend not launched...")` in `bidi.py` replaced with `SessionNotInitializedError`, which the CLI maps to a useful exit code and message instead of a raw traceback.
- **`load_auth` type annotation and runtime bug** — `auth.py` `load_auth()` now correctly handles both list and dict JSON shapes with proper type annotations and explicit `isinstance` checks.

## v2.11.0 — 2026-07-08

### Refactored

- **Action registry pattern** — `_execute_action` in `multi.py` refactored from 15 if/elif blocks to a dict-based action registry with lazy factory functions
- **Wildcard imports removed** — `cli/app.py` replaced 17 `import *` statements with explicit module imports for traceability
- **`_handle_error` simplified** — 7 repetitive `isinstance` blocks in `cli/_shared.py` replaced with dict-based exception-to-exit-code mapping
- **`_get_backend` event loop fix** — Removed fragile `get_running_loop` / `run_until_complete` pattern; added `select_with_fallback_sync` to `BackendManager` for clean sync backend selection
- **`__all__` added to all public modules** — 13 root-level modules now declare their public API surface explicitly
- **Spanish docstrings translated** — `__init__.py` and `backend/bidi.py` docstrings now in English

### Security

- **Plain-text credential warning** — `load_auth_context` in `auth.py` now emits a warning when a password is stored in plain-text JSON; suppressible via `WAVEXIS_AUTH_NO_WARN=1`

### CI/CD

- **Coverage threshold enforced** — `--cov-fail-under=80` added to pytest in unit-tests job
- **BiDi integration CI** — New `bidi-integration-tests` job installs `.[dev,bidi]` and runs integration tests
- **Multi-version mypy** — Typecheck job now runs on Python 3.11, 3.12, and 3.13
- **Dependency upper bounds pinned** — All dependencies now have `<next-major` constraints (typer, pyyaml, aiohttp, cdpwave, bidiwave, rich, pytest, ruff, mypy, etc.)

### Testing

- **Shared test fixtures** — `MockBackend` class with AsyncMock stubs added to `tests/conftest.py` as `mock_backend` and `mock_backend_factory` fixtures
- **Per-level conftest** — `tests/unit/conftest.py` and `tests/integration/conftest.py` with level-specific fixtures

## v2.10.1 — 2026-07-07

### Security

- **Path traversal fix** — `handle_multi` and `handle_auth` in serve mode now validate file paths against a configurable `--base-dir`. Without `--base-dir`, file path access is disabled by default.
- **API key authentication** — New `--api-key` flag for serve mode. All requests must include the key as a Bearer token or `api_key` query parameter. `/health` is exempt.
- **CORS middleware** — New `--cors-origins` flag for serve mode. Adds `Access-Control-Allow-*` headers for browser-based clients.

### Performance

- **Backend pool** — New `--max-concurrent` flag (default 5) limits simultaneous browser instances in serve mode via a semaphore-based pool.
- **WebSocket connection limit** — `/ws` endpoint now caps concurrent connections at 20 (configurable via `set_ws_max_connections()`). Returns 503 when full.
- **DOM mutation streaming** — Replaced `querySelectorAll('*')` polling with a `MutationObserver`-based approach in `_stream_dom_mutations`. Only collects actual mutations instead of scanning all elements.

### Fixed

- **TokenBucket race condition** — `retry_after()` is now async and uses the lock to prevent concurrent reads of `_tokens`.
- **CI silent failures** — Removed `continue-on-error: true` from integration tests, serve tests, and Docker build in `ci.yml`. Failures are now reported correctly.
- **Input validation** — All serve handlers now filter unknown JSON keys via `_safe_params()` before constructing dataclass params, preventing `TypeError` from unexpected fields.

### Changed

- `create_app()` and `serve()` accept `base_dir`, `api_key`, `cors_origins`, and `max_concurrent` parameters.
- `serve` CLI command accepts `--base-dir`, `--api-key`, `--cors-origins`, and `--max-concurrent` flags.
- Version synced between `pyproject.toml` and `wavexis/__init__.py`.

## v2.10.0 — 2026-07-07

### Added

- Graceful backend degradation — `select_with_fallback()` in `BackendManager` tries preferred backend, falls back to next if constructor fails (cdp→bidi or bidi→cdp)
- Core Web Vitals scoring — `wavexis cwv <url>` CLI command measures LCP, CLS, INP, FCP, TTFB, TBT with good/needs-improvement/poor ratings and 0-100 score
- `--budget` flag on `cwv` command for CI pass/fail thresholds (e.g. `--budget '{"lcp_ms":2500}'`)
- `POST /cwv` endpoint in serve.py for Core Web Vitals measurement via HTTP API
- Rate limiting middleware in serve.py — token bucket algorithm with `--rate-limit N` flag (requests per minute)
- `429 Too Many Requests` response with `Retry-After` header when rate limit exceeded
- `CoreWebVitalsAction` in `wavexis.actions.core_web_vitals` with THRESHOLDS and budget checking
- 19 unit tests covering backend degradation, CWV scoring, and rate limiting

### Changed

- `_get_backend()` in CLI and serve.py now uses `select_with_fallback()` for automatic backend degradation
- `create_app()` and `serve()` accept `rate_limit` parameter for HTTP API protection
- `serve` CLI command accepts `--rate-limit` flag

## v2.9.1 — 2026-07-07

### Added

- `modify_response()` method on both backends — intercept and modify response body, status, and headers in-flight via CDP Fetch domain
- `modify-response` CLI command — `wavexis modify-response <url> -p "*/api/*" -b '{"modified":true}' -s 200`
- `--wait` flag on `modify` CLI command — keeps browser open for N seconds to allow interception
- `--post-data` flag on `modify` CLI command — override request body
- `POST /modify-request` and `POST /modify-response` endpoints in serve.py
- 11 unit tests covering modify_request, modify_response, CLI commands, and serve endpoints

### Fixed

- `modify` CLI command now sets up interception before navigation and stays open with `--wait`
- `modify` CLI command now supports `--post-data` for overriding request body

## v2.9.0 — 2026-07-07

### Added

- Concurrent page operations via multi-tab support in a single browser process
- `TabHandle` class in CDP backend — shares WebSocket connection, own CDP session per tab
- `BiDiTabHandle` class in BiDi backend — shares BiDi client, own browsing context per tab
- `new_tab_handle()` method on both backends — returns a tab handle for concurrent operations
- `batch --mode tabs|processes` flag — `tabs` (default) uses 1 Chrome with N concurrent tabs, `processes` uses N Chrome processes
- `scrape --concurrency N` flag — scrape multiple URLs in parallel using tabs
- `multi --parallel` now uses separate tabs instead of broken single-session gather
- 8 unit tests covering tab creation, semaphore limits, and sequential vs parallel modes

### Fixed

- `multi --parallel` no longer causes navigation conflicts — each action gets its own tab

## v2.8.0 — 2026-07-07

### Added

- Cloud browser support: `--remote-url` flag to connect to Browserbase, Browserless, and other CDP-over-WebSocket cloud services
- `remote_url` field in `BrowserOptions` for programmatic cloud browser connections
- `CDPClient.connect(ws_url=...)` support in CDP backend for full WebSocket URLs with tokens
- `BiDiClient.connect(ws_url)` support in BiDi backend for cloud browser connections
- `remote_url` in `~/.wavexis/config.yml` global config
- Cookbook: Cloud Browsers guide with Browserbase and Browserless examples

## v2.7.0 — 2026-07-07

### Added

- Live event streaming: `dom_mutation` and `perf_metrics` event types in WebSocket `/ws`
- `_stream_dom_mutations` and `_stream_perf_metrics` streaming functions in serve.py
- WebExtension support: `extension_install`, `extension_uninstall`, `extension_list` in both backends
- CLI commands: `wavexis extension-install`, `wavexis extension-uninstall`, `wavexis extension-list`
- Browser prefs management: `get_pref`, `set_pref` in both backends
- CLI commands: `wavexis pref-get`, `wavexis pref-set`
- Abstract methods for extensions and prefs in `AbstractBackend`
- 16 unit tests covering extensions, prefs, and live event streaming

## v2.6.0 — 2026-07-07

### Added

- Action caching: `ActionCache` class with TTL, per-URL invalidation, and global clear
- `--cache-ttl` flag on `wavexis multi` to cache results for N seconds
- Cacheable actions: screenshot, dom, scrape, eval, cookies, headers
- Anti-bot stealth mode: `--stealth` global CLI flag
- `BrowserOptions.stealth` field for programmatic use
- Stealth JS injection in both CDP and BiDi backends on launch
- Hides `navigator.webdriver`, fakes plugins, languages, chrome runtime, WebGL vendor, permissions, platform, hardware concurrency, device memory

## v2.5.1 — 2026-07-07

### Added

- Core Web Vitals metrics in lighthouse performance audit: LCP, CLS, INP, TBT via PerformanceObserver
- Performance budgets: `--budget` (JSON file) and `--threshold` (inline, repeatable) CLI options
- Budget pass/fail reporting with per-metric breakdown in CLI output
- `_check_budgets` method in `LighthouseAction` for programmatic budget checking
- Scoring now includes LCP (>2500ms, >4000ms), CLS (>0.1, >0.25), INP (>200ms, >500ms) penalties

## v2.5.0 — 2026-07-07

### Added

- Annotated screenshots: `annotated_screenshot` method in both CDP and BiDi backends
- `wavexis annotate <url> -s "button,#email" -o out.png` CLI command
- Overlays numbered labels (@e1, @e2, ...) with red outlines on matched elements
- Returns image bytes plus label-to-selector mapping
- Automatic cleanup of overlay elements after screenshot capture

## v2.4.0 — 2026-07-07

### Added

- Request/response body inspection: `get_request_body`, `get_response_body` in both CDP and BiDi backends
- `wavexis inspect <url> -r <request_id> -t request|response` CLI command
- Request interception and modification: `modify_request` via CDP Fetch domain in both backends
- `wavexis modify <url> -p <pattern> -h <header> -m <method>` CLI command
- HAR replay: `replay_har` reads HAR file and replays requests via browser fetch API
- `wavexis har-replay <har_path> -u <url> -f <filter>` CLI command
- Combined tracing: `start_combined_trace`/`stop_combined_trace` capturing screenshots, network, console, and trace events
- `wavexis trace start|stop` CLI command with `--no-screenshots`, `--no-network`, `--no-console` flags
- axe-core accessibility audit: `axe_audit` injects axe-core JS and returns violations/passes/incomplete/inapplicable
- `wavexis axe <url> -o <output>` CLI command
- Event subscription: `subscribe_events`/`unsubscribe_events` for real-time console, network, dialog, and navigation events
- `wavexis events subscribe <url> -t <types> -d <duration>` CLI command
- WebSocket event streaming in serve.py for network_request, network_response, and dialog events

## v2.3.5 — 2026-07-07

### Added

- Natural language selector: `find_by_text`, `nl_click`, `nl_fill` in both CDP and BiDi backends
- `wavexis nl click/fill/find` CLI command with natural language queries
- Fuzzy text matching scoring: exact match (100), contains query (80), query contains text (60), word overlap (up to 50)
- Searches textContent, aria-label, placeholder, title, alt, and value attributes
- Returns best CSS selector for the matched element
- `--all` flag on `nl find` returns all matches ranked by score
- `--no-wait` flag to skip auto-waiting

## v2.3.4 — 2026-07-07

### Added

- Generate locator: `suggest_locator` method in both CDP and BiDi backends
- `wavexis dom <url> --action suggest_locator -s <selector>` CLI command
- `--all` flag to return all suggestions ranked by specificity
- Priority order: `#id` > `[data-testid]` > `[aria-label]` > `[role]` > `:has-text()` > `tag.classes` > `parent > tag` > `:nth-of-type()` > `tag`
- Uses `CSS.escape()` for safe selector generation

## v2.3.3 — 2026-07-07

### Added

- Shadow DOM support: `shadow_click`, `shadow_fill`, `shadow_eval` in both CDP and BiDi backends
- `wavexis shadow click/fill/eval` CLI command with `--selectors` (comma-separated piercing chain)
- `_build_shadow_pierce_js` helper generates JS that traverses `shadowRoot` boundaries
- Auto-waiting inside shadow DOM via `_wait_for_element_in_shadow` with polling and configurable timeout
- `--no-wait` flag to skip auto-waiting for shadow interactions
- Events dispatched with `composed: true` to cross shadow boundaries

## v2.3.2 — 2026-07-07

### Added

- iframe support: `iframe_click`, `iframe_fill`, `iframe_eval` in both CDP and BiDi backends
- `wavexis iframe click/fill/eval` CLI command with `--iframe`, `--selector`, `--value`, `--expression` options
- Auto-waiting inside iframes via `_wait_for_element_in_iframe` with polling and configurable timeout
- `--no-wait` flag to skip auto-waiting for iframe interactions
- Same-origin iframe support via `contentDocument` access

## v2.3.1 — 2026-07-07

### Added

- `auto_wait: bool = True` parameter in `click`, `fill`, `hover` (both backends)
- Pass `auto_wait=False` to skip element visibility polling for instant execution

## v2.3.0 — 2026-07-07

### Added

- Auto-waiting before `click`, `fill`, and `hover` in both CDP and BiDi backends
- `_wait_for_element` helper polls every 100ms until element exists and is visible (non-zero size)
- Configurable timeout (default 30s) via `WaitTimeoutError` with actionable hint
- Prevents `ElementNotFoundError` on dynamically loaded content

## v2.2.6 — 2026-07-07

### Added

- Named sessions: `--name` flag stores sessions in `~/.wavexis/sessions/`
- `wavexis session list` — list all saved named sessions with size and modification date
- `wavexis session delete --name <name>` — delete a named session
- Named sessions persist between runs, enabling stateful workflows

## v2.2.5 — 2026-07-07

### Improved

- Error messages now include actionable hints for common failures
- `ElementNotFoundError` suggests `wavexis dom` and `wavexis screenshot` for debugging
- `WaitTimeoutError` suggests increasing `--timeout` and alternative wait strategies
- `NavigationError` suggests checking URL, `--timeout`, and `--proxy`
- `SessionNotInitializedError` suggests `--headed` and checking Chromium installation
- `BackendNotAvailableError` shows install commands for both backends
- `MultiConfigError` suggests `--dry-run` to validate config

## v2.2.4 — 2026-07-07

### Added

- Progress reporting for long-running operations (`batch`, `multi`, `scrape`)
- `_progress(current, total, label)` helper shows `[n/total] — label` unless `--quiet`

## v2.2.3 — 2026-07-07

### Added

- Resource cleanup module (`wavexis.cleanup`) with `atexit` and signal handlers
- Backends are automatically registered for cleanup on crash or signal (SIGINT, SIGTERM, SIGBREAK)
- Orphaned browser processes are closed even when the process is killed unexpectedly

## v2.2.2 — 2026-07-07

### Added

- Auto scroll-into-view before `click`, `fill`, and `hover` in both CDP and BiDi backends
- `_scroll_into_view_if_needed` helper checks if element is in viewport and scrolls if needed

## v2.2.1 — 2026-07-07

### Added

- `--browser-url` global flag to connect to an existing browser (e.g. `--browser-url ws://localhost:9222`)
- `browser_url` field in `BrowserOptions` dataclass
- `browser_url` support in `config.yml` (`browser_url: ws://localhost:9222`)
- `CDPBackend.launch()` now uses `CDPClient.connect()` when `browser_url` is set instead of launching a new browser

## v2.2.0 — 2026-07-07

### Added

- `--user-data-dir` global flag for persistent browser profiles (cookies, login, extensions)
- `user_data_dir` field in `BrowserOptions` dataclass
- `user_data_dir` support in `config.yml` (`user_data_dir: /path/to/profile`)
- `user_data_dir` passed to `CDPClient.launch()` for CDP backend

## v2.1.3 — 2026-07-07

### Improved

- Fixed `_multi_watch()` bypassing `_run_async()` error handling — now uses `_run_async()` for proper `WavexisError` propagation
- Narrowed 3 `except Exception` handlers in `serve.py` WebSocket streams to `WavexisError` and `(ConnectionError, OSError)`
- Narrowed `except Exception` in `plugins.py` to `(ImportError, AttributeError, ValueError, TypeError)` for plugin loading isolation
- Verified `.gitignore` excludes `screenshot.png`

## v2.1.2 — 2026-07-07

### Refactored

- Split `cli/_workflow.py` (1238 lines) into 5 domain modules:
  - `_workflow.py` — multi, batch, record, replay (~340 lines)
  - `_config.py` — config, init, auth, completions, repl (~260 lines)
  - `_session.py` — session, extract, form (~220 lines)
  - `_advanced.py` — a11y, download, dialog, permissions, security, lighthouse (~280 lines)
  - `_serve.py` — serve, ws, plugins, backends, install_check (~140 lines)
- Moved `from pathlib import Path` to module-level imports (removed 7 inline duplicates)
- Fixed latent bug: `_multi()` now uses `execute_actions()` from `wavexis.multi` instead of non-existent `parse_yaml_config`

## v2.1.1 — 2026-07-07

### Refactored

- Added `SessionNotInitializedError` to `exceptions.py` for proper session guard errors
- Added `_require_session()` helper to `CDPBackend` — replaced 227 duplicated `if self._session is None: raise NavigationError(...)` guards
- Added `_require_client()` helper to `BiDiBackend` — replaced 4 `RuntimeError` session guards
- Removed 12 `type: ignore[union-attr]` comments in `cdp.py` (no longer needed after `_require_session()` returns `CDPSession`)
- Updated docstrings to reference `SessionNotInitializedError` instead of `NavigationError`/`RuntimeError`

## v2.1.0 — 2026-07-07

### Refactored

- Split `cli/app.py` (~3700 lines) into 10 domain modules: `_shared`, `_navigation`, `_capture`, `_input`, `_network`, `_emulation`, `_debug`, `_perf`, `_experimental`, `_workflow`
- `cli/app.py` is now a thin orchestrator (~15 lines) that imports domain modules
- Added `_write_json_output` helper to `_shared.py` for shared JSON output logic
- Updated unit tests to patch correct domain modules instead of monolithic `app.py`

## v2.0.6 — 2026-07-07

### Refactored

- Refactored `replay` command to use a single coroutine instead of 3 sequential `asyncio.run` calls
- Removed unused `contextlib` import from `cli/app.py`
- Verified `asyncio.run` is only used in CLI entry point (`cli/app.py`)

## v2.0.5 — 2026-07-07

### Fixed

- Fixed `a11y_node` and `a11y_ancestors` in `backend/cdp.py` — were passing AX `nodeId` to `Accessibility.getPartialAXTree` which expects a DOM `nodeId`, causing `CommandError: [-32602] Invalid parameters`. Now searches the full AX tree from `getFullAXTree` and filters by `nodeId`.

## v2.0.4 — 2026-07-07

### Refactored

- Extracted `_run_async` helper to eliminate ~60 `try/except asyncio.run` boilerplate patterns in `cli/app.py` (−229 lines net)
- Added `github-release` job to `release.yml` workflow — automatically creates GitHub Release with changelog notes and dist artifacts on tag push
- Narrowed `contextlib.suppress(Exception)` to `contextlib.suppress(WavexisError, OSError)` in `repl.py`
- Narrowed `contextlib.suppress(Exception)` to `contextlib.suppress(WavexisError)` in `actions/lighthouse.py`
- Removed 9 local `import json as _json` in `backend/bidi.py` — uses top-level `json` import
- Fixed mypy type errors in `cdp.py`, `scrape.py`, `eval.py`, `cli/app.py`

## v2.0.3 — 2026-07-06

### Refactored

- Removed all `# noqa` lint suppressions — converted Typer argument annotations to `Annotated` types (B008), replaced sync file I/O in async functions with `asyncio.to_thread` (ASYNC230, ASYNC240), fixed mutable default argument (B006)
- Narrowed broad `except Exception` clauses to specific exception types (`WavexisError`, `OSError`, `json.JSONDecodeError`, `KeyError`, `TypeError`, `TimeoutError`, `zipfile.BadZipFile`, `yaml.YAMLError`) across `cli/app.py`, `repl.py`, `serve.py`, `plugins.py`, `actions/record.py`, `actions/form.py`, `actions/crawl.py`, `actions/session.py`, `backend/cdp.py`
- Replaced 6 module-level mutable globals (`_preferred_backend`, `_verbose`, `_quiet`, `_headless`, `_timeout`, `_proxy`) with `CLIContext` dataclass + `contextvars.ContextVar` for thread-safe state management
- Removed unused `os` import in `backend/cdp.py` download handler
- Replaced local `import json as _json` with top-level `json` import in `backend/cdp.py`

## v2.0.2 — 2026-07-06

### Changed

- Removed redundant `import json as _json` in `webauthn` and `raw` commands — uses top-level `json` import
- Consolidated `_write_perf_output` into `_write_json_output` — eliminates duplicate function
- Replaced inline JSON output in `raw` command with `_write_json_output` call

### Refactored

- Extracted `apply_auth_context` to `wavexis/auth.py` — eliminates duplication between `serve.py` `handle_auth` and `cli/app.py` `auth` command
- Removed unused `_basic_auth` helper from `cli/app.py`

## v2.0.1 — 2026-07-06

### Fixed

- `serve.py` `/version` endpoint now returns the correct package version instead of hardcoded `1.11.2`
- `BackendManager` is now cached as a singleton via `get_manager()` — avoids re-discovering entry points on every call
- Added missing `return` after `_handle_error(e)` in 66 CLI command paths — prevents `NameError` and unintended output after errors
- `FakeBackend` in `test_manager.py` now implements `set_files` abstract method

## v2.0.0 — 2026-07-06

### Changed

- **Breaking:** Renamed package from `browsix` to `wavexis`
- CLI entry point changed from `browsix` to `wavexis`
- Plugin entry-point group changed from `browsix.plugins` to `wavexis.plugins`
- All imports updated from `browsix.*` to `wavexis.*`
- Project URLs updated to `github.com/MathiasPaulenko/wavexis`
- Version bumped to 2.0.0

## v1.0.0 — 2026-07-05

### Added

- Error handling with consistent exit codes (0 success, 1 browser, 2 config, 3 backend)
- `Output.error()`, `Output.success()`, `Output.info()` with optional rich formatting
- Global CLI flags: `--verbose`, `--quiet`, `--version`
- Shell completions command (`wavexis completions <shell>`)
- GitHub Actions CI workflow (lint, typecheck, unit tests, integration tests)
- GitHub Actions release workflow (PyPI publish, GitHub Pages docs)
- mkdocs documentation site with material theme
- Comprehensive README with badges, examples, and comparison table
- Troubleshooting guide
- Contributing guide

### Changed

- Version bumped to 1.0.0
- Development status classifier updated to "Production/Stable"
- CLI help strings improved for all commands and options
- All error messages now use `Output.error()` for consistent formatting

## v0.3.0 — 2026-06-28

### Added

- Emulation commands: device, viewport, geolocation, timezone, dark mode
- `EmulationAction` class for emulation operations
- `MultiAction` class for YAML multi-action execution
- `multi` CLI command with YAML config parsing
- `backends` CLI command to list available backends
- `install_check` CLI command to check backend installation status
- Global `--backend` CLI flag for backend selection
- `WAIT_PRESETS` and `THROTTLE_PRESETS` config dictionaries
- `EmulationParams` dataclass
- `MultiConfigError` exception for invalid multi configs
- `BackendManager.install_check()` method
- `BackendManager.list_available()` method
- `BackendManager.select(preferred)` with preferred backend support

## v0.2.0 — 2026-06-14

### Added

- DOM operations: get, query, set attribute, remove attribute, remove, focus, scroll
- HAR capture for network traffic analysis
- Cookie management: get, set, delete, clear
- Extra HTTP headers setting
- User-Agent override
- Browser context management
- Tab management: list, new, close, activate
- Console message capture
- Browser log capture
- Scrape command for batch URL processing
- `DOMAction`, `HARAction`, `TabsAction`, `ConsoleAction` classes
- `CookieParams`, `HarParams`, `DOMParams`, `TabsParams`, `ConsoleParams` dataclasses
- Device presets dictionary
- Paper sizes dictionary

## v0.1.0 — 2026-05-30

### Added

- Initial wavexis release
- `AbstractBackend` interface with all core methods
- `CDPBackend` implementation using cdpwave
- `BiDiBackend` minimal implementation using bidiwave
- `BackendManager` for backend registration and selection
- Core CLI commands: screenshot, pdf, eval, navigate, back, forward, reload, stop
- `ScreenshotAction`, `PDFAction`, `EvalAction`, `NavigateAction` classes
- `BrowserOptions`, `ScreenshotParams`, `PDFParams`, `EvalParams` dataclasses
- `WaitStrategy` with load, domcontentloaded, selector, networkidle strategies
- `Output` helpers for bytes, JSON, text, CSV
- Exception hierarchy: `wavexisError`, `BackendNotAvailableError`, `NavigationError`, `WaitTimeoutError`, `ElementNotFoundError`
- Typer CLI with help strings and no-args-is-help
- Unit and integration test infrastructure
