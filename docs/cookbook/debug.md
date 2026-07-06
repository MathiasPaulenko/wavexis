# Debugging

wavexis provides debugger commands via the CDP bridge.

## Set a breakpoint

```bash
wavexis debug-break https://example.com --line 25
```

Set a conditional breakpoint:

```bash
wavexis debug-break https://example.com --line 25 --condition "x > 100"
```

## Set a function breakpoint

```bash
wavexis debug-break https://example.com --function "handleClick"
```

## Stepping

```bash
wavexis debug-step over
wavexis debug-step into
wavexis debug-step out
```

## Pause and resume

```bash
wavexis debug-pause
wavexis debug-resume
```

## Remove a breakpoint

```bash
wavexis debug-break --remove <breakpoint-id>
```

## Get event listeners

```bash
wavexis eval https://example.com -e "
  JSON.stringify(
    getEventListeners(document.querySelector('button'))
  )
"
```

## Combined with serve mode

```bash
# Start serve mode
wavexis serve --port 8080

# Set breakpoint via API
curl -X POST http://localhost:8080/debug/breakpoint \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "line": 25}'

# Step over
curl -X POST http://localhost:8080/debug/step \
  -H "Content-Type: application/json" \
  -d '{"action": "over"}'
```
