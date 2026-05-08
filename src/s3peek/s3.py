from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import IO, Any, cast
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

from s3peek.exceptions import (
    AccessDeniedError,
    BucketNotFoundError,
    InvalidURIError,
    ObjectNotFoundError,
)


@dataclass
class ObjectMeta:
    key: str
    size: int
    last_modified: datetime
    storage_class: str
    etag: str


def parse_s3_uri(uri: str) -> tuple[str, str]:
    """Return (bucket, key) from an s3://bucket/key URI."""
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise InvalidURIError(f"Expected s3://bucket/key, got: {uri!r}")
    return parsed.netloc, parsed.path.lstrip("/")


class S3Client:
    def __init__(self, profile: str | None = None, region: str | None = None) -> None:
        self._profile = profile
        self._region = region
        self._s3_client: Any | None = None

    @property
    def _s3(self) -> Any:
        if self._s3_client is None:
            session = boto3.Session(profile_name=self._profile, region_name=self._region)
            self._s3_client = session.client("s3")
        return self._s3_client

    def list_prefix(
        self,
        bucket: str,
        prefix: str,
        *,
        delimiter: str = "/",
    ) -> list[ObjectMeta]:
        paginator = self._s3.get_paginator("list_objects_v2")
        results: list[ObjectMeta] = []
        try:
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter=delimiter):
                for obj in page.get("Contents", []):
                    results.append(
                        ObjectMeta(
                            key=obj["Key"],
                            size=obj["Size"],
                            last_modified=obj["LastModified"],
                            storage_class=obj.get("StorageClass", "STANDARD"),
                            etag=obj["ETag"].strip('"'),
                        )
                    )
        except ClientError as exc:
            _raise_from_client_error(exc, bucket=bucket)
        return results

    def stat_object(self, bucket: str, key: str) -> ObjectMeta:
        try:
            resp = self._s3.head_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            _raise_from_client_error(exc, bucket=bucket, key=key)
        return ObjectMeta(
            key=key,
            size=resp["ContentLength"],
            last_modified=resp["LastModified"],
            storage_class=resp.get("StorageClass", "STANDARD"),
            etag=resp["ETag"].strip('"'),
        )

    def range_get(self, bucket: str, key: str, *, start: int = 0, length: int = 65536) -> bytes:
        range_header = f"bytes={start}-{start + length - 1}"
        try:
            resp = self._s3.get_object(Bucket=bucket, Key=key, Range=range_header)
        except ClientError as exc:
            _raise_from_client_error(exc, bucket=bucket, key=key)
        return cast(bytes, resp["Body"].read())

    def download_object_to_fileobj(self, bucket: str, key: str, fileobj: IO[bytes]) -> None:
        """Stream an S3 object into an already-open binary file object."""
        try:
            self._s3.download_fileobj(bucket, key, fileobj)
        except ClientError as exc:
            _raise_from_client_error(exc, bucket=bucket, key=key)

    def sum_prefix_sizes(self, bucket: str, prefix: str) -> dict[str, int]:
        """Return total_bytes and count of objects under prefix."""
        paginator = self._s3.get_paginator("list_objects_v2")
        total = 0
        count = 0
        try:
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    total += obj["Size"]
                    count += 1
        except ClientError as exc:
            _raise_from_client_error(exc, bucket=bucket)
        return {"total_bytes": total, "count": count}


def _raise_from_client_error(
    exc: ClientError,
    *,
    bucket: str | None = None,
    key: str | None = None,
) -> None:
    code = exc.response["Error"]["Code"]
    if code in ("NoSuchBucket", "404") and key is None:
        raise BucketNotFoundError(bucket) from exc
    if code in ("NoSuchKey", "404"):
        raise ObjectNotFoundError(key) from exc
    if code in ("AccessDenied", "403"):
        raise AccessDeniedError(str(exc)) from exc
    raise exc
