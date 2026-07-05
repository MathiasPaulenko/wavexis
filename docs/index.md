# browsix

Browser automation CLI — wraps [cdpwave](https://pypi.org/project/cdpwave/) and [bidiwave](https://pypi.org/project/bidiwave/).

No Node.js. No Chromium download. Uses your existing Chrome/Edge installation.

## Features

- **Screenshot** — full page, viewport, or element selector
- **PDF** — generate PDFs with paper size, orientation, margins
- **Eval** — evaluate JavaScript expressions on any page
- **Scrape** — batch scrape multiple URLs with a single expression
- **DOM** — get, query, set attributes, remove elements, scroll
- **HAR** — capture network traffic as HAR 1.2
- **Cookies** — get, set, delete, clear cookies
- **Tabs** — list, create, close, activate tabs
- **Console/Logs** — capture console messages and browser logs
- **Emulation** — device presets, viewport, geolocation, timezone, dark mode
- **Multi** — execute multiple actions from a YAML config file
- **Backends** — CDP (cdpwave) or WebDriver BiDi (bidiwave)

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

## Links

- [Quickstart](quickstart.md)
- [Installation](install.md)
- [Commands](commands.md)
- [Multi config](multi.md)
- [Backends](backends.md)
- [Troubleshooting](troubleshooting.md)
- [Contributing](contributing.md)
