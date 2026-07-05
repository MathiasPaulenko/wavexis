# Multi

The `multi` command lets you execute multiple actions from a single YAML config file.

## Usage

```bash
browsix multi <config.yml>
```

## Config format

The YAML file must have an `actions` key containing a list of action entries. Each entry is a dict with a single key (the action type) and a dict of parameters.

```yaml
actions:
  - screenshot:
      url: https://example.com
      full_page: true
  - pdf:
      url: https://example.com
      paper: a4
  - eval:
      url: https://example.com
      expression: document.title
  - dom:
      url: https://example.com
      action: get
      selector: h1
  - navigate:
      url: https://example.org
  - scrape:
      urls:
        - https://example.com
        - https://example.org
      expression: document.title
```

## Supported actions

| Action | Parameters |
|--------|------------|
| `screenshot` | `url`, `full_page`, `format` |
| `pdf` | `url`, `paper` |
| `eval` | `url`, `expression` |
| `dom` | `url`, `action`, `selector` |
| `navigate` | `url` |
| `scrape` | `urls`, `expression` |

## Validation errors

Invalid config files raise `MultiConfigError` with exit code 2:

- Missing `actions` key
- `actions` is not a list
- Action entry has multiple keys
- Action parameters are not a dict
- Unknown action type

## Example

```yaml
actions:
  - screenshot:
      url: https://example.com
      full_page: true
  - eval:
      url: https://example.com
      expression: document.querySelector('h1').textContent
```

```bash
browsix multi config.yml
```

Output:

```
Completed 2 actions
  Action 1: 12345 bytes
  Action 2: Example Domain
```
