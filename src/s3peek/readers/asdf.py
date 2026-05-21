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
        self, data: bytes, *, max_headers: int = 1, deep: bool = False, **_kwargs: object
    ) -> HeaderResult:
        if deep:
            return self._read_deep(data)
        return self._read_fast(data)

    def _read_fast(self, data: bytes) -> HeaderResult:
        """Lightweight raw YAML parse — quicklook hot path, no asdf lib."""
        tree: dict[str, object] = {}
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
        except Exception:
            pass
        return HeaderResult(format="asdf", headers=[tree])

    def _read_deep(self, data: bytes) -> HeaderResult:
        """Full header extraction via asdf.open() — deep-inspect mode only."""
        import asdf  # AIDEV-NOTE: lazy import — keep out of fast-path module scope

        tree: dict[str, object] = {}
        try:
            with asdf.open(
                io.BytesIO(data),
                mode="r",
                lazy_load=False,
                memmap=False,
                ignore_unrecognized_tag=True,
                _force_raw_types=True,
            ) as af:
                tree = _to_plain(af.tree)
        except Exception:
            pass
        return HeaderResult(format="asdf", headers=[tree])


def _to_plain(obj: object) -> object:
    # AIDEV-NOTE: TaggedDict/TaggedList extend UserDict/UserList — JSON encoder hits the
    # empty underlying dict, not .data. Recurse via .items()/.data to get actual content.
    if hasattr(obj, "items"):
        return {str(k): _to_plain(v) for k, v in obj.items()}  # type: ignore[union-attr]
    if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
        return [_to_plain(v) for v in obj]  # type: ignore[union-attr]
    return obj
