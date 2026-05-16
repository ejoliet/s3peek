# Plan: S3 Browse + Lazy Hydration

**Status:** Revised iter-1 (post Architect + Critic). Ready for execution.
**Mode:** SHORT consensus (with deliberate-grade additions where Critic flagged risk).
**Author:** Planner
**Date:** 2026-05-01

---

## RALPLAN-DR Summary (revised)

### Principles (5)

1. **Header-only by default.** Never read more than `Config.max_range_get_bytes` (default 64 KiB) from any S3 object during browsing or peek. Bulk download is opt-in.
2. **Streaming UI, no blocking.** All S3 calls happen off the Textual event loop (via worker threads). The TUI must remain responsive while paginating large prefixes.
3. **Reader contract is byte-pure.** Each `BaseReader.read()` operates on an in-memory `bytes` slice. S3 is the I/O layer; readers stay format-only and unit-testable without network.
4. **Readers declare their own fetch plan.** New `BaseReader.fetch_plan(size: int) -> list[tuple[int, int]]` returns the byte ranges the reader needs (default `[(0, 65536)]`; Parquet returns `[(size - 65536, 65536)]`). Callers (TUI, `peek`) iterate the plan and concatenate the bytes — the per-format special case (footer-vs-head) lives inside the reader, not the caller.
5. **Boundary-tested with moto + realistic payloads.** All S3 logic and reader logic is exercised via `populated_bucket` (or sibling `realistic_bucket`) seeded with real Parquet/ASDF/FITS bytes — not magic-byte stubs. Magic-byte fallbacks must not produce vacuous test passes.

### Decision Drivers (top 3)

1. **Latency ceiling per navigation event:** focusing on a new object must produce a header preview in well under 1 second on a typical residential connection. This drives botocore timeouts (`connect_timeout=2`, `read_timeout=5`, `retries.max_attempts=1`), debounce on fast keyboard navigation, and an LRU result cache.
2. **Skipped tests as the acceptance grid:** **13** currently-skipped tests across `tests/test_s3.py` (3), `tests/test_quicklook.py` (5), `tests/test_presign.py` (3), and `tests/test_cli.py` (2: `test_peek`, `test_ls`) form the contract for "done." The remaining 3 skips (`test_du`, `test_share`, `test_firefly_connector_send`) are explicitly out of scope for this phase and stay skipped.
3. **Backward-compatible reader Protocol with footer-aware extension:** `BaseReader.read(data: bytes, *, max_headers: int)` is locked. The new `fetch_plan` method extends the Protocol additively (default impl on the `BaseReader` Protocol means existing readers keep working). The S3 layer adapts to it; readers grow no new I/O responsibilities.

### Viable Options

#### Option A: Synchronous range_get + Textual `@work(thread=True)` lazy hydration + reader-driven `fetch_plan` (RECOMMENDED)

`S3Client` is synchronous boto3 (with shared client across worker threads, configured retry/timeout). The TUI offloads each preview to a Textual worker thread that:
1. Calls `_dispatch_reader(key, first_512_bytes)` to pick a reader.
2. Calls `reader.fetch_plan(size)` (size from `stat_object`, cached) to compute ranges.
3. Concatenates `range_get` results into one `bytes` blob.
4. Calls `quicklook(...)` and posts a custom `HeaderReady` message back to the UI thread via `call_from_thread`.

Worker is debounced (120 ms) and results are LRU-cached (64 entries) keyed by `(bucket, key, etag)` to absorb scroll storms.

- **Pros:** matches boto3's natural sync API; trivial to test (`S3Client` callable directly under moto); Textual workers are first-class and cancellable on focus change; the `fetch_plan` indirection removes the only caller-side format special case.
- **Pros:** no asyncio/aioboto3 surface area (boto3 stays sync, fewer deps).
- **Cons:** thread-per-preview during fast scrolling can stack up — mitigated by debounce + `exclusive=True` worker group + LRU cache.
- **Cons:** cancelled workers may have already issued an HTTP GET; we close the streaming body in a `finally` block but the bytes-up-to-cancel are still consumed (accepted cost; documented in Step 5).

#### Option B: aioboto3 + Textual native async workers

Rewrite `S3Client` async-first using aioboto3; workers become `async def` coroutines on Textual's event loop.

- Pros: single concurrency model end-to-end; cancellation is structurally clean.
- Cons: introduces a new top-level dependency outside `pyproject.toml`'s declared deps; doubles the test surface (sync API still required by `peek`/`ls`/`du`/`share` Typer commands); aioboto3 lags behind boto3 in moto compatibility; `mypy_boto3_s3` stubs (already in dev deps) target sync boto3.
- **Invalidation rationale:** dependency budget (none budgeted) + the synchronous Typer command surface (would force `asyncio.run` wrappers in every CLI command) + already-installed sync stubs.

#### Option C: Pre-fetch all metadata, lazy hydrate only header bytes

`browse` lists the entire prefix up front (paginated `ListObjectsV2`), then lazy-fetches only the header range on focus.

- Pros: simpler navigation UX (size/date columns populated immediately).
- Cons: worst-case prefixes (10k+ objects) stall startup; unbounded memory; defeats "lazy" positioning.
- **Invalidation rationale:** violates Driver #1 (latency budget per navigation event must include first-paint, not just per-row hydration). Pieces of it can re-enter as a future bounded `--eager` flag with a `max_keys` ceiling — already plumbed into Step 2.

