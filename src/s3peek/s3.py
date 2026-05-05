from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import boto3


@dataclass
class ObjectMeta:
    key: str
    size: int
    last_modified: datetime
    storage_class: str
    etag: str


class S3Client:
    def __init__(self, profile: str | None = None, region: str | None = None) -> None:
        session = boto3.Session(profile_name=profile, region_name=region)
        self._s3 = session.client("s3")

    def list_prefix(
        self,
        bucket: str,
        prefix: str,
        *,
        delimiter: str = "/",
    ) -> list[ObjectMeta]:
        raise NotImplementedError

    def stat_object(self, bucket: str, key: str) -> ObjectMeta:
        raise NotImplementedError

    def range_get(self, bucket: str, key: str, *, start: int = 0, length: int = 65536) -> bytes:
        raise NotImplementedError

    def sum_prefix_sizes(self, bucket: str, prefix: str) -> dict[str, int]:
        raise NotImplementedError
