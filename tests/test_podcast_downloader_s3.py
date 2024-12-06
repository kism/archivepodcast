"""App testing different config behaviours."""

import logging
import os

import pytest

from archivepodcast.ap_downloader import PodcastDownloader
from archivepodcast.logger import TRACE_LEVEL_NUM

FLASK_ROOT_PATH = os.getcwd()


def test_init(s3, get_test_config, tmp_path, caplog):
    """Test that the app can load config and the testing attribute is set."""
    config_file = "testing_true_valid_s3.toml"
    config = get_test_config(config_file)

    bucket_name = config["app"]["s3"]["bucket"]
    s3.create_bucket(Bucket=bucket_name)

    web_root = os.path.join(tmp_path, "web")

    with caplog.at_level(TRACE_LEVEL_NUM):
        pd = PodcastDownloader(app_settings=config["app"], s3=s3, web_root=web_root)

    assert "PodcastDownloader settings (re)loaded" in caplog.text
    assert pd.s3_paths_cache == []


@pytest.fixture
def apd_aws(apa_aws, get_test_config, caplog):
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid_s3.toml"
    config = get_test_config(config_file)

    web_root = apa_aws.web_root

    return PodcastDownloader(app_settings=config["app"], s3=apa_aws.s3, web_root=web_root)


def test_download_podcast(
    apd_aws,
    get_test_config,
    mock_get_podcast_source_rss,
    mock_podcast_source_images,
    mock_podcast_source_mp3,
    caplog,
):
    """Test Fetching RSS and assets."""
    config_file = "testing_true_valid_s3.toml"
    config = get_test_config(config_file)
    mock_podcast_definition = config["podcast"][0]

    mock_get_podcast_source_rss("test_valid.rss")

    with caplog.at_level(level=logging.INFO, logger="archivepodcast.ap_downloader"):
        apd_aws.download_podcast(mock_podcast_definition)

    assert "Downloaded RSS XML, Processing" in caplog.text
    assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
    assert "Downloading asset to:" in caplog.text
    assert "Uploading to s3:" in caplog.text
    assert "s3 upload successful, removing local file" in caplog.text
    assert "HTTP ERROR:" not in caplog.text
    assert "Download Failed" not in caplog.text

    s3_object_list = apd_aws.s3.list_objects_v2(Bucket=apd_aws.app_settings["s3"]["bucket"])
    s3_object_list = [path["Key"] for path in s3_object_list.get("Contents", [])]

    assert "content/test/20200101-Test-Episode.jpg" in s3_object_list
    assert "content/test/20200101-Test-Episode.mp3" in s3_object_list
    assert "content/test/PyTest-Podcast-Archive-S3.jpg" in s3_object_list


def test_download_podcast_wav(
    apd_aws,
    get_test_config,
    mock_get_podcast_source_rss,
    mock_podcast_source_images,
    mock_podcast_source_wav,
    caplog,
):
    """Test Fetching RSS and assets."""
    config_file = "testing_true_valid_s3.toml"
    config = get_test_config(config_file)
    mock_podcast_definition = config["podcast"][0]

    mock_get_podcast_source_rss("test_valid_wav.rss")

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_downloader"):
        apd_aws.download_podcast(mock_podcast_definition)

    assert "Downloaded RSS XML, Processing" in caplog.text
    assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
    assert "Downloading asset to:" in caplog.text
    assert "Converting episode" in caplog.text
    assert "HTTP ERROR:" not in caplog.text
    assert "Download Failed" not in caplog.text

    s3_object_list = apd_aws.s3.list_objects_v2(Bucket=apd_aws.app_settings["s3"]["bucket"])
    s3_object_list = [path["Key"] for path in s3_object_list.get("Contents", [])]

    assert "content/test/20200101-Test-Episode.jpg" in s3_object_list
    assert "content/test/20200101-Test-Episode.mp3" in s3_object_list
    assert "content/test/PyTest-Podcast-Archive-S3.jpg" in s3_object_list

