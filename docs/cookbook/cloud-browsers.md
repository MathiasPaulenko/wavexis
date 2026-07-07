# Cloud Browsers

wavexis supports connecting to cloud browser services like **Browserbase**, **Browserless**, and any provider that exposes CDP over WebSocket.

## Quick start

Pass `--remote-url` with the WebSocket URL provided by your cloud service:

```bash
wavexis screenshot https://example.com -o out.png \
  --remote-url "wss://chrome.browserless.io?token=YOUR_TOKEN"
```

## Supported providers

Any service that exposes a CDP WebSocket endpoint works. Common providers:

| Provider | WebSocket URL format |
|---|---|
| Browserless | `wss://chrome.browserless.io?token=TOKEN` |
| Browserbase | `wss://connect.browserbase.com?token=TOKEN` |
| BrowserCat | `wss://api.browsercat.com/ws?token=TOKEN` |
| Self-hosted | `ws://your-server:3000` |

## Usage examples

### Screenshot

```bash
wavexis screenshot https://example.com -o out.png \
  --remote-url "wss://chrome.browserless.io?token=XXX"
```

### PDF

```bash
wavexis pdf https://example.com -o out.pdf \
  --remote-url "wss://connect.browserbase.com?token=XXX"
```

### Scrape multiple URLs

```bash
wavexis scrape https://example.com https://example.org \
  --eval "document.title" \
  --remote-url "wss://chrome.browserless.io?token=XXX"
```

### Multi-action YAML

```yaml
actions:
  - action: navigate
    url: https://example.com
  - action: screenshot
    output: out.png
```

```bash
wavexis multi config.yml --remote-url "wss://chrome.browserless.io?token=XXX"
```

## Global config

Set `remote_url` in `~/.wavexis/config.yml` to avoid passing `--remote-url` every time:

```yaml
remote_url: wss://chrome.browserless.io?token=YOUR_TOKEN
```

## What works in cloud mode

All CDP-based commands work in cloud mode — the protocol is the same whether local or remote:

- Screenshots, PDF, screencast
- DOM operations, eval, click, fill, type
- Network capture (HAR), cookies, headers
- Emulation (device, viewport, geolocation)
- Performance profiling, CSS inspection
- Accessibility audit, DOM snapshot

## Limitations

Some features depend on local browser control and may not work with all cloud providers:

- **Stealth mode** — requires Chrome launch flags, not available in managed cloud sessions
- **Extensions** — depends on provider support for `.crx` installation
- **Browser prefs** — depends on provider configuration access
- **`--headed`** — cloud browsers are always headless
- **`--user-data-dir`** — cloud providers manage their own profiles
