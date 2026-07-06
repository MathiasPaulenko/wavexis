# Init Wizard

The `browsix init` command generates `browsix.yaml` configuration files from predefined templates. It provides an interactive wizard for beginners and direct flags for scripting.

## Why use init?

Writing multi-action YAML configs from scratch requires knowing the exact action types, parameter names, and structure. The init wizard solves this by:

- **Providing templates** — 7 pre-built configs for common automation scenarios.
- **Guiding interactively** — prompts for the essential parameters (URL, expression, selector, text) so you don't need to memorize the YAML schema.
- **Generating valid YAML** — output is always parseable and ready to run with `browsix multi`.
- **Supporting non-interactive mode** — use flags for scripting and CI.

## Interactive mode

```bash
browsix init
```

The wizard shows available templates and prompts for selection:

```text
Available templates:
  1. screenshot    — Take a full-page screenshot
  2. pdf           — Generate a PDF document
  3. scrape        — Scrape content from multiple URLs
  4. eval          — Evaluate a JavaScript expression
  5. multi-step    — Navigate, click, type, and screenshot
  6. cookies       — Navigate and inspect cookies
  7. har           — Capture network traffic as HAR

Select template (number or name): 1
URL (default: https://example.com): https://my-site.com
Config saved to browsix.yaml
Run with: browsix multi browsix.yaml
```

## Non-interactive mode

Generate a config directly with flags — useful for scripts and CI:

```bash
browsix init -t screenshot -u https://example.com -o config.yaml
```

### Options

| Option | Description |
|--------|-------------|
| `-t, --template` | Template name (screenshot, pdf, scrape, eval, multi-step, cookies, har) |
| `-u, --url` | URL to use in the config (overrides template default) |
| `-e, --expression` | JavaScript expression (for scrape, eval templates) |
| `-s, --selector` | CSS selector (for multi-step click action) |
| `--text` | Text to type (for multi-step type action) |
| `-o, --output` | Output file path (default: browsix.yaml) |
| `--list` | List available templates and exit |

## Templates

### screenshot

Takes a full-page screenshot of a single URL.

```yaml
actions:
  - screenshot:
      url: https://example.com
      full_page: true
```

### pdf

Generates a PDF with A4 paper size.

```yaml
actions:
  - pdf:
      url: https://example.com
      paper: a4
```

### scrape

Scrapes content from multiple URLs by evaluating a JavaScript expression on each.

```yaml
actions:
  - scrape:
      urls:
        - https://example.com
      expression: document.title
```

### eval

Evaluates a single JavaScript expression and returns the result.

```yaml
actions:
  - eval:
      url: https://example.com
      expression: document.title
```

### multi-step

A 4-step interaction: navigate, click, type, and screenshot. Demonstrates action chaining.

```yaml
actions:
  - navigate:
      url: https://example.com
  - click:
      url: https://example.com
      selector: "#login-button"
  - type:
      url: https://example.com
      selector: "#username"
      text: admin
  - screenshot:
      url: https://example.com
      full_page: true
```

### cookies

Navigates to a URL and evaluates a cookie inspection expression.

```yaml
actions:
  - navigate:
      url: https://example.com
  - eval:
      url: https://example.com
      expression: document.cookie
```

### har

Captures network traffic as HAR 1.2 format.

```yaml
actions:
  - har:
      url: https://example.com
```

## Overrides

When using non-interactive mode, you can override template defaults:

| Override | Applies to | Effect |
|----------|-----------|--------|
| `--url` | All templates | Replaces the default URL |
| `--expression` | scrape, eval | Replaces the JavaScript expression |
| `--selector` | multi-step | Replaces the click selector |
| `--text` | multi-step | Replaces the type text |

### Example: customized multi-step

```bash
browsix init -t multi-step -u https://app.example.com -s "#submit-btn" --text "hello world" -o login.yaml
```

Generates:

```yaml
actions:
  - navigate:
      url: https://app.example.com
  - click:
      url: https://app.example.com
      selector: "#submit-btn"
  - type:
      url: https://app.example.com
      selector: "#username"
      text: hello world
  - screenshot:
      url: https://app.example.com
      full_page: true
```

## Listing templates

```bash
browsix init --list
```

Output:

```text
Available templates:
  screenshot    — Take a full-page screenshot
  pdf           — Generate a PDF document
  scrape        — Scrape content from multiple URLs
  eval          — Evaluate a JavaScript expression
  multi-step    — Navigate, click, type, and screenshot
  cookies       — Navigate and inspect cookies
  har           — Capture network traffic as HAR
```

## Workflow

A typical workflow using init:

1. **Generate a starter config**: `browsix init -t multi-step -u https://my-app.com -o config.yaml`
2. **Edit the config**: Add or modify actions in the YAML file.
3. **Validate**: `browsix multi config.yaml --dry-run`
4. **Run**: `browsix multi config.yaml`
5. **Iterate with watch**: `browsix multi config.yaml --watch` — edit and save to re-run automatically.
