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

browsix ships with a multi-stage Dockerfile for serve mode. The image is published to GHCR on every release tag.

### Pull from GHCR

```bash
docker run -p 8080:8080 ghcr.io/mathiaspaulenko/browsix:latest
```

### Build locally

```bash
docker build -t browsix .
docker run -p 8080:8080 browsix
```

### Dockerfile (multi-stage)

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY browsix/ browsix/
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
ENTRYPOINT ["browsix", "serve", "--host", "0.0.0.0", "--port", "8080"]
```

### CI matrix

CI runs unit tests on Python 3.11, 3.12, and 3.13 with coverage reporting. Serve mode tests and Docker build are verified on every push to `main`.

### Release pipeline

On `v*.*.*` tag push:
1. Build sdist + wheel
2. Publish to PyPI (trusted publishing)
3. Build and push Docker image to `ghcr.io/mathiaspaulenko/browsix` with semver tags
