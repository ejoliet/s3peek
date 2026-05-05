from __future__ import annotations

from s3peek import plugins
from s3peek.readers import HeaderResult


def quicklook(data: bytes, key: str, *, max_headers: int = 1) -> HeaderResult:
    first_bytes = data[:512]
    for reader in plugins.load_readers():
        if reader.can_read(key, first_bytes):
            return reader.read(data, max_headers=max_headers)
    return HeaderResult(format="unknown", headers=[{}])
