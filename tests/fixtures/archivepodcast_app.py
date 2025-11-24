from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from flask import Flask
from flask.testing import FlaskClient

from archivepodcast import create_app
from archivepodcast.config import ArchivePodcastConfig
from tests.constants import DUMMY_RSS_STR

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
    from pytest_mock import MockerFixture
else:
    MockerFixture = object
    S3Client = object


@pytest.fixture
def app(tmp_path: Path, get_test_config: Callable[[str], ArchivePodcastConfig]) -> Flask:
    """This fixture uses the default config within the flask app."""

    # Create a dummy RSS file since this app instance is not live and requires an existing rss feed.
    (tmp_path / "web" / "rss").mkdir(parents=True)
    with (tmp_path / "web" / "rss" / "test").open("w") as file:
        file.write(DUMMY_RSS_STR)

    return create_app(instance_path_override=str(tmp_path))


@pytest.fixture
def app_live(
    tmp_path: Path,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_get_podcast_source_rss: Callable[[str], None],
    mock_podcast_source_images: MockerFixture,
    mock_podcast_source_mp3: MockerFixture,
) -> Flask:
    """This fixture uses the default config within the flask app."""
    mock_get_podcast_source_rss("test_valid.rss")

    return create_app(instance_path_override=str(tmp_path))


@pytest.fixture
def app_live_s3(
    tmp_path: Path,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_get_podcast_source_rss: Callable[[str], None],
    mock_podcast_source_images: MockerFixture,
    mock_podcast_source_mp3: MockerFixture,
    mocked_aws: MockerFixture,
    s3: S3Client,
) -> Flask:
    """This fixture uses the default config within the flask app."""
    mock_get_podcast_source_rss("test_valid.rss")

    config = get_test_config("testing_true_valid_live_s3.json")
    bucket_name = config.app.s3.bucket
    s3.create_bucket(Bucket=bucket_name)

    return create_app(instance_path_override=str(tmp_path))


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """This returns a test client for the default app()."""
    return app.test_client()


@pytest.fixture
def client_live(app_live: Flask) -> FlaskClient:
    """This returns a test client for the default app()."""
    return app_live.test_client()


@pytest.fixture
def client_live_s3(app_live_s3: Flask) -> FlaskClient:
    """This returns a test client for the default app()."""
    return app_live_s3.test_client()
