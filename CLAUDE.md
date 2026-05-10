# s3peek

S3 TUI browser for astronomers and data engineers. Quicklook for FITS / ASDF / Parquet via HTTP Range-GET. Read-only by design.

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
1. **Python 3.12+ only.**
   Reason: relies on `asyncio.TaskGroup`, modern `typing`, and `uv`-managed wheels matching AL2023 Jenkins agent.
   Blast: silent install failure in CI, divergent dev/prod behavior.

> If an instruction below conflicts with an invariant, the invariant wins.

-----

## Recently Burned



- **2026-05-10 (pre-emptive)**: Agents tend to "helpfully" swap custom FITS/ASDF header readers for `astropy.io.fits` / `asdf`. This pulls 50+ MB of deps into the quicklook hot path and defeats the latency goal. Use only in opt-in deep-inspect mode.
- **2026-05-10 (pre-emptive)**: Agents tend to refactor sync `boto3` calls inside Textual handlers to `aioboto3` "for performance". Textual's worker/thread model already offloads; mixing two async stacks has broken adjacent IPAC TUIs. Do not refactor without a benchmark.
- **2026-05-10 (pre-emptive)**: Agents tend to call `boto3.client('s3')` with no `region_name`. Inside the `cdms` Jenkins Docker agent the metadata service is unreachable and this hangs ~70s before failing. Always pass `region_name='us-east-1'` explicitly.

-----

## Workflow Expectations



- Confirm plan before code when scope > 1 file (per Emmanuel's RDD discipline).
- Use `uv` for envs and lockfile — never raw `pip` or `venv`.
- Run `uv run pytest -q` and `uv run ruff check` before declaring done.
- Annotate non-obvious code with `AIDEV-NOTE:` / `AIDEV-TODO:` / `AIDEV-QUESTION:` so future greps land.
- When a public API or CLI flag changes, update `README.md` AND `docs/agent-context/` in the same commit.

-----

## Conventions (intentional deviations — do not "fix")



- **Custom FITS / ASDF / Parquet header parsing** — NOT `astropy.io.fits` or full `asdf` library for quicklook path. Quicklook reads only the first N KB via Range-GET; pulling in heavy libs defeats the latency goal. Full `astropy` / `asdf` only allowed in opt-in "deep inspect" mode.
- **Synchronous `boto3` inside Textual event handlers is intentional** — Textual's worker / thread model handles offloading. Do not refactor to `aioboto3` unless benchmarked; mixing two async stacks has burned this before in adjacent IPAC tools.
- **No local caching layer for quicklook** — "peek" must always reflect live S3 state (objects mutate, lifecycle policies expire). Caching is a feature request, not a default; if added, must be opt-in with explicit TTL.
- Comments tagged `AIDEV-*` are intentional anchors — preserve when refactoring.

-----

## Stack (inferred — single line each, no narration)

- Lang: Python 3.12 · Pkg: uv · Test: pytest -q · Lint: ruff
- TUI: Textual · S3: boto3 (sync, threaded by Textual) · Formats: FITS / ASDF / Parquet headers via Range-GET
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



- Spec / RDD: `README.md`
- Architecture: `docs/agent-context/architecture.md`
- Format quicklook strategy: `docs/agent-context/quicklook-strategy.md`
- Implementation plan: `docs/IMPLEMENTATION_PLAN.md`