**Decision:** Option A.

---

## Context

s3peek is a terminal-first S3 browser. The skeleton phase is done: types, exceptions, plugin discovery, format dispatch wiring, Pydantic config, and the test suite (with 13 in-scope skipped tests + 3 out-of-scope skips) are in place. This phase wires the data plane.

**Files in scope:**
- `src/s3peek/s3.py` (3 stubs to implement, 1 helper to add, retry/timeout config)
- `src/s3peek/presign.py` (3 stubs to implement)
- `src/s3peek/readers/__init__.py` (extend `BaseReader` Protocol with `fetch_plan`)
- `src/s3peek/readers/{fits,asdf,parquet,json}.py` (4 `read()` stubs to implement; `parquet.py` overrides `fetch_plan`)
- `src/s3peek/quicklook.py` (already wired; verify; add fetch-plan-aware helper)
- `src/s3peek/cli.py` (`browse`, `peek`, `ls` to implement; `_make_client(cfg)` injection helper; `du`, `share`, `firefly` left as stubs)
- `src/s3peek/browser.py` (Textual `S3Browser` to flesh out — debounce, LRU, exception handling, empty-state)
- New: `src/s3peek/uri.py` (S3 URI parsing — not yet in tree)
- Tests: extend `tests/conftest.py` (config isolation + realistic payloads), rewrite `tests/test_cli.py` URIs, unskip 13 in-scope tests, add `tests/test_uri.py`, `tests/test_readers.py`, `tests/test_browser.py`.

---

## Work Objectives

1. Make `S3Client` a working sync client over boto3, with bounded retries/timeouts, shared-client-across-threads semantics, and proper exception mapping.
2. Extend `BaseReader` Protocol with `fetch_plan`. Implement format readers so `quicklook(bytes, key)` returns populated `HeaderResult` for FITS / ASDF / Parquet / JSON.
3. Ship a `browse` TUI that lists a prefix, lazily fetches header bytes on focus (debounced + LRU-cached), runs `quicklook`, and shows the result in a side panel — without ever downloading full objects.
4. Wire `peek` and `ls` CLI commands as thin shells over `S3Client` + `quicklook`, with injectable `Config`.
5. Implement `presign.generate_presigned_url` / `parse_expiry`.
6. Move 13 in-scope skipped tests to passing; explicitly leave 3 out-of-scope skips in place; add 4 robustness tests + the test files needed.

---

## Guardrails

### Must Have

- **No full-object GETs in the browse/peek path.** Every read goes through `S3Client.range_get` with `length <= Config.max_range_get_bytes`.
- **Readers stay byte-only.** They never import `boto3`, never touch the network. They accept `bytes` and return `HeaderResult`. Their `fetch_plan` is byte-arithmetic only (uses `size: int`).
- **Exceptions mapped at the boto3 boundary.** `botocore.exceptions.ClientError` is translated to `BucketNotFoundError` / `ObjectNotFoundError` / `AccessDeniedError` inside `S3Client`. The TUI catches these in the worker and displays them in the preview pane — never crashes the app.
- **TUI must not block.** Every `S3Client` call inside `S3Browser` runs in a Textual `@work(thread=True)` worker. Cancellation on focus change is required. Streaming bodies are closed in `finally` on cancel.
- **All tests run under moto with realistic payloads.** No live AWS. The `populated_bucket` fixture seeds real Parquet / ASDF / FITS bytes.
- **Config isolated in tests.** `S3PEEK_CONFIG=/dev/null` set in autouse fixture so no developer's `~/.config/s3peek/config.toml` leaks into tests. CLI commands accept `Config` injection for clean test runs.

### Must NOT Have

- No new top-level dependencies beyond what is already in `pyproject.toml`.
- No async rewrite of `S3Client` (Option B is out for this phase).
- No reading of full objects to discover format. Format dispatch uses key extension + first 512 bytes only, as already defined in `quicklook.py`.
- No clipboard or QR side effects in tests.
- No FITS/ASDF/Parquet schema introspection beyond headers/metadata.
- No silent `Any` from boto3 paginators in `mypy --strict`. Use `mypy_boto3_s3` stubs already in dev deps; if a per-call cast is unavoidable, add a single targeted `# type: ignore[misc]` with a reason comment.

---

## Task Flow (dependency order)

```
1. uri.py + tests           (foundation)
        |
        v
2. S3Client.list_prefix / stat_object / range_get / sum_prefix_sizes
   + retry/timeout + shared client + etag strip + max_keys
        |
        +--> 3a. BaseReader Protocol: add fetch_plan default
        |        |
        |        +--> Reader.read() impls (FITS/ASDF/Parquet/JSON)
        |        |     ParquetReader.fetch_plan override
        |        |
        |        v
        |    quicklook + concat helper
        |
        +--> 3b. presign.generate_presigned_url / parse_expiry
        |
        v
4. CLI: peek + ls (thin wrappers; _make_client(cfg) injection)
        |
        v
5. browser.py: Textual TUI (debounce 120ms, LRU 64, exception handling,
   empty-state, fetch_plan dispatch, streaming-body close-on-cancel)
        |
        v
6. conftest realistic payloads + S3PEEK_CONFIG isolation
   + rewrite test_cli URIs
   + unskip the 13 in-scope tests
   + add 4 robustness tests + new test files
   + mypy --strict + ruff green
```

