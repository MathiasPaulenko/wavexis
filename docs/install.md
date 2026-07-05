# Installation

## pip

```bash
pip install browsix[cdp]
```

To use the WebDriver BiDi backend instead:

```bash
pip install browsix[bidi]
```

Both backends:

```bash
pip install browsix[cdp,bidi]
```

## pipx

For isolated installation:

```bash
pipx install browsix[cdp]
```

## Shell completions

browsix uses Typer's built-in completion support. Install completions for your shell:

```bash
browsix completions bash
browsix completions zsh
browsix completions fish
browsix completions powershell
```

## Requirements

- Python >= 3.11
- Chrome or Edge browser installed on your system
- cdpwave (for CDP backend) or bidiwave (for BiDi backend)

## Verify installation

```bash
browsix --version
browsix install_check
```
