# CI Assertions

The `--assert` flag on the `eval` command enables pass/fail gates directly from the command line. This is designed for CI/CD pipelines where you need to verify page state without writing custom scripts.

## How it works

When `--assert` is provided, `browsix eval` evaluates the JavaScript expression, compares the result against the assertion, and exits with code 0 (pass) or 1 (fail). The assertion output is printed to stdout for CI logs.

## Operators

Four assertion operators are supported:

| Operator | Syntax | Description |
|----------|--------|-------------|
| `==` | `== value` | Result must equal `value` (string comparison) |
| `!=` | `!= value` | Result must not equal `value` |
| `contains` | `contains substring` | Result must contain `substring` |
| `matches` | `matches regex` | Result must match `regex` (Python `re.search`) |

## Usage

```bash
browsix eval <url> -e "<expression>" --assert "<operator> <value>"
```

## Examples

### Equality check

Verify the page title matches an expected value:

```bash
browsix eval https://example.com -e "document.title" --assert "== Example Domain"
```

Output:

```text
assert: == Example Domain
result: Example Domain
status: PASS
```

Exit code: 0

### Inequality check

Verify the page title has changed from an old value:

```bash
browsix eval https://example.com -e "document.title" --assert "!= Old Title"
```

### Substring check

Verify the page body contains expected text:

```bash
browsix eval https://example.com -e "document.body.innerText" --assert "contains Welcome"
```

### Regex match

Verify the title matches a pattern (e.g., contains an error code):

```bash
browsix eval https://example.com -e "document.title" --assert "matches Error \\d+"
```

### Numeric comparison

The result is converted to a string before comparison, so numeric results work with `==`:

```bash
browsix eval https://example.com -e "document.querySelectorAll('a').length" --assert "== 5"
```

## CI pipeline integration

### GitHub Actions

```yaml
name: Verify deployment
on: [deployment_status]
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install browsix[cdp]
      - name: Check page title
        run: |
          browsix eval https://my-app.com \
            -e "document.title" \
            --assert "== My App — Dashboard"
      - name: Check content loaded
        run: |
          browsix eval https://my-app.com \
            -e "document.querySelector('#root').children.length" \
            --assert "!= 0"
```

### Shell script

```bash
#!/bin/bash
set -e

URL="https://my-app.com"

# Verify title
browsix eval "$URL" -e "document.title" --assert "== Dashboard"

# Verify API data loaded
browsix eval "$URL" \
  -e "document.querySelector('[data-testid=user-list]').children.length" \
  --assert "!= 0"

# Verify no error messages
browsix eval "$URL" \
  -e "document.querySelector('.error-message')?.textContent || ''" \
  --assert "== "

echo "All assertions passed"
```

## Output format

When `--assert` is used, the output always includes three lines:

```text
assert: <the assertion expression>
result: <the actual result value>
status: PASS|FAIL
```

On failure, a fourth line is printed to stderr with details:

```text
  Expected 'Expected Title', got 'Actual Title'
```

## Combining with other flags

`--assert` works alongside other `eval` options:

- `--await-promise` — assert on the resolved value of a Promise.
- `--file` — read the expression from a file and assert on the result.

```bash
browsix eval https://example.com \
  --file check.js \
  --await-promise \
  --assert "== expected result"
```

## Limitations

- **String comparison** — All comparisons are string-based. The result is converted with `str()` before comparing. This means `42` and `"42"` are equal.
- **No numeric operators** — Operators like `>`, `<`, `>=`, `<=` are not supported. Use `matches` with regex for range checks, or compare in JavaScript: `browsix eval url -e "performance.now() < 3000 ? 'pass' : 'fail'" --assert "== pass"`.
- **Single assertion** — Only one assertion per command. For multiple checks, run multiple `eval` commands or use a multi-action YAML config.
