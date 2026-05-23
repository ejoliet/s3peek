from __future__ import annotations

import io


def _make_fits_bytes() -> bytes:
    import astropy.io.fits

    primary = astropy.io.fits.PrimaryHDU()
    primary.header["INSTRUME"] = "TEST"
    buf = io.BytesIO()
    astropy.io.fits.HDUList([primary]).writeto(buf)
    return buf.getvalue()


def _make_asdf_bytes() -> bytes:
    import asdf

    buf = io.BytesIO()
    with asdf.AsdfFile({"instrument": "TEST"}) as af:
        af.write_to(buf)
    return buf.getvalue()


def test_fits_deep_with_bytesio_stream() -> None:
    from s3peek.readers.fits import FITSReader

    data = _make_fits_bytes()
    result = FITSReader()._read_deep(io.BytesIO(data), max_headers=1)
    assert result.format == "fits"
    assert len(result.headers) == 1
    assert result.headers[0].get("INSTRUME") == "TEST"


def test_asdf_deep_with_bytesio_stream() -> None:
    from s3peek.readers.asdf import ASDFReader

    data = _make_asdf_bytes()
    result = ASDFReader()._read_deep(io.BytesIO(data))
    assert result.format == "asdf"
    assert len(result.headers) == 1
    assert result.headers[0].get("instrument") == "TEST"


def test_fits_deep_with_bytes() -> None:
    from s3peek.readers.fits import FITSReader

    data = _make_fits_bytes()
    result = FITSReader()._read_deep(data, max_headers=1)
    assert result.format == "fits"
    assert result.headers[0].get("INSTRUME") == "TEST"


def test_asdf_deep_with_bytes() -> None:
    from s3peek.readers.asdf import ASDFReader

    data = _make_asdf_bytes()
    result = ASDFReader()._read_deep(data)
    assert result.format == "asdf"
    assert result.headers[0].get("instrument") == "TEST"


def test_fits_deep_stream_returns_header_result() -> None:
    from s3peek.readers import HeaderResult
    from s3peek.readers.fits import FITSReader

    data = _make_fits_bytes()
    result = FITSReader()._read_deep(io.BytesIO(data), max_headers=1)
    assert isinstance(result, HeaderResult)


def test_asdf_deep_stream_returns_header_result() -> None:
    from s3peek.readers import HeaderResult
    from s3peek.readers.asdf import ASDFReader

    data = _make_asdf_bytes()
    result = ASDFReader()._read_deep(io.BytesIO(data))
    assert isinstance(result, HeaderResult)
