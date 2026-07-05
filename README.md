# browsix

[![CI](https://github.com/MathiasPaulenko/browsix/actions/workflows/ci.yml/badge.svg)](https://github.com/MathiasPaulenko/browsix/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/browsix.svg)](https://pypi.org/project/browsix/)
[![Python](https://img.shields.io/pypi/pyversions/browsix.svg)](https://pypi.org/project/browsix/)
[![License](https://img.shields.io/github/license/MathiasPaulenko/browsix.svg)](https://github.com/MathiasPaulenko/browsix/blob/main/LICENSE)

> Browser automation CLI — wraps cdpwave and bidiwave. No Node.js, no Chromium download. Uses your existing Chrome/Edge.

## Install

```bash
pip install browsix[cdp]
```

## Quick start

```bash
# Take a screenshot
browsix screenshot https://example.com -o out.png

# Generate a PDF
browsix pdf https://example.com -o out.pdf --paper a4

# Evaluate JavaScript
browsix eval https://example.com -e "document.title"
```

## Multi-action

Create a YAML config and run multiple actions in sequence:

```yaml
# actions.yml
actions:
  - screenshot:
      url: https://example.com
      full_page: true
  - eval:
      url: https://example.com
      expression: document.title
```

```bash
browsix multi actions.yml
```

## Backends

browsix supports two backends:

- **CDP** (cdpwave) — default, full feature support. `pip install browsix[cdp]`
- **BiDi** (bidiwave) — minimal, WebDriver BiDi protocol. `pip install browsix[bidi]`

Select with `--backend`:

```bash
browsix --backend cdp screenshot https://example.com -o out.png
```

## Comparison

| Feature | browsix | shot-scraper | Playwright |
|---------|---------|--------------|------------|
| Language | Python | Python | Multi |
| Node.js required | No | Yes | Yes |
| Chromium download | No | Yes | Yes |
| CDP backend | Yes | Yes | Yes |
| BiDi backend | Yes | No | No |
| CLI-first | Yes | Yes | No |
| Multi-action YAML | Yes | No | No |
| Device emulation | Yes | Yes | Yes |
| HAR capture | Yes | No | Yes |
| PDF generation | Yes | Yes | Yes |
| Shell completions | Yes | No | No |

## Documentation

Full docs at [mathiaspaulenko.github.io/browsix](https://mathiaspaulenko.github.io/browsix/).

## License

MIT