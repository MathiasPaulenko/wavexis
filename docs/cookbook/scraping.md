# Scraping

## Single page

```bash
wavexis eval https://example.com -e "document.title"
```

## Multiple pages

```bash
wavexis scrape https://example.com https://example.org -e "document.title"
```

## Extract structured data

```bash
wavexis eval https://example.com -e "
  JSON.stringify({
    title: document.title,
    h1: document.querySelector('h1')?.textContent,
    links: Array.from(document.querySelectorAll('a')).map(a => a.href)
  })
" --await-promise
```

## With multi config

```yaml
actions:
  - scrape:
      urls:
        - https://example.com
        - https://example.org
        - https://example.net
      expression: document.title
```

```bash
wavexis multi scrape.yml
```

## DOM query

```bash
wavexis dom https://example.com --action query --selector "h1"
```
