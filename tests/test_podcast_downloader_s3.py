"""Tests for S3-specific PodcastDownloader functionality."""

import logging
import os
from pathlib import Path

import pytest

from archivepodcast.ap_downloader import PodcastDownloader

from . import FakeExceptionError


def test_init(s3, get_test_config, tmp_path, caplog):
    """Test PodcastDownloader initialization with S3 configuration."""
    config_file = "testing_true_valid_s3.toml"
    config = get_test_config(config_file)

    bucket_name = config["app"]["s3"]["bucket"]
    s3.create_bucket(Bucket=bucket_name)

    web_root = Path(tmp_path) / "web"

    with caplog.at_level(pytest.TRACE_LEVEL_NUM):
        pd = PodcastDownloader(app_config=config["app"], s3=s3, web_root=str(web_root))

    assert "PodcastDownloader config (re)loaded" in caplog.text
    assert pd.s3_paths_cache == []


def test_download_podcast(
    apd_aws,
    get_test_config,
    mock_get_podcast_source_rss,
    mock_podcast_source_images,
    mock_podcast_source_mp3,
    caplog,
):
    """Test downloading podcast RSS and assets."""
    config_file = "testing_true_valid_s3.toml"
    config = get_test_config(config_file)
    mock_podcast_definition = config["podcast"][0]

    mock_get_podcast_source_rss("test_valid.rss")

    with caplog.at_level(level=logging.INFO, logger="archivepodcast.ap_downloader"):
        apd_aws.download_podcast(mock_podcast_definition)

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

    s3_object_list = apd_aws.s3.list_objects_v2(Bucket=apd_aws.app_config["s3"]["bucket"])
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
    """Test downloading podcast RSS and assets with WAV format."""
    config_file = "testing_true_valid_s3.toml"
    config = get_test_config(config_file)
    mock_podcast_definition = config["podcast"][0]

    mock_get_podcast_source_rss("test_valid_wav.rss")

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_downloader"):
        apd_aws.download_podcast(mock_podcast_definition)

    assert "Downloaded rss feed, processing" in caplog.text
    assert "Podcast title: PyTest Test RSS feed for ArchivePodcast" in caplog.text
    assert "Downloading asset to:" in caplog.text
    assert "Converting episode" in caplog.text
    assert "HTTP ERROR:" not in caplog.text
    assert "Download Failed" not in caplog.text

    s3_object_list = apd_aws.s3.list_objects_v2(Bucket=apd_aws.app_config["s3"]["bucket"])
    s3_object_list = [path["Key"] for path in s3_object_list.get("Contents", [])]

    assert "content/test/20200101-Test-Episode.jpg" in s3_object_list
    assert "content/test/20200101-Test-Episode.mp3" in s3_object_list
    assert "content/test/PyTest-Podcast-Archive-S3.jpg" in s3_object_list


def test_upload_asset_s3_no_client(apd, caplog):
    """Test handling missing S3 client during upload."""
    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.ap_downloader"):
        apd._upload_asset_s3("test.jpg", ".jpg")

    assert "s3 client not found, cannot upload" in caplog.text


def test_upload_asset_s3_file_not_found(apd_aws, caplog):
    """Test handling file not found error during S3 upload."""
    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.ap_downloader"):
        apd_aws._upload_asset_s3("test_file_not_exist.jpg", ".jpg")

    assert "Could not upload to s3, the source file was not found" in caplog.text


def test_upload_asset_s3_unhandled_exception(apd_aws, monkeypatch, caplog):
    """Test handling unhandled exception during S3 upload."""

    def unhandled_exception(*args, **kwargs):
        raise FakeExceptionError

    monkeypatch.setattr(apd_aws.s3, "upload_file", unhandled_exception)

    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.ap_downloader"):
        apd_aws._upload_asset_s3("test_file_not_exist.jpg", ".jpg")

    assert "Unhandled s3 error" in caplog.text


def test_upload_asset_s3_os_remove_error(apd_aws, monkeypatch, caplog):
    """Test handling os.remove error during S3 upload."""

    def os_remove_error(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(os, "remove", os_remove_error)

    monkeypatch.setattr(apd_aws.s3, "upload_file", lambda *args, **kwargs: None)

    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.ap_downloader"):
        apd_aws._upload_asset_s3("test_file_mocked.jpg", ".jpg")

    assert "Could not remove the local file, the source file was not found" in caplog.text


def test_check_path_exists_s3(apd_aws, caplog):
    """Test checking if a path exists in S3."""
    apd_aws.s3.put_object(  # Bucket is empty before this
        Bucket=apd_aws.app_config["s3"]["bucket"],
        Key="content/test",
        Body="Test File Found",
        ContentType="text/html",
    )

    assert apd_aws._check_path_exists("content/test") is True
    assert apd_aws._check_path_exists("/content/test") is True

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_downloader"):
        assert apd_aws._check_path_exists("content/test/not_exist") is False

    assert "File: content/test/not_exist does not exist" in caplog.text


def test_check_path_exists_s3_client_error(apd_aws, monkeypatch, caplog):
    """Test handling non-404 S3 client error during path check."""
    from botocore.exceptions import ClientError

    def client_error_not_404(*args, **kwargs):
        raise ClientError({"Error": {"Code": "LimitExceededException"}}, "LimitExceededException")

    monkeypatch.setattr(apd_aws.s3, "head_object", client_error_not_404)

    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.ap_downloader"):
        assert apd_aws._check_path_exists("content/test") is False

    assert "s3 check file exists errored out?" in caplog.text


def test_check_path_exists_s3_unhandled_exception(apd_aws, monkeypatch, caplog):
    """Test handling unhandled exception during S3 path check."""

    def unhandled_exception(*args, **kwargs):
        raise FakeExceptionError

    monkeypatch.setattr(apd_aws.s3, "head_object", unhandled_exception)

    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.ap_downloader"):
        assert apd_aws._check_path_exists("content/test") is False

    assert "Unhandled s3 Error" in caplog.text
