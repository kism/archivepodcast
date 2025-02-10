import os
import shutil
import threading
import time

import boto3
import pytest
import tomlkit
from moto import mock_aws

from archivepodcast.ap_archiver import PodcastArchiver, PodcastDownloader


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "abc"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "xyz"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def mocked_aws(aws_credentials):
    """Mock all AWS interactions, Requires you to create your own boto3 clients."""
    with mock_aws():
        yield


@pytest.fixture
def s3(aws_credentials):
    """Return a mocked S3 client."""
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")
