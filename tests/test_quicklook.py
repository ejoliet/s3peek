from __future__ import annotations


def test_quicklook_fits() -> None:
    from s3peek.quicklook import quicklook

    data = b"SIMPLE  = T" + b" " * 69
    result = quicklook(data, "image.fits")
    assert result.format == "fits"


def test_quicklook_asdf() -> None:
    from s3peek.quicklook import quicklook

    data = b"#ASDF 1.0.0\n"
    result = quicklook(data, "file.asdf")
    assert result.format == "asdf"


def test_quicklook_parquet() -> None:
    from s3peek.quicklook import quicklook

    data = b"PAR1" + b"\x00" * 100
    result = quicklook(data, "table.parquet")
    assert result.format == "parquet"


def test_quicklook_json() -> None:
    from s3peek.quicklook import quicklook

    data = b'{"key": "value"}'
    result = quicklook(data, "meta.json")
    assert result.format == "json"


def test_quicklook_unknown_format() -> None:
    from s3peek.quicklook import quicklook

    result = quicklook(b"\x00\x01\x02\x03", "file.bin")
    assert result.format == "unknown"


def test_asdf_deep_read_full_tree() -> None:
    import io

    import asdf

    from s3peek.readers.asdf import ASDFReader

    tree = {"meta": {"telescope": "Roman", "instrument": {"name": "WFI", "detector": "WFI01"}}}
    buf = io.BytesIO()
    with asdf.AsdfFile(tree) as af:
        af.write_to(buf)
    data = buf.getvalue()

    result = ASDFReader().read(data, deep=True)
    assert result.format == "asdf"
    assert "meta" in result.headers[0]
    assert result.headers[0]["meta"]["telescope"] == "Roman"


def test_asdf_deep_includes_asdf_keys() -> None:
    import io

    import asdf

    from s3peek.readers.asdf import ASDFReader

    buf = io.BytesIO()
    with asdf.AsdfFile({"x": 1}) as af:
        af.write_to(buf)
    data = buf.getvalue()

    result = ASDFReader().read(data, deep=True)
    assert "asdf_library" in result.headers[0]


def test_quicklook_asdf_deep_flag() -> None:
    import io

    import asdf

    from s3peek.quicklook import quicklook

    buf = io.BytesIO()
    with asdf.AsdfFile({"nested": {"a": 1, "b": [1, 2, 3]}}) as af:
        af.write_to(buf)
    data = buf.getvalue()

    result = quicklook(data, "file.asdf", deep=True)
    assert result.format == "asdf"
    assert "nested" in result.headers[0]


def test_asdf_deep_numpy_array_summarized() -> None:
    """Arrays must never be expanded element-wise — regression test for recursion bomb."""
    import io

    import asdf
    import numpy as np

    from s3peek.readers.asdf import ASDFReader

    arr = np.zeros((100, 100), dtype="float32")
    buf = io.BytesIO()
    with asdf.AsdfFile({"data": arr}) as af:
        af.write_to(buf)
    data = buf.getvalue()

    result = ASDFReader().read(data, deep=True)
    array_node = result.headers[0]["data"]
    assert isinstance(array_node, dict), "array must be summarized, not expanded"
    assert array_node["__ndarray__"] is True
    assert array_node["shape"] == [100, 100]
    assert "float" in array_node["dtype"]


def test_asdf_deep_tagged_list_preserved() -> None:
    """TaggedList contents must be preserved, not silently emptied."""
    import io

    import asdf

    from s3peek.readers.asdf import ASDFReader

    buf = io.BytesIO()
    with asdf.AsdfFile({"steps": ["a", "b", "c"]}) as af:
        af.write_to(buf)
    data = buf.getvalue()

    result = ASDFReader().read(data, deep=True)
    assert result.headers[0]["steps"] == ["a", "b", "c"]


def test_asdf_deep_error_surfaced() -> None:
    """Truncated/corrupt bytes must return _parse_error key, not silent empty dict."""
    from s3peek.readers.asdf import ASDFReader

    result = ASDFReader().read(b"#ASDF 1.0.0\ntruncated", deep=True)
    assert "_parse_error" in result.headers[0]


def test_fits_deep_multi_hdu() -> None:
    """--deep must return multiple HDU headers via astropy."""
    import io

    import astropy.io.fits
    import numpy as np

    from s3peek.readers.fits import FITSReader

    primary = astropy.io.fits.PrimaryHDU()
    primary.header["TELESCOP"] = "Roman"
    ext = astropy.io.fits.ImageHDU(data=np.zeros((10, 10), dtype="int16"))
    ext.header["EXTNAME"] = "SCI"
    buf = io.BytesIO()
    astropy.io.fits.HDUList([primary, ext]).writeto(buf)
    data = buf.getvalue()

    result = FITSReader().read(data, max_headers=2, deep=True)
    assert result.format == "fits"
    assert len(result.headers) == 2
    assert result.headers[0].get("TELESCOP") == "Roman"
    assert result.headers[1].get("EXTNAME") == "SCI"


def test_fits_deep_respects_max_headers() -> None:
    """max_headers must cap HDU count even when more exist."""
    import io

    import astropy.io.fits
    import numpy as np

    from s3peek.readers.fits import FITSReader

    hdul = astropy.io.fits.HDUList([
        astropy.io.fits.PrimaryHDU(),
        astropy.io.fits.ImageHDU(data=np.zeros((4, 4), dtype="int16")),
        astropy.io.fits.ImageHDU(data=np.zeros((4, 4), dtype="int16")),
    ])
    buf = io.BytesIO()
    hdul.writeto(buf)
    data = buf.getvalue()

    result = FITSReader().read(data, max_headers=1, deep=True)
    assert len(result.headers) == 1
