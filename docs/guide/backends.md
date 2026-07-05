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
- WebAuthn, WebAudio, Media, Cast, Bluetooth (experimental)

## BiDi backend (bidiwave)

WebDriver BiDi backend. Uses the WebDriver BiDi protocol.

```bash
pip install browsix[bidi]
```

**Supported features:**

- `launch`, `navigate`, `screenshot`, `eval`, `raw`, `close`
- `go_back`, `go_forward`, `reload`, `stop_loading`, `wait_for`
- `list_tabs`, `new_tab`, `close_tab`
- DOM methods, storage methods
- `new_context`, `list_contexts`, `close_context`
- `get_window_bounds`, `set_window_bounds`
- `dialog_accept`, `dialog_dismiss`
- `grant_permission`, `reset_permissions`
- `click`, `type_text`, `fill`, `select_option`, `hover`, `key_press`, `drag`, `tap`
- `block_requests`, `intercept_requests`

**Not supported (raises `NotImplementedError`):**

- All emulation methods
- HAR capture
- Cookies, headers
- PDF generation
- Performance profiling
- Accessibility
- Service workers, animations

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
