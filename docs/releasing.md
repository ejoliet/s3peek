# Releasing s3peek

Covers PyPI publish, Homebrew formula update, and standalone binary release.

---

## Prerequisites

```bash
uv tool install build twine
gh auth login   # GitHub CLI for release assets
```

Ensure `~/.pypirc` or `TWINE_PASSWORD` env var is set (API token from pypi.org).

---

## PyPI

### 1. Bump version

Edit `pyproject.toml`:
```toml
[project]
version = "X.Y.Z"
```

Update `CHANGELOG.md` — move `[Unreleased]` entries under `[X.Y.Z]`.

### 2. Build

```bash
uv run python -m build   # produces dist/s3peek-X.Y.Z.tar.gz and .whl
```

### 3. Publish

```bash
# Test PyPI first (optional but recommended)
twine upload --repository testpypi dist/*

# Production
twine upload dist/*
```

Verify: `pip install s3peek==X.Y.Z` in a fresh venv.

### 4. Tag and push

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

CI (`release.yml`) triggers on tag push and runs the publish automatically if configured.

---

## Homebrew

The formula lives at `Formula/s3peek.rb`. Update it after the PyPI tarball is live.

### Manual bump

```bash
# Get SHA256 of the source tarball from PyPI
curl -sL https://files.pythonhosted.org/packages/.../s3peek-X.Y.Z.tar.gz | sha256sum

# Update formula
make brew-bump VERSION=X.Y.Z SHA256=<sha256>
```

Or edit `Formula/s3peek.rb` directly:
```ruby
url "https://files.pythonhosted.org/packages/.../s3peek-X.Y.Z.tar.gz"
sha256 "<sha256>"
version "X.Y.Z"
```

### Test locally

```bash
brew install --build-from-source Formula/s3peek.rb
brew test s3peek
brew audit --strict Formula/s3peek.rb
```

### Push to tap

The formula is hosted in the `ejoliet/homebrew-tap` repo. After testing:

```bash
# If using a separate tap repo:
cp Formula/s3peek.rb ../homebrew-tap/Formula/s3peek.rb
cd ../homebrew-tap && git add -A && git commit -m "s3peek X.Y.Z" && git push
```

Users install via:
```bash
brew tap ejoliet/tap
brew install s3peek
```

---

## Standalone Binary (curl install)

Standalone binaries are built via PyInstaller in CI and uploaded to GitHub Releases.

### Build locally

```bash
make build-binary        # outputs dist/s3peek (macOS) or dist/s3peek-linux
```

Requires PyInstaller:
```bash
uv tool install pyinstaller
```

### CI build (GitHub Actions)

`release.yml` runs a matrix build on `macos-latest` + `ubuntu-latest`, then uploads:

- `s3peek-macos-x86_64`
- `s3peek-linux-x86_64.tar.gz`

as GitHub Release assets on tag push.

### curl install (Linux)

Once the binary is attached to the GitHub Release:

```bash
curl -fsSL https://github.com/ejoliet/s3peek/releases/latest/download/s3peek-linux-x86_64.tar.gz \
  | tar -xz -C ~/.local/bin
chmod +x ~/.local/bin/s3peek
s3peek version
```

### curl install (macOS)

```bash
curl -fsSL https://github.com/ejoliet/s3peek/releases/latest/download/s3peek-macos-x86_64 \
  -o ~/.local/bin/s3peek
chmod +x ~/.local/bin/s3peek
s3peek version
```

> Note: macOS Gatekeeper may block unsigned binaries. Users can bypass with:
> `xattr -dr com.apple.quarantine ~/.local/bin/s3peek`
> Signing with an Apple Developer certificate is a future improvement.

---

## Release Checklist

- [ ] Version bumped in `pyproject.toml`
- [ ] `CHANGELOG.md` updated (`[Unreleased]` → `[X.Y.Z]` with date)
- [ ] `make test` passes (`uv run pytest -q`)
- [ ] `make lint` passes (`uv run ruff check`)
- [ ] PyPI publish: `twine upload dist/*`
- [ ] Tag pushed: `git tag vX.Y.Z && git push origin vX.Y.Z`
- [ ] Homebrew formula updated and pushed to tap
- [ ] GitHub Release created with binary assets attached
- [ ] `pip install s3peek==X.Y.Z` verified in clean venv
- [ ] `brew install s3peek` verified

---

## Future: Automated Release Pipeline

`release.yml` goal (when fully wired):

1. Tag `vX.Y.Z` pushed → workflow triggers
2. Build matrix: sdist + wheel + binaries (macOS + Linux)
3. `twine upload` to PyPI (via `PYPI_TOKEN` secret)
4. Create GitHub Release, upload binary assets
5. Auto-bump Homebrew formula in `ejoliet/homebrew-tap`

Items not yet implemented: binary signing (macOS notarization), Windows binary, `brew bump-formula-pr` automation.
