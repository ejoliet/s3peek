from __future__ import annotations

from s3peek.readers import HeaderResult


class FITSReader:
    extensions = (".fits", ".fit", ".fz", ".fits.gz")
    priority = 10

    def can_read(self, key: str, first_bytes: bytes) -> bool:
        return first_bytes[:9] == b"SIMPLE  =" or key.lower().endswith(self.extensions)

    def read(self, data: bytes, *, max_headers: int = 1) -> HeaderResult:
        raise NotImplementedError
