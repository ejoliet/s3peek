# GitHub Copilot Instructions for s3peek

## Project overview

`s3peek` is a terminal-first S3 browser for scientists and data engineers. It provides:

- An interactive TUI (Textual) for navigating S3 buckets and prefixes.
- In-place header quicklook for FITS, ASDF, Parquet, and JSON files via HTTP range-GETs (no full download).
- One-command pre-signed URL generation with clipboard copy.
- A plugin system (Python entry points) for custom readers, themes, and CLI commands.

**Target users:** astronomers and data engineers working with AWS-hosted science data.

---

## Tech stack

| Layer | Library |
|---|---|
| CLI | `typer` |
| TUI | `textual` |
| AWS | `boto3` |
| Astronomy formats | `astropy`, `asdf` |
| Columnar data | `pyarrow` |
| Config | `pydantic` v2 |
| Clipboard | `pyperclip` |
| Testing | `pytest`, `moto[s3]` |
| Linting | `ruff` |
| Type checking | `mypy` (strict) |

---

## Repository layout

```
src/s3peek/
├── cli.py          # Typer entry point; mounts plugin commands
├── browser.py      # Textual TUI (S3Browser app)
├── quicklook.py    # Format dispatcher — delegates to reader plugins
├── plugins.py      # Entry-point discovery: load_readers / themes / commands
├── readers/        # Built-in format readers (FITS, ASDF, Parquet, JSON)
├── themes/         # Built-in TUI themes (dark, light)
├── s3.py           # S3Client abstraction over boto3
├── presign.py      # Pre-signed URL generation
├── config.py       # Pydantic Config model + TOML loader
└── exceptions.py   # All s3peek exception classes
tests/              # pytest suite (moto for AWS mocking — never touches real AWS)
fixtures/           # Static test data files (sample.fits, .asdf, .parquet, .json)
```

---

## Coding conventions

- **Python 3.11+** — use modern syntax (`match`, `TypeAlias`, `Self`, etc.).
- **Line length:** 100 characters (`ruff` enforced).
- **Imports:** isort-style, ruff-managed (`I` rules). Standard library → third-party → local.
- **Type annotations:** required on all public functions and methods; `mypy --strict` must pass.
- **No bare `except`** — always catch a specific exception type.
- **No local state** — no database or cache files; all navigation state lives in-memory per session.
- **AWS credentials pass-through** — use the standard boto3 credential chain; never store credentials.
- **Range-GETs** — read only the minimum bytes needed for headers; never download entire files.

---

## Plugin architecture

s3peek is extended via Python entry points — no fork required.

### Reader plugin (`s3peek.readers`)

Implement `BaseReader` from `s3peek.readers`:

```python
class MyReader:
    extensions = (".myext",)
    priority = 10  # higher = tried first; >10 overrides built-ins

    def can_read(self, key: str, first_bytes: bytes) -> bool: ...
    def read(self, data: bytes, *, max_headers: int = 1) -> HeaderResult: ...
```

Register in `pyproject.toml`:
```toml
[project.entry-points."s3peek.readers"]
myformat = "my_package.reader:MyReader"
```

### Theme plugin (`s3peek.themes`)

Subclass `ThemeBase` from `s3peek.themes` and register under `s3peek.themes`.

### Command plugin (`s3peek.commands`)

Expose a `typer.Typer` instance and register under `s3peek.commands`.

---

## Development workflow

```bash
# Lint (ruff + mypy)
make lint

# Run tests (moto mocks all AWS calls)
make test

# Run tests with coverage
make test-cov

# Run a single test file
python -m pytest tests/test_plugins.py -v
```

Tests **never** touch real AWS — `moto[s3]` intercepts all boto3 calls.

---

## Adding a new built-in reader

1. Create `src/s3peek/readers/<format>.py` implementing `BaseReader`.
2. Register it in `pyproject.toml` under `[project.entry-points."s3peek.readers"]`.
3. Add a fixture file under `fixtures/` for testing.
4. Add tests in `tests/test_quicklook.py` (or a new file) using the fixture.
5. Document the reader in the table in `CONTRIBUTING.md`.

---

## Error handling

- All custom exceptions live in `src/s3peek/exceptions.py`.
- Raise project-specific exceptions rather than generic ones where possible.
- CLI commands should catch exceptions and emit a user-friendly `typer.echo` message, then exit with a non-zero code via `raise typer.Exit(code=1)`.

---

## Testing guidelines

- Use `moto` S3 fixtures from `tests/conftest.py` for any test that exercises S3 operations.
- Use fixture files from `fixtures/` for format reader tests.
- Keep tests fast — avoid network calls and avoid large file I/O.
- Prefer `pytest.mark.parametrize` for variations of the same test logic.

---

## Pull request checklist

- [ ] `make lint` passes (ruff + mypy --strict).
- [ ] `make test` passes (all existing tests green).
- [ ] New behaviour is covered by a test.
- [ ] `CHANGELOG.md` updated with a one-line entry under `Unreleased`.
- [ ] If a new reader is added, the `CONTRIBUTING.md` table is updated.
