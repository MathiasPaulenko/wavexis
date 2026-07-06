# Commands

## Global flags

These flags go before the subcommand (e.g. `wavexis --headed screenshot <url>`).

| Flag | Description |
|------|-------------|
| `--backend cdp\|bidi` | Preferred backend |
| `--verbose, -v` | Show backend logs and timing info |
| `--quiet, -q` | Suppress all output except errors |
| `--headed` | Run browser in headed mode (visible window) |
| `--timeout <ms>` | Navigation timeout in milliseconds (default: 30000) |
| `--proxy <url>` | Proxy server URL (e.g. `http://proxy:8080`, `socks5://proxy:1080`) |
| `--version` | Print wavexis version and exit |

Global flags can also be set persistently via `wavexis config`:

```bash
wavexis config set --key backend --value cdp
wavexis config set --key headless --value false
wavexis config set --key timeout --value 60000
wavexis config set --key proxy --value http://proxy:8080
```

CLI flags override config file values.

## screenshot

Take a screenshot of a web page.

```bash
wavexis screenshot <url> [options]
```

| Option | Description |
|--------|-------------|
| `-o, --output` | Output file path |
| `--full-page` | Capture full page, not just viewport |
| `--selector` | CSS selector to capture |
| `--device` | Device preset name |
| `--format` | Image format (png or jpeg) |
| `--js` | JavaScript to execute before screenshot |
| `--wait-for` | CSS selector to wait for |

## pdf

Generate a PDF of a web page.

```bash
wavexis pdf <url> [options]
```

| Option | Description |
|--------|-------------|
| `-o, --output` | Output file path |
| `--paper` | Paper size (a4, letter, legal, a3, a5) |
| `--landscape` | Use landscape orientation |
| `--margins` | Margin size (e.g. 0.4in) |
| `--media` | CSS media type (print or screen) |
| `--no-header-footer` | Omit header and footer |

## eval

Evaluate a JavaScript expression on a web page. Supports `--assert` for CI gates and `--format` for output control.

```bash
wavexis eval <url> [options]
```

| Option | Description |
|--------|-------------|
| `-e, --expression` | JavaScript expression to evaluate |
| `-o, --output` | Output file path (JSON) |
| `--await-promise` | Await a returned Promise |
| `--file` | Read expression from file |
| `--assert` | Assertion: `== value`, `!= value`, `contains text`, `matches regex` |
| `--format` | Output format: json, csv, yaml |

When `--assert` is provided, the command exits with code 0 (pass) or 1 (fail). See [CI Assertions](assert.md) for details.

## navigate

Navigate to a URL and optionally wait for an element.

```bash
wavexis navigate <url> [options]
```

## back / forward / reload / stop

Browser history navigation commands.

```bash
wavexis back
wavexis forward
wavexis reload [--ignore-cache]
wavexis stop
```

## tabs

Manage browser tabs.

```bash
wavexis tabs <action> [options]
```

Actions: `list`, `new`, `close`, `activate`

## console

Capture console messages and browser logs from a web page. Supports level filtering, output format selection, and capture mode.

```bash
wavexis console <url> [options]
```

| Option | Description |
|--------|-------------|
| `--level` | Filter by level: all, error, warning, info, log, debug |
| `--capture` | What to capture: console, logs, both (default: console) |
| `--format` | Output format: json, csv, yaml |
| `-o, --output` | Output file path |

The `--capture` option controls what data is collected:

- **console** — JavaScript `console.*` messages (console.log, console.error, etc.)
- **logs** — Browser-level log entries (network errors, CSP violations, etc.)
- **both** — Both console messages and browser logs, returned as a combined object

## logs

Capture browser log entries.

```bash
wavexis logs <url> [options]
```

## dom

DOM operations on a web page.

```bash
wavexis dom <url> [options]
```

Actions: `get`, `query`, `attr`, `remove_attr`, `remove`, `focus`, `scroll`

## scrape

Scrape multiple URLs by evaluating a JS expression on each.

```bash
wavexis scrape <urls...> [options]
```

## crawl

Crawl a website starting from a URL, collecting titles and links.

```bash
wavexis crawl <url> [options]
```

| Option | Description |
|--------|-------------|
| `-d, --depth` | Maximum crawl depth (0 = start page only, default: 2) |
| `--max-pages` | Maximum number of pages to visit (default: 50) |
| `--same-origin/--cross-origin` | Only crawl same-origin links (default: same) |
| `--pattern` | Regex pattern to filter URLs (empty = all) |
| `-o, --output` | Output file path (.json) |
| `-f, --format` | Output format (json) |

```bash
wavexis crawl https://example.com
wavexis crawl https://example.com --depth 3 --max-pages 100
wavexis crawl https://example.com --pattern '.*blog.*' -o results.json
```

## har

Capture network traffic as HAR 1.2.

```bash
wavexis har <url> [options]
```

## cookies

Manage browser cookies.

