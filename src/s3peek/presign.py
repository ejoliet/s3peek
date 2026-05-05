from __future__ import annotations


def generate_presigned_url(
    bucket: str,
    key: str,
    *,
    expiry_seconds: int = 3600,
    profile: str | None = None,
) -> str:
    raise NotImplementedError


def parse_expiry(expiry_str: str) -> int:
    raise NotImplementedError


def copy_to_clipboard(text: str) -> None:
    raise NotImplementedError
