# Raw Protocol Access

The `raw` command is an escape hatch for sending protocol commands directly to the browser backend. It works with both CDP and BiDi backends.

## Usage

```bash
wavexis raw <method> [params] [--backend cdp|bidi] [-o output]
```

- **method**: Protocol method name (e.g. `Page.reload`, `browsingContext.navigate`)
- **params**: JSON string with command parameters (default: `{}`)
- **--backend**: Choose backend (`cdp` or `bidi`). Defaults to CDP.
- **-o, --output**: Output file path (`-` for stdout, default)

## CDP Raw Commands

```bash
# Reload the page ignoring cache
wavexis raw "Page.reload" '{"ignoreCache": true}'

# Get system info
wavexis raw "SystemInfo.getInfo" '{}'

# Enable a specific domain
wavexis raw "Network.enable" '{}'

# Get all cookies
wavexis raw "Network.getCookies" '{}'
```

## BiDi Raw Commands

```bash
# Navigate to a URL via BiDi
wavexis raw --backend bidi "browsingContext.navigate" '{"context": "id", "url": "https://example.com"}'

# Get browsing context tree
wavexis raw --backend bidi "browsingContext.getTree" '{}'

# Subscribe to log events
wavexis raw --backend bidi "session.subscribe" '{"events": ["log.entryAdded"]}'
```

## Notes

- The `raw` command launches a headless browser, sends the command, and closes the browser.
- Params must be valid JSON. Invalid JSON will result in an error.
- The result is printed as JSON to stdout (or saved to a file with `-o`).
- Use `raw` when wavexis doesn't have a dedicated command for a protocol feature.
