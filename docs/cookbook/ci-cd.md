# CI/CD Integration

## GitHub Actions

```yaml
name: Screenshot
on: push
jobs:
  screenshot:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install browsix[cdp]
      - uses: browser-actions/setup-chrome@v1
      - run: browsix screenshot https://example.com -o out.png
      - uses: actions/upload-artifact@v4
        with:
          name: screenshot
          path: out.png
```

## Multi-action in CI

Create `actions.yml`:

```yaml
actions:
  - screenshot:
      url: https://example.com
      full_page: true
  - eval:
      url: https://example.com
      expression: document.title
```

```yaml
- run: browsix multi actions.yml
```

## Docker

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    chromium \
    && rm -rf /var/lib/apt/lists/*

RUN pip install browsix[cdp]

ENV CHROME_PATH=/usr/bin/chromium

CMD ["browsix", "serve", "--host", "0.0.0.0", "--port", "8080"]
```
