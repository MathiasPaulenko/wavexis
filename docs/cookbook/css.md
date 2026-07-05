# CSS Inspection

browsix can inspect CSS styles, computed values, and stylesheet rules.

## Get inline styles

```bash
browsix css-styles https://example.com --selector "h1"
```

Returns the inline style string for the matched element.

## Get computed styles

```bash
browsix css-computed https://example.com --selector "h1"
```

Returns a JSON object with all computed CSS properties.

## Get stylesheet rules

```bash
browsix css-rules https://example.com --sheet 0
```

Returns all CSS rules from the specified stylesheet index.

## List stylesheets

```bash
browsix eval https://example.com -e "
  JSON.stringify(
    Array.from(document.styleSheets).map(s => ({
      href: s.href,
      rules: s.cssRules.length
    }))
  )
" --await-promise
```

## Overlay highlight

Highlight an element with a red outline for debugging:

```bash
browsix eval https://example.com -e "
  document.querySelector('h1').style.outline = '3px solid red'
"
```
