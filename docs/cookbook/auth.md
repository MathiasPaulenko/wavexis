# Auth Profiles

browsix can save browser credentials and reuse them for authenticated scraping.

## Save credentials

```bash
browsix auth save mysite --user admin --pass secret123
```

Credentials are stored locally in `~/.browsix/auth/` encrypted with your system keyring.

## Use credentials

```bash
browsix auth use mysite --url https://example.com/login
```

This launches a browser, navigates to the login URL, fills in the credentials,
and saves the session cookies for reuse.

## List saved profiles

```bash
browsix auth list
```

## Delete a profile

```bash
browsix auth delete mysite
```

## Multi-action with auth

```yaml
actions:
  - auth:
      profile: mysite
      url: https://example.com/login
  - screenshot:
      url: https://example.com/dashboard
      full_page: true
```

```bash
browsix multi auth-screenshot.yml
```
