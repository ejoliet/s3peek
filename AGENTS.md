# AGENTS.md

## Cursor Cloud specific instructions

This is a pure Python 3.11+ project (s3peek — terminal-first S3 browser). No Node.js, Docker, or databases are required.

### Quick reference

| Action | Command |
|--------|---------|
| Install deps | `pip install -e ".[dev]"` |
| Run tests | `python3 -m pytest` |
| Run lint | `ruff check src tests && python3 -m mypy src` |
| Run CLI | `s3peek version`, `s3peek --help` |

### Caveats

- The `Makefile` uses bare `python` which may not exist on some systems. Use `python3 -m pytest` directly instead of `make test`.
- `~/.local/bin` must be in `PATH` for the `s3peek` entry point to work after `pip install -e ".[dev]"`. This is already configured in `~/.bashrc` for Cloud Agent VMs.
- Tests use `moto` to mock AWS — no real AWS credentials are needed to run the test suite.
- Pre-existing lint issues exist in the repo (3 ruff E501 line-too-long errors in `cli.py`, and mypy errors from untyped third-party libraries). These are not blockers for development.
- The `s3peek browse` command launches a Textual TUI that requires a terminal — it cannot be tested headlessly. Use the Typer `CliRunner` for CLI integration tests instead.
