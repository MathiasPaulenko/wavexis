# Troubleshooting

## Chrome not found

**Error:** `BackendNotAvailableError` or Chrome fails to launch.

**Solution:** Ensure Chrome or Edge is installed on your system.

- Windows: Check `C:\Program Files\Google\Chrome\Application\chrome.exe`
- macOS: Check `/Applications/Google Chrome.app`
- Linux: Install via `sudo apt install google-chrome-stable`

## Backend not available

**Error:** `No backend available. Install cdpwave: pip install browsix[cdp]`

**Solution:** Install the CDP backend:

```bash
pip install browsix[cdp]
```

## Navigation timeout

**Error:** `Timeout waiting for ...`

**Solution:** Increase the wait time or use a different wait strategy:

```bash
browsix screenshot https://slow-site.com --wait-for "body"
```

## Element not found

**Error:** `Element not found: <selector>`

**Solution:** Verify the CSS selector exists on the page. Use `--wait-for` to wait for the element before acting.

## BiDi driver issues

**Error:** `ImportError: bidiwave is not installed`

**Solution:** Install the BiDi backend:

```bash
pip install browsix[bidi]
```

Note: The BiDi backend is minimal and does not support emulation, DOM, HAR, or other advanced features.

## Multi config errors

**Error:** `Invalid multi config field '...'`

**Solution:** Check your YAML config:

1. Must have an `actions` key with a list
2. Each action is a dict with a single key
3. Action parameters must be a dict
4. Action type must be one of: screenshot, pdf, eval, dom, navigate, scrape

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Browser error (navigation, timeout, element not found) |
| 2 | Config error (invalid multi YAML) |
| 3 | Backend not available |
