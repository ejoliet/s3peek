from __future__ import annotations

import pytest
from moto import mock_aws

from s3peek.exceptions import AccessDeniedError
from s3peek.s3 import S3Client


@pytest.fixture
def list_dir_bucket(populated_bucket):
    """Extend populated_bucket with nested prefixes for list_dir tests."""
    populated_bucket.put_object(Bucket="test-bucket", Key="imgs/a.fits", Body=b"x")
    populated_bucket.put_object(Bucket="test-bucket", Key="imgs/b.fits", Body=b"x")
    populated_bucket.put_object(Bucket="test-bucket", Key="imgs/deep/c.fits", Body=b"x")
    populated_bucket.put_object(Bucket="test-bucket", Key="imgs/deep/d.fits", Body=b"x")
    # Zero-byte trailing-slash directory marker (should be skipped)
    populated_bucket.put_object(Bucket="test-bucket", Key="imgs/marker/", Body=b"", ContentLength=0)
    return populated_bucket


def test_list_dir_splits_prefixes_and_objects(list_dir_bucket):
    client = S3Client()
    prefixes, objects = client.list_dir("test-bucket", "imgs/")
    prefix_strs = set(prefixes)
    object_keys = {o.key for o in objects}
    assert "imgs/deep/" in prefix_strs
    assert "imgs/a.fits" in object_keys
    assert "imgs/b.fits" in object_keys
    # deep/c.fits and deep/d.fits are under a sub-prefix, not directly visible
    assert "imgs/deep/c.fits" not in object_keys


def test_list_dir_skips_zero_byte_dir_markers(list_dir_bucket):
    client = S3Client()
    _, objects = client.list_dir("test-bucket", "imgs/")
    object_keys = {o.key for o in objects}
    assert "imgs/marker/" not in object_keys


def test_list_dir_empty_prefix(populated_bucket):
    """Empty prefix at bucket root returns all top-level prefixes."""
    client = S3Client()
    prefixes, objects = client.list_dir("test-bucket", "")
    # data/ is a common prefix
    assert "data/" in prefixes
    # No objects directly at root
    assert all(not o.key.endswith("/") for o in objects)


def test_list_dir_returns_empty_for_nonexistent_prefix(populated_bucket):
    client = S3Client()
    prefixes, objects = client.list_dir("test-bucket", "nonexistent/")
    assert prefixes == []
    assert objects == []


def test_list_dir_pagination(aws_credentials):
    """Seed >1000 keys; assert all CommonPrefixes returned without truncation."""
    import boto3
    from moto import mock_aws

    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="big-bucket")
        # Create 1500 sub-prefixes each with one object
        for i in range(1500):
            s3.put_object(Bucket="big-bucket", Key=f"part-{i:04d}/obj.dat", Body=b"x")

        client = S3Client()
        prefixes, objects = client.list_dir("big-bucket", "")
        assert len(prefixes) == 1500
        assert objects == []


def test_list_dir_objects_have_metadata(list_dir_bucket):
    client = S3Client()
    _, objects = client.list_dir("test-bucket", "imgs/")
    for obj in objects:
        assert obj.key
        assert obj.size >= 0
        assert obj.last_modified is not None
