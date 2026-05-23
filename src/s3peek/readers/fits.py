from __future__ import annotations

import io

from s3peek.readers import HeaderResult

# AIDEV-NOTE: Raw FITS card parser — no astropy in quicklook fast path (CLAUDE.md invariant).
# FITS header: 80-byte fixed-width records; keyword 8 chars, value indicator '=' at pos 8,
# value field pos 10–79, comment after '/'. Header ends at END card or 2880-byte block edge.
# deep=True opt-in: uses astropy.io.fits for full multi-HDU extraction (deep-inspect mode only).
_CARD_LEN = 80
_BLOCK_LEN = 2880


class FITSReader:
    extensions = (".fits", ".fit", ".fz", ".fits.gz")
    priority = 10

    def can_read(self, key: str, first_bytes: bytes) -> bool:
        return first_bytes[:9] == b"SIMPLE  =" or key.lower().endswith(self.extensions)

    def read(
        self,
        data: bytes | io.RawIOBase,
        *,
        max_headers: int = 1,
        deep: bool = False,
        **_kwargs: object,
    ) -> HeaderResult:
        if deep:
            return self._read_deep(data, max_headers)
        raw = data if isinstance(data, bytes) else data.read()
        return self._read_fast(raw)

    def _read_fast(self, data: bytes) -> HeaderResult:
        """Raw single-HDU card parse — quicklook hot path, no astropy."""
        cards: dict[str, object] = {}
        for offset in range(0, len(data), _CARD_LEN):
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

    def _read_deep(self, data: bytes | io.RawIOBase, max_headers: int) -> HeaderResult:
        """Full multi-HDU extraction via astropy — deep-inspect mode only."""
        import astropy.io.fits  # AIDEV-NOTE: lazy import — keep out of fast-path module scope

        headers: list[dict[str, object]] = []
        try:
            # AIDEV-NOTE: If data is already a seekable stream (SeekableS3Stream),
            # pass it directly so astropy issues Range-GETs on demand instead of
            # reading a truncated bytes buffer. BytesIO wrap only for bytes input.
            stream: io.IOBase = data if isinstance(data, io.IOBase) else io.BytesIO(data)
            with astropy.io.fits.open(
                stream,
                ignore_missing_simple=True,
                memmap=False,
            ) as hdul:
                for hdu in hdul[:max_headers]:
                    headers.append(dict(hdu.header))
        except Exception as exc:
            headers = [{"_parse_error": f"{type(exc).__name__}: {exc}"}]
        return HeaderResult(format="fits", headers=headers)
