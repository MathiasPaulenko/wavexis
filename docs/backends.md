# Backends

browsix supports two backends via separate packages:

## CDP backend (cdpwave)

The default and most feature-complete backend. Uses the Chrome DevTools Protocol.

```bash
pip install browsix[cdp]
```

**Supported features:**

- Screenshots (full page, selector, device)
- PDF generation
- JavaScript evaluation
- DOM operations
- HAR capture
- Cookies, headers, user-agent
- Tab management
- Console/log capture
- Device emulation, viewport, geolocation, timezone, dark mode
- Browser contexts

## BiDi backend (bidiwave)

Minimal WebDriver BiDi backend. Uses the WebDriver BiDi protocol.

```bash
pip install browsix[bidi]
```

**Supported features (minimal):**

- `launch`, `navigate`, `screenshot`, `eval`, `raw`, `close`

**Not supported (raises `NotImplementedError`):**

- All emulation methods
- DOM operations
- HAR capture
- Tab management
- Cookies, headers
- PDF generation

## Selecting a backend

Use the `--backend` global flag:

```bash
browsix --backend cdp screenshot https://example.com -o out.png
browsix --backend bidi screenshot https://example.com -o out.png
```

## Checking installation

```bash
browsix install_check
```

Output:

```
  cdp: 2.0.1
  bidi: not installed
```

## Listing available backends

```bash
browsix backends
```
