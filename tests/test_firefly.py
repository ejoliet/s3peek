from __future__ import annotations

import pytest

pytest.importorskip("firefly_client", reason="s3peek[firefly] not installed")


@pytest.mark.skip(reason="requires a running Firefly server")
def test_firefly_connector_send() -> None:
    from s3peek.firefly import FireflyConnector

    connector = FireflyConnector("http://localhost:8080/firefly")
    url = connector.send(b"SIMPLE  = T" + b" " * 69, "test.fits")
    assert url.startswith("http")


def test_firefly_import_error_without_package(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def mock_import(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name == "firefly_client":
            raise ImportError("No module named 'firefly_client'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    from s3peek.firefly import FireflyConnector

    with pytest.raises(ImportError, match="pip install"):
        FireflyConnector("http://localhost:8080/firefly")
