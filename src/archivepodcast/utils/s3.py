"""Helper utilities for archivepodcast."""

import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from aiobotocore.session import get_session
from botocore.exceptions import ClientError
from pydantic import BaseModel

from archivepodcast.instances.config import get_ap_config

from .logger import get_logger
from .time import warn_if_too_long

logger = get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from types_aiobotocore_s3 import S3Client
    from types_aiobotocore_s3.type_defs import HeadObjectOutputTypeDef, ObjectTypeDef  # pragma: no cover
else:
    HeadObjectOutputTypeDef = object
    ObjectTypeDef = object

MAX_CACHE_AGE = 120


class S3File(BaseModel):
    """Model representing an S3 file in the cache."""

    key: str
    size: int


# ponytail: extension check, swap for per-podcast config if someone ever needs different TTLs
IMMUTABLE_SUFFIXES = (".woff2", ".mp3", ".m4a", ".opus", ".ogg", ".wav", ".flac")


def cache_control_for(path: str) -> str:
    """Cache-Control header for a webpage/asset path, keyed off the file extension."""
    if path.endswith(IMMUTABLE_SUFFIXES):
        return "public, max-age=31536000"  # 1 year, archived episodes and fonts never change
    return "public, max-age=180"


@asynccontextmanager
async def _s3_client() -> AsyncIterator[S3Client]:
    """S3 client configured from the app config."""
    s3_conf = get_ap_config().app.s3
    async with get_session().create_client(
        "s3",
        aws_access_key_id=s3_conf.access_key_id,
        aws_secret_access_key=s3_conf.secret_access_key,
        region_name=s3_conf.region or None,
        endpoint_url=s3_conf.api_url.encoded_string() if s3_conf.api_url else None,
    ) as s3_client:
        yield s3_client


async def s3_put(bucket: str, key: str, body: bytes, content_type: str, *, large_file: bool = False) -> None:
    """Upload an object to s3."""
    start_time = time.time()
    async with _s3_client() as s3_client:
        await s3_client.put_object(
            Bucket=bucket, Key=key, Body=body, ContentType=content_type, CacheControl=cache_control_for(key)
        )
    warn_if_too_long(f"upload {key} to s3", time.time() - start_time, large_file=large_file)


async def s3_head(bucket: str, key: str) -> HeadObjectOutputTypeDef:
    """Head an object in s3, raises botocore ClientError if it doesn't exist."""
    async with _s3_client() as s3_client:
        return await s3_client.head_object(Bucket=bucket, Key=key)


async def s3_delete(bucket: str, key: str) -> None:
    """Delete an object from s3."""
    async with _s3_client() as s3_client:
        await s3_client.delete_object(Bucket=bucket, Key=key)


async def s3_get(bucket: str, key: str) -> bytes:
    """Download an object from s3, returns empty bytes if it doesn't exist."""
    start_time = time.time()
    try:
        async with _s3_client() as s3_client:
            response = await s3_client.get_object(Bucket=bucket, Key=key)
            body = await response["Body"].read()
    except ClientError:
        logger.debug("Object not found in s3: %s", key)
        return b""
    warn_if_too_long(f"download {key} from s3", time.time() - start_time)
    return body


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

        async with _s3_client() as s3_client:
            paginator = s3_client.get_paginator("list_objects_v2")
            page_iterator = paginator.paginate(Bucket=bucket)

            all_objects: list[ObjectTypeDef] = []
            async for page in page_iterator:
                if "Contents" in page:
                    all_objects.extend(page["Contents"])

        self._files = all_objects
        self._last_cache_time = datetime.now(tz=UTC)
        return all_objects

    def add_file(self, s3_file: S3File) -> None:
        """Append a new S3 file to the cache."""
        self._files.append({"Key": s3_file.key, "Size": s3_file.size})

    def check_file_exists(self, key: str, size: int | None = None) -> bool:
        """Check if a file exists in the cache."""
        return any(file["Key"] == key and (size is None or file["Size"] == size) for file in self._files)
