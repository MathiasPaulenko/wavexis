# REPL

The `browsix repl` command launches an interactive shell for live browser sessions. It opens a non-headless browser and lets you execute commands in real time — navigate, click, type, take screenshots, evaluate JavaScript, and inspect page state without writing scripts.

## When to use the REPL

The REPL is designed for **interactive exploration and debugging**. Use it when you need to:

- **Explore a page** before writing a multi-action config — test selectors, check element visibility, verify JavaScript expressions.
- **Debug automation flows** — step through actions one at a time and observe the browser visually.
- **Inspect page state** — check cookies, URL, title, or evaluate arbitrary JavaScript on the current page.
- **Prototype sequences** — try click → type → screenshot interactively, then encode the working sequence into a YAML config.

## Launching

```bash
browsix repl
```

This opens a Chrome window (non-headless) and starts the interactive prompt:

```text
browsix REPL — type 'help' for commands, 'exit' to quit
browsix>
```

## Commands

The REPL supports 16 commands, each mapping to a backend operation:

| Command | Syntax | Description |
|---------|--------|-------------|
| `navigate` | `navigate <url>` | Navigate to a URL |
| `screenshot` | `screenshot [filename]` | Take a screenshot, save to file or `screenshot.png` |
| `eval` | `eval <expression>` | Evaluate a JavaScript expression |
| `click` | `click <selector>` | Click an element by CSS selector |
| `type` | `type <selector> <text>` | Type text into an input element |
| `fill` | `fill <selector> <text>` | Fill an input element (replaces content) |
| `hover` | `hover <selector>` | Hover over an element |
| `key` | `key <key>` | Press a keyboard key (e.g. `Enter`, `Tab`) |
| `cookies` | `cookies` | Get all cookies for the current page |
| `url` | `url` | Print the current page URL |
| `title` | `title` | Print the current page title |
| `wait` | `wait <seconds>` | Wait for a specified duration |
| `back` | `back` | Navigate back in browser history |
| `forward` | `forward` | Navigate forward in browser history |
| `reload` | `reload` | Reload the current page |
| `help` | `help` | Show available commands |
| `exit` | `exit` or `quit` | Exit the REPL |

## Examples

### Basic navigation and inspection

```text
browsix> navigate https://example.com
browsix> title
Example Domain
browsix> url
https://example.com/
browsix> eval document.querySelector('h1').textContent
Example Domain
```

### Form interaction

```text
browsix> navigate https://example.com/login
browsix> type #username admin@example.com
browsix> type #password secret123
browsix> click #login-button
browsix> wait 2
browsix> title
Dashboard - Example App
browsix> screenshot dashboard.png
```

### Cookie inspection

```text
browsix> navigate https://example.com
browsix> cookies
[{"name": "session", "value": "abc123", "domain": ".example.com", ...}]
```

### Keyboard input

```text
browsix> navigate https://example.com/search
browsix> type #search-input hello world
browsix> key Enter
browsix> wait 1
browsix> screenshot results.png
```

## How it works

The REPL uses an async event loop that:

1. Launches a non-headless browser via the configured backend (CDP or BiDi).
2. Reads input from stdin, parses it with `shlex.split` for proper quoting.
3. Dispatches the command to the corresponding backend method.
4. Prints the result (or saves to file for screenshots).
5. Loops until `exit`/`quit` or EOF.

The browser stays open for the duration of the session, so you can chain commands without re-launching. This makes the REPL significantly faster than running individual CLI commands for exploratory work.

## Tips

- **Selectors** — Use CSS selectors (e.g. `#id`, `.class`, `tag`). Quote selectors with special characters: `click "button[data-action='submit']"`.
- **Multi-word text** — The `type` and `fill` commands accept text with spaces. The REPL uses `shlex.split` so you can quote: `type #input "hello world"`.
- **Screenshots** — Without a filename, screenshots are saved to `screenshot.png`. Provide a path to customize: `screenshot /tmp/page.png`.
- **Backend selection** — Use `--backend bidi` to launch the REPL with the BiDi backend: `browsix --backend bidi repl`.
