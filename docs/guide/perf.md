# Performance Metrics

The `browsix perf` command captures performance data from web pages using the Chrome DevTools Protocol. It provides access to Core Web Vitals, CPU traces, code coverage, and heap snapshots — all from the command line.

## When to use perf

- **Monitor Core Web Vitals** — Check LCP, FCP, CLS, and TTFB for your pages in real browsers.
- **CI performance gates** — Capture metrics in CI pipelines and track regressions over time.
- **Code coverage** — Identify unused JavaScript and CSS on your pages.
- **CPU profiling** — Capture CPU profiles to identify long-running JavaScript.
- **Heap snapshots** — Capture memory state for leak detection.
- **Performance traces** — Record detailed browser traces for deep analysis.

## Usage

```bash
browsix perf <url> [options]
```

### Options

| Option | Description |
|--------|-------------|
| `-m, --metric` | Metric type (default: `metrics`) |
| `-o, --output` | Output file path |
| `-f, --format` | Output format: `json` or `yaml` |
| `-d, --duration` | Duration in ms (for `trace` and `profile`) |

### Metric types

| Metric | Description | Backend method |
|--------|-------------|----------------|
| `metrics` | Core Web Vitals and timing metrics | `perf_metrics()` |
| `trace` | Performance trace with timeline events | `perf_trace(duration_ms)` |
| `profile` | CPU profile with call tree | `perf_profile(duration_ms)` |
| `heap-snapshot` | Heap snapshot for memory analysis | `perf_heap_snapshot()` |
| `coverage` | JavaScript code coverage | `perf_coverage()` |
| `css-coverage` | CSS rule usage coverage | `perf_css_coverage()` |

## Core Web Vitals (metrics)

The default metric type captures key performance indicators:

```bash
browsix perf https://example.com
```

Output includes a human-readable summary:

```text
Performance Summary:
----------------------------------------
  LCP       2500 ms
  FCP       1200 ms
  CLS       0.050
  TTFB       350 ms
  DCL       1800 ms
  Load      3200 ms
----------------------------------------
```

### What each metric means

| Metric | CDP key | Description |
|--------|---------|-------------|
| **LCP** | `LargestContentfulPaint` | Time to render the largest content element. Good: < 2500ms. |
| **FCP** | `FirstContentfulPaint` | Time to render first content. Good: < 1800ms. |
| **CLS** | `CumulativeLayoutShift` | Visual stability score. Good: < 0.1. |
| **TTFB** | `TimeToFirstByte` | Time to first byte of response. Good: < 800ms. |
| **DCL** | `DOMContentLoadEventEnd` | Time when DOM content is fully loaded. |
| **Load** | `LoadEventEnd` | Time when page load event completes. |

### Saving metrics to a file

```bash
browsix perf https://example.com -o metrics.json
browsix perf https://example.com -f yaml -o metrics.yaml
```

## CPU traces

Capture a performance trace with timeline events for detailed analysis:

```bash
browsix perf https://example.com -m trace -d 5000 -o trace.json
```

The trace contains detailed event data (paint, layout, script execution, network requests) that can be loaded in Chrome DevTools or analyzed programmatically.

The `--duration` flag controls how long the trace captures (in milliseconds). Default is 3000ms (3 seconds).

## CPU profiles

Capture a CPU profile to identify JavaScript functions that consume the most time:

```bash
browsix perf https://example.com -m profile -d 5000 -o profile.json
```

The profile contains a call tree with function names, execution counts, and timing. Load it in Chrome DevTools > Performance > Profiles for visualization.

## Code coverage

### JavaScript coverage

Identify which JavaScript functions were executed and which were not:

```bash
browsix perf https://example.com -m coverage -o coverage.json
```

Output contains per-function coverage data including URL, line ranges, and execution counts. Useful for identifying dead code or measuring test coverage.

### CSS coverage

Identify which CSS rules were used on the page:

```bash
browsix perf https://example.com -m css-coverage -o css-coverage.json
```

Output contains per-rule usage data. Useful for identifying unused CSS and optimizing bundle sizes.

## Heap snapshots

Capture a snapshot of the JavaScript heap for memory analysis:

```bash
browsix perf https://example.com -m heap-snapshot -o heap.json
```

The snapshot contains all objects in the heap with their types, sizes, and references. Load it in Chrome DevTools > Memory > Heap snapshots for comparison and leak detection.

## CI integration

### Performance regression detection

Capture metrics in CI and compare against a baseline:

```bash
# Capture current metrics
browsix perf https://my-app.com -m metrics -o current-metrics.json

# Compare with baseline (using jq)
LCP=$(jq '.LargestContentfulPaint' current-metrics.json)
if [ "$LCP" -gt 3000 ]; then
  echo "LCP regression: ${LCP}ms exceeds 3000ms threshold"
  exit 1
fi
```

### Coverage tracking

Track JavaScript and CSS coverage over time:

```bash
browsix perf https://my-app.com -m coverage -o coverage-$(date +%s).json
browsix perf https://my-app.com -m css-coverage -o css-coverage-$(date +%s).json
```

## Backend notes

Performance metrics are captured via the CDP bridge. Both CDP and BiDi backends support all metric types, but the BiDi backend internally uses the CDP bridge (`browser.cdp.sendCommand`) for these operations since WebDriver BiDi does not yet have native performance APIs.

| Backend | Support | Implementation |
|---------|---------|----------------|
| CDP | Full | Native CDP commands |
| BiDi | Full | CDP bridge via `browser.cdp.sendCommand` |
