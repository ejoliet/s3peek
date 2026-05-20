from __future__ import annotations

from s3peek.readers import HeaderResult

# AIDEV-NOTE: Raw ASDF header parser — no asdf lib in quicklook path (CLAUDE.md invariant).
# ASDF files begin with '#ASDF X.Y.Z\n' then YAML key-value pairs until '...' or binary block.
# Parses only scalar key: value lines; skips asdf_* internal keys and comment lines.


class ASDFReader:
    extensions = (".asdf",)
    priority = 10

    def can_read(self, key: str, first_bytes: bytes) -> bool:
        return first_bytes[:5] == b"#ASDF" or key.lower().endswith(self.extensions)

    def read(self, data: bytes, *, max_headers: int = 1) -> HeaderResult:
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
