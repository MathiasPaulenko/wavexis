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
      - run: pip install wavexis[cdp]
      - uses: browser-actions/setup-chrome@v1
      - run: wavexis screenshot https://example.com -o out.png
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
- run: wavexis multi actions.yml
```

## Core Web Vitals budgets in CI

Fail CI when Core Web Vitals exceed thresholds:

```yaml
name: Performance
on: push
jobs:
  cwv:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install wavexis[cdp]
      - uses: browser-actions/setup-chrome@v1
      - run: |
          wavexis cwv https://example.com \
            --budget '{"lcp_ms":2500,"cls":0.1,"inp_ms":200}' \
            -o cwv-report.json
      - uses: actions/upload-artifact@v4
        with:
          name: cwv-report
          path: cwv-report.json
```

The `--budget` flag checks each metric against a max threshold. The report
includes `budgets.all_pass` (true/false) for programmatic CI gating.

## Docker

wavexis ships with a multi-stage Dockerfile for serve mode. The image is published to GHCR on every release tag.

### Pull from GHCR

```bash
docker run -p 8080:8080 ghcr.io/mathiaspaulenko/wavexis:latest
```

### Build locally

```bash
docker build -t wavexis .
docker run -p 8080:8080 wavexis
```

### Dockerfile (multi-stage)

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY wavexis/ wavexis/
RUN pip install build && python -m build --wheel

FROM python:3.12-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium fonts-liberation libgbm1 libgtk-3-0 libnss3 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install /tmp/*.whl[cdp,serve] && rm /tmp/*.whl
ENV CHROME_PATH=/usr/bin/chromium
EXPOSE 8080
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1
ENTRYPOINT ["wavexis", "serve", "--host", "0.0.0.0", "--port", "8080"]
```

### CI matrix

CI runs unit tests on Python 3.11, 3.12, and 3.13 with coverage reporting. Serve mode tests and Docker build are verified on every push to `main`.

### Release pipeline

On `v*.*.*` tag push:
1. Build sdist + wheel
2. Publish to PyPI (trusted publishing)
3. Build and push Docker image to `ghcr.io/mathiaspaulenko/wavexis` with semver tags
