from __future__ import annotations

import pytest


@pytest.mark.skip(reason="not yet implemented")
def test_generate_presigned_url() -> None:
    from s3peek.presign import generate_presigned_url

    url = generate_presigned_url("bucket", "key.fits", expiry_seconds=3600)
    assert url.startswith("https://")


@pytest.mark.skip(reason="not yet implemented")
def test_parse_expiry() -> None:
    from s3peek.presign import parse_expiry

    assert parse_expiry("1h") == 3600
    assert parse_expiry("30m") == 1800
    assert parse_expiry("7d") == 604_800


@pytest.mark.skip(reason="not yet implemented")
def test_parse_expiry_invalid() -> None:
    from s3peek.presign import parse_expiry

    with pytest.raises(ValueError):
        parse_expiry("bad")
