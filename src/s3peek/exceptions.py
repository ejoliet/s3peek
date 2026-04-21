class S3PeekError(Exception):
    """Base exception for s3peek."""


class InvalidURIError(S3PeekError):
    """S3 URI is malformed or missing bucket/key."""


class BucketNotFoundError(S3PeekError):
    """S3 bucket does not exist or is not accessible."""


class ObjectNotFoundError(S3PeekError):
    """S3 object key does not exist."""


class AccessDeniedError(S3PeekError):
    """Insufficient IAM permissions for the requested operation."""


class UnsupportedFormatError(S3PeekError):
    """File format is not supported by any registered reader."""


class FireflyConnectionError(S3PeekError):
    """Could not connect to the Firefly server."""
