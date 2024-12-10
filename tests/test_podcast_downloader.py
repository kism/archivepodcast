"""App testing different config behaviours."""

import logging
import os
from http import HTTPStatus

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

    assert "Downloaded rss feed, processing" in caplog.text
    assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
    assert "Downloading asset to:" in caplog.text
    assert "Converting episode" not in caplog.text
    assert "HTTP ERROR:" not in caplog.text
    assert "Download Failed" not in caplog.text
    # assert "lmao" in caplog.text


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

    assert "Downloaded rss feed, processing" in caplog.text
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

    assert "Downloaded rss feed, processing" in caplog.text
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

    assert "Downloaded rss feed, processing" in caplog.text
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

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_downloader") and pytest.raises(SystemExit):
        ap_downloader.check_ffmpeg()

    assert "ffmpeg not found" in caplog.text


def test_fetch_podcast_rss_error(apd, requests_mock, caplog):
    """Test that the app can load config and the testing attribute is set."""
    rss_url = "https://podcast.internal/rss/not_found"
    requests_mock.get(rss_url, status_code=404)

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_downloader"):
        apd._fetch_podcast_rss(rss_url)

    assert "Not a great web response getting RSS: 404" in caplog.text


def test_fetch_podcast_rss_value_error(apd, monkeypatch, caplog):
    """Test that the app can load config and the testing attribute is set."""
    rss_url = "https://podcast.internal/rss/not_found"

    def mock_value_error(*args, **kwargs) -> None:
        raise ValueError

    monkeypatch.setattr("requests.get", mock_value_error)

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_downloader"):
        apd._fetch_podcast_rss(rss_url)

    assert "Real early failure on grabbing the podcast rss" in caplog.text


def test_download_podcast_no_response(apd, get_test_config, monkeypatch):
    """Test _fetch_podcast_rss failure."""
    podcast = get_test_config("testing_true_valid.toml")["podcast"][0]

    def mock_fetch_podcast_rss(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr("archivepodcast.ap_downloader.PodcastDownloader._fetch_podcast_rss", mock_fetch_podcast_rss)

    assert apd.download_podcast(podcast) is None


def test_download_to_local_failure(apd, requests_mock, caplog):
    """Test local file download failure."""
    url = "https://pytest.internal/audio/test.mp3"

    requests_mock.get(url, status_code=HTTPStatus.NOT_FOUND)

    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.ap_downloader"):
        apd._download_to_local(url, "test.mp3")

    assert "HTTP ERROR" in caplog.text


@pytest.mark.parametrize(
    ("file_name", "expected_slug"),
    [
        ("lmao", "lmao"),
        (b"lmao", "lmao"),
        ("lmao ", "lmao"),
        ("lmao%", "lmao"),
        ("lmao%lmao", "lmao-lmao"),
        (" lmao", "lmao"),
        ("lmao - lmao", "lmao---lmao"),
        ("lmao_", "lmao"),
        ("lmao***", "lmao"),
        ("lmao✌️", "lmao"),
    ],
)
def test_filename_cleanup(apd, file_name, expected_slug):
    """Test filename cleanup."""
    assert apd._cleanup_file_name(file_name) == expected_slug
