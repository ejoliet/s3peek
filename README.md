# s3peek

> Terminal S3 browser — instant header quicklook for FITS, ASDF, Parquet, JSON via HTTP Range-GET. No full downloads.

[![CI](https://img.shields.io/github/actions/workflow/status/ejoliet/s3peek/ci.yml?branch=main)](https://github.com/ejoliet/s3peek/actions)
[![PyPI](https://img.shields.io/pypi/v/s3peek)](https://pypi.org/project/s3peek/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)

---

## Install

```bash
pip install s3peek
# or (isolated env, preferred)
uv tool install s3peek
```

**Requires:** Python 3.11+, AWS credentials (`~/.aws`, env vars, or instance profile), IAM `s3:ListBucket` + `s3:GetObject`.

<details>
<summary>Other install methods</summary>

**Homebrew (macOS / Linux):**
```bash
brew tap ejoliet/tap
brew install s3peek
```

**Standalone binary (no Python needed):**
```bash
curl -fsSL https://github.com/ejoliet/s3peek/releases/latest/download/s3peek-linux-x86_64.tar.gz \
  | tar -xz -C ~/.local/bin
chmod +x ~/.local/bin/s3peek
```

</details>

---

## Quick Start

```bash
# Interactive TUI bucket browser
s3peek browse s3://my-bucket/

# Print header / schema to stdout
s3peek peek s3://my-bucket/data/obs001.fits

# Full header extraction (streams via Range-GET — no full download)
s3peek peek s3://my-bucket/data/obs001.fits --deep

# Pre-signed URL → clipboard
s3peek share s3://my-bucket/data/obs001.fits

# List objects under a prefix
s3peek ls s3://my-bucket/data/

# Storage usage summary
s3peek du s3://my-bucket/data/
```

**TUI keybindings:** `↑↓` navigate · `Enter` descend · `Backspace` up · `p` peek · `d` deep-peek · `s` share · `c` copy URI · `f` Firefly · `q` quit

---

## Supported Formats

| Format | Extensions | Fast path (default) | `--deep` |
|--------|-----------|---------------------|----------|
| FITS | `.fits` `.fit` `.fz` | First HDU headers via Range-GET | Full multi-HDU via `astropy` |
| ASDF | `.asdf` | YAML tree summary via Range-GET | Full tree via `asdf` |
| Parquet | `.parquet` `.pq` | Schema + row count from footer | — |
| JSON | `.json` | Top-level keys / array length | — |

---

## Configuration

Via env var or `~/.config/s3peek/config.toml`. Run `s3peek config` to inspect current values.

| Env var | Description |
|---------|-------------|
| `AWS_DEFAULT_REGION` | AWS region (passed to boto3) |
| `FIREFLY_URL` | Firefly server, e.g. `http://localhost:8080/firefly` |
| `FIREFLY_CHANNEL` | Firefly browser channel override |
| `S3PEEK_CONFIG` | Config file path (default: `~/.config/s3peek/config.toml`) |

See [`docs/config.toml.sample`](docs/config.toml.sample) for all options with comments.

---

## Optional Extras

```bash
pip install s3peek[qr]       # --qr flag on share (QR code in terminal)
pip install s3peek[astro]    # asdf-astropy for Roman/HST pipeline files
pip install s3peek[firefly]  # Firefly visualization server integration
pip install s3peek[roman]    # Roman datamodels support
```

---

## IAM Minimum Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:ListBucket", "s3:GetObject", "s3:GetObjectAttributes"],
    "Resource": ["arn:aws:s3:::YOUR_BUCKET", "arn:aws:s3:::YOUR_BUCKET/*"]
  }]
}
```

s3peek is **read-only by design** — no `PutObject`, `DeleteObject`, or any mutating operation.

---

## Docs

- [Architecture & API reference](docs/agent-context/architecture.md)
- [Releasing (PyPI / Homebrew / binaries)](docs/releasing.md)
- [Contributing & plugin development](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## License

MIT
