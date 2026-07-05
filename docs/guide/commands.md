# Commands

## Global flags

| Flag | Description |
|------|-------------|
| `--backend cdp\|bidi` | Preferred backend |
| `--verbose, -v` | Show backend logs and timing info |
| `--quiet, -q` | Suppress all output except errors |
| `--version` | Print browsix version and exit |

## screenshot

Take a screenshot of a web page.

```bash
browsix screenshot <url> [options]
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
browsix pdf <url> [options]
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

Evaluate a JavaScript expression on a web page.

```bash
browsix eval <url> [options]
```

| Option | Description |
|--------|-------------|
| `-e, --expression` | JavaScript expression to evaluate |
| `-o, --output` | Output file path (JSON) |
| `--await-promise` | Await a returned Promise |
| `--file` | Read expression from file |

## navigate

Navigate to a URL and optionally wait for an element.

```bash
browsix navigate <url> [options]
```

## back / forward / reload / stop

Browser history navigation commands.

```bash
browsix back
browsix forward
browsix reload [--ignore-cache]
browsix stop
```

## tabs

Manage browser tabs.

```bash
browsix tabs <action> [options]
```

Actions: `list`, `new`, `close`, `activate`

## console

Capture console messages from a web page.

```bash
browsix console <url> [options]
```

## logs

Capture browser log entries.

```bash
browsix logs <url> [options]
```

## dom

DOM operations on a web page.

```bash
browsix dom <url> [options]
```

Actions: `get`, `query`, `attr`, `remove_attr`, `remove`, `focus`, `scroll`

## scrape

Scrape multiple URLs by evaluating a JS expression on each.

```bash
browsix scrape <urls...> [options]
```

## har

Capture network traffic as HAR 1.2.

```bash
browsix har <url> [options]
```

## cookies

Manage browser cookies.

```bash
browsix cookies <action> [options]
```

Actions: `get`, `set`, `delete`, `clear`

## headers

Set extra HTTP headers for all requests.

```bash
browsix headers '<json>'
```

## user-agent

Override the browser's User-Agent string.

```bash
browsix user-agent <ua>
```

## browser

Browser management commands.

```bash
browsix browser <action>
```

Actions: `version`, `new_context`, `list_contexts`

## devices

List available device presets.

```bash
browsix devices
```

## multi

Execute multiple actions from a YAML config file.

```bash
browsix multi <config>
```

## backends

List available backends.

```bash
browsix backends
```

## install_check

Check which backends are installed and their versions.

```bash
browsix install_check
```

## emulation

Emulation subcommands.

```bash
browsix emulation device <url> --device <name> [-o output]
browsix emulation viewport <url> --width <w> --height <h> [-o output]
browsix emulation geolocation <url> --lat <lat> --lon <lon> [-o output]
browsix emulation timezone <url> --tz <timezone> [-o output]
browsix emulation dark_mode <url> [-o output]
```

## raw

Send raw protocol commands directly to the browser backend.

```bash
browsix raw <method> [params] [--backend cdp|bidi] [-o output]
```

See [Raw Protocol](raw.md) for details.

## completions

Install shell completions.

```bash
browsix completions <shell>
```

Shells: `bash`, `zsh`, `fish`, `powershell`

## auth

Manage browser credential profiles for authenticated scraping.

```bash
browsix auth save <name> --user <username> --pass <password>
browsix auth use <name> --url <login-url>
browsix auth list
browsix auth delete <name>
```

## record

Record and replay browser sessions.

```bash
browsix record start <url> [-o session.json]
browsix record replay <session.json>
browsix record list
```

## serve

Start an HTTP API server.

```bash
browsix serve [--host 0.0.0.0] [--port 8080]
```

See [Serve Mode](../cookbook/serve-mode.md) for endpoint documentation.

## css

CSS inspection commands.

```bash
browsix css-styles <url> --selector "h1"
browsix css-computed <url> --selector "h1"
browsix css-rules <url> --sheet 0
```

## debug

Debugger commands (CDP bridge).

```bash
browsix debug-break <url> --line 10 [--condition "x > 5"]
browsix debug-step over|into|out
browsix debug-pause
browsix debug-resume
```

## perf

Performance profiling commands.

```bash
browsix perf-metrics <url>
browsix perf-trace <url> [-o trace.json]
browsix perf-profile <url> [-o profile.json]
browsix perf-coverage <url> [-o coverage.json]
```

## sw

Service worker management.

```bash
browsix sw list <url>
browsix sw unregister <url> --scope <scope>
browsix sw update <url> --scope <scope>
```

## animation

Animation control commands.

```bash
browsix animation list <url>
browsix animation pause <url> --id 0
browsix animation play <url> --id 0
browsix animation seek <url> --id 0 --time 500
```

## webauthn

WebAuthn virtual authenticator commands.

```bash
browsix webauthn add --protocol ctap2 --transport usb
browsix webauthn credentials <authenticator-id>
browsix webauthn remove <authenticator-id>
```

## cast

Cast commands.

```bash
browsix cast list
browsix cast start --sink <sink-name>
browsix cast stop
```

## bluetooth

Bluetooth emulation commands.

```bash
browsix bluetooth emulate --name "Test Adapter"
browsix bluetooth stop
```
