from __future__ import annotations

from io import BytesIO
from typing import cast

_FITS_MAGIC = b"SIMPLE  ="
_FITS_EXTENSIONS = (".fits", ".fit", ".fz", ".fits.gz")


class FireflyConnector:
    def __init__(self, server_url: str, channel: str | None = None) -> None:
        try:
            from firefly_client import FireflyClient
        except ImportError as exc:
            raise ImportError(
                "Firefly integration requires firefly_client. "
                "Run: pip install 's3peek[firefly]'"
            ) from exc
        self.fc = FireflyClient.make_client(url=server_url, channel=channel)

    def send(
        self,
        data: bytes,
        key: str,
        *,
        preview: bool = False,
        title: str | None = None,
        file_type: str = "auto",
    ) -> str:
        """Upload data to Firefly and display it. Returns the Firefly browser URL."""
        is_fits = data[:9] == _FITS_MAGIC or key.lower().endswith(_FITS_EXTENSIONS)
        data_type = "FITS" if is_fits else "UNKNOWN"
        file_on_server = self.fc.upload_data(BytesIO(data), data_type)
        self.fc.show_data(
            file_on_server,
            preview_metadata=preview,
            title=title or key.split("/")[-1],
        )
        return cast(str, self.fc.get_firefly_url())
