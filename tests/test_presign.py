from __future__ import annotations

import pytest

from s3peek.presign import generate_presigned_url, parse_expiry


def test_parse_expiry() -> None:
    assert parse_expiry("1h") == 3600
    assert parse_expiry("30m") == 1800
    assert parse_expiry("7d") == 604_800


def test_parse_expiry_invalid() -> None:
    with pytest.raises(ValueError):
        parse_expiry("bad")


def test_generate_presigned_url(populated_bucket) -> None:  # type: ignore[misc]
    url = generate_presigned_url("test-bucket", "data/sample.json", expiry_seconds=3600)
    assert "test-bucket" in url
    assert "sample.json" in url
