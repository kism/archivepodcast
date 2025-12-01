"""Test the application blueprint endpoints."""

import datetime
import logging
import signal
from collections.abc import Callable
from datetime import UTC
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from pytest_mock import MockerFixture

from archivepodcast.archiver.podcast_archiver import PodcastArchiver
from archivepodcast.archiver.webpages import Webpages
from archivepodcast.config import ArchivePodcastConfig
from archivepodcast.instances import podcast_archiver
from archivepodcast.instances.podcast_archiver import _get_time_until_next_run
from tests.constants import DUMMY_RSS_STR

if TYPE_CHECKING:
    from tests.fixtures.aws import AWSAioSessionMock
else:
    AWSAioSessionMock = object

from . import FakeExceptionError


def test_app_paths(
    apa: PodcastArchiver,
    client_live: FlaskClient,
    client_live_s3: FlaskClient,
    tmp_path: Path,
) -> None:
    """Verify all expected application paths return correct responses."""

    assert len(apa.webpages) > 0

    podcast_archiver._ap = apa

    for client in [client_live, client_live_s3]:
        assert client is not None

        valid_path_list = [
            "/index.html",
            "/guide.html",
            "/health",
            "/robots.txt",
            "/static/clipboard.js",
            "/favicon.ico",
            "/static/favicon.ico",
            "/static/main.css",
            "/static/fonts/fira-code-v12-latin-500.woff2",
            "/static/fonts/fira-code-v12-latin-600.woff2",
            "/static/fonts/fira-code-v12-latin-700.woff2",
            "/static/fonts/noto-sans-display-latin-500.woff2",
            "/static/fonts/noto-sans-display-latin-500italic.woff2",
        ]

        for path in valid_path_list:
            response = client.get(path)
            assert response.status_code == HTTPStatus.OK, f"Failed on {path}"

        response = client.get("/non_existent_page")
        assert response.status_code == HTTPStatus.NOT_FOUND


