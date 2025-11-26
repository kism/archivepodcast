"""Tests for PodcastArchiver S3 functionality."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import HttpUrl

from archivepodcast.archiver.podcast_archiver import PodcastArchiver
from archivepodcast.config import ArchivePodcastConfig
from archivepodcast.utils.logger import TRACE_LEVEL_NUM
from tests.constants import DUMMY_RSS_STR, FLASK_ROOT_PATH

from . import FakeExceptionError

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
    from pytest_mock import MockerFixture
else:
    MockerFixture = object
    S3Client = object

CONTENT_TYPE_PARAMS = [
    ("index.html", "text/html"),
    ("filelist.html", "text/html"),
    ("static/clipboard.js", "text/javascript"),
    ("static/filelist.js", "text/javascript"),
    ("robots.txt", "text/plain"),
    ("static/favicon.ico", "image/vnd.microsoft.icon"),
    ("static/fonts/fira-code-v12-latin-500.woff2", "font/woff2"),
]


def test_config_valid(
    tmp_path: Path,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    caplog: pytest.LogCaptureFixture,
    s3: S3Client,
) -> None:
    """Verify S3 configuration loading and bucket setup."""
    config_file = "testing_true_valid_s3.json"
    config = get_test_config(config_file)

    bucket_name = config.app.s3.bucket
    s3.create_bucket(Bucket=bucket_name)

    with caplog.at_level(logging.DEBUG):
        PodcastArchiver(
            app_config=config.app,
            podcast_list=config.podcasts,
            instance_path=tmp_path,
            root_path=FLASK_ROOT_PATH,
        )

    assert "Not using s3" not in caplog.text
    assert f"Authenticated s3, using bucket: {bucket_name}" in caplog.text


def test_render_files(apa_aws: PodcastArchiver, caplog: pytest.LogCaptureFixture) -> None:
    """Test that static pages are uploaded to s3."""
    with caplog.at_level(level=logging.DEBUG):
        apa_aws._render_files()

    assert apa_aws.s3 is not None

    list_files = apa_aws.s3.list_objects_v2(Bucket=apa_aws.app_config.s3.bucket)
    list_files_str = [path["Key"] for path in list_files.get("Contents", [])]

    assert "index.html" in list_files_str
    assert "guide.html" in list_files_str
    assert "about.html" not in list_files_str

    assert "Writing 18 pages to files locally and to s3" in caplog.text
    assert "Writing filelist.html to file locally and to s3" in caplog.text
    assert "Unhandled s3 error" not in caplog.text


def test_check_s3_no_files(apa_aws: PodcastArchiver, caplog: pytest.LogCaptureFixture) -> None:
    """Test that s3 files are checked."""
    with caplog.at_level(level=logging.INFO):
        apa_aws.check_s3_files()

    assert "Checking state of s3 bucket" in caplog.text
    assert "No objects found in the bucket" in caplog.text


def test_check_s3_files(apa_aws: PodcastArchiver, caplog: pytest.LogCaptureFixture) -> None:
    """Test that s3 files are checked."""
    apa_aws._render_files()

    with caplog.at_level(level=TRACE_LEVEL_NUM):
        apa_aws.check_s3_files()

    assert "Checking state of s3 bucket" in caplog.text
    assert "S3 Bucket Contents" in caplog.text
    assert "Unhandled s3 error" not in caplog.text


@pytest.mark.parametrize(("path", "content_type"), CONTENT_TYPE_PARAMS)
def test_s3_object_content_type(
    apa_aws: PodcastArchiver,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_podcast_source_rss_valid: MockerFixture,
    path: str,
    content_type: str,
) -> None:
    """Verify correct content types are set for S3 objects."""
    apa_aws._render_files()

    bucket = apa_aws.app_config.s3.bucket

    assert apa_aws.s3 is not None

    object_info = apa_aws.s3.head_object(Bucket=bucket, Key=path)

    assert object_info["ContentType"] == content_type


def test_check_s3_files_problem_files(apa_aws: PodcastArchiver, caplog: pytest.LogCaptureFixture) -> None:
    """Test that problem s3 paths are removed."""
    assert apa_aws.s3 is not None

    apa_aws.s3.put_object(
        Bucket=apa_aws.app_config.s3.bucket,
        Key="/index.html",
        Body="TEST leading slash",
        ContentType="text/html",
    )

    apa_aws.s3.put_object(
        Bucket=apa_aws.app_config.s3.bucket,
        Key="content/test//episode.mp3",
        Body="TEST double slash",
        ContentType="text/html",
    )

    apa_aws.s3.put_object(
        Bucket=apa_aws.app_config.s3.bucket,
        Key="/content/test//episode.mp3",
        Body="TEST double slash and leading slash",
        ContentType="text/html",
    )

    apa_aws.s3.put_object(
        Bucket=apa_aws.app_config.s3.bucket,
        Key="content/test/empty_file.mp3",
        Body="",
        ContentType="text/html",
    )

    with caplog.at_level(level=logging.WARNING):
        apa_aws.check_s3_files()

    assert "S3 Path starts with a /, this is not expected: /index.html DELETING" in caplog.text
    assert "S3 Path contains a //, this is not expected: content/test//episode.mp3 DELETING" in caplog.text
    assert "S3 Object is empty: content/test/empty_file.mp3 DELETING" in caplog.text

    s3_object_list = apa_aws.s3.list_objects_v2(Bucket=apa_aws.app_config.s3.bucket)
    s3_object_list_str = [path["Key"] for path in s3_object_list.get("Contents", [])]

    assert s3_object_list_str == []


def test_grab_podcasts_live(
    apa_aws: PodcastArchiver,
    caplog: pytest.LogCaptureFixture,
    mock_podcast_source_rss_valid: MockerFixture,
) -> None:
    """Test grabbing podcasts."""

    apa_aws.podcast_list[0].live = True

    with caplog.at_level(level=logging.DEBUG):
        apa_aws.grab_podcasts()

    assert "Processing podcast to archive: PyTest Podcast [Archive S3]" in caplog.text
    assert "Wrote rss to disk:" in caplog.text
    assert "Hosted: http://localhost:5100/rss/test" in caplog.text

    rss = str(apa_aws.get_rss_feed("test"))

    assert "PyTest Podcast [Archive S3]" in rss
    assert "http://localhost:5100/content/test/20200101-Test-Episode.mp3" in rss
    assert "http://localhost:5100/content/test/PyTest-Podcast-Archive-S3.jpg" in rss
    assert "<link>http://localhost:5100/</link>" in rss
    assert "<title>Test Episode</title>" in rss

    assert "https://pytest.internal/images/test.jpg" not in rss
    assert "https://pytest.internal/audio/test.mp3" not in rss


def test_upload_to_s3_exception(
    apa_aws: PodcastArchiver,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
    mock_podcast_source_rss_valid: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test grabbing podcasts."""

    apa_aws.podcast_list[0].live = False

    rss_path = Path(tmp_path) / "web" / "rss" / "test"
    rss_path.parent.mkdir(parents=True, exist_ok=True)
    with rss_path.open("w") as file:
        file.write(DUMMY_RSS_STR)

    def mock_unhandled_exception(*args: Any, **kwargs: Any) -> None:
        raise FakeExceptionError

    monkeypatch.setattr(apa_aws.s3, "put_object", mock_unhandled_exception)

    with caplog.at_level(level=logging.DEBUG):
        apa_aws.grab_podcasts()

    assert "Unhandled s3 error trying to upload the file:" in caplog.text


def test_load_s3_api_url(
    apa: PodcastArchiver, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Test loading the s3 api url.

    We hack the apa object (without aws) since moto doesn't support setting the endpoint_url.
    """
    apa_no_mocked_aws = apa

    test_url = HttpUrl("https://awsurl.internal/")

    apa_no_mocked_aws.app_config.storage_backend = "s3"
    apa_no_mocked_aws.app_config.s3.api_url = test_url
    apa_no_mocked_aws.app_config.s3.access_key_id = "abc"
    apa_no_mocked_aws.app_config.s3.secret_access_key = "xyz"
    apa_no_mocked_aws.app_config.s3.bucket = "test"

    def check_url_set(_: Any, endpoint_url: HttpUrl, *args: Any, **kwargs: Any) -> None:
        assert endpoint_url == test_url.encoded_string()

    monkeypatch.setattr("boto3.client", check_url_set)

    monkeypatch.setattr(apa_no_mocked_aws, "check_s3_files", lambda: None)

    with caplog.at_level(level=logging.INFO):
        apa_no_mocked_aws.load_s3()

    assert "Authenticated s3, using bucket: test" in caplog.text
    assert "No s3 client to list files" not in caplog.text  # Ensure that check_s3_files was not called
