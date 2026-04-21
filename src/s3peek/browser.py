from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header


class S3Browser(App[None]):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("p", "peek", "Peek"),
        ("s", "share", "Share"),
        ("c", "copy_uri", "Copy URI"),
        ("d", "download", "Download"),
        ("f", "firefly", "Firefly"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def action_peek(self) -> None:
        raise NotImplementedError

    def action_share(self) -> None:
        raise NotImplementedError

    def action_copy_uri(self) -> None:
        raise NotImplementedError

    def action_download(self) -> None:
        raise NotImplementedError

    def action_firefly(self) -> None:
        raise NotImplementedError
