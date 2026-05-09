from __future__ import annotations

import fnmatch
import json
from pathlib import PurePosixPath
from tempfile import NamedTemporaryFile
from typing import Annotated

import typer

import s3peek
from s3peek import plugins
from s3peek.config import Config
from s3peek.presign import copy_to_clipboard, generate_presigned_url, parse_expiry
from s3peek.quicklook import quicklook
from s3peek.s3 import S3Client, parse_s3_uri

app = typer.Typer(name="s3peek", help="Terminal-first S3 browser for scientists.")


def _mount_plugins() -> None:
    for cmd_app in plugins.load_commands():
        app.add_typer(cmd_app)


_mount_plugins()


@app.command()
def version() -> None:
    """Print s3peek version and exit."""
    typer.echo(s3peek.__version__)


@app.command()
def browse(
    uri: Annotated[str, typer.Argument(help="S3 URI, e.g. s3://bucket/prefix/")],
) -> None:
    """Open interactive TUI browser."""
    raise NotImplementedError


@app.command()
def peek(
    uri: Annotated[str, typer.Argument(help="S3 URI of a single object.")],
    output: Annotated[str, typer.Option("--output", "-o", help="text or json")] = "text",
    max_hdus: Annotated[int, typer.Option("--max-hdus", help="Max HDUs to show")] = 1,
) -> None:
    """Inspect headers of a single S3 object."""
    bucket, key = parse_s3_uri(uri)
    cfg = Config.load()
    client = S3Client(profile=cfg.aws_profile, region=cfg.aws_region)
    meta = client.stat_object(bucket, key)
    data = client.range_get(bucket, key, length=cfg.max_range_get_bytes)
    result = quicklook(data, key, max_headers=max_hdus)
    if output == "json":
        typer.echo(
            json.dumps(
                {
                    "format": result.format,
                    "size": meta.size,
                    "headers": result.headers,
                }
            )
        )
    else:
        typer.echo(f"Format: {result.format}  Size: {meta.size}  s3://{bucket}/{key}")
        for i, hdr in enumerate(result.headers):
            if len(result.headers) > 1:
                typer.echo(f"--- HDU {i} ---")
            for k, v in hdr.items():
                typer.echo(f"  {k}: {v}")


@app.command()
def share(
    uri: Annotated[str, typer.Argument(help="S3 URI of the object to share.")],
    expiry: Annotated[str, typer.Option("--expiry", help="Expiry: 1h, 30m, 7d")] = "1h",
    qr: Annotated[bool, typer.Option("--qr", help="Print QR code")] = False,
) -> None:
    """Generate a pre-signed URL and copy it to clipboard."""
    bucket, key = parse_s3_uri(uri)
    cfg = Config.load()
    expiry_secs = parse_expiry(expiry)
    url = generate_presigned_url(bucket, key, expiry_seconds=expiry_secs, profile=cfg.aws_profile)
    try:
        copy_to_clipboard(url)
        typer.echo(f"Copied ({expiry}):")
    except Exception:
        pass
    typer.echo(url)
    if qr:
        import qrcode  # type: ignore[import-untyped]
        qr_obj = qrcode.QRCode()
        qr_obj.add_data(url)
        qr_obj.make(fit=True)
        qr_obj.print_ascii()


@app.command(name="ls")
def ls_command(
    uri: Annotated[str, typer.Argument(help="S3 URI prefix.")],
    sort: Annotated[str, typer.Option("--sort", help="name|size|date")] = "name",
    filter_glob: Annotated[str | None, typer.Option("--filter", help="Glob pattern")] = None,
    output: Annotated[str, typer.Option("--output", "-o")] = "text",
) -> None:
    """List objects under an S3 prefix."""
    bucket, prefix = parse_s3_uri(uri)
    cfg = Config.load()
    items = S3Client(profile=cfg.aws_profile, region=cfg.aws_region).list_prefix(
        bucket, prefix, delimiter=""
    )
    if filter_glob:
        items = [i for i in items if fnmatch.fnmatch(i.key, filter_glob)]
    sort_key = {"size": lambda x: x.size, "date": lambda x: x.last_modified}.get(
        sort, lambda x: x.key
    )
    items.sort(key=sort_key)
    if output == "json":
        typer.echo(
            json.dumps(
                [
                    {
                        "key": i.key,
                        "size": i.size,
                        "last_modified": i.last_modified.isoformat(),
                    }
                    for i in items
                ]
            )
        )
    else:
        for i in items:
            typer.echo(f"{i.size:>12}  {i.last_modified:%Y-%m-%d %H:%M}  s3://{bucket}/{i.key}")


