# ── Stage 1: build ──────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml README.md ./
COPY browsix/ browsix/

RUN pip install --no-cache-dir build && python -m build --wheel

# ── Stage 2: runtime ────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="browsix"
LABEL org.opencontainers.image.description="Browser automation CLI — serve mode"
LABEL org.opencontainers.image.source="https://github.com/MathiasPaulenko/browsix"
LABEL org.opencontainers.image.license="MIT"

RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl[cdp,serve] && rm /tmp/*.whl

ENV CHROME_PATH=/usr/bin/chromium

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

ENTRYPOINT ["browsix", "serve", "--host", "0.0.0.0", "--port", "8080"]
