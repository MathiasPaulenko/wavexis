# Raw Protocol Access

The `raw` command is an escape hatch for sending protocol commands directly to the browser backend. It works with both CDP and BiDi backends.

## Usage

```bash
browsix raw <method> [params] [--backend cdp|bidi] [-o output]
```

- **method**: Protocol method name (e.g. `Page.reload`, `browsingContext.navigate`)
- **params**: JSON string with command parameters (default: `{}`)
- **--backend**: Choose backend (`cdp` or `bidi`). Defaults to CDP.
- **-o, --output**: Output file path (`-` for stdout, default)

## CDP Raw Commands

```bash
# Reload the page ignoring cache
browsix raw "Page.reload" '{"ignoreCache": true}'

# Get system info
browsix raw "SystemInfo.getInfo" '{}'

# Enable a specific domain
browsix raw "Network.enable" '{}'

# Get all cookies
browsix raw "Network.getCookies" '{}'
```

## BiDi Raw Commands

```bash
# Navigate to a URL via BiDi
browsix raw --backend bidi "browsingContext.navigate" '{"context": "id", "url": "https://example.com"}'

# Get browsing context tree
browsix raw --backend bidi "browsingContext.getTree" '{}'

# Subscribe to log events
browsix raw --backend bidi "session.subscribe" '{"events": ["log.entryAdded"]}'
```

## Notes

- The `raw` command launches a headless browser, sends the command, and closes the browser.
- Params must be valid JSON. Invalid JSON will result in an error.
- The result is printed as JSON to stdout (or saved to a file with `-o`).
- Use `raw` when browsix doesn't have a dedicated command for a protocol feature.
