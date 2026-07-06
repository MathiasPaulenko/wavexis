# Auth Profiles

wavexis can save browser credentials and reuse them for authenticated scraping.

## Save credentials

```bash
wavexis auth save mysite --user admin --pass secret123
```

Credentials are stored locally in `~/.wavexis/auth/` encrypted with your system keyring.

## Use credentials

```bash
wavexis auth use mysite --url https://example.com/login
```

This launches a browser, navigates to the login URL, fills in the credentials,
and saves the session cookies for reuse.

## List saved profiles

```bash
wavexis auth list
```

## Delete a profile

```bash
wavexis auth delete mysite
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
wavexis multi auth-screenshot.yml
```
