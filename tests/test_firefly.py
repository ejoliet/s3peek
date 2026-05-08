from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.skip(reason="requires a running Firefly server")
def test_firefly_connector_send() -> None:
    from s3peek.firefly import FireflyConnector

    connector = FireflyConnector("http://localhost:8080/firefly")
    url = connector.send(b"SIMPLE  = T" + b" " * 69, "test.fits")
    assert url.startswith("http")


def test_firefly_connector_passes_channel_override(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    class FakeFireflyClient:
        @staticmethod
        def make_client(**kwargs: object) -> object:
            calls.update(kwargs)
            return object()

    monkeypatch.setitem(
        sys.modules,
        "firefly_client",
        SimpleNamespace(FireflyClient=FakeFireflyClient),
    )

    from s3peek.firefly import FireflyConnector

    connector = FireflyConnector("http://localhost:8080/firefly", channel="science")

    assert connector.fc is not None
    assert calls == {
        "url": "http://localhost:8080/firefly",
        "channel_override": "science",
        "launch_browser": False,
    }


def test_firefly_connector_can_open_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    class FakeFireflyClient:
        @staticmethod
        def make_client(**kwargs: object) -> object:
            calls.update(kwargs)
            return object()

    monkeypatch.setitem(
        sys.modules,
        "firefly_client",
        SimpleNamespace(FireflyClient=FakeFireflyClient),
    )

    from s3peek.firefly import FireflyConnector

    FireflyConnector("http://localhost:8081/firefly", launch_browser=True)

    assert calls["launch_browser"] is True


def test_firefly_connector_send_uses_show_data_local_path(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    class FakeClient:
        def upload_data(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("send should let show_data handle uploads")

        def show_data(self, file_input: object, **kwargs: object) -> dict[str, bool]:
            calls["file_input"] = file_input
            calls["data"] = Path(str(file_input)).read_bytes()
            calls.update(kwargs)
            return {"success": True}

        def get_firefly_url(self) -> str:
            return "http://localhost:8081/firefly?__wsch=s3peek"

    class FakeFireflyClient:
        @staticmethod
        def make_client(**_kwargs: object) -> FakeClient:
            return FakeClient()

    monkeypatch.setitem(
        sys.modules,
        "firefly_client",
        SimpleNamespace(FireflyClient=FakeFireflyClient),
    )

    from s3peek.firefly import FireflyConnector

    url = FireflyConnector("http://localhost:8081/firefly").send(
        b"\\fixlen = T\n| ra | dec |\n| 1 | 2 |\n",
        "science/atlas-abell-test.tbl",
        preview=True,
    )

    assert url == "http://localhost:8081/firefly?__wsch=s3peek"
    assert str(calls["file_input"]).endswith(".tbl")
    assert calls["data"] == b"\\fixlen = T\n| ra | dec |\n| 1 | 2 |\n"
    assert calls["preview_metadata"] is True
    assert calls["title"] == "atlas-abell-test.tbl"


def test_firefly_connector_show_url_passes_url_to_show_data(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    class FakeClient:
        def show_data(self, file_input: object, **kwargs: object) -> dict[str, bool]:
            calls["file_input"] = file_input
            calls.update(kwargs)
            return {"success": True}

        def get_firefly_url(self) -> str:
            return "http://localhost:8081/firefly?__wsch=s3peek"

    class FakeFireflyClient:
        @staticmethod
        def make_client(**_kwargs: object) -> FakeClient:
            return FakeClient()

    monkeypatch.setitem(
        sys.modules,
        "firefly_client",
        SimpleNamespace(FireflyClient=FakeFireflyClient),
    )

    from s3peek.firefly import FireflyConnector

    presigned = "https://s3.amazonaws.com/bucket/file.asdf?X-Amz-Signature=abc"
    url = FireflyConnector("http://localhost:8081/firefly").show_url(
        presigned,
        preview=True,
        title="My File",
    )

    assert url == "http://localhost:8081/firefly?__wsch=s3peek"
    assert calls["file_input"] == presigned
    assert calls["preview_metadata"] is True
    assert calls["title"] == "My File"


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
