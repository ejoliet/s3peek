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
