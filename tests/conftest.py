from __future__ import annotations

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def s3_client(aws_credentials: None):  # type: ignore[misc]
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")


@pytest.fixture
def populated_bucket(s3_client):  # type: ignore[misc]
    s3_client.create_bucket(Bucket="test-bucket")
    s3_client.put_object(
        Bucket="test-bucket", Key="data/sample.json", Body=b'{"hello": "world"}'
    )
    s3_client.put_object(
        Bucket="test-bucket", Key="data/image.fits", Body=b"SIMPLE  = T" + b" " * 69
    )
    yield s3_client
