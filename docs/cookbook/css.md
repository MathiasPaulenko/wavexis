# CSS Inspection

wavexis can inspect CSS styles, computed values, and stylesheet rules via the `css` command group.

## Get inline styles

```bash
wavexis css styles https://example.com --selector "h1"
```

Returns the inline style string for the matched element.

## Get computed styles

```bash
wavexis css computed https://example.com --selector "h1"
```

Returns a JSON object with all computed CSS properties.

## List stylesheets

```bash
wavexis css stylesheets https://example.com
```

Returns the page's stylesheets (ID, source, URL) — use a `stylesheet_id` from this list to get its rules.

## Get stylesheet rules

```bash
wavexis css rules https://example.com --stylesheet-id <id>
```

Returns all CSS rules from the specified stylesheet.

## Overlay highlight

Highlight an element with a red outline for debugging:

```bash
wavexis eval https://example.com -e "
  document.querySelector('h1').style.outline = '3px solid red'
"
```
