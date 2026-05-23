from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock

from s3peek.browser import S3Browser, _fmt_size
from s3peek.config import Config
from s3peek.s3 import ObjectMeta


def _fake_cfg(**kwargs) -> Config:
    defaults = dict(
        aws_profile=None,
        aws_region="us-east-1",
        max_range_get_bytes=65536,
        presign_expiry_seconds=3600,
        theme="dark",
        firefly_url=None,
        firefly_channel=None,
    )
    defaults.update(kwargs)
    return Config(**defaults)


def _fake_client(prefixes=None, objects=None, range_data=b"") -> MagicMock:
    client = MagicMock()
    client.list_dir.return_value = (prefixes or [], objects or [])
    client.range_get.return_value = range_data
    client.stat_object.return_value = ObjectMeta(
        key="obj.fits",
        size=100,
        last_modified=datetime(2024, 1, 1, tzinfo=timezone.utc),
        storage_class="STANDARD",
        etag="abc",
    )
    return client


def _make_app(client=None, cfg=None, bucket="test-bucket", prefix="") -> S3Browser:
    return S3Browser(
        client=client or _fake_client(),
        cfg=cfg or _fake_cfg(),
        bucket=bucket,
        prefix=prefix,
    )


def _obj(key: str, size: int = 512) -> ObjectMeta:
    return ObjectMeta(
        key=key,
        size=size,
        last_modified=datetime(2024, 1, 1, tzinfo=timezone.utc),
        storage_class="STANDARD",
        etag="abc",
    )


def _status(app: S3Browser) -> str:
    from textual.widgets import Label
    return str(app.query_one("#status", Label).content)


# --- Unit tests (sync) ---

def test_normalize_prefix_adds_trailing_slash():
    app = _make_app(prefix="some/path")
    assert app.prefix == "some/path/"


def test_normalize_prefix_empty_stays_empty():
    app = _make_app(prefix="")
    assert app.prefix == ""


def test_normalize_prefix_already_trailing_slash():
    app = _make_app(prefix="some/path/")
    assert app.prefix == "some/path/"


def test_fmt_size_bytes():
    assert _fmt_size(500) == "500 B"


def test_fmt_size_kb():
    assert _fmt_size(2048) == "2 KB"


def test_fmt_size_none():
    assert _fmt_size(None) == "-"


def test_fmt_size_gb():
    assert _fmt_size(2 * 1024**3) == "2 GB"


# --- Pilot (async Textual) tests via asyncio.run ---

def test_quit():
    async def _run():
        app = _make_app()
        async with app.run_test() as pilot:
            await pilot.press("q")

    asyncio.run(_run())


def test_listing_renders_rows():
    async def _run():
        from textual.widgets import DataTable
        objects = [_obj("data/file.fits", 1024)]
        prefixes = ["data/sub/"]
        client = _fake_client(prefixes=prefixes, objects=objects)
        app = _make_app(client=client, prefix="data/")
        async with app.run_test() as pilot:
            await pilot.pause(delay=0.3)
            table = app.query_one("#objects", DataTable)
            assert table.row_count == 2  # 1 prefix + 1 object

    asyncio.run(_run())


def test_empty_prefix_shows_status():
    async def _run():
        client = _fake_client(prefixes=[], objects=[])
        app = _make_app(client=client)
        async with app.run_test() as pilot:
            await pilot.pause(delay=0.3)
            assert "(empty)" in _status(app)

    asyncio.run(_run())


def test_copy_uri_sets_status(monkeypatch):
    async def _run():
        objects = [_obj("myfile.fits")]
        client = _fake_client(objects=objects)
        captured: list[str] = []
        monkeypatch.setattr("s3peek.presign.copy_to_clipboard", lambda s: captured.append(s))
        app = _make_app(client=client, bucket="b")
        async with app.run_test() as pilot:
            await pilot.pause(delay=0.3)
            await pilot.press("c")
            await pilot.pause(delay=0.1)
            status = _status(app)
            assert "s3://b/myfile.fits" in status or captured == ["s3://b/myfile.fits"]

    asyncio.run(_run())


