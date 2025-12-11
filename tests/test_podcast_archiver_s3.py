"""Tests for PodcastArchiver S3 functionality."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from archivepodcast.archiver.podcast_archiver import PodcastArchiver
from archivepodcast.config import ArchivePodcastConfig
from archivepodcast.utils.logger import TRACE_LEVEL_NUM
from tests.constants import DUMMY_RSS_STR
from tests.fixtures.aws import S3ClientMock

from . import FakeExceptionError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tests.fixtures.aws import AWSAioSessionMock
else:
    MockerFixture = object
    AWSAioSessionMock = object


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
) -> None:
    """Verify S3 configuration loading and bucket setup."""
    config_file = "testing_true_valid_s3.json"
    config = get_test_config(config_file)

    with caplog.at_level(logging.DEBUG):
        ap = PodcastArchiver(
            app_config=config.app,
            podcast_list=config.podcasts,
        )

    assert ap.s3


@pytest.mark.asyncio
async def test_render_files(
    apa_aws: PodcastArchiver,
    caplog: pytest.LogCaptureFixture,
    mock_get_session: AWSAioSessionMock,
) -> None:
    """Test that static pages are uploaded to s3."""
    with caplog.at_level(level=logging.DEBUG):
        await apa_aws.renderer.render_files()

    assert apa_aws.s3

    async with mock_get_session.create_client("s3") as s3_client:
        list_files = await s3_client.list_objects_v2(Bucket=apa_aws._app_config.s3.bucket)

    list_files_str = [path["Key"] for path in list_files.get("Contents", [])]

    assert "index.html" in list_files_str
    assert "guide.html" in list_files_str
    assert "about.html" not in list_files_str

    assert "pages to files, all pages uploaded to s3" in caplog.text
    assert "Unhandled s3 error" not in caplog.text


@pytest.mark.asyncio
async def test_check_s3_no_files(apa_aws: PodcastArchiver, caplog: pytest.LogCaptureFixture) -> None:
    """Test that s3 files are checked."""
    with caplog.at_level(level=0):
        await apa_aws.renderer._check_s3_files()

    assert "Checking state of s3 bucket" in caplog.text
    assert "No objects found in the bucket" in caplog.text


@pytest.mark.asyncio
async def test__check_s3_files(apa_aws: PodcastArchiver, caplog: pytest.LogCaptureFixture) -> None:
    """Test that s3 files are checked."""
    await apa_aws.renderer.render_files()

    with caplog.at_level(level=TRACE_LEVEL_NUM):
        await apa_aws.renderer._check_s3_files()

    assert "Checking state of s3 bucket" in caplog.text
    assert "S3 Bucket Contents" in caplog.text
    assert "Unhandled s3 error" not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(("path", "content_type"), CONTENT_TYPE_PARAMS)
async def test_s3_object_content_type(
    apa_aws: PodcastArchiver,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_podcast_source_rss_valid: MockerFixture,
    mock_get_session: AWSAioSessionMock,
    path: str,
    content_type: str,
) -> None:
    """Verify correct content types are set for S3 objects."""
    await apa_aws.renderer.render_files()
    file_list = await apa_aws.get_file_list()
    await apa_aws.renderer.render_filelist_html(file_list)

    bucket = apa_aws._app_config.s3.bucket

    assert apa_aws.s3

    async with mock_get_session.create_client("s3") as s3_client:
        object_info = await s3_client.head_object(Bucket=bucket, Key=path)

    assert object_info["ContentType"] == content_type


@pytest.mark.asyncio
async def test_check_s3_files_problem_files(
    apa_aws: PodcastArchiver,
    mock_get_session: AWSAioSessionMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that problem s3 paths are removed."""
    assert apa_aws.s3

    async with mock_get_session.create_client("s3") as s3_client:
        await s3_client.put_object(
            Bucket=apa_aws._app_config.s3.bucket,
            Key="/index.html",
            Body="TEST leading slash",
            ContentType="text/html",
        )

        await s3_client.put_object(
            Bucket=apa_aws._app_config.s3.bucket,
            Key="content/test//episode.mp3",
            Body="TEST double slash",
            ContentType="text/html",
        )

        await s3_client.put_object(
            Bucket=apa_aws._app_config.s3.bucket,
            Key="/content/test//episode.mp3",
            Body="TEST double slash and leading slash",
            ContentType="text/html",
        )

        await s3_client.put_object(
            Bucket=apa_aws._app_config.s3.bucket,
            Key="content/test/empty_file.mp3",
            Body="",
            ContentType="text/html",
        )

    with caplog.at_level(level=logging.WARNING):
        await apa_aws.renderer._check_s3_files()

    assert "S3 Path starts with a /, this is not expected: /index.html DELETING" in caplog.text
    assert "S3 Path contains a //, this is not expected: content/test//episode.mp3 DELETING" in caplog.text
    assert "S3 Object is empty: content/test/empty_file.mp3 DELETING" in caplog.text

    async with mock_get_session.create_client("s3") as s3_client:
        s3_object_list = await s3_client.list_objects_v2(Bucket=apa_aws._app_config.s3.bucket)
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
    assert "Hosted feed: http://localhost:5100/rss/test" in caplog.text

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

    monkeypatch.setattr(S3ClientMock, "put_object", mock_unhandled_exception)  # Doctors hate him!

    with caplog.at_level(level=logging.DEBUG):
        apa_aws.grab_podcasts()

    assert "Unhandled s3 error trying to upload the file:" in caplog.text
