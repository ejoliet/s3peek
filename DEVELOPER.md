# Developer Guide

## Prerequisites

- Python 3.11+
- One of: `uv` (recommended), `pip` + `venv`, or `conda`

### What's in each install extra

| Extra | Packages installed |
|-------|--------------------|
| _(none)_ | Runtime only: `typer`, `textual`, `boto3`, `astropy`, `asdf`, `pyarrow`, `pyperclip`, `pydantic` |
| `[dev]` | Everything above **plus** `pytest`, `pytest-cov`, `moto[s3]`, `ruff`, `mypy`, `boto3-stubs[s3]` |
| `[firefly]` | `firefly_client>=3.4.0` (PyPI) — [caltech-ipac/firefly_client](https://github.com/caltech-ipac/firefly_client) |
| `[roman]` | `roman_datamodels>=2.0,<3` |
| `[astro]` | `asdf-astropy` |
| `[qr]` | `qrcode` |

> `moto[s3]` = AWS mock lib, intercepts all `boto3` calls -> tests never touch real AWS.
> `pytest` + `pytest-cov` = test runner + coverage.

---

## Setup with uv (recommended)

[uv](https://github.com/astral-sh/uv) = fast all-in-one Python pkg manager.

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and enter the repo
git clone https://github.com/ejoliet/s3peek.git
cd s3peek

# Create a virtual environment and install all dev dependencies
uv venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Verify
s3peek version
```

Optional extras:

```bash
uv pip install -e ".[dev,firefly]"
uv pip install -e ".[dev,roman]"
uv pip install -e ".[dev,firefly,roman]"
```

---

## Setup with venv + pip

```bash
git clone https://github.com/ejoliet/s3peek.git
cd s3peek

python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -e ".[dev]"

# Verify
s3peek version
```

---

## Setup with conda / mamba

```bash
git clone https://github.com/ejoliet/s3peek.git
cd s3peek

conda create -n s3peek python=3.11
conda activate s3peek

pip install -e ".[dev]"

# Verify
s3peek version
```

---

## Daily workflow

```bash
# Lint (ruff + mypy)
make lint

# Run tests
make test

# Run tests with coverage report
make test-cov

# Run a single test file
python -m pytest tests/test_plugins.py -v

# Run only non-skipped tests
python -m pytest -v --ignore=tests/test_s3.py
```

---

## Environment variables

Copy `.env.example` to `.env`, fill as needed. Vars never required for tests (`moto` mocks AWS). Only needed for real S3 bucket or live Firefly server.

```bash
cp .env.example .env
# edit .env with your values
```

| Variable | Description |
|----------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS credentials (or use `~/.aws/credentials` / IAM role) |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `AWS_DEFAULT_REGION` | Default region, e.g. `us-east-1` |
| `FIREFLY_URL` | Firefly server URL, e.g. `http://localhost:8080/firefly` |
| `FIREFLY_CHANNEL` | Firefly browser channel (auto-generated if unset) |
| `S3PEEK_CONFIG` | Path to custom `config.toml` (default: `~/.config/s3peek/config.toml`) |

---

## Config file

`~/.config/s3peek/config.toml` (or path in `S3PEEK_CONFIG`):

```toml
theme = "dark"                  # dark | light | any installed theme plugin
aws_profile = "my-profile"      # optional, overrides default AWS profile
aws_region = "us-west-2"
presign_expiry_seconds = 3600
max_range_get_bytes = 65536

firefly_url = "http://localhost:8080/firefly"
firefly_channel = "my-session"
```

---

## Project layout

```
s3peek/
├── src/s3peek/
│   ├── __init__.py         # __version__
│   ├── cli.py              # Typer entry point; mounts plugin commands
│   ├── quicklook.py        # Format dispatcher (delegates to readers via plugins)
│   ├── plugins.py          # Entry-point discovery: load_readers/themes/commands
│   ├── readers/            # Built-in format readers (FITS, ASDF, Parquet, JSON)
│   ├── themes/             # Built-in TUI themes (dark, light)
│   ├── s3.py               # S3Client abstraction over boto3
│   ├── presign.py          # Pre-signed URL generation
│   ├── browser.py          # Textual TUI (S3Browser app)
│   ├── firefly.py          # FireflyConnector — send objects to Firefly
│   ├── config.py           # Pydantic Config model + TOML loader
│   └── exceptions.py       # All s3peek exception classes
├── tests/                  # pytest suite (moto for AWS mocking)
├── fixtures/               # Static test data files
├── CONTRIBUTING.md         # How to write reader, theme, and command plugins
├── DEVELOPER.md            # This file
└── pyproject.toml          # Build config, deps, entry points, ruff/mypy config
```

---

## Writing and testing a plugin locally

```bash
# Create a minimal plugin package in a sibling directory
mkdir -p ../s3peek-myplugin/s3peek_myplugin
# ... implement BaseReader (see CONTRIBUTING.md) ...

# Install it into the same venv in editable mode
pip install -e ../s3peek-myplugin

# s3peek discovers it immediately — no restart needed
python -m pytest tests/test_plugins.py -v
```

---

## Submitting changes

1. Fork repo, create branch: `git checkout -b feat/my-feature`
2. Make changes, ensure `make lint && make test` passes
3. Open PR against `main`

---

## Building and publishing to PyPI

### Manual release (local)

```bash
# Install build tools
pip install build twine

# Build sdist + wheel into dist/
python -m build

# Inspect what will be uploaded
twine check dist/*

# Upload to TestPyPI first (recommended before a real release)
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ s3peek

# Upload to PyPI
twine upload dist/*
```

With `uv` (no separate `twine` needed):

```bash
uv build                        # creates dist/
uv publish --token $PYPI_TOKEN  # or configure keyring
```

### Automated release via GitHub Actions

`.github/workflows/release.yml` triggers on tags matching `v*`, publishes to PyPI via **OIDC trusted publishing** — no stored API tokens needed.

**One-time setup on PyPI:**

1. Go to PyPI project -> *Manage* -> *Publishing*
2. Add trusted publisher:
   - Owner: `ejoliet`
   - Repository: `s3peek`
   - Workflow: `release.yml`
   - Environment: `pypi`
3. Create `pypi` environment in GitHub repo settings (*Settings → Environments*)

**Cutting a release:**

```bash
# Bump version in pyproject.toml and src/s3peek/__init__.py, then:
git add pyproject.toml src/s3peek/__init__.py CHANGELOG.md
git commit -m "chore: release v0.2.0"
git tag v0.2.0
git push origin main --tags
```

Workflow builds pkg, calls `pypa/gh-action-pypi-publish` with OIDC — no `PYPI_TOKEN` secret once trusted publishing configured.