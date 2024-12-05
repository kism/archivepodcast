"""App testing different config behaviours."""

import logging
import os

import boto3
import pytest
from moto import mock_aws

FLASK_ROOT_PATH = os.getcwd()


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def s3(aws_credentials):
    """Return a mocked S3 client."""
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")


@pytest.fixture
def mocked_aws(aws_credentials):
    """Mock all AWS interactions, Requires you to create your own boto3 clients."""
    with mock_aws():
        yield


def test_config_valid(tmp_path, get_test_config, caplog, s3, mock_threads_none):
    """Test that the app can load config and the testing attribute is set."""
    config_file = "testing_true_valid_s3.toml"
    config = get_test_config(config_file)

    bucket_name = config["app"]["s3"]["bucket"]
    s3.create_bucket(Bucket=bucket_name)

    from archivepodcast.ap_archiver import PodcastArchiver

    with caplog.at_level(logging.DEBUG):
        PodcastArchiver(
            app_settings=config["app"],
            podcast_list=config["podcast"],
            instance_path=tmp_path,
            root_path=FLASK_ROOT_PATH,
        )

    assert "Not using s3" not in caplog.text
    assert f"Authenticated s3, using bucket: {bucket_name}" in caplog.text


@pytest.fixture
def pa_aws(tmp_path, get_test_config, caplog, s3):
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid_s3.toml"
    config = get_test_config(config_file)

    bucket_name = config["app"]["s3"]["bucket"]
    s3.create_bucket(Bucket=bucket_name)

    from archivepodcast.ap_archiver import PodcastArchiver

    return PodcastArchiver(
        app_settings=config["app"], podcast_list=config["podcast"], instance_path=tmp_path, root_path=FLASK_ROOT_PATH
    )


def test_tktktktktk(pa_aws, caplog):
    """Test TKTKTKTKTKKT."""

    app_path = os.getcwd()

    try:
        contents = os.listdir(app_path)
        logging.debug(f"Contents of {app_path}: {contents}")
    except Exception as e:
        logging.error(f"Error listing contents of {app_path}: {e}")

    assert "archivepodcast" in contents

    assert pa_aws.s3 is not None

    pa_aws.s3.put_object(
        Body="hello world",
        Bucket=pa_aws.app_settings["s3"]["bucket"],
        Key="hello.txt",
        ContentType="text/plain",
    )

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_archiver.render_static"):
        pa_aws._render_static()

    list_files = pa_aws.s3.list_objects_v2(Bucket=pa_aws.app_settings["s3"]["bucket"])
    list_files = [path["Key"] for path in list_files.get("Contents", [])]

    assert "hello.txt" in list_files
    assert "index.html" in list_files


    assert "Uploading static pages to s3 in the background" in caplog.text
    assert "Uploading static item" in caplog.text
    assert "Done uploading static pages to s3" in caplog.text
