"""App testing different config behaviours."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import magic
import pytest

from archivepodcast.config import ArchivePodcastConfig
from archivepodcast.downloader import downloader
from archivepodcast.downloader.downloader import PodcastDownloader
from archivepodcast.utils.logger import TRACE_LEVEL_NUM
from tests.constants import TEST_WAV_FILE

if TYPE_CHECKING:
    from pytest_mock import MockerFixture  # pragma: no cover
else:
    MockerFixture = object


def test_init(
    get_test_config: Callable[[str], ArchivePodcastConfig],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the app can load config and the testing attribute is set."""
    config_file = "testing_true_valid.json"
    config = get_test_config(config_file)

    web_root = Path(tmp_path) / "web"

    with caplog.at_level(TRACE_LEVEL_NUM):
        apd = PodcastDownloader(app_config=config.app, s3=None, web_root=web_root)

    assert "PodcastDownloader config (re)loaded" in caplog.text
    assert apd.s3_paths_cache == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_config_name",
    [
        "testing_true_valid.json",
        "testing_true_valid_no_override_info.json",
    ],
)
async def test_download_podcast(
    apd: PodcastDownloader,
    test_config_name: str,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_podcast_source_rss_valid: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test Fetching RSS and assets."""
    config_file = test_config_name
    config = get_test_config(config_file)
    mock_podcast_definition = config.podcasts[0]

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.downloader"):
        await apd.download_podcast(mock_podcast_definition)

    assert "Downloaded rss feed, processing" in caplog.text
    assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
    assert "Downloading asset to:" in caplog.text
    assert "Converting episode" not in caplog.text
    assert "HTTP ERROR:" not in caplog.text
    assert "Download Failed" not in caplog.text
    # assert "str" in caplog.text


@pytest.mark.asyncio
async def test_download_podcast_wav(
    apd: PodcastDownloader,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_podcast_source_rss_wav: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test Fetching RSS and assets."""
    config_file = "testing_true_valid.json"
    config = get_test_config(config_file)
    mock_podcast_definition = config.podcasts[0]

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.downloader"):
        await apd.download_podcast(mock_podcast_definition)

    assert "Downloaded rss feed, processing" in caplog.text
    assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
    assert "Downloading asset to:" in caplog.text
    assert "Converting episode" in caplog.text
    assert "HTTP ERROR:" not in caplog.text
    assert "Download Failed" not in caplog.text


@pytest.mark.asyncio
async def test_download_podcast_wav_wav_exists(
    apd: PodcastDownloader,
    tmp_path: Path,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_podcast_source_rss_wav: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test Fetching RSS and assets."""
    config_file = "testing_true_valid.json"
    config = get_test_config(config_file)
    mock_podcast_definition = config.podcasts[0]

    test_podcast_content_dir = Path(tmp_path) / "web" / "content" / "test"

    Path(test_podcast_content_dir).mkdir(parents=True, exist_ok=True)

    episode_file_name = "20200101-Test-Episode"
    tmp_wav_path = Path(test_podcast_content_dir) / f"{episode_file_name}.wav"
    tmp_mp3_path = Path(test_podcast_content_dir) / f"{episode_file_name}.mp3"

    tmp_wav_path.write_bytes(TEST_WAV_FILE)

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.downloader"):
        await apd.download_podcast(mock_podcast_definition)

    assert "Downloaded rss feed, processing" in caplog.text
    assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
    assert "Downloading asset to:" in caplog.text
    assert "Converting episode" in caplog.text
    assert "Removing wav version of" in caplog.text
    assert "HTTP ERROR:" not in caplog.text
    assert "Download Failed" not in caplog.text

    assert not tmp_wav_path.exists()
    assert tmp_mp3_path.exists()
    assert magic.from_file(tmp_mp3_path, mime=True) == "audio/mpeg"  # Check that the file is actually an mp3


@pytest.mark.asyncio
async def test_download_podcast_wav_mp3_exists(
    apd: PodcastDownloader,
    tmp_path: Path,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_podcast_source_rss_wav: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test Fetching RSS and assets."""
    apd.s3 = None
    config_file = "testing_true_valid.json"
    config = get_test_config(config_file)
    mock_podcast_definition = config.podcasts[0]

    test_podcast_content_dir = Path(tmp_path) / "web" / "content" / "test"

    test_podcast_content_dir.mkdir(parents=True, exist_ok=True)

    episode_file_name = "20200101-Test-Episode"
    tmp_wav_path = test_podcast_content_dir / f"{episode_file_name}.wav"
    tmp_mp3_path = test_podcast_content_dir / f"{episode_file_name}.mp3"

    tmp_mp3_path.write_text("Test MP3")

    with caplog.at_level(level=5, logger="archivepodcast.downloader"):
        await apd.download_podcast(mock_podcast_definition)

    assert "Downloaded rss feed, processing" in caplog.text
    assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
    assert "Downloading asset to:" in caplog.text
    assert "Converting episode" not in caplog.text
    assert f"{episode_file_name}.mp3 exists locally" in caplog.text
    assert "HTTP ERROR:" not in caplog.text
    assert "Download Failed" not in caplog.text

    assert not tmp_wav_path.exists()


def test_no_ffmpeg(tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the app exists when there is no ffmpeg."""

    monkeypatch.setattr("shutil.which", lambda x: None)

    monkeypatch.setattr("pathlib.Path.exists", lambda x: False)

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.downloader") and pytest.raises(SystemExit):  # type: ignore[truthy-bool]
        downloader.check_ffmpeg()

    assert "ffmpeg not found" in caplog.text


@pytest.mark.asyncio
async def test_fetch_podcast_rss_value_error(
    apd: PodcastDownloader, mock_podcast_source_not_found: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that the app can load config and the testing attribute is set."""
    rss_url = "https://podcast.internal/rss/not_found"

    def mock_value_error(*args: Any, **kwargs: Any) -> None:
        raise ValueError

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.downloader"):
        await apd._fetch_podcast_rss(rss_url)

    assert "Not a great web response getting RSS: 404" in caplog.text


@pytest.mark.asyncio
async def test_download_podcast_no_response(
    apd: PodcastDownloader, get_test_config: Callable[[str], ArchivePodcastConfig], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test _fetch_podcast_rss failure."""
    podcast = get_test_config("testing_true_valid.json").podcasts[0]

    async def mock_fetch_podcast_rss(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr("archivepodcast.downloader.PodcastDownloader._fetch_podcast_rss", mock_fetch_podcast_rss)

    tree, healthy_download = await apd.download_podcast(podcast)

    assert tree is None
    assert not healthy_download


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
def test_filename_cleanup(apd: PodcastDownloader, file_name: str, expected_slug: str) -> None:
    """Test filename cleanup."""
    assert apd._cleanup_file_name(file_name) == expected_slug
