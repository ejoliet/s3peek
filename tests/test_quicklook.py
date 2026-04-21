from __future__ import annotations

import pytest


@pytest.mark.skip(reason="not yet implemented")
def test_quicklook_fits() -> None:
    from s3peek.quicklook import quicklook

    data = b"SIMPLE  = T" + b" " * 69
    result = quicklook(data, "image.fits")
    assert result.format == "fits"


@pytest.mark.skip(reason="not yet implemented")
def test_quicklook_asdf() -> None:
    from s3peek.quicklook import quicklook

    data = b"#ASDF 1.0.0\n"
    result = quicklook(data, "file.asdf")
    assert result.format == "asdf"


@pytest.mark.skip(reason="not yet implemented")
def test_quicklook_parquet() -> None:
    from s3peek.quicklook import quicklook

    data = b"PAR1" + b"\x00" * 100
    result = quicklook(data, "table.parquet")
    assert result.format == "parquet"


@pytest.mark.skip(reason="not yet implemented")
def test_quicklook_json() -> None:
    from s3peek.quicklook import quicklook

    data = b'{"key": "value"}'
    result = quicklook(data, "meta.json")
    assert result.format == "json"


@pytest.mark.skip(reason="not yet implemented")
def test_quicklook_unknown_format() -> None:
    from s3peek.quicklook import quicklook

    result = quicklook(b"\x00\x01\x02\x03", "file.bin")
    assert result.format == "unknown"