---

## Detailed TODOs

### Step 1 — S3 URI parsing (foundation)

**Files:**
- New: `src/s3peek/uri.py`
- New: `tests/test_uri.py`

**Method signatures:**

```python
@dataclass(frozen=True)
class S3URI:
    bucket: str
    key: str

    @property
    def is_prefix(self) -> bool: ...

def parse_s3_uri(uri: str) -> S3URI: ...
def to_uri(bucket: str, key: str) -> str: ...
```

`parse_s3_uri` raises `InvalidURIError` (already in `exceptions.py`) on non-`s3://`, missing bucket, or DNS-invalid bucket name.

**Tests proving it works (`tests/test_uri.py`, new):**
- `parse_s3_uri("s3://bucket/path/file.fits")` → `S3URI(bucket="bucket", key="path/file.fits")` with `is_prefix=False`.
- `parse_s3_uri("s3://bucket/")` → `S3URI(bucket="bucket", key="")` with `is_prefix=True`.
- `parse_s3_uri("s3://bucket")` → same as above (no trailing slash, empty key, is_prefix True).
- `parse_s3_uri("https://...")` raises `InvalidURIError`.
- `parse_s3_uri("s3:///key")` (empty bucket) raises `InvalidURIError`.
- `to_uri("b", "k/x")` round-trips through `parse_s3_uri`.

**Acceptance criteria:**
- All 6 cases above pass.
- No external deps used.

### Step 2 — `S3Client` data plane

**File:** `src/s3peek/s3.py`

**Method signatures + docstring additions:**

```python
import boto3
import botocore.config
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client as Boto3S3Client

class S3Client:
    """
    Thin synchronous wrapper around boto3 S3 client.

    Thread-safety: ``boto3.client("s3")`` is constructed once in ``__init__``
    and shared across worker threads. boto3 documents the low-level client
    as safe for concurrent ``list_*`` / ``head_*`` / ``get_*`` calls. The
    underlying ``boto3.Session`` is also constructed once at app startup and
    is treated as read-only thereafter. Do not mutate session/client config
    after construction.
    """

    _s3: "Boto3S3Client"

    def __init__(
        self,
        profile: str | None = None,
        region: str | None = None,
        *,
        max_keys: int = 1000,
    ) -> None:
        session = boto3.Session(profile_name=profile, region_name=region)
        cfg = botocore.config.Config(
            connect_timeout=2,
            read_timeout=5,
            retries={"max_attempts": 1, "mode": "standard"},
        )
        self._s3 = session.client("s3", config=cfg)
        self._max_keys = max_keys

    def list_prefix(
        self,
        bucket: str,
        prefix: str,
        *,
        delimiter: str = "/",
        max_keys: int | None = None,
    ) -> list[ObjectMeta]:
        """Paginate list_objects_v2; cap at self._max_keys (or override).
        Surface CommonPrefixes as synthetic ObjectMeta(size=0, storage_class="DIR",
        key=<prefix>/). Map ClientError: NoSuchBucket -> BucketNotFoundError;
        AccessDenied/403 -> AccessDeniedError.
        """

    def stat_object(self, bucket: str, key: str) -> ObjectMeta:
        """head_object; map 404 -> ObjectNotFoundError, 403 -> AccessDeniedError.
        Strip surrounding double quotes from etag (head_object returns
        '"abc123"'-style values per S3 spec).
        """

    def range_get(
        self, bucket: str, key: str, *, start: int = 0, length: int = 65536
    ) -> bytes:
        """get_object with Range=f"bytes={start}-{start+length-1}".
        Cap length at Config.max_range_get_bytes (caller-enforced).
        Map 416 (out of range) -> b"".
        Caller is responsible for closing the underlying streaming body
        if interrupted; this method consumes body.read() fully on its happy
        path.
        """

    def sum_prefix_sizes(self, bucket: str, prefix: str) -> dict[str, int]:
        """Optional helper for `du`; group by top-level segment after prefix.
        Out of scope for this phase but stub stays."""
```

