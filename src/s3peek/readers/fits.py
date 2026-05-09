from __future__ import annotations

import io
from typing import cast

from s3peek.readers import HeaderResult


class FITSReader:
    extensions = (".fits", ".fit", ".fz", ".fits.gz")
    priority = 10

    def can_read(self, key: str, first_bytes: bytes) -> bool:
        return first_bytes[:9] == b"SIMPLE  =" or key.lower().endswith(self.extensions)

    def read(self, data: bytes, *, max_headers: int = 1) -> HeaderResult:
        from astropy.io import fits  # type: ignore[import-untyped]

        with fits.open(io.BytesIO(data), ignore_missing_simple=True) as hdus:
            headers = [cast(dict[str, object], dict(hdu.header)) for hdu in hdus[:max_headers]]
        return HeaderResult(format="fits", headers=headers)
