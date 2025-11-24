import os
from collections.abc import Generator
from typing import TYPE_CHECKING

import boto3
import pytest
from moto import mock_aws

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client  # pragma: no cover
    from pytest_mock import MockerFixture  # pragma: no cover
else:
    MockerFixture = object
    S3Client = object


@pytest.fixture
def aws_credentials() -> None:
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "abc"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "xyz"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def mocked_aws(aws_credentials: MockerFixture) -> Generator[None]:
    """Mock all AWS interactions, Requires you to create your own boto3 clients."""
    with mock_aws():
        yield


@pytest.fixture
def s3(aws_credentials: MockerFixture) -> Generator[S3Client, None, None]:
    """Return a mocked S3 client."""
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")
