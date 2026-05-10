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
- [ ] New behavior is covered by a test.
- [ ] `CHANGELOG.md` updated with a one-line entry under `Unreleased`.
- [ ] If a new reader is added, the `CONTRIBUTING.md` table is updated.

---

## Decision-making guidance

When suggesting or generating code, apply these priorities in order:

1. **Correctness** — the change must be functionally correct and handle edge cases.
2. **Safety** — never introduce credential storage, full-file S3 downloads, or bare `except` blocks.
3. **Minimal footprint** — prefer small, surgical changes over broad refactors.
4. **Consistency** — match the style, naming, and patterns already in the affected file.
5. **Testability** — every new public function or command should be coverable by a `pytest` + `moto` test.

If two approaches are roughly equivalent, prefer the one that keeps the plugin interface stable so third-party readers and themes continue to work without changes.

---

## Context / memory anchors

Because Copilot context resets between sessions, the following are the most important facts to re-establish at the start of any new conversation about this codebase:

- The entry-point group names are `s3peek.readers`, `s3peek.themes`, and `s3peek.commands` — changing them would be a breaking change for all third-party plugins.
- All AWS interactions go through `src/s3peek/s3.py` (`S3Client`). Never call `boto3` directly from CLI commands or readers.
- `quicklook.py` is the single dispatcher; it does **not** know about formats — it delegates to whichever reader `plugins.load_readers()` returns.
- `moto[s3]` is the only acceptable mock for S3 in tests. Do not use `unittest.mock` to patch boto3 at the call site.
- `mypy --strict` must pass. Every function and method needs type annotations.

---

## Implementation plan template

When planning a non-trivial change, structure the plan as:

1. **Goal** — one sentence describing the outcome.
2. **Affected modules** — list files that will change.
3. **Interface changes** — describe any changes to public APIs or entry-point contracts.
4. **Test plan** — which existing tests cover this, and what new tests are needed.
5. **Rollout** — any migration steps or version-bump requirements.
6. **Open questions** — anything that needs a decision before implementation starts.

Share the plan in the PR description or as a comment before writing code for large features.

---

## Branching and workflow conventions

| Activity | Branch prefix | Example |
|---|---|---|
| New feature | `feat/` | `feat/hdf5-reader` |
| Bug fix | `fix/` | `fix/presign-expiry-default` |
| Chore / maintenance | `chore/` | `chore/bump-ruff` |
| Documentation | `docs/` | `docs/update-contributing` |

- All PRs target `main`.
- Squash-merge is preferred for small changes; merge commits for features with meaningful history.
- Tag format: `vMAJOR.MINOR.PATCH` (semver). The `release.yml` workflow triggers on tags matching `v*`.

---

## Peer review QA checklist

Reviewers and Copilot should verify:

- [ ] No new `boto3` calls outside `src/s3peek/s3.py`.
- [ ] No credentials, tokens, or secrets appear anywhere in the diff.
- [ ] Range-GET byte limits respected — no reader fetches more than `config.max_range_get_bytes`.
- [ ] New exceptions are subclasses of the base class in `exceptions.py`, not raw `Exception`.
- [ ] Public functions have type annotations and docstrings (one-liner minimum).
- [ ] Third-party plugin interface (`BaseReader`, `ThemeBase`, `typer.Typer`) is unchanged unless the PR is explicitly an API revision.
- [ ] `moto` is used for all S3 interactions in tests — no live AWS calls.
- [ ] `CHANGELOG.md` has a one-line entry under `Unreleased`.

---

## Security guidelines

- **No credential storage** — never write AWS keys, tokens, or secrets to disk, environment files committed to the repo, or log output.
- **Pre-signed URL expiry** — default is `presign_expiry_seconds = 3600`; do not raise the ceiling above 7 days (AWS maximum).
- **Input validation** — S3 URIs from the user must be parsed and validated before use; reject malformed `s3://` URIs early with a clear error message.
- **Dependency pinning** — minimum versions are pinned in `pyproject.toml`; avoid adding dependencies with known CVEs (check the GitHub Advisory Database before adding).
- **No shell injection** — never pass user-supplied strings to `subprocess`, `os.system`, or shell=True invocations.
- **Clipboard output only** — pre-signed URLs are written to the clipboard and/or stdout. They are never logged to a file.

---

## Cloud / AWS engineer context

- **Credential chain** — s3peek relies entirely on the boto3 default credential chain: `~/.aws/credentials`, environment variables (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`), EC2 instance profiles, and ECS task roles. No custom auth logic.
- **Region** — `aws_region` in `config.toml` or `AWS_DEFAULT_REGION` env var. If unset, boto3 uses its own default (usually `us-east-1`).
- **IAM minimum permissions required:**
  - `s3:ListBucket` on the target bucket.
  - `s3:GetObject` on the target prefix.
  - `s3:GetObjectAttributes` for stat operations.
  - No write permissions are required or used.
- **VPC / private buckets** — works transparently when the environment has a VPC endpoint for S3 or appropriate routing; no special configuration needed in s3peek.
- **Moto mock** — all tests use `moto[s3]` with `@mock_aws`. The fixture in `tests/conftest.py` creates a fresh bucket per test. Real AWS is never contacted during `make test`.
- **Pre-signed URLs** — generated via `boto3` `generate_presigned_url`; expiry defaults to 3600 s and is configurable. The URL is signed with whichever credentials boto3 resolved at runtime.
