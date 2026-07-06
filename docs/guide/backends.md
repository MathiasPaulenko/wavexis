# Backends

wavexis supports two backends with **full feature parity** as of v1.7.0.

## CDP backend (cdpwave)

The default backend. Uses the Chrome DevTools Protocol directly.

```bash
pip install wavexis[cdp]
```

All 100+ methods are supported natively.

## BiDi backend (bidiwave)

WebDriver BiDi backend. Uses a combination of:

- **BiDi native commands** — `browsingContext.navigate`, `script.evaluate`, `storage.getCookies`, etc.
- **JS workarounds** — `script.evaluate` with JavaScript for DOM, CSS, service workers, animations, cache storage
- **CDP bridge** — `browser.cdp.sendCommand` for Debugger, WebAuthn, WebAudio, Media, Cast, Bluetooth, performance profiling, accessibility, IndexedDB, HAR

```bash
pip install wavexis[bidi]
```

All 100+ methods are supported. Zero `NotImplementedError`.

### BiDi implementation strategies

| Strategy | Used for |
|----------|----------|
| BiDi native | Navigation, screenshots, tabs, cookies, contexts, dialogs, permissions, input, storage |
| JS workaround | DOM, CSS inspection, overlay, cache storage, service workers, animations |
| CDP bridge | Performance profiling, accessibility, debug, HAR, IndexedDB, WebAuthn, WebAudio, Media, Cast, Bluetooth, security, downloads |

## Selecting a backend

Use the `--backend` global flag:

```bash
wavexis --backend cdp screenshot https://example.com -o out.png
wavexis --backend bidi screenshot https://example.com -o out.png
```

## Checking installation

```bash
wavexis install_check
```

Output:

```
  cdp: 2.0.1
  bidi: 1.7.2
```

## Listing available backends

```bash
wavexis backends
```

## When to use which

- **CDP** — Chrome/Edge only. Most direct protocol access. Best for debugging and profiling.
- **BiDi** — Works with any WebDriver BiDi-compatible browser (Chrome, Firefox, Safari). Best for cross-browser automation. Falls back to CDP bridge for Chrome-specific features.
