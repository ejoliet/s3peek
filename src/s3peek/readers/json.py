from __future__ import annotations

import json

from s3peek.readers import HeaderResult


class JSONReader:
    extensions = (".json",)
    priority = 10

    def can_read(self, key: str, first_bytes: bytes) -> bool:
        return key.lower().endswith(self.extensions)

    def read(self, data: bytes, *, max_headers: int = 1) -> HeaderResult:
        obj = json.loads(data)
        if isinstance(obj, dict):
            hdr = {k: str(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            hdr = {"type": "array", "length": str(len(obj))}
        else:
            hdr = {"value": str(obj)}
        return HeaderResult(format="json", headers=[hdr])
