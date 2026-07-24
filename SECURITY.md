# Security Policy

## Supported Versions

wavexis is under active development. Security fixes are applied to the latest
release only.

| Version  | Supported |
|----------|-----------|
| 2.16.x   | Yes       |
| < 2.16   | No        |

## Reporting a Vulnerability

If you discover a security vulnerability in wavexis, please report it
responsibly:

1. **Do not** open a public GitHub issue
2. Email **<mathias.paulenko@outlook.com>** with:
   - A description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)
3. You will receive a response within 48 hours

## Security Considerations

wavexis wraps cdpwave and bidiwave to control browsers via CDP and WebDriver BiDi.
Keep the following in mind:

- **Remote debugging port**: wavexis uses `--remote-debugging-port` via cdpwave
  which exposes a WebSocket endpoint. In production, ensure this port is not
  accessible to untrusted networks.
- **Arbitrary JavaScript execution**: `wavexis eval` executes arbitrary
  JavaScript in the browser context. Only run trusted code. In `serve` mode,
  `/eval` and `/ws` are only registered when `--api-key` is provided.
- **Browser subprocess**: The browser process inherits the permissions of the
  user running the Python script. Run with least privilege.
- **URL navigation**: `wavexis screenshot` and other commands can open any URL.
  In `serve` mode, navigation URLs are validated to allow only `http`, `https`,
  `about`, and `data` schemes; `javascript:` and `file:` are rejected.
- **Auth context**: The `--auth` flag loads cookies and headers from a JSON file.
  Do not commit auth context files to version control. Auth context files should
  include a `target_origin` field so credentials are only sent to the intended
  origin.
- **File path access in serve mode**: When running `wavexis serve --base-dir`,
  file paths referenced by actions are restricted to that directory. Do not run
  the server without `--api-key` or `--base-dir` in untrusted environments.
- **Environment variables in multi configs**: YAML `{{env.KEY}}` substitutions
  are limited to the comma-separated list in `WAVEXIS_ENV_ALLOWLIST`.

## Disclosure Policy

- Vulnerabilities are disclosed after a fix is released
- Credit is given to the reporter (unless they prefer to remain anonymous)
