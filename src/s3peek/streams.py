from __future__ import annotations

import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from s3peek.s3 import S3Client

# AIDEV-NOTE: SeekableS3Stream issues S3 Range-GETs on demand as the caller seeks/reads.
# Chunks are cached by chunk_index to avoid re-fetching adjacent regions during sequential
# reads (e.g. astropy scanning HDU headers one block at a time).
# The 10 MB guard on read(-1) prevents accidental full-file downloads — callers should
# always use seek()+read(n) for specific ranges. The guard fires only for unbounded reads
# where the remaining file exceeds 10 MB; partial tail reads below the threshold are fine.
_READ_ALL_GUARD_BYTES = 10 * 1024 * 1024  # 10 MB


class SeekableS3Stream(io.RawIOBase):
    """Seekable file-like object backed by S3 Range-GETs.

    Issues Range-GETs on demand as the caller seeks/reads.
    Uses a simple chunk cache (chunk_size granularity) to avoid
    re-fetching adjacent regions.
    """

    def __init__(
        self,
        client: S3Client,
        bucket: str,
        key: str,
        size: int,
        chunk_size: int = 262144,
    ) -> None:
        super().__init__()
        self._client = client
        self._bucket = bucket
        self._key = key
        self._size = size
        self._chunk_size = chunk_size
        self._pos = 0
        self._cache: dict[int, bytes] = {}

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    def tell(self) -> int:
        return self._pos

    def seek(self, pos: int, whence: int = 0) -> int:
        if whence == 0:
            self._pos = pos
        elif whence == 1:
            self._pos += pos
        elif whence == 2:
            self._pos = self._size + pos
        else:
            raise ValueError(f"Invalid whence value: {whence}")
        self._pos = max(0, min(self._pos, self._size))
        return self._pos

    def readinto(self, b: bytearray | memoryview) -> int:  # type: ignore[override]  # deliberately narrow: io machinery only passes bytearray/memoryview; widening to Buffer buys nothing
        n = len(b)
        data = self._read_range(self._pos, n)
        actual = len(data)
        b[:actual] = data
        self._pos += actual
        return actual

    def read(self, n: int = -1) -> bytes:
        if self._pos >= self._size:
            return b""
        if n == -1 or n is None:
            remaining = self._size - self._pos
            if remaining > _READ_ALL_GUARD_BYTES:
                raise OSError(
                    f"read(-1) would fetch {remaining:,} bytes from S3 "
                    f"(object size {self._size:,}). Use seek()+read(n) to fetch specific "
                    f"ranges. To read the full file, increase _READ_ALL_GUARD_BYTES or "
                    f"use explicit reads."
                )
            n = remaining
        data = self._read_range(self._pos, n)
        self._pos += len(data)
        return data

    def _read_range(self, start: int, length: int) -> bytes:
        """Fetch bytes [start, start+length) using chunk cache."""
        if length <= 0 or start >= self._size:
            return b""
        end = min(start + length, self._size)
        result = bytearray()
        pos = start
        while pos < end:
            chunk_idx = pos // self._chunk_size
            chunk_start = chunk_idx * self._chunk_size
            if chunk_idx not in self._cache:
                fetch_len = min(self._chunk_size, self._size - chunk_start)
                self._cache[chunk_idx] = self._client.range_get(
                    self._bucket,
                    self._key,
                    start=chunk_start,
                    length=fetch_len,
                )
            chunk = self._cache[chunk_idx]
            offset_in_chunk = pos - chunk_start
            bytes_from_chunk = min(len(chunk) - offset_in_chunk, end - pos)
            result += chunk[offset_in_chunk : offset_in_chunk + bytes_from_chunk]
            pos += bytes_from_chunk
        return bytes(result)
