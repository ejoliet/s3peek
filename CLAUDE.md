# s3peek

S3 TUI browser for astronomers and data engineers. Quicklook for FITS / ASDF / Parquet / JSON via HTTP Range-GET. Read-only by design.

-----

## Project Invariants (DO NOT VIOLATE)



1. **Read-only client — never PUT, DELETE, COPY, or any mutating S3 op.**
   Reason: s3peek is a browser, not a manager. Users point it at production buckets (IRSA, MAST, internal IPAC); any write risks data corruption or accidental cost.
   Blast: silent data loss in shared buckets; trust in tool gone; possible audit incident on IRSA-managed buckets.
1. **HTTP Range-GET only for quicklook — never full-object download.**
   Reason: FITS/ASDF/Parquet files routinely hit 1–100 GB. Full GETs blow egress budgets, freeze the TUI, and defeat the purpose of "peek".
   Blast: surprise AWS egress bill, frozen UI on large files, user abandons tool.
1. **AWS region pinned to `us-east-1`, account `<AWS_ACCOUNT_ID>` (default profile)** — never rely on boto3 region auto-resolve.
   Reason: IRSA + Roman SSC buckets live there; cross-region requests silently fail or 403.
   Blast: confusing IAM denials, cross-region transfer cost spike.
1. **Python 3.11+ only.**
   Reason: relies on `asyncio.TaskGroup` (3.11+), modern `typing`, and `uv`-managed wheels matching AL2023 Jenkins agent. `pyproject.toml requires-python=">=3.11"`; ruff/mypy target `py311`; classifiers cover 3.11 + 3.12.
   Blast: silent install failure in CI, divergent dev/prod behavior.

> If an instruction below conflicts with an invariant, the invariant wins.

-----

## Recently Burned



- **2026-05-10 (pre-emptive)**: Agents tend to "helpfully" swap custom FITS/ASDF header readers for `astropy.io.fits` / `asdf`. This pulls 50+ MB of deps into the quicklook hot path and defeats the latency goal. Use only in opt-in deep-inspect mode.
- **2026-05-21 (decided)**: `FITSReader._read_deep()` uses `astropy.io.fits.open(BytesIO, memmap=False)` for multi-HDU extraction — lazy import, only when `deep=True`. Fast path (`_read_fast`) stays pure-byte, no astropy.
- **2026-05-21 (decided)**: `ASDFReader._read_deep()` uses `asdf.open(BytesIO, lazy_load=True, _force_raw_types=True)` — arrays arrive as `TaggedDict` with `_tag` containing `"ndarray"`, summarized as `{"__ndarray__": True, "shape": [...], "dtype": "..."}` by `_to_plain()`. The `__iter__` fallback in `_to_plain` was intentionally removed (element-wise numpy recursion bomb).
- **2026-05-23 (resolved)**: `peek --deep` on `s3://` URIs no longer fails fast. `SeekableS3Stream` (`src/s3peek/streams.py`) issues Range-GETs on demand as astropy/asdf seek through the file — works on arbitrarily large files, no full download. `--max-range-bytes` flag overrides fast-path limit per invocation.
- **2026-05-23 (decided)**: TUI browser (`browser.py`) implemented — `S3Browser(App)` with `@work(thread=True)` for all boto3 calls. `d` key = deep-peek via `SeekableS3Stream` (Range-GET only, not full download). `s3.list_dir()` paginates `CommonPrefixes`+`Contents`, skips zero-byte dir markers. Firefly TUI path uses presigned URL (`fc.show_url`), not tmpfile download. `self.theme` assignment removed — raises `InvalidThemeError` in current Textual; use `DEFAULT_CSS` instead. Textual `VerticalScroll` lives in `textual.containers`, not `textual.widgets`.
- **2026-05-10 (pre-emptive)**: Agents tend to refactor sync `boto3` calls inside Textual handlers to `aioboto3` "for performance". Textual's worker/thread model already offloads; mixing two async stacks has broken adjacent IPAC TUIs. Do not refactor without a benchmark.
- **2026-05-10 (pre-emptive)**: Agents tend to call `boto3.client('s3')` with no `region_name`. Inside the `cdms` Jenkins Docker agent the metadata service is unreachable and this hangs ~70s before failing. Always pass `region_name='us-east-1'` explicitly.

