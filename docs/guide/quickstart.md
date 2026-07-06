# Quickstart

This tutorial takes about 5 minutes. You'll learn to take screenshots, generate PDFs, evaluate JavaScript, and run multi-action configs.

## Install

```bash
pip install wavexis[cdp]
```

wavexis detects Chrome, Edge, Brave, or Chromium on your system. No browser download needed.

## First screenshot

```bash
wavexis screenshot https://example.com -o out.png
```

Output: `Screenshot saved to out.png`

## First PDF

```bash
wavexis pdf https://example.com -o out.pdf --paper a4
```

Output: `PDF saved to out.pdf`

## First eval

```bash
wavexis eval https://example.com -e "document.title"
```

Output: `"Example Domain"`

## Multi-action

Create a YAML config `actions.yml`:

```yaml
actions:
  - screenshot:
      url: https://example.com
      full_page: true
  - eval:
      url: https://example.com
      expression: document.title
```

Run it:

```bash
wavexis multi actions.yml
```

## Device emulation

```bash
wavexis emulation device https://example.com --device iphone-15 -o mobile.png
```

## What's next?

- [Commands](commands.md) — full command reference
- [Multi Config](multi.md) — YAML multi-action configs with watch mode
- [REPL](repl.md) — interactive browser shell for live sessions
- [Init Wizard](init.md) — generate configs from templates
- [Performance](perf.md) — Core Web Vitals and profiling
- [CI Assertions](assert.md) — pass/fail gates for CI pipelines
- [Backends](backends.md) — CDP vs BiDi with full parity
- [Raw Protocol](raw.md) — escape hatch for direct protocol commands
- [Cookbook: Auth](../cookbook/auth.md) — credential profiles
- [Cookbook: Record & Replay](../cookbook/record-replay.md) — session recording
- [Cookbook: Serve Mode](../cookbook/serve-mode.md) — HTTP API server
- [Cookbook: CSS](../cookbook/css.md) — CSS inspection
- [Cookbook: Debug](../cookbook/debug.md) — debugger commands
