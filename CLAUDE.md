# s3peek

S3 TUI browser for astronomers and data engineers. Quicklook for FITS / ASDF / Parquet via HTTP Range-GET. Read-only by design.

-----

## Project Invariants (DO NOT VIOLATE)

1. **Read-only client — never PUT, DELETE, COPY, or any mutating S3 op.**
   Reason: s3peek = browser, not manager. Users point at prod buckets (IRSA, MAST, IPAC internal); writes risk data corruption or accidental cost.
   Blast: silent data loss in shared buckets; trust gone; possible audit incident on IRSA-managed buckets.
1. **HTTP Range-GET only for quicklook — never full-object download.**
   Reason: FITS/ASDF/Parquet routinely 1–100 GB. Full GETs blow egress, freeze TUI, defeat "peek".
   Blast: surprise AWS egress bill, frozen UI on large files, user abandons tool.
1. **AWS region pinned to `us-east-1`, account `<AWS_ACCOUNT_ID>` (default profile)** — never rely on boto3 region auto-resolve.
   Reason: IRSA + Roman SSC buckets live there; cross-region requests silently fail or 403.
   Blast: confusing IAM denials, cross-region transfer cost spike.
1. **Python 3.12+ only.**
   Reason: needs `asyncio.TaskGroup`, modern `typing`, `uv`-managed wheels matching AL2023 Jenkins agent.
   Blast: silent CI install failure, divergent dev/prod behavior.

> If instruction below conflicts with invariant, invariant wins.

-----

## Recently Burned

- **2026-05-10 (pre-emptive)**: Agents swap custom FITS/ASDF header readers for `astropy.io.fits` / `asdf`. Pulls 50+ MB deps into quicklook hot path, defeats latency goal. Use only in opt-in deep-inspect mode.
- **2026-05-10 (pre-emptive)**: Agents refactor sync `boto3` inside Textual handlers to `aioboto3` "for performance". Textual worker/thread model already offloads; mixing two async stacks broke adjacent IPAC TUIs. No refactor without benchmark.
- **2026-05-10 (pre-emptive)**: Agents call `boto3.client('s3')` with no `region_name`. Inside `cdms` Jenkins Docker agent metadata service unreachable — hangs ~70s before failing. Always pass `region_name='us-east-1'` explicitly.

-----

## Workflow Expectations

- Confirm plan before code when scope > 1 file (per Emmanuel's RDD discipline).
- Use `uv` for envs and lockfile — never raw `pip` or `venv`.
- Run `uv run pytest -q` and `uv run ruff check` before declaring done.
- Annotate non-obvious code with `AIDEV-NOTE:` / `AIDEV-TODO:` / `AIDEV-QUESTION:` so future greps land.
- Public API or CLI flag changes → update `README.md` AND `docs/agent-context/` same commit.

-----

## Conventions (intentional deviations — do not "fix")

- **Custom FITS / ASDF / Parquet header parsing** — NOT `astropy.io.fits` or full `asdf` library for quicklook path. Quicklook reads only first N KB via Range-GET; heavy libs defeat latency goal. Full `astropy` / `asdf` only in opt-in "deep inspect" mode.
- **Synchronous `boto3` inside Textual event handlers is intentional** — Textual worker/thread model handles offloading. No refactor to `aioboto3` without benchmark; mixing two async stacks burned this before in adjacent IPAC tools.
- **No local caching layer for quicklook** — "peek" must reflect live S3 state (objects mutate, lifecycle policies expire). Caching = feature request, not default; if added, must be opt-in with explicit TTL.
- Comments tagged `AIDEV-*` are intentional anchors — preserve when refactoring.

-----

## Stack (inferred — single line each, no narration)

- Lang: Python 3.12 · Pkg: uv · Test: pytest -q · Lint: ruff
- TUI: Textual · S3: boto3 (sync, threaded by Textual) · Formats: FITS / ASDF / Parquet headers via Range-GET
- Cloud: AWS us-east-1 / acct `<AWS_ACCOUNT_ID>` · CI: Jenkins (label `cdms`, Dockerized agent)
- License: MIT

-----

## Out of Scope for the Agent

- No write/delete/copy commands "for completeness". s3peek = browser. Need mutation → point at `aws s3` or `s5cmd`.
- No `aioboto3` or `aiobotocore` without benchmark showing measurable win over existing Textual worker model.
- No `astropy` or `asdf` in quicklook code path. Deep-inspect mode only.
- No `uv.lock` regeneration with `--upgrade` unless explicitly asked — pins deliberate for AL2023 wheel compat.
- No cloud providers beyond S3-compatible endpoints in v1 (no GCS, no Azure). Scope creep kills focus.

-----

## Deeper Context (optional reads)

- Spec / RDD: `README.md`
- Architecture: `docs/agent-context/architecture.md`
- Format quicklook strategy: `docs/agent-context/quicklook-strategy.md`
- Implementation plan: `docs/IMPLEMENTATION_PLAN.md`