-----

## Workflow Expectations



- Confirm plan before code when scope > 1 file (per Emmanuel's RDD discipline).
- Use `uv` for envs and lockfile — never raw `pip` or `venv`.
- Before declaring done: `make test` (`pytest`, moto-mocked S3) and `make lint` (`ruff check src tests` **+ `mypy src` strict**). mypy strict is a hard gate — type-annotate fully. Under `uv`: `uv run make test` / `uv run make lint`.
- Annotate non-obvious code with `AIDEV-NOTE:` / `AIDEV-TODO:` / `AIDEV-QUESTION:` so future greps land.
- When a public API or CLI flag changes, update `README.md` AND `docs/agent-context/` in the same commit.

-----

## Conventions (intentional deviations — do not "fix")



- **Custom FITS / ASDF / Parquet / JSON header parsing** — NOT `astropy.io.fits` or full `asdf` library for quicklook fast path. Quicklook reads only the first N KB via Range-GET; pulling in heavy libs defeats the latency goal.
  - `_read_fast()` (default): pure-byte, no deps, returns first HDU / fast YAML scan.
  - `_read_deep()` (opt-in, `--deep` flag): lazy-import `astropy.io.fits` (FITS) or `asdf` (ASDF). Multi-HDU / full-tree. Only triggered when user explicitly passes `--deep`.
  - Four built-in readers registered: `fits`, `asdf`, `parquet`, `json`. `astropy`/`asdf`/`pyarrow` ARE core `dependencies` (not optional extras) — keep them lazy-imported in deep paths, don't move them to `[project.optional-dependencies]`.
- **Plugin system via `importlib.metadata.entry_points`** (`plugins.py`) — readers and themes are discovered from `[project.entry-points."s3peek.readers"]` / `."s3peek.themes"]`. Add a new format by registering an entry point, not by hardcoding in the dispatcher. Modules: `presign.py` (pre-signed URLs), `firefly.py` (Firefly viz), `themes/`.
- **Synchronous `boto3` inside Textual event handlers is intentional** — Textual's worker / thread model handles offloading. Do not refactor to `aioboto3` unless benchmarked; mixing two async stacks has burned this before in adjacent IPAC tools.
- **No local caching layer for quicklook** — "peek" must always reflect live S3 state (objects mutate, lifecycle policies expire). Caching is a feature request, not a default; if added, must be opt-in with explicit TTL.
- Comments tagged `AIDEV-*` are intentional anchors — preserve when refactoring.

-----

## Stack (inferred — single line each, no narration)

- Lang: Python 3.11+ · Pkg: uv · Test: pytest (moto[s3]) · Lint: ruff + mypy (strict)
- CLI: typer (7 cmds: browse, peek, share, ls, du, config, firefly) · Config: pydantic v2 + TOML
- TUI: Textual · S3: boto3 (sync, threaded by Textual) · Formats: FITS / ASDF / Parquet / JSON headers via Range-GET
- Cloud: AWS us-east-1 / acct `<AWS_ACCOUNT_ID>` · CI: Jenkins (label `cdms`, Dockerized agent)
- License: MIT

-----

## Out of Scope for the Agent



- Don't add write/delete/copy commands "for completeness". s3peek is a browser. If a user needs mutation, point them to `aws s3` or `s5cmd`.
- Don't introduce `aioboto3` or `aiobotocore` without a benchmark showing measurable win over the existing Textual worker model.
- Don't pull `astropy` or `asdf` into the quicklook code path. Deep-inspect mode only.
- Don't regenerate `uv.lock` with `--upgrade` unless explicitly asked — pins are deliberate for AL2023 wheel compatibility.
- Don't add cloud providers beyond S3-compatible endpoints in v1 (no GCS, no Azure). Scope creep kills focus.

-----

## Deeper Context (optional reads)



- Spec / quickstart: `README.md`
- Architecture & API reference: `docs/agent-context/architecture.md`
- Contributing & plugin development: `CONTRIBUTING.md`
- Developer guide: `DEVELOPER.md`
- Releasing (PyPI / Homebrew / binaries): `docs/releasing.md`
