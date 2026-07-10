"""Helper utilities for archivepodcast."""

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from aiobotocore.session import get_session
from pydantic import BaseModel

from archivepodcast.instances.config import get_ap_config_s3_client

from .logger import get_logger
from .time import warn_if_too_long

logger = get_logger(__name__)

if TYPE_CHECKING:
    from types_aiobotocore_s3.type_defs import ObjectTypeDef  # pragma: no cover
else:
    ObjectTypeDef = object

MAX_CACHE_AGE = 120


class S3File(BaseModel):
    """Model representing an S3 file in the cache."""

    key: str
    size: int


async def s3_put(bucket: str, key: str, body: bytes, content_type: str, *, large_file: bool = False) -> None:
    """Upload an object to s3."""
    s3_config = get_ap_config_s3_client()
    session = get_session()
    start_time = time.time()
    async with session.create_client("s3", **s3_config.model_dump()) as s3_client:
        await s3_client.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)
    warn_if_too_long(f"upload {key} to s3", time.time() - start_time, large_file=large_file)


class S3FileCache(BaseModel):
    """Model representing a cache of S3 files."""

    _last_cache_time: datetime | None = None

    _files: list[ObjectTypeDef] = []

    async def get_all(self, bucket: str) -> list[ObjectTypeDef]:
        """List all objects in an S3 bucket using pagination."""
        if self._last_cache_time:
            age = (datetime.now(tz=UTC) - self._last_cache_time).total_seconds()
            logger.trace("S3 Cache hit! Age: %.2f seconds", age)
            if age < MAX_CACHE_AGE:
                return self._files

        logger.debug("Fetching object list from S3, no cache available")

        s3_config = get_ap_config_s3_client()

        session = get_session()
        async with session.create_client("s3", **s3_config.model_dump()) as s3_client:
            paginator = s3_client.get_paginator("list_objects_v2")
            page_iterator = paginator.paginate(Bucket=bucket)

            all_objects: list[ObjectTypeDef] = []
            async for page in page_iterator:
                if "Contents" in page:
                    all_objects.extend(page["Contents"])

        self._files = all_objects
        self._last_cache_time = datetime.now(tz=UTC)
        return all_objects

    async def get_all_list_str(self, bucket: str) -> list[str]:
        """Get all S3 file keys as strings."""
        s3_files = await self.get_all(bucket)
        return [s3_file["Key"] for s3_file in s3_files]

    def add_file(self, s3_file: S3File) -> None:
        """Append a new S3 file to the cache."""
        self._files.append({"Key": s3_file.key, "Size": s3_file.size})

    def check_file_exists(self, key: str, size: int | None = None) -> bool:
        """Check if a file exists in the cache."""
        return any(file["Key"] == key and (size is None or file["Size"] == size) for file in self._files)
