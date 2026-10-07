# Debugging

wavexis provides debugger commands via the `debug` group (CDP — Chrome only).

## Set a breakpoint

```bash
wavexis debug breakpoint https://example.com --url https://example.com/app.js --line 25
```

Set a conditional breakpoint:

```bash
wavexis debug breakpoint https://example.com \
  --url https://example.com/app.js --line 25 --condition "x > 100"
```

## Set a function breakpoint

```bash
wavexis debug function-breakpoint https://example.com --function-name "handleClick"
```

## Stepping

```bash
wavexis debug step-over https://example.com
wavexis debug step-into https://example.com
wavexis debug step-out https://example.com
```

## Pause and resume

```bash
wavexis debug pause https://example.com
wavexis debug resume https://example.com
```

## Remove a breakpoint

```bash
wavexis debug remove-breakpoint https://example.com --breakpoint-id <id>
```

## Get event listeners

```bash
wavexis eval https://example.com -e "
  JSON.stringify(
    getEventListeners(document.querySelector('button'))
  )
"
```

## See also

Run `wavexis debug --help` for the full list of debugger sub-commands
(callstack, disable, enable, listeners, source, and more).
