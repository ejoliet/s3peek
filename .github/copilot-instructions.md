# GitHub Copilot Instructions for s3peek

## Project overview

`s3peek` — terminal-first S3 browser for scientists and data engineers. Provides:

- Interactive TUI (Textual) for navigating S3 buckets and prefixes.
- In-place header quicklook for FITS, ASDF, Parquet, JSON via HTTP range-GETs (no full download).
- One-command pre-signed URL generation with clipboard copy.
- Plugin system (Python entry points) for custom readers, themes, CLI commands.

**Target users:** astronomers and data engineers on AWS-hosted science data.

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
- **No bare `except`** — always catch specific exception type.
- **No local state** — no database or cache files; navigation state lives in-memory per session.
- **AWS credentials pass-through** — use standard boto3 credential chain; never store credentials.
- **Range-GETs** — read minimum bytes for headers; never download entire files.

---

## Plugin architecture

s3peek extends via Python entry points — no fork required.

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

Subclass `ThemeBase` from `s3peek.themes`, register under `s3peek.themes`.

### Command plugin (`s3peek.commands`)

Expose `typer.Typer` instance, register under `s3peek.commands`.

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
2. Register in `pyproject.toml` under `[project.entry-points."s3peek.readers"]`.
3. Add fixture file under `fixtures/` for testing.
4. Add tests in `tests/test_quicklook.py` (or new file) using fixture.
5. Document reader in table in `CONTRIBUTING.md`.

---

## Error handling

- All custom exceptions in `src/s3peek/exceptions.py`.
- Raise project-specific exceptions over generic ones where possible.
- CLI commands catch exceptions, emit user-friendly `typer.echo` message, exit non-zero via `raise typer.Exit(code=1)`.

---

## Testing guidelines

- Use `moto` S3 fixtures from `tests/conftest.py` for any test exercising S3 operations.
- Use fixture files from `fixtures/` for format reader tests.
- Keep tests fast — no network calls, no large file I/O.
- Prefer `pytest.mark.parametrize` for variations of same test logic.

---

## Pull request checklist

- [ ] `make lint` passes (ruff + mypy --strict).
- [ ] `make test` passes (all existing tests green).
- [ ] New behavior covered by test.
- [ ] `CHANGELOG.md` updated with one-line entry under `Unreleased`.
- [ ] New reader added → `CONTRIBUTING.md` table updated.

---

## Decision-making guidance

Priorities in order:

1. **Correctness** — functionally correct, handles edge cases.
2. **Safety** — no credential storage, no full-file S3 downloads, no bare `except`.
3. **Minimal footprint** — small surgical changes over broad refactors.
4. **Consistency** — match style, naming, patterns in affected file.
5. **Testability** — every new public function or command coverable by `pytest` + `moto` test.

Two approaches roughly equivalent → prefer one that keeps plugin interface stable so third-party readers and themes work without changes.

---

## Context / memory anchors

Most important facts to re-establish at start of new conversation:

- Entry-point group names are `s3peek.readers`, `s3peek.themes`, `s3peek.commands` — changing them breaks all third-party plugins.
- All AWS interactions go through `src/s3peek/s3.py` (`S3Client`). Never call `boto3` directly from CLI commands or readers.
- `quicklook.py` is single dispatcher; does **not** know formats — delegates to whichever reader `plugins.load_readers()` returns.
- `moto[s3]` is only acceptable S3 mock in tests. Don't use `unittest.mock` to patch boto3 at call site.
- `mypy --strict` must pass. Every function and method needs type annotations.

---

## Implementation plan template

For non-trivial changes, structure plan as:

1. **Goal** — one sentence describing outcome.
2. **Affected modules** — list files that will change.
3. **Interface changes** — any changes to public APIs or entry-point contracts.
4. **Test plan** — which existing tests cover this, what new tests needed.
5. **Rollout** — migration steps or version-bump requirements.
6. **Open questions** — anything needing decision before implementation starts.

Share plan in PR description or comment before writing code for large features.

---

## Branching and workflow conventions

| Activity | Branch prefix | Example |
|---|---|---|
| New feature | `feat/` | `feat/hdf5-reader` |
| Bug fix | `fix/` | `fix/presign-expiry-default` |
| Chore / maintenance | `chore/` | `chore/bump-ruff` |
| Documentation | `docs/` | `docs/update-contributing` |

- All PRs target `main`.
- Squash-merge preferred for small changes; merge commits for features with meaningful history.
- Tag format: `vMAJOR.MINOR.PATCH` (semver). `release.yml` workflow triggers on tags matching `v*`.

---

## Peer review QA checklist

Reviewers and Copilot verify:

- [ ] No new `boto3` calls outside `src/s3peek/s3.py`.
- [ ] No credentials, tokens, or secrets in diff.
- [ ] Range-GET byte limits respected — no reader fetches more than `config.max_range_get_bytes`.
- [ ] New exceptions subclass base class in `exceptions.py`, not raw `Exception`.
- [ ] Public functions have type annotations and docstrings (one-liner minimum).
- [ ] Third-party plugin interface (`BaseReader`, `ThemeBase`, `typer.Typer`) unchanged unless PR is explicit API revision.
- [ ] `moto` used for all S3 interactions in tests — `mock_aws()` context manager from `moto` (see `tests/conftest.py`); no live AWS calls.
- [ ] `CHANGELOG.md` has one-line entry under `Unreleased`.

---

## Security guidelines

- **No credential storage** — never write AWS keys, tokens, or secrets to disk, committed env files, or log output.
- **Pre-signed URL expiry** — default `presign_expiry_seconds = 3600`; ceiling max 7 days (AWS maximum).
- **Input validation** — S3 URIs from user must be parsed and validated before use; reject malformed `s3://` URIs early (missing bucket name, invalid key characters, wrong scheme) with clear error.
- **Dependency pinning** — minimum versions pinned in `pyproject.toml`; avoid deps with known CVEs (check GitHub Advisory Database before adding).
- **No shell injection** — never pass user-supplied strings to `subprocess`, `os.system`, or `shell=True`.
- **Clipboard output only** — pre-signed URLs written to clipboard and/or stdout. Never logged to file.

---

## Cloud / AWS engineer context

- **Credential chain** — s3peek relies on boto3 default credential chain: `~/.aws/credentials`, env vars (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`), EC2 instance profiles, ECS task roles. No custom auth logic.
- **Region** — `aws_region` in `config.toml` or `AWS_DEFAULT_REGION` env var. If unset, boto3 uses own default (usually `us-east-1`).
- **IAM minimum permissions:**
  - `s3:ListBucket` on target bucket.
  - `s3:GetObject` on target prefix.
  - `s3:GetObjectAttributes` for stat operations.
  - No write permissions required or used.
- **VPC / private buckets** — works transparently with VPC endpoint for S3 or appropriate routing; no special s3peek config needed.
- **Moto mock** — all tests use `moto[s3]` with `mock_aws()` context manager (from `moto import mock_aws`). Fixture in `tests/conftest.py` creates fresh bucket per test. Real AWS never contacted during `make test`.
- **Pre-signed URLs** — generated via `boto3` `generate_presigned_url`; expiry defaults to 3600 s, configurable. URL signed with whichever credentials boto3 resolved at runtime.