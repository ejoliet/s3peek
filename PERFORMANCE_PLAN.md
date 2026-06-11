# PERFORMANCE_PLAN

## Status

This plan is prepared from the completed audit.
No refactor or behavior changes have been made yet.
Waiting for approval before implementation.

## Objectives

1. Improve perceived CLI/TUI responsiveness.
2. Reduce S3/network and memory overhead for large scientific files.
3. Keep behavior stable and plugin contracts unchanged.
4. Add enough measurement to validate ROI after each optimization.

## Execution Strategy

## Phase 1 — Baseline Measurement (No Functional Changes)

- Add/enable timing capture for:
  - `plugins.load_readers()` and `quicklook()` dispatch
  - `Config.load()`
  - S3 `list_dir`, `list_prefix`, `stat_object`, `range_get`
  - Deep peek end-to-end duration
- Capture baseline metrics in representative scenarios:
  - Small JSON/FITS quicklook
  - Deep FITS/ASDF quicklook
  - Large-prefix `du`
  - Firefly with/without presign

Deliverable: baseline table for response time, request count, memory envelope.

## Phase 2 — High Impact / Low Risk

1. Memoize plugin discovery and instantiated readers/themes/commands.
2. Cache resolved config once per process invocation.
3. Reuse initialized `S3Client` per command path.
4. Improve expensive-operation visibility (`du` progress/explicit warning).

Validation:
- Existing test suite green.
- No CLI behavior or output contract regressions.
- Baseline-vs-after comparison for command latency.

## Phase 3 — High Impact / Medium Risk

1. Add bounded LRU chunk cache for `SeekableS3Stream`.
2. Implement footer-aware Parquet quicklook probe strategy.
3. Optimize Firefly large-file path (prefer presign/size-driven strategy).

Validation:
- Deep reader correctness tests + new edge-case tests.
- Memory profiling under deep-peek workloads.
- S3 request count and bytes transferred comparison.

## Phase 4 — Remaining Optimizations

1. JSON preview shallow parsing strategy.
2. Local-file large-input guard/streaming parity with S3 paths.

Validation:
- Functional parity for supported formats.
- Memory/CPU checks for large local JSON inputs.

## Phase 5 — Re-Measure and Report

- Re-run baseline scenarios.
- Summarize:
  - Response-time delta
  - Throughput delta
  - Memory delta
  - S3 request/byte delta
  - Cost implications
- Publish implementation summary with risk notes and rollback guidance.

## Change Control and Safety

- Preserve existing functionality and plugin entry-point contracts.
- Keep quicklook fast path dependency-light.
- Preserve read-only S3 behavior.
- Do not introduce breaking changes unless explicitly approved.
- Land changes in small, reviewable increments with tests.

## Test and Verification Plan

- Run repository lint and typing gates.
- Run full test suite after each phase.
- Add targeted tests for:
  - Plugin/config memoization behavior
  - Stream cache bound/eviction correctness
  - Parquet footer-read strategy
  - Firefly transfer-path decisions

## Approval Gate

Implementation will start only after explicit approval of this plan.
