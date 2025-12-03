"""App testing different config behaviours."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp
import magic
import pytest

from archivepodcast.archiver.podcast_archiver import PodcastArchiver
from archivepodcast.config import ArchivePodcastConfig
from archivepodcast.downloader import asset_downloader
from archivepodcast.downloader.downloader import PodcastsDownloader
from archivepodcast.utils.logger import TRACE_LEVEL_NUM
from tests.constants import TEST_WAV_FILE
from tests.models.aiohttp import FakeSession

if TYPE_CHECKING:
    from pytest_mock import MockerFixture  # pragma: no cover
else:
    MockerFixture = object


@pytest.mark.asyncio
async def test_init(
    get_test_config: Callable[[str], ArchivePodcastConfig],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the app can load config and the testing attribute is set."""
    config_file = "testing_true_valid.json"
    config = get_test_config(config_file)
    podcast = config.podcasts[0]

    aiohttp_session = FakeSession(responses={})

    with caplog.at_level(TRACE_LEVEL_NUM):
        PodcastsDownloader(app_config=config.app, s3=False, podcast=podcast, aiohttp_session=aiohttp_session)  # type: ignore[arg-type]

    assert "Initialising AssetDownloader for podcast" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_config_name",
    [
        "testing_true_valid.json",
        "testing_true_valid_no_override_info.json",
    ],
)
async def test_download_podcast(
    test_config_name: str,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_podcast_source_rss_valid: MockerFixture,
    apa: PodcastArchiver,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test Fetching RSS and assets."""

    # Create the PodcastsDownloader after the mock is in place
    config = get_test_config(test_config_name)
    podcast = apa.podcast_list[0]
    aiohttp_session = aiohttp.ClientSession()

    apd = PodcastsDownloader(app_config=config.app, s3=False, podcast=podcast, aiohttp_session=aiohttp_session)

    try:
        with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.downloader"):
            await apd.download_podcast()

        assert "Downloaded rss feed, processing" in caplog.text
        assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
        assert "Downloaded asset to:" in caplog.text
        assert "Converting episode" not in caplog.text
        assert "HTTP ERROR:" not in caplog.text
        assert "Download Failed" not in caplog.text
    finally:
        # Clean up the session
        await aiohttp_session.close()
    # assert "str" in caplog.text


@pytest.mark.asyncio
async def test_download_podcast_wav(
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_podcast_source_rss_wav: MockerFixture,
    apa: PodcastArchiver,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test Fetching RSS and assets."""

    # Create the PodcastsDownloader after the mock is in place
    config_file = "testing_true_valid.json"
    config = get_test_config(config_file)
    podcast = apa.podcast_list[0]
    aiohttp_session = aiohttp.ClientSession()

    apd = PodcastsDownloader(app_config=config.app, s3=False, podcast=podcast, aiohttp_session=aiohttp_session)

    try:
        with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.downloader"):
            await apd.download_podcast()

        assert "Downloaded rss feed, processing" in caplog.text
        assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
        assert "Downloaded asset to:" in caplog.text
        assert "Converting episode" in caplog.text
        assert "HTTP ERROR:" not in caplog.text
        assert "Download Failed" not in caplog.text
    finally:
        # Clean up the session
        await aiohttp_session.close()


@pytest.mark.asyncio
async def test_download_podcast_wav_wav_exists(
    tmp_path: Path,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_podcast_source_rss_wav: MockerFixture,
    apa: PodcastArchiver,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test Fetching RSS and assets."""

    # Create the PodcastsDownloader after the mock is in place
    config_file = "testing_true_valid.json"
    config = get_test_config(config_file)
    podcast = apa.podcast_list[0]
    aiohttp_session = aiohttp.ClientSession()

    apd = PodcastsDownloader(app_config=config.app, s3=False, podcast=podcast, aiohttp_session=aiohttp_session)

    test_podcast_content_dir = Path(tmp_path) / "web" / "content" / "test"

    Path(test_podcast_content_dir).mkdir(parents=True, exist_ok=True)

    episode_file_name = "20200101-Test-Episode"
    tmp_wav_path = Path(test_podcast_content_dir) / f"{episode_file_name}.wav"
    tmp_mp3_path = Path(test_podcast_content_dir) / f"{episode_file_name}.mp3"

    tmp_wav_path.write_bytes(TEST_WAV_FILE)

    try:
        with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.downloader"):
            await apd.download_podcast()

        assert "Downloaded rss feed, processing" in caplog.text
        assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
        assert "Downloaded asset to:" in caplog.text
        assert "Converting episode" in caplog.text
        assert "Removing wav version of" in caplog.text
        assert "HTTP ERROR:" not in caplog.text
        assert "Download Failed" not in caplog.text

        assert not tmp_wav_path.exists()
        assert tmp_mp3_path.exists()
        assert magic.from_file(tmp_mp3_path, mime=True) == "audio/mpeg"  # Check that the file is actually an mp3
    finally:
        # Clean up the session
        await aiohttp_session.close()


@pytest.mark.asyncio
async def test_download_podcast_wav_mp3_exists(
    tmp_path: Path,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_podcast_source_rss_wav: MockerFixture,
    apa: PodcastArchiver,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test Fetching RSS and assets."""

    # Create the PodcastsDownloader after the mock is in place
    config_file = "testing_true_valid.json"
    config = get_test_config(config_file)
    podcast = apa.podcast_list[0]
    aiohttp_session = aiohttp.ClientSession()

    apd = PodcastsDownloader(app_config=config.app, s3=False, podcast=podcast, aiohttp_session=aiohttp_session)
    apd._s3 = False

    test_podcast_content_dir = Path(tmp_path) / "web" / "content" / "test"

    test_podcast_content_dir.mkdir(parents=True, exist_ok=True)

    episode_file_name = "20200101-Test-Episode"
    tmp_wav_path = test_podcast_content_dir / f"{episode_file_name}.wav"
    tmp_mp3_path = test_podcast_content_dir / f"{episode_file_name}.mp3"

    tmp_mp3_path.write_text("Test MP3")

    try:
        with caplog.at_level(level=5, logger="archivepodcast.downloader"):
            await apd.download_podcast()

        assert "Downloaded rss feed, processing" in caplog.text
        assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
        assert "Downloaded asset to:" in caplog.text
        assert "Converting episode" not in caplog.text
        assert f"{episode_file_name}.mp3 exists locally" in caplog.text
        assert "HTTP ERROR:" not in caplog.text
        assert "Download Failed" not in caplog.text

        assert not tmp_wav_path.exists()
    finally:
        # Clean up the session
        await aiohttp_session.close()


def test_no_ffmpeg(tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the app exists when there is no ffmpeg."""

    monkeypatch.setattr("shutil.which", lambda x: None)

    monkeypatch.setattr("pathlib.Path.exists", lambda x: False)

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.downloader") and pytest.raises(SystemExit):  # type: ignore[truthy-bool]
        asset_downloader.check_ffmpeg()

    assert "ffmpeg not found" in caplog.text


@pytest.mark.asyncio
async def test_fetch_podcast_rss_value_error(
    apd: PodcastsDownloader,
    mock_podcast_source_not_found: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the app can load config and the testing attribute is set."""

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.downloader"):
        await apd._download_and_parse_rss()

    assert "[test] RSS download attempt failed with HTTP status 404, not retrying" in caplog.text


@pytest.mark.asyncio
async def test_download_podcast_no_response(
    apd: PodcastsDownloader, get_test_config: Callable[[str], ArchivePodcastConfig], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test _fetch_podcast_rss failure."""

    async def mock_fetch_podcast_rss(*args: Any, **kwargs: Any) -> tuple[None, None]:
        return None, None

    monkeypatch.setattr("archivepodcast.downloader.PodcastsDownloader._fetch_podcast_rss", mock_fetch_podcast_rss)

    tree = await apd.download_podcast()

    assert tree is None
    assert not apd._feed_download_healthy


@pytest.mark.parametrize(
    ("file_name", "expected_slug"),
    [
        ("str", "str"),
        (b"str", "str"),
        ("str ", "str"),
        ("str%", "str"),
        ("str%str", "str-str"),
        (" str", "str"),
        ("str - str", "str---str"),
        ("str_", "str"),
        ("str***", "str"),
        ("str✌️", "str"),
    ],
)
def test_filename_cleanup(apd: PodcastsDownloader, file_name: str, expected_slug: str) -> None:
    """Test filename cleanup."""
    assert apd._cleanup_file_name(file_name) == expected_slug
