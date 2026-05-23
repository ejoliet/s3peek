from __future__ import annotations

import io

from s3peek.readers import HeaderResult

# AIDEV-NOTE: Raw ASDF header parser — no asdf lib in quicklook path (CLAUDE.md invariant).
# ASDF files begin with '#ASDF X.Y.Z\n' then YAML key-value pairs until '...' or binary block.
# Parses only scalar key: value lines; skips asdf_* internal keys and comment lines.
# deep=True opt-in: uses asdf.open() for full tree extraction (deep-inspect mode only).


class ASDFReader:
    extensions = (".asdf",)
    priority = 10

    def can_read(self, key: str, first_bytes: bytes) -> bool:
        return first_bytes[:5] == b"#ASDF" or key.lower().endswith(self.extensions)

    def read(
        self,
        data: bytes | io.RawIOBase,
        *,
        max_headers: int = 1,
        deep: bool = False,
        **_kwargs: object,
    ) -> HeaderResult:
        if deep:
            return self._read_deep(data)
        raw = data if isinstance(data, bytes) else data.read()
        return self._read_fast(raw)

    def _read_fast(self, data: bytes) -> HeaderResult:
        """Lightweight raw YAML parse — quicklook hot path, no asdf lib."""
        tree: dict[str, object] = {}
        error: str | None = None
        try:
            text = data[:8192].decode("utf-8", errors="replace")
            for line in text.splitlines():
                if line.startswith("...") or line.startswith("\x00"):
                    break
                if line.startswith("#") or ":" not in line:
                    continue
                k, _, v = line.partition(":")
                k = k.strip()
                if k and not k.startswith("asdf") and not k.startswith("%"):
                    tree[k] = v.strip()
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        if error:
            tree["_parse_error"] = error
        return HeaderResult(format="asdf", headers=[tree])

    def _read_deep(self, data: bytes | io.RawIOBase) -> HeaderResult:
        """Full header extraction via asdf.open() — deep-inspect mode only."""
        import asdf  # AIDEV-NOTE: lazy import — keep out of fast-path module scope

        tree: dict[str, object] = {}
        try:
            # AIDEV-NOTE: lazy_load=True is load-bearing — peek --deep is a header
            # inspector; array blocks must never be materialized into memory.
            # _force_raw_types=True keeps tagged objects as TaggedDict/TaggedList
            # so _to_plain can detect them via _tag without loading converters.
            # If data is already a seekable stream (SeekableS3Stream), pass it directly
            # so asdf issues Range-GETs on demand instead of reading a truncated buffer.
            stream: io.IOBase = data if isinstance(data, io.IOBase) else io.BytesIO(data)
            with asdf.open(
                stream,
                mode="r",
                lazy_load=True,
                memmap=False,
                ignore_unrecognized_tag=True,
                _force_raw_types=True,
            ) as af:
                tree = _to_plain(af.tree)  # type: ignore[arg-type]
        except Exception as exc:
            tree = {"_parse_error": f"{type(exc).__name__}: {exc}"}
        return HeaderResult(format="asdf", headers=[tree])


def _to_plain(obj: object) -> object:
    # AIDEV-NOTE: With _force_raw_types=True, ASDF ndarray blocks arrive as TaggedDict
    # carrying _tag with "ndarray". Detect via tag first — never expand array payload.
    # The __iter__ fallback is intentionally absent: duck-typing iterables caused
    # element-wise recursion over numpy arrays (recursion bomb on large blocks).
    if getattr(obj, "_tag", None) and "ndarray" in str(obj._tag):
        return {
            "__ndarray__": True,
            "shape": list(obj.get("shape") or ()),  # type: ignore[union-attr]
            "dtype": str(obj.get("datatype", "unknown")),  # type: ignore[union-attr]
        }
    # AIDEV-NOTE: Defensive guard for live numpy/NDArrayType — only fires if
    # _force_raw_types=True is ever removed or a future code path bypasses it.
    if hasattr(obj, "shape") and hasattr(obj, "dtype"):
        return {
            "__ndarray__": True,
            "shape": list(getattr(obj, "shape", ()) or ()),
            "dtype": str(getattr(obj, "dtype", "unknown")),
        }
    if hasattr(obj, "items"):
        return {str(k): _to_plain(v) for k, v in obj.items()}  # type: ignore[union-attr]
    # TaggedList MRO: TaggedList -> UserList -> list; iteration via UserList.__iter__
    # correctly yields .data contents (confirmed against asdf 5.3.0).
    if isinstance(obj, (list, tuple)):
        return [_to_plain(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, bytes):
        return obj.decode("utf-8", "replace")
    return repr(obj)
