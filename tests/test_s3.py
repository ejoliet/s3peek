from __future__ import annotations

import pytest


@pytest.mark.skip(reason="not yet implemented")
def test_list_prefix(populated_bucket) -> None:  # type: ignore[misc]
    from s3peek.s3 import S3Client

    client = S3Client()
    results = client.list_prefix("test-bucket", "data/")
    assert len(results) > 0


@pytest.mark.skip(reason="not yet implemented")
def test_stat_object(populated_bucket) -> None:  # type: ignore[misc]
    from s3peek.s3 import S3Client

    client = S3Client()
    meta = client.stat_object("test-bucket", "data/sample.json")
    assert meta.key == "data/sample.json"


@pytest.mark.skip(reason="not yet implemented")
def test_range_get(populated_bucket) -> None:  # type: ignore[misc]
    from s3peek.s3 import S3Client

    client = S3Client()
    data = client.range_get("test-bucket", "data/sample.json", length=64)
    assert len(data) <= 64
