from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

import pytest

from s3peek.exceptions import InvalidURIError, ObjectNotFoundError
from s3peek.s3 import S3Client, parse_s3_uri


def test_s3_client_hydrates_boto3_client_lazily(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    class FakeSession:
        def __init__(self, **kwargs: object) -> None:
            calls.append(("session", kwargs))

        def client(self, service_name: str) -> object:
            calls.append(("client", service_name))
            return SimpleNamespace()

    monkeypatch.setattr("s3peek.s3.boto3.Session", FakeSession)

    client = S3Client(profile="science", region="us-west-2")

    assert calls == []
    assert client._s3 is client._s3
    assert calls == [
        ("session", {"profile_name": "science", "region_name": "us-west-2"}),
        ("client", "s3"),
    ]


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


def test_list_prefix(populated_bucket: object) -> None:
    client = S3Client()
    results = client.list_prefix("test-bucket", "data/")
    keys = {r.key for r in results}
    assert "data/sample.json" in keys
    assert "data/image.fits" in keys
    assert "data/spectrum.asdf" in keys


def test_stat_object(populated_bucket: object) -> None:
    client = S3Client()
    meta = client.stat_object("test-bucket", "data/sample.json")
    assert meta.key == "data/sample.json"
    assert meta.size == len(b'{"hello": "world"}')


def test_range_get(populated_bucket: object) -> None:
    client = S3Client()
    data = client.range_get("test-bucket", "data/sample.json", length=5)
    assert len(data) <= 5
    assert data == b'{"hel'


def test_download_object_to_fileobj(populated_bucket: object) -> None:
    client = S3Client()
    target = BytesIO()

    client.download_object_to_fileobj("test-bucket", "data/sample.json", target)

    assert target.getvalue() == b'{"hello": "world"}'


def test_sum_prefix_sizes(populated_bucket: object) -> None:
    client = S3Client()
    result = client.sum_prefix_sizes("test-bucket", "data/")
    assert result["count"] == 3
    assert result["total_bytes"] > 0


def test_stat_object_not_found(populated_bucket: object) -> None:
    client = S3Client()
    with pytest.raises(ObjectNotFoundError):
        client.stat_object("test-bucket", "data/missing.fits")
