from __future__ import annotations

from s3peek.readers import HeaderResult

# AIDEV-NOTE: Raw FITS card parser — no astropy in quicklook path (CLAUDE.md invariant).
# FITS header: 80-byte fixed-width records; keyword 8 chars, value indicator '=' at pos 8,
# value field pos 10–79, comment after '/'. Header ends at END card or 2880-byte block edge.
_CARD_LEN = 80
_BLOCK_LEN = 2880


class FITSReader:
    extensions = (".fits", ".fit", ".fz", ".fits.gz")
    priority = 10

    def can_read(self, key: str, first_bytes: bytes) -> bool:
        return first_bytes[:9] == b"SIMPLE  =" or key.lower().endswith(self.extensions)

    def read(self, data: bytes, *, max_headers: int = 1, **_kwargs: object) -> HeaderResult:
        cards: dict[str, object] = {}
        limit = min(len(data), _BLOCK_LEN * max_headers)
        for offset in range(0, limit, _CARD_LEN):
            card = data[offset : offset + _CARD_LEN]
            if len(card) < _CARD_LEN:
                break
            try:
                raw_key = card[:8].decode("ascii", errors="replace").strip()
            except Exception:
                continue
            if raw_key == "END":
                break
            if card[8:9] == b"=":
                raw_val = card[10:].decode("ascii", errors="replace")
                val = raw_val.split("/")[0].strip().strip("'").strip()
                if raw_key:
                    cards[raw_key] = val
        return HeaderResult(format="fits", headers=[cards])
