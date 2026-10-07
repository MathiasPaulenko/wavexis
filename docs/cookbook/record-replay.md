# Record & Replay

wavexis can record a browser session and save it as a YAML config that can be
replayed later with `replay` or `multi`.

## Record a session

```bash
wavexis record https://example.com -o session.yml
```

By default the browser executes a scripted set of actions (`--actions`) and
records them to a wavexis multi-action YAML file. With `--interactive`, a
non-headless browser opens instead and real user interactions (clicks, input
changes, key presses, scrolling, navigations) are captured until the duration
ends or the session stops.

| Option | Description |
|--------|-------------|
| `-o, --output` | Output YAML file (default: `session.yml`) |
| `--actions` | Comma-separated action types to record (default: `screenshot,eval`) |
| `--selector` | CSS selector for click/type actions |
| `--text` | Text for type action |
| `--expression` | JavaScript expression for eval action |
| `--interactive` | Capture real interactions in a visible browser |
| `--headless` | Run interactive recording headless |
| `-d, --duration` | Recording duration in seconds (interactive, default: 60) |

## Replay a session

```bash
wavexis replay session.yml
```

Replays all recorded actions in sequence — useful for regression testing or
repeating complex workflows. The file is plain YAML, so you can edit the
recorded steps before replaying.

## Recorded YAML is editable

The output uses the same format as `wavexis multi`:

```yaml
actions:
  - navigate:
      url: https://example.com
  - click:
      selector: "#login"
  - type:
      selector: "#username"
      text: "admin"
  - screenshot:
      full_page: true
```

You can add or reorder steps, then run them with `wavexis replay` or
`wavexis multi` interchangeably.

## CI/CD with replay

```yaml
name: Regression Test
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install wavexis[cdp]
      - uses: browser-actions/setup-chrome@v1
      - run: wavexis replay checkout-flow.yml
```
