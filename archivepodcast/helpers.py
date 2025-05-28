"""Helper utilities for archivepodcast."""

from typing import TYPE_CHECKING

from lxml import etree  # pragma: no cover

from .logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client  # pragma: no cover
else:
    S3Client = object


def list_all_s3_objects(s3_client: S3Client, bucket: str) -> list:
    """List all objects in an S3 bucket using pagination.

    Args:
        s3_client: Boto3 S3 client instance
        bucket: Name of the S3 bucket

    Returns:
        List of all objects in the bucket
    """
    paginator = s3_client.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(Bucket=bucket)

    all_objects: list = []
    for page in page_iterator:
        if "Contents" in page:
            all_objects.extend(page["Contents"])

    return all_objects


def tree_no_episodes(tree: etree._ElementTree | None) -> bool:
    """Check if the XML tree has no episodes."""
    if tree is None:
        return True
    return not tree.xpath("//item") and not tree.xpath("//channel/item")
