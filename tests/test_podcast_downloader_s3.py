"""Tests for S3-specific PodcastDownloader functionality."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from botocore.exceptions import ClientError

from archivepodcast.config import ArchivePodcastConfig
from archivepodcast.downloader.downloader import PodcastDownloader
from archivepodcast.utils.logger import TRACE_LEVEL_NUM
from tests.fixtures.aws import S3ClientMock

from . import FakeExceptionError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture  # pragma: no cover
    from types_aiobotocore_s3.type_defs import ObjectTypeDef  # pragma: no cover

    from tests.fixtures.aws import AWSAioSessionMock
else:
    ObjectTypeDef = object
    MockerFixture = object
    AWSAioSessionMock = object


def test_init(
    get_test_config: Callable[[str], ArchivePodcastConfig],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test PodcastDownloader initialization with S3 configuration."""
    config_file = "testing_true_valid_s3.json"
    config = get_test_config(config_file)

    web_root = Path(tmp_path) / "web"

    with caplog.at_level(TRACE_LEVEL_NUM):
        PodcastDownloader(app_config=config.app, s3=True, web_root=web_root)

    assert "PodcastDownloader config (re)loaded" in caplog.text


async def test_download_podcast(
    apd_aws: PodcastDownloader,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_podcast_source_rss_valid: MockerFixture,
    mock_get_session: AWSAioSessionMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test downloading podcast RSS and assets."""
    assert apd_aws.s3
    config_file = "testing_true_valid_s3.json"
    config = get_test_config(config_file)
    mock_podcast_definition = config.podcasts[0]

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.downloader"):
        await apd_aws.download_podcast(mock_podcast_definition)

    assert "Downloaded rss feed, processing" in caplog.text
    assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
    assert "Downloading asset to:" in caplog.text
    assert "Uploading to s3:" in caplog.text
    assert "Removing local file" in caplog.text
    assert "Uploading podcast cover art to s3" in caplog.text
    assert "HTTP ERROR:" not in caplog.text
    assert "Download Failed" not in caplog.text
    assert "Unhandled s3 error" not in caplog.text
    assert "Could not upload to s3" not in caplog.text

    async with mock_get_session.create_client("s3") as s3_client:
        s3_object_list = await s3_client.list_objects_v2(Bucket=apd_aws.app_config.s3.bucket)
    s3_object_list_str = [path["Key"] for path in s3_object_list.get("Contents", [])]

    assert "content/test/20200101-Test-Episode.jpg" in s3_object_list_str
    assert "content/test/20200101-Test-Episode.mp3" in s3_object_list_str
    assert "content/test/PyTest-Podcast-Archive-S3.jpg" in s3_object_list_str


@pytest.mark.asyncio
async def mock_podcast_source_rss_wav(
    apd_aws: PodcastDownloader,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_podcast_source_rss_valid: MockerFixture,
    mock_get_session: AWSAioSessionMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test downloading podcast RSS and assets with WAV format."""
    assert apd_aws.s3

    config_file = "testing_true_valid_s3.json"
    config = get_test_config(config_file)
    mock_podcast_definition = config.podcasts[0]

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.downloader"):
        await apd_aws.download_podcast(mock_podcast_definition)

    assert "Downloaded rss feed, processing" in caplog.text
    assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
    assert "Downloading asset to:" in caplog.text
    assert "Converting episode" in caplog.text
    assert "HTTP ERROR:" not in caplog.text
    assert "Download Failed" not in caplog.text

    async with mock_get_session.create_client("s3") as s3_client:
        s3_object_list = await s3_client.list_objects_v2(Bucket=apd_aws.app_config.s3.bucket)
    s3_object_list_str = [path["Key"] for path in s3_object_list.get("Contents", [])]

    assert "content/test/20200101-Test-Episode.jpg" in s3_object_list_str
    assert "content/test/20200101-Test-Episode.mp3" in s3_object_list_str
    assert "content/test/PyTest-Podcast-Archive-S3.jpg" in s3_object_list_str


@pytest.mark.asyncio
async def test_upload_asset_s3_no_client(apd: PodcastDownloader, caplog: pytest.LogCaptureFixture) -> None:
    """Test handling missing S3 client during upload."""
    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.downloader"):
        await apd._upload_asset_s3(Path("test.jpg"), ".jpg")

    assert "s3 client not found, cannot upload" in caplog.text


@pytest.mark.asyncio
async def test_upload_asset_s3_file_not_found(apd_aws: PodcastDownloader, caplog: pytest.LogCaptureFixture) -> None:
    """Test handling file not found error during S3 upload."""
    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.downloader"):
        await apd_aws._upload_asset_s3(Path("test_file_not_exist.jpg"), ".jpg")

    assert "Could not upload to s3, the source file was not found" in caplog.text


@pytest.mark.asyncio
async def test_upload_asset_s3_unhandled_exception(
    apd_aws: PodcastDownloader, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Test handling unhandled exception during S3 upload."""

    def unhandled_exception(*args: Any, **kwargs: Any) -> None:
        raise FakeExceptionError

    monkeypatch.setattr(S3ClientMock, "put_object", unhandled_exception)

    with caplog.at_level(level=logging.ERROR):
        await apd_aws._upload_asset_s3(Path("test_file_not_exist.jpg"), ".jpg")

    assert "Could not upload to s3, the source file was not found" in caplog.text


@pytest.mark.asyncio
async def test_upload_asset_s3_os_remove_error(
    apd_aws: PodcastDownloader, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Test handling Path.unlink error during S3 upload."""
    assert apd_aws.s3

    def path_unlink_error(*args: Any, **kwargs: Any) -> None:
        raise FileNotFoundError

    monkeypatch.setattr(Path, "unlink", path_unlink_error)

    monkeypatch.setattr(S3ClientMock, "put_object", lambda *args, **kwargs: None)

    with caplog.at_level(level=logging.ERROR):
        await apd_aws._upload_asset_s3(Path("test_file_mocked.jpg"), ".jpg")

    assert "Could not upload to s3, the source file was not found" in caplog.text


@pytest.mark.asyncio
async def test_check_path_exists_s3(
    apd_aws: PodcastDownloader,
    mock_get_session: AWSAioSessionMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test checking if a path exists in S3."""
    assert apd_aws.s3

    async with mock_get_session.create_client("s3") as s3_client:
        await s3_client.put_object(  # Bucket is empty before this
            Bucket=apd_aws.app_config.s3.bucket,
            Key="content/test",
            Body="Test File Found",
            ContentType="text/html",
        )

    assert await apd_aws._check_path_exists("/content/test") is True

    # Test path handling and if the cache gets hit
    with caplog.at_level(level=TRACE_LEVEL_NUM, logger="archivepodcast.downloader"):
        assert await apd_aws._check_path_exists("content/test") is True
        assert "s3 path content/test exists in s3_paths_cache, skipping" in caplog.text

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.downloader"):
        assert await apd_aws._check_path_exists("content/test/not_exist") is False

    assert "File: content/test/not_exist does not exist" in caplog.text


@pytest.mark.asyncio
async def test_check_path_exists_s3_client_error(
    apd_aws: PodcastDownloader,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test handling non-404 S3 client error during path check."""
    assert apd_aws.s3

    def client_error_not_404(*args: Any, **kwargs: Any) -> None:
        raise ClientError({"Error": {"Code": "LimitExceededException"}}, "LimitExceededException")

    monkeypatch.setattr(S3ClientMock, "head_object", client_error_not_404)

    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.downloader"):
        assert await apd_aws._check_path_exists("content/test") is False

    assert "s3 check file exists errored out?" in caplog.text


@pytest.mark.asyncio
async def test_check_path_exists_s3_unhandled_exception(
    apd_aws: PodcastDownloader, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Test handling unhandled exception during S3 path check."""

    def unhandled_exception(*args: Any, **kwargs: Any) -> None:
        raise FakeExceptionError

    monkeypatch.setattr(S3ClientMock, "head_object", unhandled_exception)

    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.downloader"):
        assert await apd_aws._check_path_exists("content/test") is False

    assert "Unhandled s3 Error" in caplog.text
