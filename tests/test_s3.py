from __future__ import annotations

import pytest

from s3peek.exceptions import InvalidURIError, ObjectNotFoundError
from s3peek.s3 import S3Client, parse_s3_uri


def test_parse_s3_uri_valid() -> None:
    bucket, key = parse_s3_uri("s3://my-bucket/path/to/file.fits")
    assert bucket == "my-bucket"
    assert key == "path/to/file.fits"


def test_parse_s3_uri_root_prefix() -> None:
    bucket, key = parse_s3_uri("s3://my-bucket/")
    assert bucket == "my-bucket"
    assert key == ""


def test_parse_s3_uri_invalid() -> None:
    with pytest.raises(InvalidURIError):
        parse_s3_uri("https://not-s3/bucket/key")


def test_list_prefix(populated_bucket) -> None:  # type: ignore[misc]
    client = S3Client()
    results = client.list_prefix("test-bucket", "data/")
    assert len(results) == 2
    keys = {r.key for r in results}
    assert "data/sample.json" in keys
    assert "data/image.fits" in keys


def test_stat_object(populated_bucket) -> None:  # type: ignore[misc]
    client = S3Client()
    meta = client.stat_object("test-bucket", "data/sample.json")
    assert meta.key == "data/sample.json"
    assert meta.size == len(b'{"hello": "world"}')


def test_range_get(populated_bucket) -> None:  # type: ignore[misc]
    client = S3Client()
    data = client.range_get("test-bucket", "data/sample.json", length=5)
    assert len(data) <= 5
    assert data == b'{"hel'


def test_sum_prefix_sizes(populated_bucket) -> None:  # type: ignore[misc]
    client = S3Client()
    result = client.sum_prefix_sizes("test-bucket", "data/")
    assert result["count"] == 2
    assert result["total_bytes"] > 0


def test_stat_object_not_found(populated_bucket) -> None:  # type: ignore[misc]
    client = S3Client()
    with pytest.raises(ObjectNotFoundError):
        client.stat_object("test-bucket", "data/missing.fits")
