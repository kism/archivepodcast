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
        pd = PodcastDownloader(app_settings=config["app"], s3=None, web_root=web_root)

    assert "PodcastDownloader settings (re)loaded" in caplog.text
    assert pd.s3_paths_cache == []


@pytest.fixture
def pd(pa, get_test_config, caplog, mock_threads_none):
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid.toml"
    config = get_test_config(config_file)

    web_root = pa.web_root

    return PodcastDownloader(app_settings=config["app"], s3=None, web_root=web_root)


@pytest.mark.parametrize(
    "test_config_name",
    [
        "testing_true_valid.toml",
        "testing_true_valid_no_override_info.toml",
    ],
)
def test_download_podcast(
    pd,
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
        pd.download_podcast(mock_podcast_definition)

    assert "Downloaded RSS XML, Processing" in caplog.text
    assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
    assert "Downloading asset to:" in caplog.text
    assert "HTTP ERROR:" not in caplog.text
    assert "Download Failed" not in caplog.text


def test_download_podcast_wav(
    pd,
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
        pd.download_podcast(mock_podcast_definition)

    assert "Downloaded RSS XML, Processing" in caplog.text
    assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
    assert "Downloading asset to:" in caplog.text
    assert "HTTP ERROR:" not in caplog.text
    assert "Download Failed" not in caplog.text
