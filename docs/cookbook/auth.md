# Auth Contexts

wavexis can apply an authentication context (cookies, custom headers, HTTP
basic auth) loaded from a JSON file before navigating to a protected URL.

## Create an auth context file

```json
{
  "cookies": [
    {"name": "session_id", "value": "abc123", "domain": ".example.com", "path": "/"}
  ],
  "headers": {
    "X-Custom-Auth": "token-xyz"
  },
  "username": "admin",
  "password": "secret123"
}
```

- `cookies` — list of cookie objects (`name` and `value` required)
- `headers` — extra HTTP headers sent on every request
- `username`/`password` — HTTP basic auth credentials
- `target_origin` — optional; rejects navigation to a different origin

> Storing passwords in plain-text JSON is insecure — prefer environment
> variables or a secrets manager for real credentials.

## Apply the context

```bash
wavexis auth context.json https://example.com/dashboard
```

The browser navigates to the URL to establish the origin, applies cookies and
headers, then navigates again. The result of `document.title` is printed so
you can verify the page loaded.

## Screenshot after auth

```bash
wavexis auth context.json https://example.com/dashboard --screenshot -o page.png
```

## In serve mode

`POST /auth` applies an auth context via the HTTP API (requires `--base-dir`):

```bash
wavexis serve --api-key secret --base-dir ./work

curl -X POST http://localhost:8080/auth \
  -H "Authorization: Bearer secret" \
  -H "Content-Type: application/json" \
  -d '{"context": "context.json", "url": "https://example.com/dashboard"}'
```

The `context` path is resolved relative to `--base-dir`.
