from __future__ import annotations

import io

from s3peek.readers import HeaderResult


class ASDFReader:
    extensions = (".asdf",)
    priority = 10

    def can_read(self, key: str, first_bytes: bytes) -> bool:
        return first_bytes[:5] == b"#ASDF" or key.lower().endswith(self.extensions)

    def read(self, data: bytes, *, max_headers: int = 1) -> HeaderResult:
        import asdf  # type: ignore[import-untyped]

        with asdf.open(io.BytesIO(data)) as af:
            tree: dict[str, object] = {
                str(k): str(v) for k, v in af.tree.items() if not str(k).startswith("asdf")
            }
        return HeaderResult(format="asdf", headers=[tree])
