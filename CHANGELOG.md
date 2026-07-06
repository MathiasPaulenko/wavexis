# Changelog

All notable changes to wavexis are documented in this file.

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
