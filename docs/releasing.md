# Releasing s3peek

Covers PyPI publish, Homebrew formula update, and standalone binary release.

---

## Prerequisites

```bash
uv tool install build twine
gh auth login   # GitHub CLI for release assets
```

> **API token no longer required.** `release.yml` uses PyPI Trusted Publishing (OIDC) — no
> `~/.pypirc` or `TWINE_PASSWORD` needed for the automated publish path. See
> [PyPI Trusted Publisher](#pypi-trusted-publisher-oidc-setup) below.

---

## PyPI

### 1. Bump version

Edit `pyproject.toml`:
```toml
[project]
version = "X.Y.Z"
```

Update `CHANGELOG.md` — move `[Unreleased]` entries under `[X.Y.Z]`.

### 2. Build (local verification)

```bash
uv run python -m build   # produces dist/s3peek-X.Y.Z.tar.gz and .whl
uv run twine check dist/*
```

### 3. Publish via GitHub Release (automated — preferred)

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

Then on GitHub: **Releases → Draft a new release → choose tag `vX.Y.Z` → Publish release**.

`release.yml` triggers on `release: published`, runs build + TestPyPI dry-run (non-blocking)
+ PyPI publish via OIDC. No secrets required — see [Trusted Publisher setup](#pypi-trusted-publisher-oidc-setup).

### 4. Verify

```bash
pip install s3peek==X.Y.Z   # in a fresh venv
```

### Manual publish (fallback only)

If the automated workflow fails and a manual push is needed:

```bash
# Test PyPI first
twine upload --repository testpypi dist/*

# Production (requires TWINE_PASSWORD or ~/.pypirc as fallback)
twine upload dist/*
```

---

## PyPI Trusted Publisher (OIDC Setup)

`release.yml` uses [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) — OIDC
token exchange, no stored API token in repo secrets.

### One-time setup (first release only)

**Step 1 — PyPI production**

1. Go to pypi.org → your projects → **s3peek** → Settings → Publishing.
2. Click **"Add a pending publisher"** and fill in **exact** values (mismatches cause 403):

   | Field | Value |
   |-------|-------|
   | Owner | `ejoliet` |
   | Repository | `s3peek` |
   | Workflow filename | `release.yml` ← the **filename**, not the `name:` field |
   | Environment name | `pypi` ← must byte-match `environment: pypi` in the job |

**Step 2 — TestPyPI (dry-run lane)**

Repeat Step 1 on test.pypi.org with **Environment name = `testpypi`**.

**Step 3 — GitHub Environments**

In the `ejoliet/s3peek` repo: Settings → Environments → create two environments:
- `pypi`
- `testpypi`

Optional hardening: add required reviewers or tag/branch protection rules on `pypi`.

### Workflow behavior

| Job | Trigger | Blocking? |
|-----|---------|-----------|
| `build` | every release | yes — `publish-pypi` needs it |
| `publish-testpypi` | every release | **no** — `continue-on-error: true`; prod publish does not depend on it |
| `publish-pypi` | every release | yes — fails hard on error |

### Version-burn rollback

> **PyPI filenames are immutable.** Once `s3peek-X.Y.Z-*.whl` is uploaded you **cannot**
> re-upload the same version, even if the release was deleted. If a bad artifact is published:
> bump to `vX.Y.Z+1` (or `vX.Y.(Z+1)`) and cut a new release. Use the TestPyPI lane first for
> any risky or uncertain release.

### Supply-chain note

`gh-action-pypi-publish@release/v1` is the project's floating tag (acceptable for most teams).
For stricter supply-chain hygiene, pin to a specific SHA:

```yaml
uses: pypa/gh-action-pypi-publish@81e3e71  # example — check latest SHA on GitHub
```

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
- [ ] `make lint` passes (`uv run ruff check src tests && python -m mypy src`)
- [ ] PyPI Trusted Publisher configured (one-time — see [setup](#pypi-trusted-publisher-oidc-setup))
- [ ] GitHub Environments `pypi` and `testpypi` exist in repo settings (one-time)
- [ ] Tag pushed and GitHub Release published: triggers `release.yml` automatically
- [ ] `release.yml` CI green — `build` + `publish-pypi` jobs pass
- [ ] Homebrew formula updated and pushed to tap
- [ ] GitHub Release created with binary assets attached
- [ ] `pip install s3peek==X.Y.Z` verified in clean venv
- [ ] `brew install s3peek` verified

---

## Automated Release Pipeline (`release.yml`)

Current implementation:

1. GitHub Release published (tag `vX.Y.Z`) → `release.yml` triggers
2. `build` job: sdist + wheel, `twine check dist/*`, upload artifact
3. `publish-testpypi` job: non-blocking dry-run to test.pypi.org (OIDC, `continue-on-error`)
4. `publish-pypi` job: publish to pypi.org (OIDC, no token secret needed)

Items not yet implemented: binary signing (macOS notarization), Windows binary,
`brew bump-formula-pr` automation, binary matrix build upload to GitHub Release assets.
