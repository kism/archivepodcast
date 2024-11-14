"""App testing different config behaviours."""

import logging
import os

import boto3
import pytest
from moto import mock_aws

ROOT_PATH = os.path.join(os.getcwd(), "archivepodcast")


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


@pytest.fixture # We need to mock threads out since they won't have context
def mock_threads(monkeypatch):
    """Mock thread start to prevent threads from actually starting."""
    monkeypatch.setattr("threading.Thread.start", lambda _: None)


def test_config_valid(tmp_path, get_test_config, caplog, s3, mock_threads):
    """Test that the app can load config and the testing attribute is set."""
    config_file = "testing_true_valid_s3.toml"
    config = get_test_config(config_file)

    bucket_name = config["app"]["s3"]["bucket"]
    s3.create_bucket(Bucket=bucket_name)

    from archivepodcast.ap_archiver import PodcastArchiver

    with caplog.at_level(logging.DEBUG):
        PodcastArchiver(
            app_settings=config["app"], podcast_list=config["podcast"], instance_path=tmp_path
        )

    assert "Not using s3" not in caplog.text
    assert f"Authenticated s3, using bucket: {bucket_name}" in caplog.text

@pytest.fixture
def pa_aws(tmp_path, get_test_config, caplog, s3, mock_threads):
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid_s3.toml"
    config = get_test_config(config_file)

    bucket_name = config["app"]["s3"]["bucket"]
    s3.create_bucket(Bucket=bucket_name)

    from archivepodcast.ap_archiver import PodcastArchiver

    return PodcastArchiver(
        app_settings=config["app"], podcast_list=config["podcast"], instance_path=tmp_path
    )


def test_no_about_page(pa_aws, caplog): # Move this to non aws tests
    """Test no about page."""
    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_archiver"):
        pa_aws.make_about_page()

    assert "About page doesn't exist" in caplog.text



# def test_tktktktktk(pa_aws, caplog):
#     """Test TKTKTKTKTKKT."""

#     app_path = os.getcwd()

#     try:
#         contents = os.listdir(app_path)
#         logging.debug(f"Contents of {app_path}: {contents}")
#     except Exception as e:
#         logging.error(f"Error listing contents of {app_path}: {e}")

#     assert "archivepodcast" in contents



#     with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_archiver.upload_static"):
#         pa_aws._upload_static()

#     assert "Uploading static pages to s3 in the background" in caplog.text
#     assert "Uploading static item" in caplog.text
#     assert "Done uploading static pages to s3" in caplog.text
