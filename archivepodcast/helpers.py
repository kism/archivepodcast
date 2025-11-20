"""Helper utilities for archivepodcast."""

from pathlib import Path
from typing import TYPE_CHECKING

from lxml import etree

from .logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client  # pragma: no cover
    from mypy_boto3_s3.type_defs import ObjectTypeDef  # pragma: no cover
else:
    S3Client = object
    ObjectTypeDef = object


def list_all_s3_objects(s3_client: S3Client, bucket: str) -> list[ObjectTypeDef]:
    """List all objects in an S3 bucket using pagination.

    Args:
        s3_client: Boto3 S3 client instance
        bucket: Name of the S3 bucket

    Returns:
        List of all objects in the bucket
    """
    paginator = s3_client.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(Bucket=bucket)

    all_objects: list[ObjectTypeDef] = []
    for page in page_iterator:
        if "Contents" in page:
            all_objects.extend(page["Contents"])

    return all_objects


def tree_no_episodes(tree: etree._ElementTree | None) -> bool:
    """Check if the XML tree has no episodes."""
    if tree is None:
        return True
    return len(tree.xpath("//item")) == 0


class InstanceDir:
    """Handler for the instance dir."""

    _instance_dir: Path | None = None

    def get(self) -> Path:
        """Get the instance directory path."""
        if self._instance_dir is None:
            msg = "InstanceDir has not been set."
            raise ValueError(msg)

        return self._instance_dir

    def get_settings_path(self) -> Path:
        """Get the path to the settings file in the instance directory."""
        return self.get() / "config.json"

    def set(self, path: Path) -> None:
        """Set the instance directory path."""
        self._instance_dir = path


instance_dir = InstanceDir()
