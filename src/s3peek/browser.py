from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import botocore.exceptions
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.message import Message
from textual.widgets import DataTable, Footer, Header, Label, Static

from s3peek.exceptions import AccessDeniedError, BucketNotFoundError

if TYPE_CHECKING:
    from s3peek.config import Config
    from s3peek.s3 import ObjectMeta, S3Client


@dataclass
class Entry:
    name: str
    key: str
    size: int | None
    last_modified: datetime | None
    is_prefix: bool


class ListingReady(Message):
    def __init__(self, prefix: str, prefixes: list[str], objects: list[ObjectMeta]) -> None:
        self.prefix = prefix
        self.prefixes = prefixes
        self.objects = objects
        super().__init__()


class ListingFailed(Message):
    def __init__(self, prefix: str, error: Exception) -> None:
        self.prefix = prefix
        self.error = error
        super().__init__()


class QuicklookReady(Message):
    def __init__(self, key: str, text: str) -> None:
        self.key = key
        self.text = text
        super().__init__()


class QuicklookFailed(Message):
    def __init__(self, key: str, error: Exception) -> None:
        self.key = key
        self.error = error
        super().__init__()


class S3Browser(App[None]):
    DEFAULT_CSS = """
    Screen {
        layout: vertical;
    }
    #breadcrumb {
        height: 1;
        background: $boost;
        color: $text-muted;
        padding: 0 1;
    }
    #body {
        layout: horizontal;
        height: 1fr;
    }
    #objects {
        width: 2fr;
    }
    #qp {
        width: 1fr;
        border-left: solid $primary;
        padding: 0 1;
        display: none;
    }
    #qp.visible {
        display: block;
    }
    #status {
        height: 1;
        background: $boost;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("p", "peek", "Peek"),
        Binding("d", "deep_peek", "Deep"),
        Binding("s", "share", "Share"),
        Binding("c", "copy_uri", "Copy URI"),
        Binding("f", "firefly", "Firefly"),
        Binding("backspace", "back", "Back"),
        Binding("u", "back", "Back", show=False),
        Binding("r", "reload", "Reload"),
        # AIDEV-TODO: implement filter action (v2)
    ]

    def __init__(
        self,
        *,
        client: S3Client,
        cfg: Config,
        bucket: str,
        prefix: str,
    ) -> None:
        super().__init__()
        self.s3_client = client
        self.cfg = cfg
        self.bucket = bucket
        # Normalize prefix: non-empty must have trailing slash
        if prefix and not prefix.endswith("/"):
            prefix += "/"
        self.prefix = prefix
        self.history: list[str] = []
        self._entries: list[Entry] = []
        self._qp_key: str | None = None  # which key the quicklook panel is showing
        self._qp_visible = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("", id="breadcrumb")
        yield Label("", id="status")
        with Horizontal(id="body"):
            yield DataTable(id="objects", cursor_type="row", zebra_stripes=True)
            with VerticalScroll(id="qp"):
                yield Static("", id="qp-content")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#objects", DataTable)
        table.add_columns("Name", "Size", "Modified", "Type")
        self._refresh_listing()

    def _refresh_listing(self) -> None:
        self._update_breadcrumb()
        self._set_status("Loading…")
        self._load_listing(self.prefix)

    def _update_breadcrumb(self) -> None:
        parts = ["s3://", self.bucket, "/"]
        if self.prefix:
            for part in self.prefix.split("/"):
                if part:
                    parts.append(part + "/")
        self.query_one("#breadcrumb", Static).update(" > ".join(p for p in parts if p))

    def _set_status(self, msg: str) -> None:
        self.query_one("#status", Label).update(msg)

    def _render_entries(self, prefixes: list[str], objects: list[ObjectMeta]) -> None:
        entries: list[Entry] = []
        for p in prefixes:
            name = p[len(self.prefix):]
            entries.append(Entry(name=name, key=p, size=None, last_modified=None, is_prefix=True))
        for obj in objects:
            name = obj.key[len(self.prefix):]
            entries.append(
                Entry(
                    name=name,
                    key=obj.key,
                    size=obj.size,
                    last_modified=obj.last_modified,
                    is_prefix=False,
                )
            )
        self._entries = entries
        table = self.query_one("#objects", DataTable)
        table.clear()
        if not entries:
            self._set_status("(empty)")
            return
        for i, e in enumerate(entries):
            size_str = _fmt_size(e.size) if e.size is not None else "-"
            mod_str = e.last_modified.strftime("%Y-%m-%d %H:%M") if e.last_modified else "-"
            suffix = PurePosixPath(e.name).suffix.lstrip(".").upper()
            type_str = "DIR" if e.is_prefix else (suffix or "OBJ")
            table.add_row(e.name, size_str, mod_str, type_str, key=str(i))
        self._set_status(f"{len(prefixes)} prefix(es), {len(objects)} object(s)")

    @work(thread=True, exclusive=True, group="listing")
    def _load_listing(self, prefix: str) -> None:
        try:
            prefixes, objects = self.s3_client.list_dir(self.bucket, prefix)
            self.post_message(ListingReady(prefix, prefixes, objects))
        except Exception as exc:
            self.post_message(ListingFailed(prefix, exc))

    def on_listing_ready(self, msg: ListingReady) -> None:
        if msg.prefix != self.prefix:
            return  # stale — user navigated again
        self._render_entries(msg.prefixes, msg.objects)

    def on_listing_failed(self, msg: ListingFailed) -> None:
        if msg.prefix != self.prefix:
            return
        err = msg.error
        if isinstance(err, BucketNotFoundError):
            self._set_status(f"Bucket not found: {self.bucket}")
            self.set_timer(3.0, self.action_quit)
        elif isinstance(err, AccessDeniedError):
            self._set_status(
                f"403 Access denied: {self.bucket}/{msg.prefix}. Check AWS profile."
            )
        elif isinstance(err, botocore.exceptions.NoCredentialsError):
            self._set_status("No AWS credentials. Run `aws sso login`.")
        else:
            self._set_status(f"{type(err).__name__}: {err}")
        # Keep prior table visible — do NOT clear it

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key.value is None:
            return
        idx = int(event.row_key.value)
        entry = self._entries[idx]
        if entry.is_prefix:
            self.history.append(self.prefix)
            self.prefix = entry.key
            self._refresh_listing()
        else:
            # Auto-peek on object selection
            self._trigger_quicklook(entry.key, deep=False)

    def _trigger_quicklook(self, key: str, *, deep: bool) -> None:
        panel = self.query_one("#qp")
        self.query_one("#qp-content", Static).update("Loading…")
        panel.add_class("visible")
        self._qp_visible = True
        self._qp_key = key
        if deep:
            self._set_status("Deep peek (streaming)…")
            self._load_deep_peek(key)
        else:
            self._set_status("Loading quicklook…")
            self._load_quicklook(key)

    @work(thread=True, exclusive=True, group="quicklook")
    def _load_quicklook(self, key: str) -> None:
        try:
            from s3peek.quicklook import quicklook

            data = self.s3_client.range_get(self.bucket, key, length=self.cfg.max_range_get_bytes)
            result = quicklook(data, key, max_headers=1, deep=False)
            text = _format_result(result)
            self.post_message(QuicklookReady(key, text))
        except Exception as exc:
            self.post_message(QuicklookFailed(key, exc))

    @work(thread=True, exclusive=True, group="quicklook")
    def _load_deep_peek(self, key: str) -> None:
        # AIDEV-TODO: add cfg.deep_peek_max_bytes soft cap to refuse very large files early
        try:
            from s3peek.quicklook import quicklook
            from s3peek.streams import SeekableS3Stream

            meta = self.s3_client.stat_object(self.bucket, key)
            stream = SeekableS3Stream(self.s3_client, self.bucket, key, size=meta.size)
            result = quicklook(stream, key, max_headers=999, deep=True)
            text = _format_result(result)
            self.post_message(QuicklookReady(key, text))
        except Exception as exc:
            # AIDEV-TODO: catch InvalidObjectState for Glacier objects
            self.post_message(QuicklookFailed(key, exc))

    def on_quicklook_ready(self, msg: QuicklookReady) -> None:
        if msg.key != self._qp_key:
            return
        self.query_one("#qp-content", Static).update(msg.text)
        self._set_status(f"Quicklook: {PurePosixPath(msg.key).name}")

    def on_quicklook_failed(self, msg: QuicklookFailed) -> None:
        if msg.key != self._qp_key:
            return
        self._set_status(f"Quicklook error: {type(msg.error).__name__}: {msg.error}")
        self.query_one("#qp-content", Static).update(f"Error: {msg.error}")

    def action_peek(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        if entry.is_prefix:
            self._set_status("Select an object (not a prefix) to peek")
            return
        if self._qp_visible and self._qp_key == entry.key:
            # Toggle off
            self.query_one("#qp").remove_class("visible")
            self._qp_visible = False
            self._qp_key = None
        else:
            self._trigger_quicklook(entry.key, deep=False)

    def action_deep_peek(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        if entry.is_prefix:
            self._set_status("Select an object (not a prefix) for deep peek")
            return
        self._trigger_quicklook(entry.key, deep=True)

    def action_share(self) -> None:
        entry = self._selected_entry()
        if entry is None or entry.is_prefix:
            self._set_status("Select an object to share")
            return
        self._set_status("Generating presigned URL…")
        self._run_share(entry.key)

    @work(thread=True, group="share")
    def _run_share(self, key: str) -> None:
        try:
            from s3peek.presign import copy_to_clipboard, generate_presigned_url

            url = generate_presigned_url(
                self.bucket,
                key,
                expiry_seconds=self.cfg.presign_expiry_seconds,
                profile=self.cfg.aws_profile,
            )
            try:
                copy_to_clipboard(url)
                suffix = "…" if len(url) > 80 else ""
                msg = f"Copied (1h): {url[:80]}{suffix}"
            except Exception:
                suffix = "…" if len(url) > 80 else ""
                msg = f"URL (clipboard unavailable): {url[:80]}{suffix}"
            self.call_from_thread(self._set_status, msg)
        except Exception as exc:
            self.call_from_thread(self._set_status, f"Share error: {exc}")

    def action_copy_uri(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        uri = f"s3://{self.bucket}/{entry.key}"
        try:
            from s3peek.presign import copy_to_clipboard

            copy_to_clipboard(uri)
            self._set_status(f"Copied: {uri}")
        except Exception:
            self._set_status(f"URI (clipboard unavailable): {uri}")

    def action_firefly(self) -> None:
        if not self.cfg.firefly_url:
            self._set_status("No firefly_url configured — set firefly_url in config")
            return
        entry = self._selected_entry()
        if entry is None or entry.is_prefix:
            self._set_status("Select an object to send to Firefly")
            return
        self._set_status("Sending to Firefly…")
        self._run_firefly(entry.key)

    @work(thread=True, group="firefly")
    def _run_firefly(self, key: str) -> None:
        try:
            from s3peek.cli import _should_auto_preview
            from s3peek.firefly import FireflyConnector
            from s3peek.presign import generate_presigned_url

            meta = self.s3_client.stat_object(self.bucket, key)
            filename = PurePosixPath(key).name or "object"
            presigned_url = generate_presigned_url(
                self.bucket,
                key,
                expiry_seconds=self.cfg.presign_expiry_seconds,
                profile=self.cfg.aws_profile,
            )
            fc = FireflyConnector(
                self.cfg.firefly_url,  # type: ignore[arg-type]
                channel=self.cfg.firefly_channel,
                launch_browser=True,
            )
            preview = _should_auto_preview(key, meta.size)
            url = fc.show_url(presigned_url, preview=preview, title=filename)
            self.call_from_thread(self._set_status, f"Opened in Firefly: {url}")
        except ImportError as exc:
            self.call_from_thread(
                self._set_status,
                f"Firefly not available: {exc}. Run: pip install 's3peek[firefly]'",
            )
        except Exception as exc:
            self.call_from_thread(self._set_status, f"Firefly error: {exc}")

    async def action_back(self) -> None:
        if self.history:
            self.prefix = self.history.pop()
        else:
            # Derive parent prefix
            stripped = self.prefix.rstrip("/")
            if "/" in stripped:
                self.prefix = stripped.rsplit("/", 1)[0] + "/"
            else:
                self.prefix = ""
        self._refresh_listing()

    def action_reload(self) -> None:
        self._refresh_listing()

    def _selected_entry(self) -> Entry | None:
        table = self.query_one("#objects", DataTable)
        if table.cursor_row is None or not self._entries:
            return None
        if table.cursor_row >= len(self._entries):
            return None
        return self._entries[table.cursor_row]


def _fmt_size(size: int | None) -> str:
    if size is None:
        return "-"
    f = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if f < 1024 or unit == "TB":
            return f"{f:.0f} {unit}"
        f /= 1024
    return str(f)


def _format_result(result: object) -> str:
    lines = [f"Format: {result.format}"]  # type: ignore[attr-defined]
    for i, hdr in enumerate(result.headers):  # type: ignore[attr-defined]
        if len(result.headers) > 1:  # type: ignore[attr-defined]
            lines.append(f"--- HDU {i} ---")
        for k, v in hdr.items():
            lines.append(f"  {k}: {v}")
    return "\n".join(lines)
