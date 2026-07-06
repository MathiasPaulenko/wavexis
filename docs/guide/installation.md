# Installation

## pip

```bash
pip install wavexis[cdp]
```

To use the WebDriver BiDi backend instead:

```bash
pip install wavexis[bidi]
```

Both backends:

```bash
pip install wavexis[cdp,bidi]
```

## pipx

For isolated installation:

```bash
pipx install wavexis[cdp]
```

## Shell completions

wavexis uses Typer's built-in completion support. Install completions for your shell:

```bash
wavexis completions bash
wavexis completions zsh
wavexis completions fish
wavexis completions powershell
```

## Requirements

- Python >= 3.11
- Chrome or Edge browser installed on your system
- cdpwave (for CDP backend) or bidiwave (for BiDi backend)

## Verify installation

```bash
wavexis --version
wavexis install_check
```