```bash
wavexis cookies <action> [options]
```

Actions: `get`, `set`, `delete`, `clear`

## input

Input interaction subcommands (click, type, fill, select, hover, key, drag, tap, scroll, upload).

```bash
wavexis input <action> <args> [options]
```

| Subcommand | Description |
|------------|-------------|
| `click` | Click an element |
| `type` | Type text into an element |
| `fill` | Fill an input with a value |
| `select` | Select an option in a `<select>` |
| `hover` | Hover over an element |
| `key` | Press a keyboard key |
| `drag` | Drag an element to a target |
| `tap` | Tap an element (touch emulation) |
| `scroll` | Scroll to element or by offset |
| `upload` | Upload files to a file input |

```bash
wavexis input click https://example.com "#button"
wavexis input type https://example.com "#input" "hello"
wavexis input scroll https://example.com --selector "#footer"
wavexis input scroll https://example.com --x 0 --y 500
wavexis input upload https://example.com "#file-input" /path/to/file.pdf
```

## session

Save and load browser session state (cookies + localStorage + sessionStorage).

```bash
wavexis session save <url> -o <file>
wavexis session load <file> [url]
```

```bash
wavexis session save https://app.com -o mysession.json
wavexis session load mysession.json https://app.com/dashboard
```

## extract

Extract structured data from a page using a CSS selector schema.

```bash
wavexis extract <url> -s '<schema>' [--selector <css>] [options]
```

| Option | Description |
|--------|-------------|
| `-s, --schema` | JSON mapping field names to CSS selectors |
| `--selector` | CSS selector to scope extraction (repeats per match) |
| `-o, --output` | Output file path (.json) |

```bash
wavexis extract https://shop.com -s '{"title":"h1","price":".price"}'
wavexis extract https://shop.com/products \
    -s '{"name":".name","price":".price"}' --selector ".product"
```

## form

Auto-fill form fields from JSON data and optionally submit.

```bash
wavexis form <url> -d '<data>' [--submit <selector>] [options]
```

| Option | Description |
|--------|-------------|
| `-d, --data` | JSON mapping CSS selectors to values |
| `--submit` | CSS selector for submit button |
| `-o, --output` | Output file path (.json) |

```bash
wavexis form https://app.com/register -d '{"#name":"Mathias","#email":"test@test.com"}'
wavexis form https://app.com/register -d '{"#name":"Mathias"}' --submit "#submit-btn"
```

## ws

Intercept WebSocket frames on a page. Capture sent/received or mock responses.

```bash
wavexis ws <url> [options]
```

| Option | Description |
|--------|-------------|
| `--duration` | Capture duration in ms (default: 5000) |
| `--pattern` | Regex pattern to filter WS URLs |
| `--mock` | JSON mapping request payloads to mock responses |
| `-o, --output` | Output file path (.json) |

```bash
wavexis ws https://app.com --duration 10000
wavexis ws https://app.com --pattern '.*api.*' -o frames.json
wavexis ws https://app.com --mock '{"ping":"pong"}' --duration 5000
```

## lighthouse

Run a Lighthouse-style audit (performance, accessibility, SEO, best practices).

```bash
wavexis lighthouse <url> [options]
```

| Option | Description |
|--------|-------------|
| `-c, --category` | Audit category (repeatable): performance, accessibility, seo, best-practices |
| `-o, --output` | Output file path (.json) |

```bash
wavexis lighthouse https://example.com
wavexis lighthouse https://example.com -c performance -c seo -o report.json
```

## headers

Set extra HTTP headers for all requests.

```bash
wavexis headers '<json>'
```

## user-agent

Override the browser's User-Agent string.

```bash
wavexis user-agent <ua>
```

## browser

Browser management commands.

```bash
wavexis browser <action>
```

Actions: `version`, `new_context`, `list_contexts`

## devices

List available device presets.

```bash
wavexis devices
```

## multi

Execute multiple actions from a YAML config file. See [Multi Config](multi.md) for detailed documentation.

```bash
wavexis multi <config> [options]
```

| Option | Description |
|--------|-------------|
| `--watch` | Re-run on config file changes |
| `--dry-run` | Validate and show plan without launching browser |
| `--parallel` | Execute all actions concurrently instead of sequentially |

## backends

List available backends.

```bash
wavexis backends
```

## install_check

Check which backends are installed and their versions.

```bash
wavexis install_check
```

## emulation

Emulation subcommands.

```bash
wavexis emulation device <url> --device <name> [-o output]
wavexis emulation viewport <url> --width <w> --height <h> [-o output]
wavexis emulation geolocation <url> --lat <lat> --lon <lon> [-o output]
wavexis emulation timezone <url> --tz <timezone> [-o output]
wavexis emulation dark_mode <url> [-o output]
```

## raw

Send raw protocol commands directly to the browser backend.

```bash
wavexis raw <method> [params] [--backend cdp|bidi] [-o output]
```

See [Raw Protocol](raw.md) for details.

