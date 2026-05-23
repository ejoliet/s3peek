from __future__ import annotations

import io

from s3peek import plugins
from s3peek.readers import HeaderResult


def quicklook(
    data: bytes | io.RawIOBase,
    key: str,
    *,
    max_headers: int = 1,
    deep: bool = False,
) -> HeaderResult:
    first_bytes = data[:512] if isinstance(data, bytes) else data.read(512)
    if not isinstance(data, bytes):
        data.seek(0)
    for reader in plugins.load_readers():
        if reader.can_read(key, first_bytes):
            return reader.read(data, max_headers=max_headers, deep=deep)
    return HeaderResult(format="unknown", headers=[{}])
