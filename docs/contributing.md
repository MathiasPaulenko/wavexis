# Contributing

## Setup

```bash
git clone https://github.com/MathiasPaulenko/browsix.git
cd browsix
pip install -e ".[dev,cdp]"
```

## Running tests

```bash
# Unit tests
pytest tests/unit/ -m unit -v

# Integration tests (requires Chrome)
pytest tests/integration/ -m integration -v

# All tests
pytest tests/ -v
```

## Code style

- **Linter:** ruff
- **Type checker:** mypy (strict mode)
- **Line length:** 100 chars
- **Python:** >= 3.11

```bash
ruff check .
mypy browsix/ --ignore-missing-imports
```

## PR process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `pytest tests/ -v`
5. Run linters: `ruff check . && mypy browsix/ --ignore-missing-imports`
6. Commit with conventional commits: `feat: add new command`, `fix: resolve timeout bug`
7. Push and open a PR

## Project structure

```
browsix/
  browsix/
    actions/     # Action classes (screenshot, pdf, eval, etc.)
    backend/     # Backend implementations (cdp, bidi, manager)
    cli/         # Typer CLI app
    config.py    # Dataclasses and presets
    exceptions.py
    multi.py     # YAML multi-action parser
    output.py    # Output helpers
  tests/
    unit/        # Unit tests (mocked)
    integration/ # Integration tests (real Chrome)
  docs/          # mkdocs documentation
```

## Releasing

Releases are automated via GitHub Actions:

1. Tag a release: `git tag v1.0.0`
2. Push the tag: `git push origin v1.0.0`
3. CI builds the package, publishes to PyPI, and deploys docs to GitHub Pages
