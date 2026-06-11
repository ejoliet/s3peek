# PERFORMANCE_AUDIT

## Scope and Method

Audit performed across:
- Application architecture (`src/s3peek/*.py`)
- Reader plugins (`src/s3peek/readers/*.py`)
- CLI/TUI runtime paths (`cli.py`, `browser.py`, `streams.py`, `s3.py`)
- Dependency and packaging setup (`pyproject.toml`, `Makefile`)
- Test and deployment config (`tests/*`, `.github/workflows/*`)

No relational database, ORM, queue broker, or HTTP API server exists in this codebase today, so DB/queue/API endpoint findings are marked **N/A** where appropriate.

## Architecture Summary (Performance-Relevant)

- `S3Client` wraps boto3 and performs listing, stat, range GET, full download, and prefix aggregation.
- `quicklook()` dispatches to plugin readers by loading entry points at call time.
- TUI (`S3Browser`) uses Textual worker threads for S3/network work.
- Deep FITS/ASDF paths stream from S3 using `SeekableS3Stream` chunked range GET with in-memory chunk cache.
- Firefly flow supports both presigned URL mode and local temporary download mode.

---

## Bottlenecks and Opportunities

| ID | Area | Bottleneck | Root Cause | Est. Impact | Risk | Recommended Fix |
|---|---|---|---|---|---|---|
| B1 | Plugin dispatch | Repeated entry-point discovery and class instantiation on each `quicklook()` call | `plugins.load_readers()` calls `entry_points()` each time | Medium latency reduction for repeated peeks (10–40 ms/op depending env/plugins) | Low | Add process-local memoization for readers/themes/commands |
| B2 | Config loading | Repeated file parse + env merge in commands | `Config.load()` called in many command paths | Small per-command CPU/IO savings; improves CLI responsiveness | Low | Cache resolved config once per process, with explicit reload path only if needed |
| B3 | S3 session churn | New `S3Client` instances in multiple commands instead of reuse | Command functions create fresh client each invocation | Small–medium reduction in startup/session overhead | Low | Reuse one initialized client within each command execution path |
| B4 | Deep stream memory growth | Unbounded chunk cache in `SeekableS3Stream` | `_cache` dict never evicts chunks | High memory risk on large deep scans (can grow to hundreds of MB+) | Medium | Add bounded LRU cache with max bytes/chunks from config |
| B5 | Parquet quicklook reliability/perf | Schema read from partial bytes may fail and retries are not optimized | Parquet metadata in footer; current path often reads wrong region | Medium user-perceived latency and lower hit-rate | Medium | Two-step footer probe: tail range read + metadata slice read |
| B6 | JSON quicklook memory | Full `json.loads(data)` for selected range bytes | Full parse allocates full object graph | Small–medium memory/CPU overhead for larger previews | Low | Return shallow summary from streaming/token-limited parse for preview mode |
| B7 | Firefly default path | Full object download to temp file when `--presign` not set | `download_fileobj` used by default path | High latency + bandwidth + local disk IO for large files | Medium | Prefer presigned URL mode by default for large objects or add size threshold auto-switch |
| B8 | Prefix size aggregation | `sum_prefix_sizes` must scan entire prefix object list | S3 has no server-side SUM aggregate | High latency/cost on very large prefixes | Low | Add progress reporting, optional early-limit/sample, and docs warning for huge prefixes |
| B9 | CLI local file peek | `Path.read_bytes()` reads whole local file | No max-size guard for local files | Medium memory spike for large local files | Low | Add max-bytes guard/streaming local file mode aligned with S3 fast/deep behavior |
| B10 | Observability | No timing/diagnostic mode for hot operations | No instrumentation hooks | Medium (blocks optimization validation) | Low | Add optional `--profile`/debug timing logs for list, stat, range-get, parse |

---

## ROI Prioritization

## Tier 1: High Impact / Low Risk (Do First)

1. **B1 plugin memoization**
2. **B2 config caching**
3. **B3 per-command S3 client reuse**
4. **B10 lightweight instrumentation**
5. **B8 UX/guardrails for expensive `du` scans**

Expected gain (combined): faster command startup and repeated operations, better diagnosability, no behavior break.

## Tier 2: High Impact / Medium Risk (Do Second)

1. **B4 bounded chunk cache for deep streaming**
2. **B5 parquet footer-aware quicklook**
3. **B7 Firefly large-object transfer strategy**

Expected gain (combined): major memory and network savings on large scientific files; risk is in behavior compatibility and edge-format handling.

## Tier 3: Everything Else

1. **B6 JSON shallow preview optimization**
2. **B9 local file guard/streaming parity**

Expected gain: incremental CPU/memory improvement and safer local handling.

---

## Deep-Dive by Requested Area

## Database

- **Status:** N/A (no DB layer, ORM, SQL, migrations, or query planner usage in repository).
- No N+1 query or index findings applicable.

## Application Layer

Findings:
- Repeated plugin and config resolution in hot paths (B1, B2).
- Repeated client creation across command execution paths (B3).
- Potentially large in-memory cache growth during deep reads (B4).
- Full-object local parsing in some formats/paths (B6, B9).

## Caching

- Positive: `SeekableS3Stream` has chunk cache reducing repeated range GETs.
- Gaps: no eviction strategy (B4), no memoized plugin/config cache (B1/B2).

## Queues & Background Processing

- **Status:** N/A external queues/workers.
- Internal threaded background work in Textual is appropriate; no queue backpressure controls currently exposed.

## API Performance

- **Status:** No standalone HTTP API endpoints.
- Closest equivalent is CLI/TUI command latency and S3 request volume.

## Frontend / Asset Loading

- TUI-only app (Textual), no JS bundle pipeline.
- Main risk is UI responsiveness under long S3 operations; worker offload is already used.

## Infrastructure / Deployment

Findings:
- CI installs with plain `pip install -e ".[dev]"` (could be slower and less reproducible vs `uv` workflow used by project guidance).
- No runtime connection pool tuning exposed for boto3 client (typically acceptable for current CLI/TUI concurrency profile).

---

## Risk Assessment

- **Low risk changes:** memoization, config/client reuse, instrumentation.
- **Medium risk changes:** cache eviction policy (can alter deep-read behavior), parquet footer strategy (format edge cases), Firefly transfer mode defaults (user workflow expectation).
- **Primary regression risks:** deep FITS/ASDF correctness, plugin discovery behavior, Firefly usability for restricted environments.

---

## Expected Performance Gains (If Plan Is Implemented)

- **Response time:** faster repeated peeks and command startup; reduced long-tail delays on large files.
- **Throughput:** more operations per session due to less redundant initialization and network transfer.
- **Memory usage:** bounded deep-read memory via cache limits; lower spikes in large preview paths.
- **Database load:** N/A.
- **Infrastructure cost:** reduced S3 data transfer and local disk IO (especially Firefly + deep-read scenarios).

---

## Significant Changes to Target (When Approved)

For each significant implementation item, document in follow-up PR:
1. What changed
2. Why it changed
3. Measured/estimated impact on response time, throughput, memory, load, and cost

Current status: **audit complete; no refactor changes applied yet.**
