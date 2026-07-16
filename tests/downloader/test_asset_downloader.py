"""Tests for AssetDownloader functionality."""

import logging
from typing import TYPE_CHECKING

import pytest

from archivepodcast.downloader.asset_downloader import AssetDownloader
from archivepodcast.instances.path_cache import s3_file_cache
from archivepodcast.instances.path_helper import get_app_paths
from archivepodcast.utils.logger import TRACE_LEVEL_NUM
from archivepodcast.utils.s3 import S3File
from tests import FakeExceptionError
from tests.models.aiohttp import FakeResponseDef, FakeSession

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from archivepodcast.config import ArchivePodcastConfig
    from tests.fixtures.aws import AWSAioSessionMock
else:
    AWSAioSessionMock = object


@pytest.mark.asyncio
async def test_download_asset_already_exists(
    get_test_config: Callable[[str], ArchivePodcastConfig],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test downloading an asset that already exists."""
    config_file = "testing_true_valid.json"
    config = get_test_config(config_file)
    podcast = config.podcasts[0]

    responses: dict[str, FakeResponseDef] = {}
    aiohttp_session = FakeSession(responses=responses)

    downloader = AssetDownloader(
        podcast=podcast,
        app_config=config.app,
        s3=False,
        aiohttp_session=aiohttp_session,  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    )

    # Create the file
    content_dir = get_app_paths().web_root / "content" / podcast.name_one_word
    content_dir.mkdir(parents=True, exist_ok=True)
    test_file = content_dir / "test-episode.mp3"
    test_file.write_text("test content")

    with caplog.at_level(TRACE_LEVEL_NUM):
        await downloader._download_asset(
            url="https://example.com/test.mp3",
            title="test-episode",
            extension=".mp3",
        )

    assert "Already downloaded: test-episode.mp3" in caplog.text


@pytest.mark.asyncio
async def test_check_path_exists_str_path(
    get_test_config: Callable[[str], ArchivePodcastConfig],
    tmp_path: Path,
) -> None:
    """Test _check_path_exists with string path."""
    config_file = "testing_true_valid.json"
    config = get_test_config(config_file)
    podcast = config.podcasts[0]

    responses: dict[str, FakeResponseDef] = {}
    aiohttp_session = FakeSession(responses=responses)

    downloader = AssetDownloader(
        podcast=podcast,
        app_config=config.app,
        s3=False,
        aiohttp_session=aiohttp_session,  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    )

    # Create the file
    content_dir = get_app_paths().web_root / "content" / podcast.name_one_word
    content_dir.mkdir(parents=True, exist_ok=True)
    test_file = content_dir / "test.mp3"
    test_file.write_text("test")

    # Test with string path
    exists = await downloader._check_path_exists(str(test_file))
    assert exists is True


@pytest.mark.asyncio
async def test_check_path_exists_s3_not_in_cache(
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_get_session: AWSAioSessionMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test _check_path_exists with S3 when file is not in cache or S3."""
    config_file = "testing_true_valid_s3.json"
    config = get_test_config(config_file)
    podcast = config.podcasts[0]

    responses: dict[str, FakeResponseDef] = {}
    aiohttp_session = FakeSession(responses=responses)

    downloader = AssetDownloader(
        podcast=podcast,
        app_config=config.app,
        s3=True,
        aiohttp_session=aiohttp_session,  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    )

    # Create a path that doesn't exist in S3 cache
    content_dir = get_app_paths().web_root / "content" / podcast.name_one_word
    test_file = content_dir / "nonexistent.mp3"

    # Ensure the file is not in S3 cache
    s3_path = test_file.relative_to(get_app_paths().web_root).as_posix()
    assert not s3_file_cache.check_file_exists(s3_path)

    with caplog.at_level(logging.DEBUG):
        exists = await downloader._check_path_exists(test_file)

    # File should not exist
    assert exists is False

    # Should see the debug message that file doesn't exist in S3
    assert "does not exist 🙅‍ in the s3 bucket" in caplog.text


@pytest.mark.asyncio
async def test_upload_asset_s3_remove_original_false_already_exists(
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_get_session: AWSAioSessionMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test _upload_asset_s3 with remove_original=False when file already exists in S3 cache."""
    config_file = "testing_true_valid_s3.json"
    config = get_test_config(config_file)
    podcast = config.podcasts[0]

    responses: dict[str, FakeResponseDef] = {}
    aiohttp_session = FakeSession(responses=responses)

    downloader = AssetDownloader(
        podcast=podcast,
        app_config=config.app,
        s3=True,
        aiohttp_session=aiohttp_session,  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    )

    # Create the file
    content_dir = get_app_paths().web_root / "content" / podcast.name_one_word
    content_dir.mkdir(parents=True, exist_ok=True)
    test_file = content_dir / "test-cover.jpg"
    test_file.write_bytes(b"test cover art content")

    # Add file to S3 cache with matching size
    s3_path = test_file.relative_to(get_app_paths().web_root).as_posix()
    s3_file_cache.add_file(S3File(key=s3_path, size=test_file.stat().st_size))

    with caplog.at_level(logging.DEBUG):
        await downloader._upload_asset_s3(test_file, ".jpg", remove_original=False)

    assert "exists in s3_paths_cache and matches in size, skipping upload" in caplog.text
    assert test_file.exists()  # File should still exist


@pytest.mark.asyncio
async def test_upload_asset_s3_remove_original_false_upload_and_keep(
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_get_session: AWSAioSessionMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test _upload_asset_s3 with remove_original=False uploads file and keeps the original."""
    config_file = "testing_true_valid_s3.json"
    config = get_test_config(config_file)
    podcast = config.podcasts[0]

    responses: dict[str, FakeResponseDef] = {}
    aiohttp_session = FakeSession(responses=responses)

    downloader = AssetDownloader(
        podcast=podcast,
        app_config=config.app,
        s3=True,
        aiohttp_session=aiohttp_session,  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    )

    # Create the file
    content_dir = get_app_paths().web_root / "content" / podcast.name_one_word
    content_dir.mkdir(parents=True, exist_ok=True)
    test_file = content_dir / "test-cover.jpg"
    test_content = b"test cover art content"
    test_file.write_bytes(test_content)

    with caplog.at_level(TRACE_LEVEL_NUM):
        await downloader._upload_asset_s3(test_file, ".jpg", remove_original=False)

    # File should be uploaded with debug log level (not info)
    assert "Uploading to s3:" in caplog.text
    assert "Uploaded asset to s3:" in caplog.text

    # File should still exist locally
    assert test_file.exists()
    assert test_file.read_bytes() == test_content

    # Should not see "Removing local file" message
    assert "Removing local file" not in caplog.text

    # Verify file was added to S3 mock
    async with mock_get_session.create_client("s3") as s3_client:
        s3_object_list = await s3_client.list_objects_v2(Bucket=config.app.s3.bucket)

    s3_path = test_file.relative_to(get_app_paths().web_root).as_posix()
    s3_object_keys = [obj["Key"] for obj in s3_object_list.get("Contents", [])]
    assert s3_path in s3_object_keys


@pytest.mark.asyncio
async def test_download_cover_art_s3_not_found_anywhere(
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_get_session: AWSAioSessionMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test cover art in s3 mode when it exists neither locally nor in the bucket."""
    config_file = "testing_true_valid_s3.json"
    config = get_test_config(config_file)
    podcast = config.podcasts[0]

    downloader = AssetDownloader(
        podcast=podcast,
        app_config=config.app,
        s3=True,
        aiohttp_session=FakeSession(responses={}),  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    )

    calls: list[str] = []

    async def mock_download_to_local(self, url, destination) -> None:
        calls.append("download")

    async def mock_upload_asset_s3(self, file_path, extension, *, remove_original) -> None:
        calls.append("upload")

    monkeypatch.setattr(AssetDownloader, "_download_to_local", mock_download_to_local)
    monkeypatch.setattr(AssetDownloader, "_upload_asset_s3", mock_upload_asset_s3)

    await downloader._download_cover_art("https://example.com/cover.jpg", "cover", ".jpg")

    assert calls == ["download", "upload"]


@pytest.mark.asyncio
async def test_upload_asset_s3_unhandled_error(
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_get_session: AWSAioSessionMock,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that an unhandled error during s3 upload is logged and marks the feed unhealthy."""
    config_file = "testing_true_valid_s3.json"
    config = get_test_config(config_file)
    podcast = config.podcasts[0]

    downloader = AssetDownloader(
        podcast=podcast,
        app_config=config.app,
        s3=True,
        aiohttp_session=FakeSession(responses={}),  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    )

    content_dir = get_app_paths().web_root / "content" / podcast.name_one_word
    content_dir.mkdir(parents=True, exist_ok=True)
    test_file = content_dir / "test-cover.jpg"
    test_file.write_bytes(b"test cover art content")

    async def mock_put_asset_s3(self, *args, **kwargs) -> None:
        raise FakeExceptionError

    monkeypatch.setattr(AssetDownloader, "_put_asset_s3", mock_put_asset_s3)

    with caplog.at_level(logging.ERROR):
        await downloader._upload_asset_s3(test_file, ".jpg", remove_original=False)

    assert "Unhandled s3 error" in caplog.text
    assert not downloader._feed_download_healthy


@pytest.mark.asyncio
async def test_put_asset_s3_remove_original_file_gone(
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_get_session: AWSAioSessionMock,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that a file vanishing before local removal is logged, not raised."""
    config_file = "testing_true_valid_s3.json"
    config = get_test_config(config_file)
    podcast = config.podcasts[0]

    downloader = AssetDownloader(
        podcast=podcast,
        app_config=config.app,
        s3=True,
        aiohttp_session=FakeSession(responses={}),  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    )

    content_dir = get_app_paths().web_root / "content" / podcast.name_one_word
    content_dir.mkdir(parents=True, exist_ok=True)
    test_file = content_dir / "test-episode.mp3"
    test_file.write_bytes(b"episode content")

    async def mock_unlink(self, missing_ok=False) -> None:
        raise FileNotFoundError

    monkeypatch.setattr("archivepodcast.downloader.asset_downloader.AsyncPath.unlink", mock_unlink)

    with caplog.at_level(logging.ERROR):
        await downloader._put_asset_s3(test_file, "content/test/test-episode.mp3", "audio/mpeg", remove_original=True)

    assert "Could not remove the local file, the source file was not found" in caplog.text


@pytest.mark.asyncio
async def test_check_path_exists_s3_found_in_bucket(
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_get_session: AWSAioSessionMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test _check_path_exists finding the file in the bucket via head_object."""
    config_file = "testing_true_valid_s3.json"
    config = get_test_config(config_file)
    podcast = config.podcasts[0]

    downloader = AssetDownloader(
        podcast=podcast,
        app_config=config.app,
        s3=True,
        aiohttp_session=FakeSession(responses={}),  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    )

    s3_key = "content/test/exists.mp3"
    async with mock_get_session.create_client("s3") as s3_client:
        await s3_client.put_object(Bucket=config.app.s3.bucket, Key=s3_key, Body=b"x", ContentType="audio/mpeg")

    # Clear the cache so the check has to hit head_object
    s3_file_cache._files = []

    with caplog.at_level(logging.DEBUG):
        exists = await downloader._check_path_exists(s3_key)

    assert exists is True
    assert "exists in s3 bucket" in caplog.text
    assert s3_file_cache.check_file_exists(s3_key)
