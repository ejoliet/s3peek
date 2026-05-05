from __future__ import annotations

from s3peek.readers import HeaderResult


class ASDFReader:
    extensions = (".asdf",)
    priority = 10

    def can_read(self, key: str, first_bytes: bytes) -> bool:
        return first_bytes[:5] == b"#ASDF" or key.lower().endswith(self.extensions)

    def read(self, data: bytes, *, max_headers: int = 1) -> HeaderResult:
        raise NotImplementedError
