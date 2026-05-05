from __future__ import annotations

import io

from s3peek.readers import HeaderResult


class ParquetReader:
    extensions = (".parquet", ".pq")
    priority = 10

    def can_read(self, key: str, first_bytes: bytes) -> bool:
        return first_bytes[:4] == b"PAR1" or key.lower().endswith(self.extensions)

    def read(self, data: bytes, *, max_headers: int = 1) -> HeaderResult:
        import pyarrow.parquet as pq

        try:
            schema = pq.read_schema(io.BytesIO(data))
            fields = {f.name: str(f.type) for f in schema}
        except Exception:
            fields = {"note": "schema in footer; file too large for range-get preview"}
        return HeaderResult(format="parquet", headers=[fields])