def test_app_paths_not_generated(
    apa: PodcastArchiver,
    client_live: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the error for when a page has not been generated."""
    # Ensure that no webpages can be added by the thread.

    def mock_add_webpage(*args: Any, **kwargs: Any) -> None:
        pass

    podcast_archiver._ap = apa

    monkeypatch.setattr("archivepodcast.archiver.webpages.Webpages.add", mock_add_webpage)

    apa.webpages = Webpages()

    webpage_list = [
        "/index.html",
        "/guide.html",
        "/robots.txt",
        "/favicon.ico",
        "/health",
    ]

    for webpage in webpage_list:
        with caplog.at_level(level=logging.WARNING):
            response = client_live.get(webpage)

        assert response.status_code == HTTPStatus.OK
        assert "Webpage not in cache serving from disk" in caplog.text
        assert webpage in caplog.text
        caplog.clear()


@pytest.mark.asyncio
async def test_app_path_about(
    apa: PodcastArchiver,
    client_live: FlaskClient,
    tmp_path: Path,
) -> None:
    """Test the about page."""

    podcast_archiver._ap = apa

    about_path = Path(tmp_path) / "about.md"
    if about_path.exists():
        about_path.unlink()

    await apa._load_about_page()
    response = client_live.get("/about.html")
    assert response.status_code == HTTPStatus.NOT_FOUND

    about_path.write_text("Test")

    await apa._load_about_page()
    response = client_live.get("/about.html")
    assert response.status_code == HTTPStatus.OK, f"About page should exist, got status code: {response.status_code}"


def test_rss_feed(
    apa: PodcastArchiver,
    app_live: Flask,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the RSS feed."""

    podcast_archiver._ap = apa
    apa.podcast_list[0].live = True
    apa.grab_podcasts()

    client_live = app_live.test_client()

    response = client_live.get("/rss/test")
    assert response.status_code == HTTPStatus.OK
    assert response.content_type == "application/rss+xml; charset=utf-8"

    response = client_live.get("/rss/non_existent_feed")
    assert response.status_code == HTTPStatus.NOT_FOUND

    rss_file = Path(tmp_path) / "web" / "rss" / "test_from_file"
    rss_file.parent.mkdir(parents=True, exist_ok=True)
    rss_file.write_text(DUMMY_RSS_STR)

    assert Path(apa.instance_path).joinpath("web", "rss", "test_from_file").exists()

    with caplog.at_level(logging.WARNING):
        response = client_live.get("/rss/test_from_file")

    response_str = response.data.decode("utf-8")
    assert response_str == DUMMY_RSS_STR
    assert response.status_code == HTTPStatus.OK
    assert "not live, sending cached version from disk" in caplog.text

    response = client_live.get("/content/test/20200101-Test-Episode.mp3")
    assert response.status_code == HTTPStatus.OK


def test_rss_feed_type_error(
    apa: PodcastArchiver,
    app_live: Flask,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the RSS feed."""

    podcast_archiver._ap = apa
    ap = apa

    client_live = app_live.test_client()

    def return_type_error(*args: Any, **kwargs: Any) -> None:
        raise TypeError

    monkeypatch.setattr(ap, "get_rss_feed", return_type_error)

    response = client_live.get("/rss/test")
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_rss_feed_unhandled_error(
    apa: PodcastArchiver,
    app_live: Flask,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the RSS feed."""

    podcast_archiver._ap = apa
    ap = apa

    ap.grab_podcasts()

    client_live = app_live.test_client()

    with Path(tmp_path / "web" / "rss" / "test").open("w") as file:
        file.write(DUMMY_RSS_STR)

    def return_key_error(*args: Any, **kwargs: Any) -> None:
        raise KeyError

    monkeypatch.setattr(ap, "get_rss_feed", return_key_error)

    def return_unhandled_error(*args: Any, **kwargs: Any) -> None:
        raise FakeExceptionError

    monkeypatch.setattr("lxml.etree.tostring", return_unhandled_error)

    response = client_live.get("/rss/test")
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_content_s3(
    apa_aws: PodcastArchiver,
    app_live_s3: Flask,
    monkeypatch: pytest.MonkeyPatch,
    mock_get_session: MockerFixture,
) -> None:
    """Test the RSS feed."""

    monkeypatch.setattr(podcast_archiver, "_ap", apa_aws)

    ap = apa_aws

    ap.grab_podcasts()

    client_live = app_live_s3.test_client()

    response = client_live.get("/content/test/20200101-Test-Episode.mp3")
    assert response.status_code == HTTPStatus.TEMPORARY_REDIRECT


def test_reload_config(
    app: Flask,
    apa: PodcastArchiver,
    tmp_path: Path,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the reload config function."""

    podcast_archiver._ap = apa

    get_test_config("testing_true_valid.json")

    with caplog.at_level(logging.DEBUG), app.app_context():
        podcast_archiver.reload_config(signal.SIGHUP)

    assert "Finished adhoc config reload" in caplog.text


def test_reload_config_exception(
    apa: PodcastArchiver,
    tmp_path: Path,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the reload config function."""

    podcast_archiver._ap = apa

    get_test_config("testing_true_valid.json")

    def load_config_exception(*args: Any, **kwargs: Any) -> None:
        raise FakeExceptionError

    monkeypatch.setattr(podcast_archiver._ap, "load_config", load_config_exception)

    with caplog.at_level(logging.ERROR):
        podcast_archiver.reload_config(signal.SIGHUP)

    assert "Error reloading config" in caplog.text


@pytest.mark.parametrize(
    ("time", "expected_seconds"),
    [
        (datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC), 1200),  # 1200 seconds = 20 minutes
        (datetime.datetime(2020, 1, 1, 0, 30, 0, tzinfo=UTC), 3000),  # 3000 seconds = 50 minutes
    ],
)
def test_time_until_next_run(time: datetime.datetime, expected_seconds: int) -> None:
    """Test the logic for waiting for the next run."""

    assert _get_time_until_next_run(time) == expected_seconds


@pytest.mark.asyncio
async def test_file_list(apa: PodcastArchiver, client_live: Flask, tmp_path: Path) -> None:
    """Test that files are listed."""

    podcast_archiver._ap = apa
    ap = apa

    content_path = Path("content") / "test" / "20200101-Test-Episode.mp3"
    file_path = tmp_path / "web" / content_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("test")

    ap.podcast_downloader.__init__(app_config=ap.app_config, s3=ap.s3, web_root=ap.web_root)
    await ap._render_filelist_html()

    response = client_live.get("/filelist.html")

    assert response.status_code == HTTPStatus.OK
    assert "/index.html" in response.data.decode("utf-8")
    assert str(content_path) in response.data.decode("utf-8")


@pytest.mark.asyncio
async def test_file_list_s3(
    apa_aws: PodcastArchiver,
    client_live_s3: Flask,
    mock_get_session: AWSAioSessionMock,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that s3 files are listed."""

    monkeypatch.setattr(podcast_archiver, "_ap", apa_aws)

    content_s3_path = "content/test/20200101-Test-Episode.mp3"

    assert apa_aws.s3 is True

    async with mock_get_session.create_client("s3") as s3_client:
        await s3_client.put_object(Bucket=apa_aws.app_config.s3.bucket, Key=content_s3_path, Body=b"test")

    # Check that the file is in the cache
    apa_aws.podcast_downloader.__init__(app_config=apa_aws.app_config, s3=apa_aws.s3, web_root=apa_aws.web_root)

    _, file_cache = await apa_aws.podcast_downloader.get_file_list()
    assert content_s3_path in file_cache

    # Check that the file is in filelist.html
    with caplog.at_level(logging.DEBUG):
        await apa_aws._render_files()
        await apa_aws._render_filelist_html()

    assert "Done writing filelist.html to file" in caplog.text

    response = client_live_s3.get("/filelist.html")
    assert response.status_code == HTTPStatus.OK

    response_html = response.data.decode("utf-8")

    assert "/index.html" in response_html  # File list
    assert content_s3_path in response_html  # Content


def test_api_reload(
    apa: PodcastArchiver,
    client_live: Flask,
    place_test_config: Callable[[str, Path], None],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the reload API endpoint."""
    monkeypatch.setattr(podcast_archiver, "_ap", apa)
    apa.debug = True

    place_test_config("testing_true_valid.json", Path(apa.instance_path))

    response = client_live.get("/api/reload")
    assert response.status_code == HTTPStatus.OK
    assert "does not exist, loading defaults" not in caplog.text
    assert "Podcast has no name_one_word set in config, cannot proceed" not in caplog.text


def test_api_reload_no_debug(apa: PodcastArchiver, client_live: Flask, caplog: pytest.LogCaptureFixture) -> None:
    """Test the reload API endpoint."""

    podcast_archiver._ap = apa
    apa.debug = False

    response = client_live.get("/api/reload")
    assert response.status_code == HTTPStatus.FORBIDDEN
