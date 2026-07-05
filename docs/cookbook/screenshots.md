# Screenshots

## Full page

```bash
browsix screenshot https://example.com -o full.png --full-page
```

## Element selector

```bash
browsix screenshot https://example.com -o element.png --selector "h1"
```

## Device emulation

```bash
browsix screenshot https://example.com -o mobile.png --device iphone-15
```

## With JavaScript

```bash
browsix screenshot https://example.com -o dark.png --js "document.body.style.background = 'black'"
```

## Wait for element

```bash
browsix screenshot https://slow-site.com -o out.png --wait-for "main-content"
```

## JPEG format

```bash
browsix screenshot https://example.com -o out.jpg --format jpeg
```
