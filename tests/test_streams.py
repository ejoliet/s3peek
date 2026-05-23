from __future__ import annotations

from unittest.mock import MagicMock

import pytest  # noqa: I001

from s3peek.streams import _READ_ALL_GUARD_BYTES, SeekableS3Stream


def _make_stream(data: bytes, chunk_size: int = 16) -> tuple[SeekableS3Stream, MagicMock]:
    client = MagicMock()
    size = len(data)

    def fake_range_get(bucket: str, key: str, *, start: int = 0, length: int = 65536) -> bytes:
        return data[start : start + length]

    client.range_get.side_effect = fake_range_get
    stream = SeekableS3Stream(client, "bucket", "key", size=size, chunk_size=chunk_size)
    return stream, client


def test_seek_and_read_calls_range_get_correct_range() -> None:
    data = b"0123456789abcdef"
    stream, client = _make_stream(data, chunk_size=16)
    stream.seek(4)
    result = stream.read(6)
    assert result == b"456789"
    client.range_get.assert_called_once_with("bucket", "key", start=0, length=16)


def test_seek_end_positions_at_eof() -> None:
    data = b"hello world"
    stream, _ = _make_stream(data)
    pos = stream.seek(0, 2)
    assert pos == len(data)
    assert stream.tell() == len(data)


def test_seek_cur_advances_position() -> None:
    data = b"abcdefghij"
    stream, _ = _make_stream(data)
    stream.seek(3)
    stream.seek(2, 1)
    assert stream.tell() == 5


def test_chunk_cache_avoids_double_fetch() -> None:
    data = b"x" * 32
    stream, client = _make_stream(data, chunk_size=16)
    stream.seek(0)
    stream.read(8)
    stream.seek(0)
    stream.read(8)
    assert client.range_get.call_count == 1


def test_read_past_eof_returns_empty() -> None:
    data = b"short"
    stream, _ = _make_stream(data)
    stream.seek(0, 2)
    assert stream.read(10) == b""


def test_seekable_and_readable() -> None:
    data = b"data"
    stream, _ = _make_stream(data)
    assert stream.seekable() is True
    assert stream.readable() is True


def test_read_all_guard_raises_for_large_stream() -> None:
    large_size = _READ_ALL_GUARD_BYTES + 1
    client = MagicMock()
    stream = SeekableS3Stream(client, "bucket", "key", size=large_size, chunk_size=65536)
    with pytest.raises(OSError, match="read\\(-1\\)"):
        stream.read(-1)


def test_read_all_small_stream_returns_full_content() -> None:
    data = b"small content"
    stream, _ = _make_stream(data, chunk_size=64)
    result = stream.read(-1)
    assert result == data


def test_readinto_advances_position() -> None:
    data = b"abcdefgh"
    stream, _ = _make_stream(data, chunk_size=16)
    buf = bytearray(4)
    n = stream.readinto(buf)
    assert n == 4
    assert bytes(buf) == b"abcd"
    assert stream.tell() == 4