def test_navigate_into_prefix():
    async def _run():
        prefixes = ["data/sub/"]
        client = _fake_client(prefixes=prefixes, objects=[])
        client.list_dir.side_effect = [
            (prefixes, []),
            ([], []),
        ]
        app = _make_app(client=client, prefix="data/")
        async with app.run_test() as pilot:
            await pilot.pause(delay=0.3)
            await pilot.press("enter")
            await pilot.pause(delay=0.3)
            assert app.prefix == "data/sub/"
            assert "data/" in app.history

    asyncio.run(_run())


def test_back_navigation():
    async def _run():
        client = _fake_client(prefixes=["data/"], objects=[])
        client.list_dir.side_effect = [
            (["data/"], []),
            ([], []),
            (["data/"], []),
        ]
        app = _make_app(client=client, prefix="")
        async with app.run_test() as pilot:
            await pilot.pause(delay=0.3)
            await pilot.press("enter")
            await pilot.pause(delay=0.2)
            assert app.prefix == "data/"
            await pilot.press("backspace")
            await pilot.pause(delay=0.2)
            assert app.prefix == ""

    asyncio.run(_run())


def test_listing_error_keeps_prior_table():
    """On ListingFailed, existing table rows remain visible."""
    from s3peek.exceptions import AccessDeniedError

    async def _run():
        from textual.widgets import DataTable
        objects = [_obj("good.fits")]
        client = _fake_client()
        client.list_dir.side_effect = [
            ([], objects),
            AccessDeniedError("denied"),
        ]
        app = _make_app(client=client)
        async with app.run_test() as pilot:
            await pilot.pause(delay=0.3)
            table = app.query_one("#objects", DataTable)
            assert table.row_count == 1

            await pilot.press("r")
            await pilot.pause(delay=0.3)
            assert table.row_count == 1
            status = _status(app)
            assert any(word in status for word in ("403", "Access", "denied"))

    asyncio.run(_run())


def test_firefly_no_url_shows_status():
    async def _run():
        client = _fake_client()
        app = _make_app(client=client, cfg=_fake_cfg(firefly_url=None))
        async with app.run_test() as pilot:
            await pilot.pause(delay=0.1)
            await pilot.press("f")
            await pilot.pause(delay=0.1)
            status = _status(app)
            assert "firefly_url" in status.lower() or "not configured" in status.lower()

    asyncio.run(_run())


def test_peek_on_prefix_shows_status():
    async def _run():
        prefixes = ["data/sub/"]
        client = _fake_client(prefixes=prefixes, objects=[])
        app = _make_app(client=client)
        async with app.run_test() as pilot:
            await pilot.pause(delay=0.3)
            await pilot.press("p")
            await pilot.pause(delay=0.1)
            status = _status(app)
            assert "prefix" in status.lower() or "object" in status.lower()

    asyncio.run(_run())


# --- CLI integration test ---

def test_browse_cli_constructs_app(monkeypatch):
    """browse() constructs S3Browser with correct args and calls run()."""
    from typer.testing import CliRunner

    from s3peek.cli import app as cli_app

    ran: list[dict] = []

    class FakeApp:
        def __init__(self, *, client, cfg, bucket, prefix):
            ran.append({"bucket": bucket, "prefix": prefix})

        def run(self):
            pass

    monkeypatch.setattr("s3peek.browser.S3Browser", FakeApp)
    monkeypatch.setattr("s3peek.cli.S3Client", lambda **kw: MagicMock())

    runner = CliRunner()
    result = runner.invoke(cli_app, ["browse", "s3://my-bucket/my/prefix/"])
    assert result.exit_code == 0
    assert ran[0]["bucket"] == "my-bucket"
    assert ran[0]["prefix"] == "my/prefix/"
