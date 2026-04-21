from __future__ import annotations

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
    assert "--preview" in result.output


@pytest.mark.skip(reason="not yet implemented")
def test_peek() -> None:
    result = runner.invoke(app, ["peek", "s3://bucket/file.fits"])
    assert result.exit_code == 0


@pytest.mark.skip(reason="not yet implemented")
def test_ls() -> None:
    result = runner.invoke(app, ["ls", "s3://bucket/"])
    assert result.exit_code == 0


@pytest.mark.skip(reason="not yet implemented")
def test_du() -> None:
    result = runner.invoke(app, ["du", "s3://bucket/"])
    assert result.exit_code == 0


@pytest.mark.skip(reason="not yet implemented")
def test_share() -> None:
    result = runner.invoke(app, ["share", "s3://bucket/file.fits"])
    assert result.exit_code == 0
