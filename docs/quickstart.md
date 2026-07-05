# Quickstart

## 1. Install

```bash
pip install browsix[cdp]
```

This installs browsix with the CDP backend (cdpwave). You also need Chrome or Edge installed on your system.

## 2. First screenshot

```bash
browsix screenshot https://example.com -o out.png
```

Output: `Screenshot saved to out.png`

## 3. First PDF

```bash
browsix pdf https://example.com -o out.pdf --paper a4
```

Output: `PDF saved to out.pdf`

## 4. First eval

```bash
browsix eval https://example.com -e "document.title"
```

Output: `"Example Domain"`

## 5. Multi-action

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
browsix multi actions.yml
```

## 6. Device emulation

```bash
browsix emulation device https://example.com --device iphone-15 -o mobile.png
```

## Next steps

- [Commands reference](commands.md)
- [Multi config](multi.md)
- [Backends](backends.md)
