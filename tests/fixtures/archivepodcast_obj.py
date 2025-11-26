import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from archivepodcast.archiver.podcast_archiver import PodcastArchiver
from archivepodcast.config import ArchivePodcastConfig
from archivepodcast.downloader.downloader import PodcastDownloader
from tests.constants import FLASK_ROOT_PATH

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
    from pytest_mock import MockerFixture
else:
    MockerFixture = object
    S3Client = object


@pytest.fixture
def apa(
    tmp_path: Path,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    caplog: pytest.LogCaptureFixture,
) -> PodcastArchiver:
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid.json"
    config = get_test_config(config_file)

    apa = PodcastArchiver(
        app_config=config.app,
        podcast_list=config.podcasts,
        instance_path=tmp_path,
        root_path=FLASK_ROOT_PATH,
    )

    while apa.health.currently_loading_config() or apa.health.currently_rendering():
        time.sleep(0.05)

    return apa


@pytest.fixture
def no_render_files(monkeypatch: pytest.MonkeyPatch) -> None:
    """Monkeypatch render_files to prevent it from running."""
    monkeypatch.setattr("archivepodcast.archiver.PodcastArchiver.render_files", lambda _: None)


@pytest.fixture
def apa_aws(
    tmp_path: Path,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    no_render_files: MockerFixture,
    caplog: pytest.LogCaptureFixture,
    s3: S3Client,
    mocked_aws: MockerFixture,
) -> PodcastArchiver:
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid_s3.json"
    config = get_test_config(config_file)

    bucket_name = config.app.s3.bucket
    s3.create_bucket(Bucket=bucket_name)

    # Prevent weird threading issues

    apa_aws = PodcastArchiver(
        app_config=config.app,
        podcast_list=config.podcasts,
        instance_path=tmp_path,
        root_path=FLASK_ROOT_PATH,
    )

    while apa_aws.health.currently_loading_config() or apa_aws.health.currently_rendering():
        time.sleep(0.05)

    return apa_aws


# endregion

# region PodcastDownloader object


@pytest.fixture
def apd(
    apa: PodcastArchiver,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    caplog: pytest.LogCaptureFixture,
) -> PodcastDownloader:
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid.json"
    config = get_test_config(config_file)

    web_root = apa.web_root

    return PodcastDownloader(app_config=config.app, s3=None, web_root=web_root)


@pytest.fixture
def apd_aws(
    apa_aws: PodcastArchiver,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mocked_aws: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> PodcastDownloader:
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid_s3.json"
    config = get_test_config(config_file)

    web_root = apa_aws.web_root

    return PodcastDownloader(app_config=config.app, s3=apa_aws.s3, web_root=web_root)
