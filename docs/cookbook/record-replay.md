# Record & Replay

wavexis can record a browser session (clicks, navigation, input) and replay it later.

## Record a session

```bash
wavexis record start https://example.com -o session.json
```

This launches a browser, navigates to the URL, and records all interactions
until you close the browser or press Ctrl+C. The session is saved as JSON.

## Replay a session

```bash
wavexis record replay session.json
```

This replays all recorded interactions in sequence. Useful for regression
testing or repeating complex workflows.

## List recorded sessions

```bash
wavexis record list
```

## Record with multi-action

```yaml
actions:
  - record:
      url: https://example.com
      output: checkout-flow.json
  - screenshot:
      url: https://example.com/checkout
      full_page: true
```

```bash
wavexis multi record-flow.yml
```

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
      - run: wavexis record replay checkout-flow.json
```
