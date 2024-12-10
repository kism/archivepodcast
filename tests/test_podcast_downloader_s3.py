"""App testing different config behaviours."""

import logging
import os

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


def test_upload_asset_s3_no_client(apd, caplog):
    """Test upload failure when no s3 client."""
    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.ap_downloader"):
        apd._upload_asset_s3("test.jpg", ".jpg")

    assert "s3 client not found, cannot upload" in caplog.text


def test_upload_asset_s3_file_not_found(apd_aws, caplog):
    """Test upload failure when no s3 client."""
    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.ap_downloader"):
        apd_aws._upload_asset_s3("test_file_not_exist.jpg", ".jpg")

    assert "Could not upload to s3, the source file was not found" in caplog.text


def test_upload_asset_s3_unhandled_exception(apd_aws, monkeypatch, caplog):
    """Test upload failure when no s3 client."""

    class FakeExceptionError(Exception):
        pass

    def unhandled_exception(*args, **kwargs) -> None:
        raise FakeExceptionError

    monkeypatch.setattr(apd_aws.s3, "upload_file", unhandled_exception)

    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.ap_downloader"):
        apd_aws._upload_asset_s3("test_file_not_exist.jpg", ".jpg")

    assert "Unhandled s3 Error" in caplog.text

def test_check_path_exists_s3(apd_aws, caplog):
    """Test check path exists."""
    apd_aws.s3.put_object( # Bucket is empty before this
        Bucket=apd_aws.app_settings["s3"]["bucket"],
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
    """Test non-404 s3 client error handling."""
    from botocore.exceptions import ClientError

    def client_error_not_404(*args, **kwargs) -> None:
        raise ClientError({"Error": {"Code": "LimitExceededException"}}, "LimitExceededException")

    monkeypatch.setattr(apd_aws.s3, "head_object", client_error_not_404)

    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.ap_downloader"):
        assert apd_aws._check_path_exists("content/test") is False

    assert "s3 check file exists errored out?" in caplog.text

def test_check_path_exists_s3_unhandled_exception(apd_aws, monkeypatch, caplog):
    """Test unhandled exception handling."""
    class FakeExceptionError(Exception):
        pass

    def unhandled_exception(*args, **kwargs) -> None:
        raise FakeExceptionError

    monkeypatch.setattr(apd_aws.s3, "head_object", unhandled_exception)

    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.ap_downloader"):
        assert apd_aws._check_path_exists("content/test") is False

    assert "Unhandled s3 Error" in caplog.text
