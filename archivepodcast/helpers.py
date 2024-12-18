"""Helper functions for the archivepodcast module."""

from typing import TYPE_CHECKING

from .logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client  # pragma: no cover
else:
    S3Client = object


def list_all_s3_objects(s3_client: S3Client, bucket: str) -> list:
    """Function to list all objects in the s3 bucket."""
    paginator = s3_client.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(Bucket=bucket)

    all_objects: list = []
    for page in page_iterator:
        if "Contents" in page:
            all_objects.extend(page["Contents"])

    return all_objects
