"""Tests for AssetDownloader functionality."""

from collections.abc import Callable
from pathlib import Path

import pytest

from archivepodcast.config import ArchivePodcastConfig
from archivepodcast.downloader.asset_downloader import AssetDownloader
from archivepodcast.instances.path_helper import get_app_paths
from archivepodcast.utils.logger import TRACE_LEVEL_NUM
from tests.models.aiohttp import FakeResponseDef, FakeSession


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
        aiohttp_session=aiohttp_session,  # type: ignore[arg-type]
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
        aiohttp_session=aiohttp_session,  # type: ignore[arg-type]
    )

    # Create the file
    content_dir = get_app_paths().web_root / "content" / podcast.name_one_word
    content_dir.mkdir(parents=True, exist_ok=True)
    test_file = content_dir / "test.mp3"
    test_file.write_text("test")

    # Test with string path
    exists = await downloader._check_path_exists(str(test_file))
    assert exists is True
