# Developer Guide

## Prerequisites

- Python 3.11+
- One of: `uv` (recommended), `pip` + `venv`, or `conda`

---

## Setup with uv (recommended)

[uv](https://github.com/astral-sh/uv) is a fast all-in-one Python package manager.

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

To add optional extras (e.g. Firefly or Roman support):

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

Copy `.env.example` to `.env` and fill in as needed. Variables are never required
for the test suite (moto mocks AWS). They are only needed when pointing at a real
S3 bucket or a live Firefly server.

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
| `S3PEEK_CONFIG` | Path to a custom `config.toml` (default: `~/.config/s3peek/config.toml`) |

---

## Config file

`~/.config/s3peek/config.toml` (or the path in `S3PEEK_CONFIG`):

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

1. Fork the repo and create a branch: `git checkout -b feat/my-feature`
2. Make changes, ensure `make lint && make test` passes
3. Open a pull request against `main`
