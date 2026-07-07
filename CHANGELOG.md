# Changelog

All notable changes to wavexis are documented in this file.

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