@app.command()
def du(
    uri: Annotated[str, typer.Argument(help="S3 URI prefix.")],
    human_readable: Annotated[bool, typer.Option("--human-readable", "-h")] = True,
) -> None:
    """Summarize storage usage under an S3 prefix."""
    bucket, prefix = parse_s3_uri(uri)
    cfg = Config.load()
    result = S3Client(profile=cfg.aws_profile, region=cfg.aws_region).sum_prefix_sizes(
        bucket,
        prefix,
    )
    size, count = result["total_bytes"], result["count"]
    if human_readable:
        display_size = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if display_size < 1024 or unit == "TB":
                break
            display_size /= 1024
        typer.echo(f"{display_size:.1f} {unit}  ({count} objects)  s3://{bucket}/{prefix}")
    else:
        typer.echo(f"{result['total_bytes']}\t{count}\ts3://{bucket}/{prefix}")


_LARGE_FILE_THRESHOLD = 50 * 1024 * 1024  # 50 MB


def _should_auto_preview(key: str, size_bytes: int) -> bool:
    """Return True when Firefly's metadata picker improves the experience."""
    suffix = PurePosixPath(key).suffix.lower()
    return suffix == ".asdf" or size_bytes > _LARGE_FILE_THRESHOLD


@app.command()
def firefly(
    uri: Annotated[str, typer.Argument(help="S3 URI of the object to visualize.")],
    server: Annotated[str | None, typer.Option("--server", help="Firefly server URL")] = None,
    channel: Annotated[str | None, typer.Option("--channel", help="Browser tab channel")] = None,
    open_browser: Annotated[
        bool,
        typer.Option("--open-browser/--no-open-browser", help="Open Firefly in a browser tab (default: open)"),
    ] = True,
    preview: Annotated[
        bool | None,
        typer.Option("--preview/--no-preview", help="Metadata picker (default: auto for ASDF and files >50 MB)"),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Display title")] = None,
    presign: Annotated[
        bool,
        typer.Option("--presign/--no-presign", help="Use presigned URL (Firefly fetches from S3)"),
    ] = False,
    expiry: Annotated[
        str, typer.Option("--expiry", help="Presigned URL expiry: 1h, 30m, 7d")
    ] = "1h",
) -> None:
    """Send an S3 object to a Firefly visualization server."""
    from s3peek.firefly import FireflyConnector

    bucket, key = parse_s3_uri(uri)
    cfg = Config.load()
    server_url = server or cfg.firefly_url
    if not server_url:
        typer.echo("Error: --server required or set firefly_url in config", err=True)
        raise typer.Exit(1)
    filename = PurePosixPath(key).name or "object"
    client = S3Client(profile=cfg.aws_profile, region=cfg.aws_region)
    meta = client.stat_object(bucket, key)
    effective_preview = preview if preview is not None else _should_auto_preview(key, meta.size)
    fc = FireflyConnector(
        server_url,
        channel=channel or cfg.firefly_channel,
        launch_browser=open_browser,
    )
    if presign:
        typer.echo(f"Generating presigned URL for {filename}...")
        expiry_secs = parse_expiry(expiry)
        presigned_url = generate_presigned_url(
            bucket, key, expiry_seconds=expiry_secs, profile=cfg.aws_profile
        )
        typer.echo(f"Sending to Firefly at {server_url}...")
        url = fc.show_url(presigned_url, preview=effective_preview, title=title or filename)
    else:
        suffix = PurePosixPath(filename).suffix or ".dat"
        typer.echo(f"Downloading {filename}...")
        with NamedTemporaryFile(suffix=suffix) as tmp:
            client.download_object_to_fileobj(bucket, key, tmp.file)
            tmp.flush()
            typer.echo(f"Sending to Firefly at {server_url}...")
            url = fc.show_path(tmp.name, preview=effective_preview, title=title or filename)
    typer.echo(url)
