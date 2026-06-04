from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class HeaderResult:
    format: str
    headers: list[dict[str, object]] = field(default_factory=list)


@runtime_checkable
class BaseReader(Protocol):
    extensions: tuple[str, ...]
    priority: int

    def can_read(self, key: str, first_bytes: bytes) -> bool: ...
    def read(  # noqa: E501
        self,
        data: bytes | io.RawIOBase,
        *,
        max_headers: int = 1,
        deep: bool = False,
        **_kwargs: object,
    ) -> HeaderResult: ...
