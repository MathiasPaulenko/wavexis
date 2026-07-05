# Debugging

browsix provides debugger commands via the CDP bridge.

## Set a breakpoint

```bash
browsix debug-break https://example.com --line 25
```

Set a conditional breakpoint:

```bash
browsix debug-break https://example.com --line 25 --condition "x > 100"
```

## Set a function breakpoint

```bash
browsix debug-break https://example.com --function "handleClick"
```

## Stepping

```bash
browsix debug-step over
browsix debug-step into
browsix debug-step out
```

## Pause and resume

```bash
browsix debug-pause
browsix debug-resume
```

## Remove a breakpoint

```bash
browsix debug-break --remove <breakpoint-id>
```

## Get event listeners

```bash
browsix eval https://example.com -e "
  JSON.stringify(
    getEventListeners(document.querySelector('button'))
  )
"
```

## Combined with serve mode

```bash
# Start serve mode
browsix serve --port 8080

# Set breakpoint via API
curl -X POST http://localhost:8080/debug/breakpoint \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "line": 25}'

# Step over
curl -X POST http://localhost:8080/debug/step \
  -H "Content-Type: application/json" \
  -d '{"action": "over"}'
```
