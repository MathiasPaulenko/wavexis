# Contributing to browsix

Thank you for your interest in contributing to browsix! This document outlines
the process for contributing bug reports, feature requests, code changes, and
documentation improvements.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- A Chromium-based browser (Chrome, Edge, Brave, or Chromium)
- Git

### Development Setup

```bash
git clone https://github.com/MathiasPaulenko/browsix.git
cd browsix
pip install -e ".[cdp,dev]"
```

### Running Tests

```bash
# Unit tests (no browser required)
pytest tests/unit/ -v --cov=browsix --cov-report=term-missing

# Linting and type checking
ruff check .
mypy browsix/

# Spike test (requires Chrome installed)
python spike.py
```

### Project Structure

```
browsix/
├── browsix/              # Source code
│   ├── cli/              # Typer CLI commands
│   ├── backend/          # Backend abstraction (CDPBackend, BiDiBackend)
│   ├── actions/          # Action classes (ScreenshotAction, etc.)
│   ├── config.py         # Dataclasses for params and presets
│   ├── auth.py           # Auth context loader
│   ├── output.py         # Output helpers (file, stdout, JSON)
│   └── exceptions.py     # Custom exceptions
├── tests/                # Test suite
│   ├── unit/             # Unit tests with mocks
│   └── integration/      # Integration tests (require Chrome)
├── docs/                 # Documentation
└── pyproject.toml        # Project configuration
```

## How to Contribute

### Reporting Bugs

Before creating a bug report, check existing issues to avoid duplicates. When
creating a bug report, use the **Bug Report** issue template and include:

1. A clear description of the problem
2. Steps to reproduce the issue
3. Expected vs actual behavior
4. browsix version, Python version, OS, and browser version
5. Minimal command example (if applicable)

### Suggesting Features

Use the **Feature Request** issue template. Describe:

1. The problem your feature would solve
2. The proposed solution
3. Alternatives you've considered

### Pull Requests

1. **Fork** the repository and create your branch from `main`
2. **Write tests** for your changes — unit tests are required for new features
3. **Ensure all checks pass**:
   ```bash
   ruff check .
   mypy browsix/
   pytest tests/unit/ -v
   ```
4. **Use conventional commit messages**:
   - `feat:` new feature
   - `fix:` bug fix
   - `docs:` documentation only
   - `refactor:` code change that neither fixes a bug nor adds a feature
   - `test:` adding or correcting tests
   - `chore:` tooling, dependencies, config
5. **Keep PRs focused** — one feature or fix per PR
6. **Update documentation** if your change affects the public API

### Code Style

- Follow PEP 8 (enforced by ruff, line-length=100)
- Use type hints for all function parameters and return types
- Write docstrings in Google style for all public methods
- Prefer small, single-responsibility functions
- No comments that don't add value — the code should be self-documenting

## Release Process

Releases are managed by the maintainer:

1. Version bump in `pyproject.toml` and `browsix/__init__.py`
2. Create annotated git tag (`vX.Y.Z`)
3. GitHub Actions builds and publishes to PyPI automatically

Versioning follows [Semantic Versioning](https://semver.org/):
- **MAJOR**: breaking API changes
- **MINOR**: new features, backwards compatible
- **PATCH**: bug fixes, backwards compatible

## Questions?

Feel free to open a **Question** issue or reach out at
**mathias.paulenko@outlook.com**.

By participating in this project, you agree to abide by the
[Code of Conduct](CODE_OF_CONDUCT.md).
