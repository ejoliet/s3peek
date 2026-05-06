from __future__ import annotations

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
            self.fc.show_data(
                tmp.name,
                preview_metadata=preview,
                title=title or filename,
            )
        return cast(str, self.fc.get_firefly_url())
