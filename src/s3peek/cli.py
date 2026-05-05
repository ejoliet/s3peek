from __future__ import annotations

from typing import Annotated

import typer

import s3peek
from s3peek import plugins

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
    raise NotImplementedError


@app.command()
def share(
    uri: Annotated[str, typer.Argument(help="S3 URI of the object to share.")],
    expiry: Annotated[str, typer.Option("--expiry", help="Expiry: 1h, 30m, 7d")] = "1h",
    qr: Annotated[bool, typer.Option("--qr", help="Print QR code")] = False,
) -> None:
    """Generate a pre-signed URL and copy it to clipboard."""
    raise NotImplementedError


@app.command(name="ls")
def ls_command(
    uri: Annotated[str, typer.Argument(help="S3 URI prefix.")],
    sort: Annotated[str, typer.Option("--sort", help="name|size|date")] = "name",
    filter_glob: Annotated[str | None, typer.Option("--filter", help="Glob pattern")] = None,
    output: Annotated[str, typer.Option("--output", "-o")] = "text",
) -> None:
    """List objects under an S3 prefix."""
    raise NotImplementedError


@app.command()
def du(
    uri: Annotated[str, typer.Argument(help="S3 URI prefix.")],
    human_readable: Annotated[bool, typer.Option("--human-readable", "-h")] = True,
) -> None:
    """Summarize storage usage under an S3 prefix."""
    raise NotImplementedError


@app.command()
def firefly(
    uri: Annotated[str, typer.Argument(help="S3 URI of the object to visualize.")],
    server: Annotated[str | None, typer.Option("--server", help="Firefly server URL")] = None,
    channel: Annotated[str | None, typer.Option("--channel", help="Browser tab channel")] = None,
    preview: Annotated[bool, typer.Option("--preview", help="Show metadata picker first")] = False,
    title: Annotated[str | None, typer.Option("--title", help="Display title")] = None,
) -> None:
    """Send an S3 object to a Firefly visualization server."""
    raise NotImplementedError
