# browsix

Browser automation CLI — wraps [cdpwave](https://pypi.org/project/cdpwave/) and [bidiwave](https://pypi.org/project/bidiwave/).

No Node.js. No Chromium download. Uses your existing Chrome/Edge installation.

## Why browsix?

- **CLI-first** — screenshot, PDF, eval, scrape from the command line
- **Multi-backend** — CDP (cdpwave) or WebDriver BiDi (bidiwave), switch with `--backend`
- **Multi-action** — batch multiple actions from a single YAML config
- **Serve mode** — HTTP API server powered by aiohttp
- **Raw protocol** — escape hatch for direct CDP/BiDi commands
- **Experimental domains** — WebAuthn, WebAudio, Media, Cast, Bluetooth
- **Fully typed** — `mypy --strict` across the entire codebase
- **MIT licensed** — permissive, compatible with any use

## Install

```bash
pip install browsix[cdp]
```

## Quick start

```bash
browsix screenshot https://example.com -o out.png
browsix pdf https://example.com -o out.pdf
browsix eval https://example.com -e "document.title"
```

## Commands

| Command | Description |
|---------|-------------|
| `screenshot` | Full page, viewport, or element selector |
| `pdf` | Generate PDFs with paper size, orientation, margins |
| `eval` | Evaluate JavaScript expressions |
| `scrape` | Batch scrape multiple URLs |
| `dom` | Get, query, set attributes, remove, scroll |
| `har` | Capture network traffic as HAR 1.2 |
| `cookies` | Get, set, delete, clear cookies |
| `tabs` | List, create, close, activate tabs |
| `emulation` | Device, viewport, geolocation, timezone, dark mode |
| `multi` | Execute multiple actions from YAML |
| `raw` | Send raw CDP/BiDi protocol commands |
| `serve` | HTTP API server mode |

## Next steps

- [Quickstart](guide/quickstart.md) — 5-minute tutorial
- [Guide](guide/installation.md) — in-depth coverage of each feature
- [Cookbook](cookbook/serve-mode.md) — recipes for common scenarios
- [API Reference](api/cli.md) — auto-generated docs for every module
- [Troubleshooting](guide/troubleshooting.md) — common errors and solutions
