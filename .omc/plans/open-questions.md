# Open Questions

## s3-browse-and-lazy-hydration - 2026-05-01 (initial draft)

- [x] Should the TUI cache the most recent N `HeaderResult`s per session? — Resolved iter-1: 64-entry LRU keyed by `(bucket, key, etag)` is in scope.
- [ ] Should `peek --output json` include the raw `bytes` length sampled, for reproducibility? — Deferred to phase-2.
- [x] Is `du` worth landing in this phase given `sum_prefix_sizes` is essentially a `list_prefix` reduction? — Resolved iter-1: out of scope, phase-2.
- [ ] What Textual minor version should be pinned? `>=0.60` is broad and the worker/`call_from_thread` API drifts. — Decide if CI flakes appear.
- [x] For the Parquet lazy-hydration path, is the extra HEAD-then-range-from-end pattern acceptable, or should we add a `stat+range` combined helper to `S3Client`? — Resolved iter-1: kept as separate HEAD + range, absorbed by LRU cache.
- [ ] Should reader top-level imports stay lazy (deferred to `read()`) to keep `s3peek --help` snappy? — Affects cold-start latency vs. error-locality.

## s3-browse-and-lazy-hydration - 2026-05-01 (revised iter-1, post Architect+Critic)

- [ ] `_cfg` test seam on Typer commands — should we expose a real `--config-path` CLI flag instead of a hidden private kwarg? — Affects test ergonomics and user-facing CLI surface; the hidden kwarg approach works for tests but is not idiomatic Typer.
- [ ] `botocore.config.Config` retry/timeout values (`connect_timeout=2`, `read_timeout=5`, `retries.max_attempts=1`) — should these be exposed in `Config` (Pydantic settings) for ops tuning, or kept hardcoded? — Affects deployability on slow networks.
- [ ] Streaming-body close on cancel — current plan documents the bytes-already-consumed cost as accepted. Should we add a metrics counter (`workers_cancelled_total`, `bytes_wasted_total`) for observability? — Out of scope for phase-1; tracked for phase-2.
- [ ] Debounce constant `DEBOUNCE_MS = 120` — class-level constant or `Config` field? — Affects per-user tuning vs. simplicity.
- [ ] LRU `LRU_MAX = 64` — class-level constant or `Config` field? Memory upper bound is ~640 KiB; probably fine as constant but worth confirming.
- [ ] `mypy_boto3_s3` — if a paginator return type still surfaces as `Any` despite the stubs, is the per-call `# type: ignore[misc]` with reason comment acceptable, or should we wrap the paginator in an explicit cast helper? — Style decision.
- [ ] `populated_bucket` fixture growth — should we split into `populated_bucket` (light, current behavior) and `realistic_bucket` (with real Parquet/ASDF/FITS payloads), or grow the single fixture? Test slowdown vs. fixture clarity.
- [ ] Plugin dispatch collision policy — current plan says "higher priority wins, log warning." Should we instead **fail loudly** (raise) on collision in a development environment? — Affects plugin author DX.
