from __future__ import annotations

import re

import boto3


def generate_presigned_url(
    bucket: str,
    key: str,
    *,
    expiry_seconds: int = 3600,
    profile: str | None = None,
) -> str:
    s3 = boto3.Session(profile_name=profile).client("s3")
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expiry_seconds,
    )


def parse_expiry(expiry_str: str) -> int:
    """Parse e.g. '1h', '30m', '7d' → seconds."""
    m = re.fullmatch(r"(\d+)([smhd])", expiry_str.lower())
    if not m:
        raise ValueError(f"Invalid expiry {expiry_str!r}. Use e.g. 1h, 30m, 7d")
    return int(m.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]


def copy_to_clipboard(text: str) -> None:
    import pyperclip  # type: ignore[import-untyped]
    pyperclip.copy(text)
