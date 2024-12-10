"""App testing different config behaviours."""

import logging
import os

import pytest

from . import FakeExceptionError

FLASK_ROOT_PATH = os.getcwd()


def test_config_valid(tmp_path, get_test_config, caplog, s3):
    """Test that the app can load config and the testing attribute is set."""
    config_file = "testing_true_valid_s3.toml"
    config = get_test_config(config_file)

    bucket_name = config["app"]["s3"]["bucket"]
    s3.create_bucket(Bucket=bucket_name)

    from archivepodcast.ap_archiver import PodcastArchiver

    with caplog.at_level(logging.DEBUG):
        PodcastArchiver(
            app_settings=config["app"],
            podcast_list=config["podcast"],
            instance_path=tmp_path,
            root_path=FLASK_ROOT_PATH,
        )

    assert "Not using s3" not in caplog.text
    assert f"Authenticated s3, using bucket: {bucket_name}" in caplog.text


def test_render_static(apa_aws, caplog):
    """Test that static pages are uploaded to s3."""
    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_archiver.render_static"):
        apa_aws._render_static()

    list_files = apa_aws.s3.list_objects_v2(Bucket=apa_aws.app_settings["s3"]["bucket"])
    list_files = [path["Key"] for path in list_files.get("Contents", [])]

    assert "index.html" in list_files
    assert "guide.html" in list_files
    assert "about.html" not in list_files

    assert "Uploading static pages to s3 in the background" in caplog.text
    assert "Uploading static item" in caplog.text
    assert "Done uploading static pages to s3" in caplog.text


def test_check_s3_no_files(apa_aws, caplog):
    """Test that s3 files are checked."""
    with caplog.at_level(level=logging.INFO, logger="archivepodcast.ap_archiver"):
        apa_aws.check_s3_files()

    assert "Checking state of s3 bucket" in caplog.text
    assert "No objects found in the bucket" in caplog.text


def test_check_s3_files(apa_aws, caplog):
    """Test that s3 files are checked."""
    apa_aws._render_static()

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_archiver"):
        apa_aws.check_s3_files()

    assert "Checking state of s3 bucket" in caplog.text
    assert "S3 Bucket Contents" in caplog.text


def test_check_s3_files_problem_files(apa_aws, caplog):
    """Test that problem s3 paths are removed."""
    apa_aws.s3.put_object(
        Bucket=apa_aws.app_settings["s3"]["bucket"],
        Key="/index.html",
        Body="TEST leading slash",
        ContentType="text/html",
    )

    apa_aws.s3.put_object(
        Bucket=apa_aws.app_settings["s3"]["bucket"],
        Key="content/test//episode.mp3",
        Body="TEST double slash",
        ContentType="text/html",
    )

    with caplog.at_level(level=logging.WARNING, logger="archivepodcast.ap_archiver"):
        apa_aws.check_s3_files()

    assert "S3 Path starts with a /, this is not expected: /index.html DELETING" in caplog.text
    assert "S3 Path contains a //, this is not expected: content/test//episode.mp3 DELETING" in caplog.text

    s3_object_list = apa_aws.s3.list_objects_v2(Bucket=apa_aws.app_settings["s3"]["bucket"])
    s3_object_list = [path["Key"] for path in s3_object_list.get("Contents", [])]

    assert s3_object_list == []


def test_grab_podcasts_live(
    apa_aws,
    caplog,
    mock_get_podcast_source_rss,
    mock_podcast_source_images,
    mock_podcast_source_mp3,
):
    """Test grabbing podcasts."""
    mock_get_podcast_source_rss("test_valid.rss")

    apa_aws.podcast_list[0]["live"] = True

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_archiver"):
        apa_aws.grab_podcasts()

    assert "Processing settings entry: PyTest Podcast [Archive S3]" in caplog.text
    assert "Wrote rss to disk:" in caplog.text
    assert "Hosted: http://localhost:5000/rss/test" in caplog.text

    rss = str(apa_aws.get_rss_feed("test"))

    assert "PyTest Podcast [Archive S3]" in rss
    assert "http://localhost:5000/content/test/20200101-Test-Episode.mp3" in rss
    assert "http://localhost:5000/content/test/PyTest-Podcast-Archive-S3.jpg" in rss
    assert "<link>http://localhost:5000/</link>" in rss
    assert "<title>Test Episode</title>" in rss

    assert "https://pytest.internal/images/test.jpg" not in rss
    assert "https://pytest.internal/audio/test.mp3" not in rss


def test_upload_to_s3_exception(
    apa_aws,
    caplog,
    tmp_path,
    mock_get_podcast_source_rss,
    mock_podcast_source_images,
    mock_podcast_source_mp3,
    monkeypatch,
):
    """Test grabbing podcasts."""
    mock_get_podcast_source_rss("test_valid.rss")
    apa_aws.podcast_list[0]["live"] = False

    with open(os.path.join(tmp_path, "web", "rss", "test"), "w") as file:
        file.write(pytest.DUMMY_RSS_STR)

    def mock_unhandled_exception(*args, **kwargs) -> None:
        raise FakeExceptionError

    monkeypatch.setattr(apa_aws.s3, "put_object", mock_unhandled_exception)

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_archiver"):
        apa_aws.grab_podcasts()

    assert "Unhandled s3 error trying to upload the file:" in caplog.text


def test_load_s3_api_url(apa, monkeypatch, caplog):
    """Test loading the s3 api url.

    We hack the apa object (without aws) since moto doesn't support setting the endpoint_url.
    """
    apa_no_mocked_aws = apa

    test_url = "https://awsurl.internal/"

    apa_no_mocked_aws.app_settings["storage_backend"] = "s3"
    apa_no_mocked_aws.app_settings["s3"] = {}
    apa_no_mocked_aws.app_settings["s3"]["api_url"] = test_url
    apa_no_mocked_aws.app_settings["s3"]["access_key_id"] = "abc"
    apa_no_mocked_aws.app_settings["s3"]["secret_access_key"] = "xyz"
    apa_no_mocked_aws.app_settings["s3"]["bucket"] = "test"

    def check_url_set(_, endpoint_url: str, *args, **kwargs) -> None:
        assert endpoint_url == test_url

    monkeypatch.setattr("boto3.client", check_url_set)

    monkeypatch.setattr(apa_no_mocked_aws, "check_s3_files", lambda: None)

    with caplog.at_level(level=logging.INFO, logger="archivepodcast.ap_archiver"):
        apa_no_mocked_aws.load_s3()

    assert "Authenticated s3, using bucket: test" in caplog.text
    assert "No s3 client to list files" not in caplog.text  # Ensure that check_s3_files was not called
