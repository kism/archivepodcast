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
def app(tmp_path, get_test_config):
    """This fixture uses the default config within the flask app."""
    from archivepodcast import create_app

    # Create a dummy RSS file since this app instance is not live and requires an existing rss feed.
    os.makedirs(os.path.join(tmp_path, "web", "rss"))
    with open(os.path.join(tmp_path, "web", "rss", "test"), "w") as file:
        file.write(pytest.DUMMY_RSS_STR)

    return create_app(test_config=get_test_config("testing_true_valid.toml"), instance_path=tmp_path)


@pytest.fixture
def app_live(
    tmp_path,
    get_test_config,
    mock_get_podcast_source_rss,
    mock_podcast_source_images,
    mock_podcast_source_mp3,
):
    """This fixture uses the default config within the flask app."""
    mock_get_podcast_source_rss("test_valid.rss")

    from archivepodcast import create_app

    return create_app(test_config=get_test_config("testing_true_valid_live.toml"), instance_path=tmp_path)


@pytest.fixture
def app_live_s3(
    tmp_path,
    get_test_config,
    mock_get_podcast_source_rss,
    mock_podcast_source_images,
    mock_podcast_source_mp3,
    mocked_aws,
    s3,
):
    """This fixture uses the default config within the flask app."""
    mock_get_podcast_source_rss("test_valid.rss")

    from archivepodcast import create_app

    config = get_test_config("testing_true_valid_live_s3.toml")
    bucket_name = config["app"]["s3"]["bucket"]
    s3.create_bucket(Bucket=bucket_name)

    return create_app(test_config=config, instance_path=tmp_path)


@pytest.fixture
def client(app):
    """This returns a test client for the default app()."""
    return app.test_client()


@pytest.fixture
def client_live(app_live):
    """This returns a test client for the default app()."""
    return app_live.test_client()


@pytest.fixture
def client_live_s3(app_live_s3):
    """This returns a test client for the default app()."""
    return app_live_s3.test_client()


@pytest.fixture
def runner(app):
    """TODO?????"""
    return app.test_cli_runner()
