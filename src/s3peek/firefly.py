from __future__ import annotations

from os import PathLike
from pathlib import PurePosixPath
from tempfile import NamedTemporaryFile
from typing import cast


class FireflyConnector:
    def __init__(
        self,
        server_url: str,
        channel: str | None = None,
        *,
        launch_browser: bool = False,
    ) -> None:
        try:
            from firefly_client import FireflyClient
        except ImportError as exc:
            raise ImportError(
                "Firefly integration requires firefly_client. "
                "Run: pip install 's3peek[firefly]'"
            ) from exc
        self.fc = FireflyClient.make_client(
            url=server_url,
            channel_override=channel,
            launch_browser=launch_browser,
        )

    def send(
        self,
        data: bytes,
        key: str,
        *,
        preview: bool = False,
        title: str | None = None,
    ) -> str:
        """Upload data to Firefly and display it. Returns the Firefly browser URL."""
        filename = PurePosixPath(key).name
        suffix = PurePosixPath(filename).suffix or ".dat"
        with NamedTemporaryFile(suffix=suffix) as tmp:
            tmp.write(data)
            tmp.flush()
            return self.show_path(
                tmp.name,
                preview=preview,
                title=title or filename,
            )

    def show_path(
        self,
        path: str | PathLike[str],
        *,
        preview: bool = False,
        title: str | None = None,
    ) -> str:
        """Display a local file path in Firefly. Returns the Firefly browser URL."""
        self.fc.show_data(
            str(path),
            preview_metadata=preview,
            title=title,
        )
        return cast(str, self.fc.get_firefly_url())
