from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from s3peek.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("browse", "peek", "share", "ls", "du", "firefly", "version"):
        assert cmd in result.output


def test_firefly_help() -> None:
    result = runner.invoke(app, ["firefly", "--help"])
    assert result.exit_code == 0
    assert "--server" in result.output
    assert "--channel" in result.output
    assert "--open-browser" in result.output
    assert "--preview" in result.output
    assert "--title" in result.output
    assert "--presign" in result.output
    assert "--expiry" in result.output


def test_firefly_requires_server_or_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("FIREFLY_URL", raising=False)
    monkeypatch.setenv("S3PEEK_CONFIG", str(tmp_path / "missing.toml"))

    result = runner.invoke(app, ["firefly", "s3://test-bucket/data/image.fits"])

    assert result.exit_code == 1
    assert "Error: --server required or set firefly_url in config" in result.output


def test_firefly_sends_presigned_url_with_flag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    populated_bucket: object,
) -> None:
    calls: dict[str, object] = {}

    class FakeClient:
        def show_data(self, file_input: object, **kwargs: object) -> dict[str, bool]:
            calls["file_input"] = file_input
            calls.update(kwargs)
            return {"success": True}

        def get_firefly_url(self) -> str:
            return "http://localhost:8080/firefly?__wsch=science"

    class FakeFireflyClient:
        @staticmethod
        def make_client(**kwargs: object) -> FakeClient:
            calls["make_client"] = kwargs
            return FakeClient()

    monkeypatch.setenv("FIREFLY_URL", "http://localhost:8080/firefly")
    monkeypatch.setenv("FIREFLY_CHANNEL", "science")
    monkeypatch.setenv("S3PEEK_CONFIG", str(tmp_path / "missing.toml"))
    monkeypatch.setitem(
        sys.modules,
        "firefly_client",
        SimpleNamespace(FireflyClient=FakeFireflyClient),
    )

    result = runner.invoke(
        app,
        ["firefly", "s3://test-bucket/data/image.fits", "--presign", "--preview", "--title", "My FITS"],
    )

    assert result.exit_code == 0, result.output
    assert "Generating presigned URL" in result.output
    assert "Sending to Firefly" in result.output
    assert "http://localhost:8080/firefly?__wsch=science" in result.output
    file_input = calls["file_input"]
    assert isinstance(file_input, str)
    assert file_input.startswith("https://")
    assert calls["preview_metadata"] is True
    assert calls["title"] == "My FITS"


