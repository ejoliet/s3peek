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


def test_firefly_requires_server_or_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("FIREFLY_URL", raising=False)
    monkeypatch.setenv("S3PEEK_CONFIG", str(tmp_path / "missing.toml"))

    result = runner.invoke(app, ["firefly", "s3://test-bucket/data/image.fits"])

    assert result.exit_code == 1
    assert "Error: --server required or set firefly_url in config" in result.output


def test_firefly_streams_s3_object_to_local_firefly(
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
    assert "http://localhost:8080/firefly?__wsch=science" in result.output
    assert calls["make_client"] == {
        "url": "http://localhost:8080/firefly",
        "channel_override": "science",
        "launch_browser": False,
    }
    assert calls["data"] == b"SIMPLE  = T" + b" " * 69
    assert calls["exists_during_show"] is True
    file_input = calls["file_input"]
    assert isinstance(file_input, Path)
    assert file_input.suffix == ".fits"
    assert not file_input.exists()
    assert calls["preview_metadata"] is True
    assert calls["title"] == "Local FITS"


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
