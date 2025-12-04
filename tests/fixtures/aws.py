import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging import getLogger
from typing import TYPE_CHECKING, Self

import pytest
from botocore.exceptions import ClientError as S3ClientError
from types_aiobotocore_s3.type_defs import (
    HeadObjectOutputTypeDef,
    ListObjectsV2OutputTypeDef,
    ObjectTypeDef,
    PutObjectRequestBucketPutObjectTypeDef,
)

from archivepodcast.instances.path_cache import s3_file_cache
from archivepodcast.utils.s3 import S3File

logger = getLogger(__name__)

if TYPE_CHECKING:
    from aiobotocore.paginate import AioPageIterator  # pragma: no cover
    from pytest_mock import MockerFixture  # pragma: no cover
    from types_aiobotocore_s3 import S3Client  # pragma: no cover
else:
    MockerFixture = object
    S3Client = object
    AioPageIterator = object


@pytest.fixture
def aws_credentials() -> None:
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "abc"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "xyz"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


_objects: dict[str, PutObjectRequestBucketPutObjectTypeDef] = {}


class PaginatorMock:
    def __init__(self, objects: dict[str, PutObjectRequestBucketPutObjectTypeDef]) -> None:
        self._objects = objects

    def paginate(self, **kwargs: object) -> AsyncGenerator[ListObjectsV2OutputTypeDef]:
        async def generator() -> AsyncGenerator[ListObjectsV2OutputTypeDef, None]:
            contents: list[ObjectTypeDef] = []
            for key, obj in list(self._objects.items()):
                body = obj.get("Body", b"")
                size = len(body) if isinstance(body, (bytes, str)) else 0

                new_obj: ObjectTypeDef = {
                    "Key": key,
                    "Size": size,
                }
                contents.append(new_obj)

            output: ListObjectsV2OutputTypeDef = {
                "Name": "example-bucket",
                "Prefix": "",
                "KeyCount": len(_objects),
                "MaxKeys": 1000,
                "IsTruncated": False,
                "Delimiter": "",
                "EncodingType": "url",
                "ContinuationToken": "",
                "NextContinuationToken": "",
                "StartAfter": "",
                "RequestCharged": "requester",
                "ResponseMetadata": {
                    "RequestId": "EXAMPLE_REQUEST123",
                    "HostId": "EXAMPLE_HOST123",
                    "HTTPStatusCode": 200,
                    "RetryAttempts": 0,
                    "HTTPHeaders": {},
                },
                "Contents": contents,
            }

            yield output

        return generator()


class S3ClientMock:
    def get_paginator(self, operation_name: str) -> PaginatorMock:
        return PaginatorMock(_objects)

    def get_waiter(self, waiter_name: str) -> None:
        pass

    async def list_objects_v2(self, Bucket: str, **kwargs: object) -> ListObjectsV2OutputTypeDef:
        contents: list[ObjectTypeDef] = []

        for key, obj in _objects.items():
            body = obj.get("Body", b"")
            size = len(body) if isinstance(body, (bytes, str)) else 0

            new_obj: ObjectTypeDef = {
                "Key": key,
                "Size": size,
            }
            contents.append(new_obj)

        output: ListObjectsV2OutputTypeDef = {
            "Name": Bucket,
            "Prefix": "",
            "KeyCount": len(_objects),
            "MaxKeys": 1000,
            "IsTruncated": False,
            "Delimiter": "",
            "EncodingType": "url",
            "ContinuationToken": "",
            "NextContinuationToken": "",
            "StartAfter": "",
            "RequestCharged": "requester",
            "ResponseMetadata": {
                "RequestId": "EXAMPLE_REQUEST123",
                "HostId": "EXAMPLE_HOST123",
                "HTTPStatusCode": 200,
                "RetryAttempts": 0,
                "HTTPHeaders": {},
            },
            "Contents": contents,
        }

        return output

    async def put_object(self, Bucket: str, Key: str, Body: str | bytes, ContentType: str = "") -> None:
        _objects[Key] = PutObjectRequestBucketPutObjectTypeDef(Key=Key, Body=Body, ContentType=ContentType)

        # Update the s3_file_cache with the new file
        size = len(Body) if hasattr(Body, "__len__") else 0
        s3_file_cache.add_file(S3File(key=Key, size=size))  # This is to make tests pass, might be a hack

    async def delete_object(self, Bucket: str, Key: str) -> None:
        _objects.pop(Key, None)

    async def head_object(self, Bucket: str, Key: str) -> HeadObjectOutputTypeDef:
        wip = _objects.get(Key)
        if wip is not None:
            return HeadObjectOutputTypeDef(wip)  # type: ignore[no-any-return] # ???

        raise S3ClientError(
            operation_name="HeadObject", error_response={"Error": {"Code": "404", "Message": "Not Found"}}
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    def close(self) -> None:
        pass


class AWSAioSessionMock:
    @asynccontextmanager
    async def create_client(self, service_name: str, **kwargs: object) -> AsyncGenerator[S3ClientMock, None]:
        yield S3ClientMock()

    async def send(self, *args: object, **kwargs: object) -> None:
        pass

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


class AIOHTTPSessionMock:
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def send(self, *args: object, **kwargs: object) -> None:
        pass


@pytest.fixture
def mock_get_session(monkeypatch: pytest.MonkeyPatch) -> AWSAioSessionMock:
    """Mock aiobotocore session.get_session to return a mock session. Also returns the session, why not."""
    global _objects  # noqa: PLW0603
    _objects = {}

    # Also clear the s3_file_cache to ensure tests start fresh
    s3_file_cache._files = []
    s3_file_cache._last_cache_time = None

    mocked_session = AWSAioSessionMock()

    monkeypatch.setattr("aiobotocore.session.AioSession", lambda *args: AWSAioSessionMock())

    monkeypatch.setattr(
        "aiobotocore.session.get_session",
        lambda: mocked_session,
    )

    monkeypatch.setattr(
        "archivepodcast.utils.s3.get_session",
        lambda: mocked_session,
    )

    monkeypatch.setattr(
        "aiobotocore.httpsession.AIOHTTPSession",
        AIOHTTPSessionMock,
    )

    return mocked_session
