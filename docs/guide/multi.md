# Multi Config

The `multi` command lets you execute multiple actions from a single YAML config file. All actions run sequentially on a single browser session, avoiding the overhead of launching a browser for each action.

## Usage

```bash
browsix multi <config.yml>
```

## Config format

The YAML file must have an `actions` key containing a list of action entries. Each entry is a dict with a single key (the action type) and a dict of parameters.

```yaml
actions:
  - screenshot:
      url: https://example.com
      full_page: true
  - pdf:
      url: https://example.com
      paper: a4
  - eval:
      url: https://example.com
      expression: document.title
  - dom:
      url: https://example.com
      action: get
      selector: h1
  - navigate:
      url: https://example.org
  - scrape:
      urls:
        - https://example.com
        - https://example.org
      expression: document.title
```

### How it works

1. browsix parses the YAML file and validates its structure.
2. A single browser instance is launched.
3. Each action is dispatched to the corresponding action class (`ScreenshotAction`, `EvalAction`, etc.).
4. Actions execute sequentially — each one completes before the next starts.
5. Results are collected and printed. Binary results (screenshots, PDFs) show byte counts; text results show a preview.
6. The browser is closed after all actions complete.

## Watch mode

Re-execute the config automatically when the file changes. This is designed for iterative config development — edit the YAML, save, and see results immediately:

```bash
browsix multi config.yml --watch
```

Output:

```text
Watching config.yml for changes (Ctrl+C to stop)...
[14:32:05] Completed 3 actions
  Waiting for changes...
  File changed, re-running...
[14:32:18] Completed 3 actions
  Waiting for changes...
```

Watch mode uses file polling (1-second interval) for cross-platform compatibility. Press `Ctrl+C` to stop.

## Dry run

Validate the config and show the planned actions without launching a browser:

```bash
browsix multi config.yml --dry-run
```

Output:

```text
Plan: 3 action(s)
  1. screenshot: https://example.com (full_page=True)
  2. eval: https://example.com — document.title
  3. pdf: https://example.com (paper=a4)
```

Dry run is useful for:

- **Validating config syntax** — catches structural errors before running.
- **Reviewing action sequences** — verify the order and parameters of actions.
- **CI validation** — ensure configs are valid in pull requests without executing them.

## Supported actions

| Action | Parameters | Description |
|--------|------------|-------------|
| `screenshot` | `url`, `full_page`, `format` | Take a screenshot |
| `pdf` | `url`, `paper`, `landscape` | Generate a PDF |
| `eval` | `url`, `expression`, `await_promise` | Evaluate JavaScript |
| `dom` | `url`, `action`, `selector` | DOM operations |
| `navigate` | `url` | Navigate to a URL |
| `scrape` | `urls`, `expression` | Batch scrape multiple URLs |
| `click` | `url`, `selector` | Click an element |
| `type` | `url`, `selector`, `text` | Type text into an element |
| `cookies` | `url`, `action`, `cookie`, `name`, `domain` | Cookie operations |
| `headers` | `url`, `action`, `headers`, `user_agent` | HTTP headers and user agent |

## Cookies in multi

The `cookies` action supports four operations: `get`, `set`, `delete`, `clear`.

### Get cookies

```yaml
actions:
  - cookies:
      url: https://example.com
      action: get
```

### Set a cookie

```yaml
actions:
  - cookies:
      url: https://example.com
      action: set
      cookie:
        name: session_token
        value: abc123
        domain: .example.com
        path: /
```

### Delete a cookie

```yaml
actions:
  - cookies:
      url: https://example.com
      action: delete
      name: session_token
      domain: .example.com
```

### Clear all cookies

```yaml
actions:
  - cookies:
      url: https://example.com
      action: clear
```

## Headers in multi

The `headers` action supports two operations: `set-headers` (set extra HTTP headers) and `set-user-agent` (override the User-Agent string).

### Set extra HTTP headers

```yaml
actions:
  - headers:
      url: https://example.com
      action: set-headers
      headers:
        X-Custom-Header: my-value
        Authorization: Bearer token123
  - screenshot:
      url: https://example.com
```

Headers are applied before subsequent actions in the sequence, so the screenshot will be taken with the custom headers active.

### Override User-Agent

```yaml
actions:
  - headers:
      url: https://example.com
      action: set-user-agent
      user_agent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"
  - screenshot:
      url: https://example.com
```

## Validation errors

Invalid config files raise `MultiConfigError` with exit code 2:

- Missing `actions` key
- `actions` is not a list
- Action entry has multiple keys
- Action parameters are not a dict
- Unknown action type

## Example: login flow

A complete login flow with cookie inspection:

```yaml
actions:
  - navigate:
      url: https://app.example.com/login
  - type:
      url: https://app.example.com/login
      selector: "#username"
      text: admin@example.com
  - type:
      url: https://app.example.com/login
      selector: "#password"
      text: secret123
  - click:
      url: https://app.example.com/login
      selector: "#login-button"
  - eval:
      url: https://app.example.com/dashboard
      expression: document.title
  - cookies:
      url: https://app.example.com/dashboard
      action: get
  - screenshot:
      url: https://app.example.com/dashboard
      full_page: true
```

```bash
browsix multi login-flow.yml
```

Output:

```text
Completed 7 actions
  Action 1: None
  Action 2: None
  Action 3: None
  Action 4: None
  Action 5: Dashboard - Example App
  Action 6: [{"name": "session", "value": "abc123", ...}]
  Action 7: 45678 bytes
```