## completions

Install shell completions.

```bash
wavexis completions <shell>
```

Shells: `bash`, `zsh`, `fish`, `powershell`

## auth

Manage browser credential profiles for authenticated scraping.

```bash
wavexis auth save <name> --user <username> --pass <password>
wavexis auth use <name> --url <login-url>
wavexis auth list
wavexis auth delete <name>
```

## record

Record and replay browser sessions.

```bash
wavexis record start <url> [-o session.json]
wavexis record replay <session.json>
wavexis record list
```

## serve

Start an HTTP API server.

```bash
wavexis serve [--host 0.0.0.0] [--port 8080]
```

See [Serve Mode](../cookbook/serve-mode.md) for endpoint documentation.

## css

CSS inspection commands.

```bash
wavexis css-styles <url> --selector "h1"
wavexis css-computed <url> --selector "h1"
wavexis css-rules <url> --sheet 0
```

## debug

Debugger commands (CDP bridge).

```bash
wavexis debug-break <url> --line 10 [--condition "x > 5"]
wavexis debug-step over|into|out
wavexis debug-pause
wavexis debug-resume
```

## perf

Capture performance metrics from a web page. See [Performance](perf.md) for detailed documentation.

```bash
wavexis perf <url> [options]
```

| Option | Description |
|--------|-------------|
| `-m, --metric` | Metric type: metrics, trace, profile, heap-snapshot, coverage, css-coverage |
| `-f, --format` | Output format: json, yaml |
| `-o, --output` | Output file path |
| `-d, --duration` | Duration in ms (for trace and profile) |

```bash
# Core Web Vitals (LCP, FCP, CLS, TTFB)
wavexis perf https://example.com

# CPU trace (5 seconds)
wavexis perf https://example.com -m trace -d 5000 -o trace.json

# JS code coverage
wavexis perf https://example.com -m coverage -o coverage.json

# CSS coverage
wavexis perf https://example.com -m css-coverage -o css-coverage.json

# Heap snapshot
wavexis perf https://example.com -m heap-snapshot -o heap.json
```

## sw

Service worker management.

```bash
wavexis sw list <url>
wavexis sw unregister <url> --scope <scope>
wavexis sw update <url> --scope <scope>
```

## animation

Animation control commands.

```bash
wavexis animation list <url>
wavexis animation pause <url> --id 0
wavexis animation play <url> --id 0
wavexis animation seek <url> --id 0 --time 500
```

## webauthn

WebAuthn virtual authenticator commands.

```bash
wavexis webauthn add --protocol ctap2 --transport usb
wavexis webauthn credentials <authenticator-id>
wavexis webauthn remove <authenticator-id>
```

## cast

Cast commands.

```bash
wavexis cast list
wavexis cast start --sink <sink-name>
wavexis cast stop
```

## bluetooth

Bluetooth emulation commands.

```bash
wavexis bluetooth emulate --name "Test Adapter"
wavexis bluetooth stop
```

## repl

Interactive REPL for live browser sessions. See [REPL](repl.md) for detailed documentation.

```bash
wavexis repl
```

Launches a non-headless browser and an interactive shell with 16 commands: `navigate`, `screenshot`, `eval`, `click`, `type`, `fill`, `hover`, `key`, `cookies`, `url`, `title`, `wait`, `back`, `forward`, `reload`, `help`, `exit`.

## init

Generate a `wavexis.yaml` config from templates. See [Init Wizard](init.md) for detailed documentation.

```bash
# Interactive wizard
wavexis init

# Non-interactive with flags
wavexis init -t multi-step -u https://example.com -o config.yaml

# List available templates
wavexis init --list
```

| Option | Description |
|--------|-------------|
| `-t, --template` | Template name |
| `-u, --url` | URL to use in config |
| `-e, --expression` | JavaScript expression (scrape, eval) |
| `-s, --selector` | CSS selector (multi-step) |
| `--text` | Text to type (multi-step) |
| `-o, --output` | Output file path (default: wavexis.yaml) |
| `--list` | List available templates and exit |

Templates: `screenshot`, `pdf`, `scrape`, `eval`, `multi-step`, `cookies`, `har`.

## config

Manage global wavexis configuration at `~/.wavexis/config.yml`.

```bash
wavexis config <action> [options]
```

| Action | Description |
|--------|-------------|
| `show` | Print current config file contents |
| `set` | Set a key-value pair in the config |
| `init` | Create a default config file |
| `path` | Print the config file path |

| Option | Description |
|--------|-------------|
| `--key` | Config key (`backend`, `headless`, `timeout`, `proxy`) |
| `--value` | Value to set |

```bash
# Show current config
wavexis config show

# Set defaults
wavexis config set --key backend --value cdp
wavexis config set --key headless --value false
wavexis config set --key timeout --value 60000
wavexis config set --key proxy --value http://proxy:8080

# Create initial config
wavexis config init

# Show config file path
wavexis config path
```