**Etag-strip rule (item #10):** in `stat_object`, after `resp = self._s3.head_object(...)`, do `etag = resp["ETag"].strip('"')` and store the stripped value on `ObjectMeta`. This stripped value is what the LRU cache key uses in Step 5.

**Pagination cap (additional item):** `list_prefix` aggregates results from the paginator but stops at `max_keys` (default 1000). The cap is parameterized so a future `--eager` flag can raise it.

**Tests proving it works (existing `tests/test_s3.py`, unskip 3 + add 3 new):**
- Unskip: `test_list_prefix_returns_objects`, `test_stat_object_returns_metadata`, `test_range_get_honors_length`.
- New: `test_list_prefix_unknown_bucket_raises_BucketNotFoundError`.
- New: `test_stat_object_strips_etag_quotes` (asserts `meta.etag` does not contain `"`).
- New: `test_list_prefix_max_keys_cap` (seeds 5 objects, calls with `max_keys=2`, asserts result length 2).

**Acceptance criteria:**
- All 6 above tests green.
- `S3Client._s3` attribute typed as `mypy_boto3_s3.S3Client` (under `TYPE_CHECKING`); `mypy --strict src/s3peek/s3.py` clean.
- If paginator return types still surface as `Any`, add `# type: ignore[misc]  # boto3 paginator returns dict[str, Any]; concrete shape enforced by S3Client._handle_*` with that exact comment text.
- Manual smoke (developer): `python -c "from s3peek.s3 import S3Client; c = S3Client(); print(c.list_prefix('s3-public-anon-bucket', '', max_keys=5))"` returns within 5s and respects the cap.

### Step 3a — Reader `fetch_plan` + `read()` implementations

**Files:**
- `src/s3peek/readers/__init__.py` (Protocol extension)
- `src/s3peek/readers/{fits,asdf,parquet,json}.py` (`read` impls; Parquet `fetch_plan` override)
- `src/s3peek/quicklook.py` (concat helper; verify dispatcher)

**Protocol extension (item #1):**

```python
# src/s3peek/readers/__init__.py
@runtime_checkable
class BaseReader(Protocol):
    extensions: tuple[str, ...]
    priority: int

    def can_read(self, key: str, first_bytes: bytes) -> bool: ...
    def read(self, data: bytes, *, max_headers: int = 1) -> HeaderResult: ...

    def fetch_plan(self, size: int) -> list[tuple[int, int]]:
        """Return list of (start, length) byte ranges this reader needs.

        Default: a single 64 KiB head slice. Parquet overrides to fetch the
        footer. Implementors may return multiple ranges; the caller
        concatenates them in order before calling .read().
        """
        return [(0, 65536)]
```

Because `BaseReader` is a `Protocol`, the default implementation is provided by adding it to a sibling **abstract base class** `_DefaultFetchPlanMixin` that each concrete reader inherits from, OR by making `BaseReader` a `runtime_checkable` Protocol with a method body (Python 3.12+ supports this for Protocols). The implementation chooses the simpler route: add a small concrete base class `DefaultFetchPlanReader` exported from `readers/__init__.py` and have FITS/JSON/ASDF inherit from it. Parquet overrides explicitly.

**Reader implementation contracts:**

- **FITS (`fits.py`):** lazy-import `astropy.io.fits` inside `read()`. Use `fits.open(io.BytesIO(data), memmap=False, ignore_missing_end=True)`. Iterate HDUs up to `max_headers`. Each header dict: `{"hdu": i, "name": hdu.name, ...}` with selected keys (`SIMPLE`, `BITPIX`, `NAXIS*`, `EXTNAME`, `OBJECT`, `DATE-OBS`). On `OSError`/`ValueError` from truncated input, return `HeaderResult(format="fits", headers=[{"error": "truncated"}])`. Inherits default `fetch_plan` (head 64 KiB).

- **ASDF (`asdf.py`):** Try `asdf.open(io.BytesIO(data), lazy_load=True, copy_arrays=False)` for the YAML tree. On failure, fall back to manual slice between `b"#ASDF"` and `b"...\n"` parsed via `yaml.safe_load`. Return `HeaderResult(format="asdf", headers=[<top-level tree keys>])`. Inherits default `fetch_plan`.

- **Parquet (`parquet.py`):** Override `fetch_plan(size)` to return `[(max(0, size - 65536), min(size, 65536))]` (footer slice; clamped for tiny files). `read()` uses `pyarrow.parquet.ParquetFile(pyarrow.BufferReader(data))`; on truncation/`OSError`/`pyarrow.lib.ArrowInvalid` returns `HeaderResult(format="parquet", headers=[{"error": "incomplete metadata"}])`.

- **JSON (`json.py`):** `json.loads(data.decode("utf-8", errors="replace"))`. Walk top-level keys to a single dict `{key: type_name(value)}`. Inherits default `fetch_plan`.

**Quicklook concat helper (`quicklook.py`):**

```python
def quicklook_from_s3(
    client: S3Client,
    bucket: str,
    key: str,
    size: int,
    *,
    first_bytes: bytes,
    max_headers: int = 1,
) -> HeaderResult:
    reader = _dispatch_reader(key, first_bytes)  # existing
    plan = reader.fetch_plan(size)
    chunks: list[bytes] = []
    for start, length in plan:
        chunks.append(client.range_get(bucket, key, start=start, length=length))
    return reader.read(b"".join(chunks), max_headers=max_headers)
```

Caller (peek + browser) provides `first_bytes` (the head slice) for dispatch and `size` (from `stat_object`).

**Tests proving it works:**
- Unskip 5 in `tests/test_quicklook.py`.
- New `tests/test_readers.py` covers per-reader happy path against the **realistic payloads** seeded into `populated_bucket` (see Step 6).
- New `tests/test_readers.py` adds the **4 robustness tests (item #3):**
  1. `test_fits_truncated_below_magic` — feed 4 bytes (less than 9-byte FITS magic), assert `read()` does not raise and returns a `HeaderResult` with an `error` field.
  2. `test_parquet_partial_footer_below_1kib` — feed 800 bytes ending with the Parquet `PAR1` magic but truncated metadata, assert `read()` returns `HeaderResult(format="parquet", headers=[{"error": ...}])` without raising.
  3. `test_range_get_past_eof_returns_empty` — call `client.range_get(bucket, small_key, start=999999, length=64)` and assert `b""` is returned (no 416 propagation).
  4. `test_dispatch_collision_uses_priority` — register two stub readers via `plugins.register_test_reader` (helper added under test fixture) both claiming the same magic; assert the higher-`priority` reader wins and a warning is logged.

**Acceptance criteria:**
- All 5 unskipped quicklook tests green.
- All 4 robustness tests green.
- Parquet path proves it round-trips against a real `pyarrow.parquet.write_table(...)` output (not just magic bytes).
- `mypy --strict` clean on all reader files.

### Step 3b — `presign` helpers

**File:** `src/s3peek/presign.py`

**Method signatures:**

```python
def parse_expiry(expiry_str: str) -> int:
    """Regex ^(\d+)([smhd])$; multipliers s=1, m=60, h=3600, d=86400.
    Raise ValueError on mismatch (already asserted in test_presign)."""

def generate_presigned_url(
    bucket: str,
    key: str,
    *,
    expiry_seconds: int = 3600,
    profile: str | None = None,
) -> str:
    """boto3.Session(profile_name=profile).client("s3").generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expiry_seconds)
    """

def copy_to_clipboard(text: str) -> None:
    """Best-effort: pyperclip.copy(text); on failure log warning, no raise.
    Skipped under TTY-less / headless CI."""
```

**Tests proving it works:**
- Unskip all 3 tests in `tests/test_presign.py` (`test_parse_expiry_seconds`, `test_parse_expiry_invalid_raises_value_error`, `test_generate_presigned_url_returns_https_under_moto`).

**Acceptance criteria:**
- All 3 green under moto.
- `parse_expiry` rejects empty string, `"1x"`, `"abc"`, `"-1h"`.

### Step 4 — `peek` and `ls` CLI commands + `_make_client` injection helper

**File:** `src/s3peek/cli.py`

**Implementation outline:**

```python
def _make_client(cfg: Config | None = None) -> tuple[S3Client, Config]:
    """Build the (client, cfg) pair used by every CLI command.

    Tests pass a clean Config(); production calls pass None and use Config.load().
    Lifted out of each command so tests can inject without touching the global
    Typer app surface.
    """
    cfg = cfg or Config.load()
    return S3Client(profile=cfg.aws_profile, region=cfg.aws_region), cfg


@app.command()
def peek(
    uri: str,
    output: str = "text",
    max_hdus: int = 1,
    _cfg: Config | None = None,  # test seam, hidden from --help via callback
) -> None:
    parsed = parse_s3_uri(uri)
    if parsed.is_prefix:
        raise typer.BadParameter("peek requires an object key")
    client, cfg = _make_client(_cfg)
    meta = client.stat_object(parsed.bucket, parsed.key)
    head = client.range_get(parsed.bucket, parsed.key, start=0, length=cfg.max_range_get_bytes)
    result = quicklook_from_s3(
        client, parsed.bucket, parsed.key, meta.size,
        first_bytes=head, max_headers=max_hdus,
    )
    if output == "json":
        typer.echo(json.dumps(asdict(result), default=str))
    else:
        render_header_result(result)


@app.command(name="ls")
def ls_command(
    uri: str,
    sort: str = "name",
    filter_glob: str | None = None,
    output: str = "text",
    _cfg: Config | None = None,
) -> None:
    parsed = parse_s3_uri(uri)
    client, cfg = _make_client(_cfg)
    metas = client.list_prefix(parsed.bucket, parsed.key)
    # apply glob filter, sort, render via Rich Table or json.dumps.
```

The `_cfg` seam is hidden from Typer's `--help` (use `typer.Argument(... hidden=True)` or a private kwarg with no `Annotated[...]` so Typer skips it). Tests call `peek.callback(_cfg=Config())` directly, OR use a dedicated helper `cli._test_invoke_peek(uri, _cfg=Config())`.

**Tests proving it works:**
- Rewrite URIs in `tests/test_cli.py` (item #6):
  - `s3://bucket/file.fits` → `s3://test-bucket/data/image.fits`
  - `s3://bucket/` → `s3://test-bucket/data/`
- Unskip `test_peek` and `test_ls`. Both gain the `populated_bucket` fixture and inject a clean `Config()` via `_make_client(cfg=Config())` (or via the test seam above).
- Add `test_peek_outputs_json_with_format_field` asserting `--output json` emits parseable JSON with `"format": "json"` for the seeded `data/sample.json`.

**Acceptance criteria:**
- `tests/test_cli.py::test_peek` and `::test_ls` green.
- `s3peek peek s3://test-bucket/data/sample.json --output json` (under moto) prints valid JSON containing `"format": "json"`.
- `s3peek ls s3://test-bucket/data/` lists all seeded objects (json, fits, parquet, asdf).
- `test_du`, `test_share`, and `test_firefly_connector_send` remain `@pytest.mark.skip(reason="out of scope: phase-2")`.

### Step 5 — Textual `S3Browser` with debounce + LRU + exception handling

**File:** `src/s3peek/browser.py`

**Layout:**
- Left pane: `DataTable` listing `ObjectMeta` (key, size, last_modified) for the current prefix. Shows `"Loading..."` placeholder before first list, `"No objects found"` if `list_prefix` returned `[]`.
- Right pane: `RichLog` showing the current selection's `HeaderResult` (or error message if hydration failed).
- Bottom: `Footer` with bindings.

**Implementation outline:**

```python
from collections import OrderedDict
import time

class S3Browser(App[None]):
    BINDINGS = [...]
    DEBOUNCE_MS = 120
    LRU_MAX = 64

    def __init__(self, uri: str, client: S3Client, cfg: Config):
        super().__init__()
        self.parsed = parse_s3_uri(uri)
        self.client = client
        self.cfg = cfg
        self._current_worker = None
        self._lru: OrderedDict[tuple[str, str, str], HeaderResult] = OrderedDict()
        self._last_focus_ts: float = 0.0

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield DataTable(id="objects")
            yield RichLog(id="preview")
        yield Footer()

    async def on_mount(self) -> None:
        self.query_one("#preview", RichLog).write("Loading...")
        self.run_worker(self._load_prefix, thread=True)

    def _load_prefix(self) -> None:
        try:
            metas = self.client.list_prefix(self.parsed.bucket, self.parsed.key)
        except (BucketNotFoundError, AccessDeniedError) as e:
            self.call_from_thread(self._show_error, str(e))
            return
        self.call_from_thread(self._populate_table, metas)
        if not metas:
            self.call_from_thread(self._show_empty)

    @on(DataTable.RowHighlighted)
    def _on_focus(self, event: DataTable.RowHighlighted) -> None:
        # Debounce: 120ms minimum between fired hydration workers.
        now = time.monotonic()
        if (now - self._last_focus_ts) * 1000 < self.DEBOUNCE_MS:
            self.set_timer(self.DEBOUNCE_MS / 1000, lambda: self._maybe_hydrate(event))
            return
        self._last_focus_ts = now
        self._maybe_hydrate(event)

    def _maybe_hydrate(self, event: DataTable.RowHighlighted) -> None:
        if self._current_worker is not None:
            self._current_worker.cancel()
        key = event.data_table.get_row(event.row_key)[0]
        self._current_worker = self.run_worker(
            lambda: self._hydrate(key), thread=True, exclusive=True,
            group="hydrate",
        )

    def _hydrate(self, key: str) -> None:
        if key.endswith("/"):
            return  # directory pseudo-row
        try:
            meta = self.client.stat_object(self.parsed.bucket, key)
        except (ObjectNotFoundError, AccessDeniedError) as e:
            self.call_from_thread(self._show_error, f"{key}: {e}")
            return

        cache_key = (self.parsed.bucket, key, meta.etag)
        if cache_key in self._lru:
            self._lru.move_to_end(cache_key)
            self.call_from_thread(self._show_preview, self._lru[cache_key])
            return

        # Fetch head slice for dispatch, then run reader's fetch_plan.
        body_iter = None
        try:
            head = self.client.range_get(
                self.parsed.bucket, key, start=0, length=self.cfg.max_range_get_bytes,
            )
            result = quicklook_from_s3(
                self.client, self.parsed.bucket, key, meta.size,
                first_bytes=head, max_headers=1,
            )
        except (ObjectNotFoundError, AccessDeniedError) as e:
            self.call_from_thread(self._show_error, f"{key}: {e}")
            return
        finally:
            # If a body was opened by range_get and the worker is being
            # cancelled mid-flight, ensure we close the streaming body.
            # range_get fully consumes body.read() on success, so this is
            # only needed on cancel; documented tradeoff: the cancelled
            # worker has already consumed bytes up to the cancel point,
            # but the HTTP connection is released back to the pool.
            if body_iter is not None:
                body_iter.close()

        self._lru[cache_key] = result
        if len(self._lru) > self.LRU_MAX:
            self._lru.popitem(last=False)
        self.call_from_thread(self._show_preview, result)

    def _show_empty(self) -> None:
        self.query_one("#preview", RichLog).clear()
        self.query_one("#preview", RichLog).write("No objects found")

    def _show_error(self, msg: str) -> None:
        self.query_one("#preview", RichLog).write(f"[red]{msg}[/red]")

    def _show_preview(self, result: HeaderResult) -> None:
        log = self.query_one("#preview", RichLog)
        log.clear()
        log.write(format_header_result_rich(result))
```

Plus an entry-point: `def run(uri: str) -> None:` so `cli.browse` becomes a one-liner: `S3Browser(uri, S3Client(...), Config.load()).run()`.

**Streaming body close on cancel (item #9):** the `try/finally` above documents the tradeoff. Real `boto3.client.get_object` returns a `StreamingBody`; in `range_get` we hold a reference to `resp["Body"]` and `body.close()` is invoked in `finally` before returning. On worker cancel, the bytes-up-to-cancel-point have already been consumed (accepted cost — TUI never displays them). The HTTP connection is returned to the boto3 connection pool.

**Tests proving it works (`tests/test_browser.py`, new):**
- `test_browser_lists_prefix_under_moto` — instantiate with `populated_bucket`, drive via `App.run_test()` pilot, assert table populated.
- `test_browser_focus_change_cancels_in_flight_worker` — spy on `worker.cancel`; focus row 0 then immediately row 1; assert cancel called once.
- `test_browser_hydrate_respects_max_range_get_bytes` — stub `S3Client.range_get` to record `length=` argument; assert no call exceeds `cfg.max_range_get_bytes`.
- `test_browser_lru_cache_hits_skip_range_get` — focus row 0 twice; assert second focus produces no new `range_get` call.
- `test_browser_debounce_collapses_fast_navigation` — fire 5 RowHighlighted events within 50ms; assert `_hydrate` runs at most twice (debounce throttles to 120ms).
- `test_browser_handles_object_not_found_without_crash` — stub `stat_object` to raise `ObjectNotFoundError`; assert app stays alive and preview pane shows the error message.
- `test_browser_empty_prefix_shows_no_objects_found` — point at empty prefix; assert "No objects found" rendered.

**Acceptance criteria:**
- `cli.browse` no longer raises `NotImplementedError`; launches the TUI when a TTY is attached.
- All 7 `test_browser.py` tests green.
- No call path in `_hydrate` requests more than `cfg.max_range_get_bytes` per range (asserted by stubbed client).
- `mypy --strict src/s3peek/browser.py` clean.
- Manual smoke (developer): `s3peek browse s3://<real-bucket>/<prefix>/` against an accessible bucket; arrow-key holds populate the right pane within 1s on a 1-MB FITS file; rapid arrow-key spam does not stack up workers.

### Step 6 — Test sweep + CI green

**File edits:**

1. **`tests/conftest.py` (item #5 + item #7):**
   - Add an autouse fixture that sets `monkeypatch.setenv("S3PEEK_CONFIG", "/dev/null")` for every test in the suite, so no developer's `~/.config/s3peek/config.toml` leaks.
   - Extend `populated_bucket` to also seed:
     - `data/table.parquet`: real bytes from `pyarrow.parquet.write_table(pa.table({"a": [1, 2], "b": ["x", "y"]}), buf)`.
     - `data/cube.asdf`: real bytes from `asdf.AsdfFile({"meta": {"name": "cube"}}).write_to(buf)`.
     - `data/image.fits` (replace the 80-byte stub) with real bytes from `astropy.io.fits.PrimaryHDU(data=numpy.zeros((4,4), dtype=numpy.float32)).writeto(buf)` (will be >1 KiB, satisfying item #7's >1 KiB requirement).
   - Existing `data/sample.json` stays.

2. **`tests/test_cli.py` (item #6):**
   - Replace `s3://bucket/file.fits` → `s3://test-bucket/data/image.fits`.
   - Replace `s3://bucket/` → `s3://test-bucket/data/`.
   - Add `populated_bucket` fixture to `test_peek` and `test_ls`. Pass `Config()` via `_make_client` injection (test invokes the underlying callable, not Typer's CLI runner, OR uses a `--config-path /dev/null` flag if added).
   - Remove `@pytest.mark.skip` from `test_peek` and `test_ls`.

3. **Unskip the 13 in-scope tests:**
   - `tests/test_s3.py`: 3 tests.
   - `tests/test_quicklook.py`: 5 tests.
   - `tests/test_presign.py`: 3 tests.
   - `tests/test_cli.py`: `test_peek` + `test_ls` (2 tests).
   - **Explicitly NOT unskipped (out of scope, item #12):** `tests/test_cli.py::test_du`, `tests/test_cli.py::test_share`, `tests/test_firefly.py::test_firefly_connector_send`. Their skip reasons get updated to `reason="out of scope: phase-2"`.

4. **New test files:**
   - `tests/test_uri.py` (Step 1).
   - `tests/test_readers.py` (Step 3a happy paths + 4 robustness tests).
   - `tests/test_browser.py` (Step 5).

5. **mypy & ruff:** `mypy --strict src` clean. `ruff check src tests` clean. Any unavoidable `# type: ignore[misc]` for boto3 paginators must include a reason comment (item #11).

**Definition of done for this step:**
- `pytest -v` reports 0 failed; skipped count is exactly 3 (`test_du`, `test_share`, `test_firefly_connector_send`).
- `ruff check src tests` clean.
- `mypy --strict src` clean.
- Manual smoke: arrow-key navigation in `s3peek browse` against a real bucket populates the right pane within 1s on a 1-MB FITS file.

---

## Success Criteria (overall)

- [ ] **Exactly 13** previously-skipped tests now pass; **3** out-of-scope skips remain explicit.
- [ ] **4 robustness tests** added (truncated FITS magic, partial Parquet footer, range_get past EOF, dispatch collision).
- [ ] New tests cover URI parsing, each reader against realistic payloads, debounce, LRU cache, and exception handling.
- [ ] `S3Client` is the sole place where `botocore.ClientError` is caught and translated to typed `S3PeekError` subclasses; etag quotes stripped; bounded retry/timeout config applied.
- [ ] `BaseReader` Protocol carries `fetch_plan` with sensible default; ParquetReader overrides for footer access.
- [ ] `browse` TUI never reads more than `Config.max_range_get_bytes` per range, debounces 120 ms, LRU-caches 64 results, and never crashes on `ObjectNotFoundError` / `AccessDeniedError`.
- [ ] `peek`, `ls`, `browse` work end-to-end against moto with realistic Parquet/ASDF/FITS payloads and against real S3 in a manual smoke check.
- [ ] CLI commands accept injectable `Config` for tests; `S3PEEK_CONFIG=/dev/null` autouse fixture ensures no config leak.
- [ ] No new top-level dependencies added.
- [ ] `mypy --strict src` and `ruff check src tests` pass on changed files.

---

## Out of Scope (explicit)

- `du`, `share`, and `firefly` CLI commands (presign helpers do land; clipboard/QR rendering in `share` does not). Their tests stay skipped with `reason="out of scope: phase-2"`.
- TUI download action (`d`), Firefly send (`f`), copy-URI (`c`), share (`s`), peek action (`p`) — `BINDINGS` stay declared, `action_*` methods stay `NotImplementedError`.
- Glob/regex object filters in the TUI search bar (CLI `ls --filter` is in scope).
- Cross-session caching of `HeaderResult`s (in-session LRU only).
- `--eager` listing flag (the `max_keys` plumbing is added but the Typer flag is not).

---

## Risk Notes

1. **Parquet footer access pattern** (now hidden behind `fetch_plan`). Range-from-end requires `stat_object` first to know object size. One HEAD per Parquet focus event. Acceptable; the LRU cache absorbs repeats.
2. **astropy import latency.** First `import astropy.io.fits` is ~300ms. Mitigation: lazy-import inside `FITSReader.read`, never at module top.
3. **Textual API drift.** `>=0.60` is broad; the worker/`call_from_thread` API has shifted. If CI flakes, pin a tested minor in a follow-up.
4. **Cancelled worker still consumed bytes.** A focus change cancels in-flight workers; the bytes already received are wasted. Quantified cost: at most one 64 KiB GET per cancel. On a requester-pays bucket that's $0.0036 per 1k cancels (S3 GET pricing). Acceptable; documented.
5. **Botocore retry/timeout tuning** (`connect_timeout=2`, `read_timeout=5`, `max_attempts=1`) is aggressive to meet the 1s budget. On a flaky network, single-attempt failures will surface in the preview pane as errors. Acceptable; better to show "Timed out" than to stall the TUI.

---

## Open Questions (deferred)

- Should the TUI cache survive across sessions (disk-backed)? Out of scope.
- Should `peek --output json` include `bytes_sampled` for reproducibility? Currently no.
- Is `du` worth landing in this phase since `sum_prefix_sizes` is a `list_prefix` reduction? Marked out; reconsider in phase-2.

---

## ADR (Architecture Decision Record)

**Decision:** Implement Option A — synchronous `S3Client` + Textual `@work(thread=True)` lazy hydration, with `BaseReader.fetch_plan` extension to handle Parquet's footer-from-end requirement at the reader layer (not the caller layer).

**Drivers (top 3):**
1. Per-navigation latency budget under 1 second on residential networks (drives bounded retry/timeout, debounce, LRU cache).
2. Locked `BaseReader.read(data: bytes, *, max_headers: int)` Protocol; new I/O patterns must be additive (drives `fetch_plan` extension).
3. Test acceptance grid: 13 in-scope skipped tests must turn green without disturbing 3 explicitly out-of-scope skips.

**Alternatives considered:**
- **Option B (aioboto3):** invalidated by zero-new-deps budget + sync Typer command surface (would require `asyncio.run` wrappers everywhere) + already-installed `mypy_boto3_s3` sync stubs. Re-considerable in a future async-rewrite phase.
- **Option C (pre-fetch all metadata):** invalidated by latency Driver #1 — large prefixes (10k+ objects) stall startup. The `max_keys` parameter on `list_prefix` keeps the door open for a future `--eager` flag without re-architecting.

**Why Option A was chosen:**
- Zero new deps; stays within the manifest already declared in `pyproject.toml`.
- boto3 sync API is the natural fit for Typer's sync command surface — `peek`, `ls`, `share`, `du`, `firefly` all stay simple synchronous functions.
- Textual's worker model (`@work(thread=True)` + `call_from_thread`) is first-class, cancellable, and well-documented.
- The `fetch_plan` Protocol extension removes the only caller-side format-specific code (the old plan had a Parquet special case in the TUI's `_hydrate`); now every reader self-describes its byte requirements.
- Bounded retry/timeout + debounce + LRU together hit the 1s latency target without dropping into async.

**Consequences (trade-offs):**
- Cancelled workers may have already consumed up to 64 KiB. On requester-pays buckets, fast scrolling costs ~$0.0036 per 1k cancels — acceptable, documented in Step 5.
- Single-attempt retry config means flaky networks surface "Timed out" in the preview pane instead of stalling. Better UX than blocking, but transient errors no longer auto-recover.
- The TUI carries a 64-entry LRU per session; memory cost is bounded (≤ 64 × ~10 KiB result objects = ~640 KiB).
- `mypy_boto3_s3` becomes a hard dev-dep requirement for `mypy --strict` to pass; it is already in `pyproject.toml:53` so no new spend.
- Adding `fetch_plan` to the Protocol with a default impl requires a small concrete `DefaultFetchPlanReader` base class for the runtime-checkable Protocol pattern; this is a tiny structural addition documented in Step 3a.

**Follow-ups (out of scope, tracked here):**
- Phase-2: implement `du`, `share` (with clipboard + QR), `firefly` send, TUI download/peek/copy actions.
- Phase-2: consider an `--eager` listing flag using the `max_keys` plumbing already in place.
- Phase-2: disk-backed cross-session header cache (today's LRU is in-session only).
- Phase-2: surface `bytes_sampled` in `peek --output json` for reproducibility.
- Future: revisit Option B (aioboto3) if/when other parts of s3peek go async.