def test_firefly_downloads_and_streams_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    populated_bucket: object,
) -> None:
    calls: dict[str, object] = {}

    class FakeClient:
        def show_data(self, file_input: object, **kwargs: object) -> dict[str, bool]:
            path = Path(str(file_input))
            calls["file_input"] = path
            calls["data"] = path.read_bytes()
            calls["exists_during_show"] = path.exists()
            calls.update(kwargs)
            return {"success": True}

        def get_firefly_url(self) -> str:
            return "http://localhost:8080/firefly?__wsch=science"

    class FakeFireflyClient:
        @staticmethod
        def make_client(**kwargs: object) -> FakeClient:
            calls["make_client"] = kwargs
            return FakeClient()

    monkeypatch.setenv("FIREFLY_URL", "http://localhost:8080/firefly")
    monkeypatch.setenv("FIREFLY_CHANNEL", "science")
    monkeypatch.setenv("S3PEEK_CONFIG", str(tmp_path / "missing.toml"))
    monkeypatch.setitem(
        sys.modules,
        "firefly_client",
        SimpleNamespace(FireflyClient=FakeFireflyClient),
    )

    result = runner.invoke(
        app,
        [
            "firefly",
            "s3://test-bucket/data/image.fits",
            "--preview",
            "--title",
            "Local FITS",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Downloading image.fits" in result.output
    assert "Sending to Firefly" in result.output
    assert "http://localhost:8080/firefly?__wsch=science" in result.output
    assert calls["make_client"] == {
        "url": "http://localhost:8080/firefly",
        "channel_override": "science",
        "launch_browser": True,
    }
    assert calls["data"] == b"SIMPLE  = T" + b" " * 69
    assert calls["exists_during_show"] is True
    file_input = calls["file_input"]
    assert isinstance(file_input, Path)
    assert file_input.suffix == ".fits"
    assert not file_input.exists()
    assert calls["preview_metadata"] is True
    assert calls["title"] == "Local FITS"


def test_should_auto_preview_asdf() -> None:
    from s3peek.cli import _should_auto_preview

    assert _should_auto_preview("data/spectrum.asdf", 0) is True
    assert _should_auto_preview("data/CUBE.ASDF", 0) is True


def test_should_auto_preview_large_file() -> None:
    from s3peek.cli import _should_auto_preview

    large = 51 * 1024 * 1024
    assert _should_auto_preview("data/image.fits", large) is True
    assert _should_auto_preview("data/image.fits", 1024) is False


def test_firefly_auto_preview_asdf(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    populated_bucket: object,
) -> None:
    calls: dict[str, object] = {}

    class FakeClient:
        def show_data(self, file_input: object, **kwargs: object) -> dict[str, bool]:
            calls["file_input"] = file_input
            calls.update(kwargs)
            return {"success": True}

        def get_firefly_url(self) -> str:
            return "http://localhost:8080/firefly?__wsch=science"

    class FakeFireflyClient:
        @staticmethod
        def make_client(**kwargs: object) -> FakeClient:
            return FakeClient()

    monkeypatch.setenv("FIREFLY_URL", "http://localhost:8080/firefly")
    monkeypatch.setenv("FIREFLY_CHANNEL", "science")
    monkeypatch.setenv("S3PEEK_CONFIG", str(tmp_path / "missing.toml"))
    monkeypatch.setitem(sys.modules, "firefly_client", SimpleNamespace(FireflyClient=FakeFireflyClient))

    result = runner.invoke(app, ["firefly", "s3://test-bucket/data/spectrum.asdf"])

    assert result.exit_code == 0, result.output
    assert calls["preview_metadata"] is True


def test_firefly_auto_preview_large_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    populated_bucket: object,
) -> None:
    calls: dict[str, object] = {}

    class FakeClient:
        def show_data(self, file_input: object, **kwargs: object) -> dict[str, bool]:
            calls["file_input"] = file_input
            calls.update(kwargs)
            return {"success": True}

        def get_firefly_url(self) -> str:
            return "http://localhost:8080/firefly?__wsch=science"

    class FakeFireflyClient:
        @staticmethod
        def make_client(**kwargs: object) -> FakeClient:
            return FakeClient()

    monkeypatch.setenv("FIREFLY_URL", "http://localhost:8080/firefly")
    monkeypatch.setenv("FIREFLY_CHANNEL", "science")
    monkeypatch.setenv("S3PEEK_CONFIG", str(tmp_path / "missing.toml"))
    monkeypatch.setitem(sys.modules, "firefly_client", SimpleNamespace(FireflyClient=FakeFireflyClient))

    from s3peek import s3 as s3_module

    monkeypatch.setattr(
        s3_module.S3Client,
        "stat_object",
        lambda self, bucket, key: SimpleNamespace(size=60 * 1024 * 1024),
    )

    result = runner.invoke(app, ["firefly", "s3://test-bucket/data/image.fits"])

    assert result.exit_code == 0, result.output
    assert calls["preview_metadata"] is True


def test_firefly_no_preview_overrides_auto(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    populated_bucket: object,
) -> None:
    calls: dict[str, object] = {}

    class FakeClient:
        def show_data(self, file_input: object, **kwargs: object) -> dict[str, bool]:
            calls["file_input"] = file_input
            calls.update(kwargs)
            return {"success": True}

        def get_firefly_url(self) -> str:
            return "http://localhost:8080/firefly?__wsch=science"

    class FakeFireflyClient:
        @staticmethod
        def make_client(**kwargs: object) -> FakeClient:
            return FakeClient()

    monkeypatch.setenv("FIREFLY_URL", "http://localhost:8080/firefly")
    monkeypatch.setenv("FIREFLY_CHANNEL", "science")
    monkeypatch.setenv("S3PEEK_CONFIG", str(tmp_path / "missing.toml"))
    monkeypatch.setitem(sys.modules, "firefly_client", SimpleNamespace(FireflyClient=FakeFireflyClient))

    result = runner.invoke(app, ["firefly", "s3://test-bucket/data/spectrum.asdf", "--no-preview"])

    assert result.exit_code == 0, result.output
    assert calls["preview_metadata"] is False


def test_peek_json(populated_bucket: object) -> None:
    result = runner.invoke(app, ["peek", "s3://test-bucket/data/sample.json"])
    assert result.exit_code == 0, result.output
    assert "json" in result.output
    assert "hello" in result.output


def test_ls(populated_bucket: object) -> None:
    result = runner.invoke(app, ["ls", "s3://test-bucket/data/"])
    assert result.exit_code == 0, result.output
    assert "sample.json" in result.output
    assert "image.fits" in result.output


@pytest.mark.skip(reason="not yet implemented")
def test_du() -> None:
    result = runner.invoke(app, ["du", "s3://bucket/"])
    assert result.exit_code == 0


@pytest.mark.skip(reason="not yet implemented")
def test_share() -> None:
    result = runner.invoke(app, ["share", "s3://bucket/file.fits"])
    assert result.exit_code == 0
