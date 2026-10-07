# Core Web Vitals

The `wavexis cwv` command measures Core Web Vitals (LCP, CLS, INP) with actionable
ratings, a 0-100 score, and optional CI budgets for performance gating.

## Usage

```bash
wavexis cwv <url> [options]
```

| Option | Description |
|--------|-------------|
| `-o, --output` | Output file path (- for stdout) |
| `--observe` | Observation period in ms (default: 5000) |
| `--budget` | JSON budget thresholds |

## Metrics measured

| Metric | Description | Good | Needs improvement | Poor |
|--------|-------------|------|-------------------|------|
| **LCP** | Largest Contentful Paint | < 2500ms | 2500-4000ms | > 4000ms |
| **CLS** | Cumulative Layout Shift | < 0.1 | 0.1-0.25 | > 0.25 |
| **INP** | Interaction to Next Paint | < 200ms | 200-500ms | > 500ms |
| **FCP** | First Contentful Paint | < 1800ms | 1800-3000ms | > 3000ms |
| **TTFB** | Time to First Byte | < 800ms | 800-1800ms | > 1800ms |
| **TBT** | Total Blocking Time | < 200ms | 200-600ms | > 600ms |

## Scoring

The 0-100 score is calculated as a weighted average of the three Core Web Vitals:

- LCP: 40% weight
- CLS: 30% weight
- INP: 30% weight

Scores 90+ are green, 50-89 are yellow, below 50 are red.

## CI budgets

Pass JSON thresholds to fail CI when metrics exceed limits:

```bash
wavexis cwv https://example.com \
  --budget '{"lcp_ms":2500,"cls":0.1,"inp_ms":200}' \
  -o cwv-report.json
```

The report includes a `budgets` object with `all_pass` (boolean) and per-metric
`pass`/`fail` status. Exit code 0 if all budgets pass, 1 if any fail.

## Serve mode

The `POST /cwv` endpoint provides the same functionality via HTTP:

```bash
curl -X POST http://localhost:8080/cwv \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "budgets": {"lcp_ms": 2500}}'
```

## Backend notes

CWV metrics are collected via `PerformanceObserver` JavaScript API, which works
on both CDP and BiDi backends without requiring the CDP bridge.

| Backend | Support | Implementation |
|---------|---------|----------------|
| CDP | Full | `PerformanceObserver` via `Runtime.evaluate` |
| BiDi | Full | `PerformanceObserver` via `script.evaluate` |
