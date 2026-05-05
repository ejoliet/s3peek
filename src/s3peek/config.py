from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

_DEFAULT_CONFIG_PATH = Path.home() / ".config" / "s3peek" / "config.toml"


class Config(BaseModel):
    aws_profile: str | None = None
    aws_region: str | None = None
    default_bucket: str | None = None
    presign_expiry_seconds: int = Field(default=3600, ge=1, le=604800)
    max_range_get_bytes: int = Field(default=65536, ge=1024)
    theme: str = "dark"
    firefly_url: str | None = None
    firefly_channel: str | None = None

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        config_path = path or Path(os.environ.get("S3PEEK_CONFIG", str(_DEFAULT_CONFIG_PATH)))
        data: dict[str, Any] = {}
        if config_path.exists():
            data = tomllib.loads(config_path.read_text())
        if url := os.environ.get("FIREFLY_URL"):
            data["firefly_url"] = url
        if channel := os.environ.get("FIREFLY_CHANNEL"):
            data["firefly_channel"] = channel
        if region := os.environ.get("AWS_DEFAULT_REGION"):
            data.setdefault("aws_region", region)
        return cls(**data)
