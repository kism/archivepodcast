"""App testing different config behaviours."""

import logging
import os

import pytest

from archivepodcast.ap_downloader import PodcastDownloader
from archivepodcast.logger import TRACE_LEVEL_NUM

FLASK_ROOT_PATH = os.getcwd()


def test_init(get_test_config, tmp_path, caplog):
    """Test that the app can load config and the testing attribute is set."""
    config_file = "testing_true_valid.toml"
    config = get_test_config(config_file)

    web_root = os.path.join(tmp_path, "web")

    with caplog.at_level(TRACE_LEVEL_NUM):
        apd = PodcastDownloader(app_settings=config["app"], s3=None, web_root=web_root)

    assert "PodcastDownloader settings (re)loaded" in caplog.text
    assert apd.s3_paths_cache == []


@pytest.fixture
def apd(apa, get_test_config, caplog):
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid.toml"
    config = get_test_config(config_file)

    web_root = apa.web_root

    return PodcastDownloader(app_settings=config["app"], s3=None, web_root=web_root)


@pytest.mark.parametrize(
    "test_config_name",
    [
        "testing_true_valid.toml",
        "testing_true_valid_no_override_info.toml",
    ],
)
def test_download_podcast(
    apd,
    test_config_name,
    get_test_config,
    mock_get_podcast_source_rss,
    mock_podcast_source_images,
    mock_podcast_source_mp3,
    caplog,
):
    """Test Fetching RSS and assets."""
    config_file = test_config_name
    config = get_test_config(config_file)
    mock_podcast_definition = config["podcast"][0]

    mock_get_podcast_source_rss("test_valid.rss")

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_downloader"):
        apd.download_podcast(mock_podcast_definition)

    assert "Downloaded RSS XML, Processing" in caplog.text
    assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
    assert "Downloading asset to:" in caplog.text
    assert "Converting episode" not in caplog.text
    assert "HTTP ERROR:" not in caplog.text
    assert "Download Failed" not in caplog.text


def test_download_podcast_wav(
    apd,
    get_test_config,
    mock_get_podcast_source_rss,
    mock_podcast_source_images,
    mock_podcast_source_wav,
    caplog,
):
    """Test Fetching RSS and assets."""
    config_file = "testing_true_valid.toml"
    config = get_test_config(config_file)
    mock_podcast_definition = config["podcast"][0]

    mock_get_podcast_source_rss("test_valid_wav.rss")

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_downloader"):
        apd.download_podcast(mock_podcast_definition)

    assert "Downloaded RSS XML, Processing" in caplog.text
    assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
    assert "Downloading asset to:" in caplog.text
    assert "Converting episode" in caplog.text
    assert "HTTP ERROR:" not in caplog.text
    assert "Download Failed" not in caplog.text


def test_download_podcast_wav_wav_exists(
    apd,
    tmp_path,
    get_test_config,
    mock_get_podcast_source_rss,
    mock_podcast_source_images,
    mock_podcast_source_wav,
    caplog,
):
    """Test Fetching RSS and assets."""
    config_file = "testing_true_valid.toml"
    config = get_test_config(config_file)
    mock_podcast_definition = config["podcast"][0]

    test_podcast_content_dir = os.path.join(tmp_path, "web", "content", "test")

    os.makedirs(test_podcast_content_dir, exist_ok=True)

    tmp_wav_path = os.path.join(test_podcast_content_dir, "20200101-Test-Episode.wav")

    with open(tmp_wav_path, "wb") as f:
        f.write(pytest.TEST_WAV_FILE)

    mock_get_podcast_source_rss("test_valid_wav.rss")

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_downloader"):
        apd.download_podcast(mock_podcast_definition)

    assert "Downloaded RSS XML, Processing" in caplog.text
    assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
    assert "Downloading asset to:" in caplog.text
    assert "Converting episode" in caplog.text
    assert "Removing wav version of" in caplog.text
    assert "HTTP ERROR:" not in caplog.text
    assert "Download Failed" not in caplog.text

    assert not os.path.exists(tmp_wav_path)


def test_download_podcast_wav_mp3_exists(
    apd,
    tmp_path,
    get_test_config,
    mock_get_podcast_source_rss,
    mock_podcast_source_images,
    mock_podcast_source_wav,
    caplog,
):
    """Test Fetching RSS and assets."""
    config_file = "testing_true_valid.toml"
    config = get_test_config(config_file)
    mock_podcast_definition = config["podcast"][0]

    test_podcast_content_dir = os.path.join(tmp_path, "web", "content", "test")

    os.makedirs(test_podcast_content_dir, exist_ok=True)

    episode_file_name = "20200101-Test-Episode"
    tmp_wav_path = os.path.join(test_podcast_content_dir, f"{episode_file_name}.wav")
    tmp_mp3_path = os.path.join(test_podcast_content_dir, f"{episode_file_name}.mp3")

    with open(tmp_mp3_path, "w") as f:
        f.write("Test MP3")

    mock_get_podcast_source_rss("test_valid_wav.rss")

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_downloader"):
        apd.download_podcast(mock_podcast_definition)

    assert "Downloaded RSS XML, Processing" in caplog.text
    assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
    assert "Downloading asset to:" in caplog.text
    assert "Converting episode" not in caplog.text
    assert f"{episode_file_name}.mp3 exists locally" in caplog.text
    assert "HTTP ERROR:" not in caplog.text
    assert "Download Failed" not in caplog.text

    assert not os.path.exists(tmp_wav_path)


def test_no_ffmpeg(tmp_path, caplog, monkeypatch):
    """Test that the app exists when there is no ffmpeg."""

    from archivepodcast import ap_downloader

    monkeypatch.setattr("shutil.which", lambda x: None)

    # with pytest.raises(SystemExit):
    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_downloader") and pytest.raises(SystemExit):
        ap_downloader.check_ffmpeg()

    assert "ffmpeg not found" in caplog.text
