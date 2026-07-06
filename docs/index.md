# wavexis

Browser automation CLI — wraps [cdpwave](https://pypi.org/project/cdpwave/) and [bidiwave](https://pypi.org/project/bidiwave/).

No Node.js. No Chromium download. Uses your existing Chrome/Edge installation.

## Why wavexis?

wavexis is a command-line tool for browser automation. It wraps the cdpwave (Chrome DevTools Protocol) and bidiwave (WebDriver BiDi) libraries, exposing their capabilities through a single unified CLI. You don't need Node.js, Playwright, or a separate Chromium download — wavexis launches your existing Chrome or Edge installation directly.

### Core concepts

- **Backend** — The browser driver that executes commands. Two backends with full feature parity: CDP (default, via cdpwave) and BiDi (via bidiwave). Switch with `--backend bidi` without losing functionality.
- **Action** — A single operation (screenshot, eval, click, etc.). Each action maps to a CLI command or a step in a multi-action YAML config.
- **Multi-action** — A YAML config that chains multiple actions in sequence on a single browser session. Avoids the overhead of launching a browser per action.
- **Serve mode** — An HTTP API server that exposes all wavexis commands as REST endpoints with WebSocket streaming for real-time events.
- **REPL** — An interactive shell for live browser sessions. Navigate, click, type, and inspect in real time without writing scripts.
- **Init wizard** — An interactive generator that creates `wavexis.yaml` configs from predefined templates for common automation scenarios.

### Key features

- **CLI-first** — screenshot, PDF, eval, scrape from the command line
- **Multi-backend** — CDP (cdpwave) or WebDriver BiDi (bidiwave), switch with `--backend`
- **Full parity** — both backends implement all 100+ methods (BiDi uses native + JS + CDP bridge)
- **Multi-action** — batch multiple actions from a single YAML config with `--watch` for iterative development
- **Serve mode** — HTTP API server powered by aiohttp
- **Auth profiles** — save and reuse browser credentials
- **Record & replay** — record browser sessions and replay them
- **Interactive REPL** — live browser shell with 16 commands
- **Config wizard** — generate wavexis.yaml from 7 templates interactively
- **CI assertions** — `--assert` flag on `eval` for pass/fail gates with exit codes
- **Performance metrics** — LCP, FCP, CLS, TTFB, CPU traces, profiles, coverage
- **Console capture** — console messages and browser logs with level filtering
- **Raw protocol** — escape hatch for direct CDP/BiDi commands
- **Experimental domains** — WebAuthn, WebAudio, Media, Cast, Bluetooth
- **Fully typed** — `mypy --strict` across the entire codebase
- **MIT licensed** — permissive, compatible with any use

## Install

```bash
pip install wavexis[cdp]
```

## Quick start

```bash
wavexis screenshot https://example.com -o out.png
wavexis pdf https://example.com -o out.pdf
wavexis eval https://example.com -e "document.title"
```

## Commands

| Command | Description |
|---------|-------------|
| `screenshot` | Full page, viewport, or element selector |
| `pdf` | Generate PDFs with paper size, orientation, margins |
| `eval` | Evaluate JavaScript expressions (with `--assert` for CI gates) |
| `scrape` | Batch scrape multiple URLs |
| `dom` | Get, query, set attributes, remove, scroll |
| `har` | Capture network traffic as HAR 1.2 |
| `cookies` | Get, set, delete, clear cookies |
| `tabs` | List, create, close, activate tabs |
| `emulation` | Device, viewport, geolocation, timezone, dark mode |
| `multi` | Execute multiple actions from YAML (with `--watch`, `--dry-run`) |
| `raw` | Send raw CDP/BiDi protocol commands |
| `serve` | HTTP API server mode |
| `auth` | Save, use, list, delete credential profiles |
| `record` | Record and replay browser sessions |
| `css` | Inspect styles, computed values, rules |
| `debug` | Breakpoints, stepping, pause, resume |
| `perf` | Metrics (LCP/FCP/CLS/TTFB), trace, profile, coverage, heap snapshot |
| `console` | Capture console messages and browser logs (with `--capture`, `--format`) |
| `repl` | Interactive REPL for live browser sessions |
| `init` | Generate wavexis.yaml from templates interactively |
| `sw` | Service worker list, unregister, update |
| `animation` | List, pause, play, seek animations |
| `webauthn` | Virtual authenticator management |
| `cast` | List sinks, start/stop tab mirroring |
| `bluetooth` | Emulate and stop Bluetooth adapter |

## Next steps

- [Quickstart](guide/quickstart.md) — 5-minute tutorial
- [Installation](guide/installation.md) — setup and shell completions
- [Commands](guide/commands.md) — full command reference
- [Multi Config](guide/multi.md) — YAML multi-action configs with watch mode
- [REPL](guide/repl.md) — interactive browser shell
- [Init Wizard](guide/init.md) — config generation from templates
- [Performance](guide/perf.md) — Core Web Vitals and profiling
- [CI Assertions](guide/assert.md) — pass/fail gates for CI pipelines
- [Backends](guide/backends.md) — CDP vs BiDi with full parity
- [Raw Protocol](guide/raw.md) — escape hatch for direct protocol commands
- [Cookbook](cookbook/serve-mode.md) — recipes for common scenarios
- [API Reference](api/cli.md) — auto-generated docs for every module
- [Troubleshooting](guide/troubleshooting.md) — common errors and solutions
