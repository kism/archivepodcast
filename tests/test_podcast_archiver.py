"""Tests for PodcastArchiver functionality."""

import logging
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from archivepodcast.archiver.podcast_archiver import PodcastArchiver
from archivepodcast.instances.path_helper import get_app_paths
from tests.constants import DUMMY_RSS_STR

from . import FakeExceptionError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
else:
    MockerFixture = object


@pytest.mark.asyncio
async def test_no_about_page(apa: PodcastArchiver, caplog: pytest.LogCaptureFixture) -> None:
    """Verify behavior when about page is missing."""
    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.archiver"):
        await apa.renderer._load_about_page()

    assert "About page doesn't exist" in caplog.text


@pytest.mark.asyncio
async def test_about_page(apa: PodcastArchiver, caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    """Test about page."""
    about_path = tmp_path / "about.md"
    with about_path.open("w") as f:
        f.write("About page exists!")

    with caplog.at_level(level=logging.INFO, logger="archivepodcast.archiver"):
        await apa.renderer._load_about_page()

    assert "About page exists!" in caplog.text


@pytest.mark.asyncio
async def test_check_s3_files_no_client(apa: PodcastArchiver, caplog: pytest.LogCaptureFixture) -> None:
    """Test that s3 files are checked."""
    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.archiver"):
        await apa.renderer._check_s3_files()

    assert "Checking state of s3 bucket" in caplog.text
    assert "No s3 client to list" in caplog.text


def test_grab_podcasts_not_live(
    apa: PodcastArchiver,
    caplog: pytest.LogCaptureFixture,
    mock_podcast_source_rss_valid: Callable[[str], Coroutine[Any, Any, None]],
) -> None:
    """Test grabbing podcasts."""

    apa.podcast_list[0].live = False

    rss_path = Path(get_app_paths().instance_path) / "web" / "rss" / "test"
    rss_path.parent.mkdir(parents=True, exist_ok=True)
    rss_path.write_text(DUMMY_RSS_STR)

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.archiver"):
        apa.grab_podcasts()

    assert "Processing podcast to archive: PyTest Podcast [Archive]" in caplog.text
    assert '"live": false, in config so not fetching new episodes' in caplog.text
    assert "Loaded rss from file" in caplog.text
    assert "Cannot find rss feed file" not in caplog.text
    assert "Unable to host podcast, something is wrong" not in caplog.text

    assert "No response, loading rss from file" not in caplog.text  # This shouldn't happen

    get_rss = str(apa.get_rss_feed("test"), "utf-8")

    assert get_rss == DUMMY_RSS_STR


def test_grab_podcasts_unhandled_exception(
    apa: PodcastArchiver,
    caplog: pytest.LogCaptureFixture,
    mock_podcast_source_rss_valid: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test grabbing podcasts."""

    apa.podcast_list[0].live = False

    rss_path = Path(get_app_paths().instance_path) / "web" / "rss" / "test"
    rss_path.parent.mkdir(parents=True, exist_ok=True)
    rss_path.write_text(DUMMY_RSS_STR)

    def mock_get_rss_feed_exception(*args: Any, **kwargs: Any) -> None:
        raise FakeExceptionError

    monkeypatch.setattr(apa, "_grab_podcast", mock_get_rss_feed_exception)

    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.archiver"):
        apa.grab_podcasts()

    assert "Error grabbing podcast:" in caplog.text


def test_grab_podcasts_invalid_rss(
    apa: PodcastArchiver,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test grabbing podcasts."""
    apa.podcast_list[0].live = False

    rss = "INVALID"

    rss_path = Path(get_app_paths().instance_path) / "web" / "rss" / "test"
    rss_path.parent.mkdir(parents=True, exist_ok=True)
    rss_path.write_text(rss)

    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.archiver"):
        apa.grab_podcasts()

    assert "Syntax error in rss feed file" in caplog.text


def test_grab_podcasts_not_live_no_existing_feed(
    apa: PodcastArchiver,
    caplog: pytest.LogCaptureFixture,
    mock_podcast_source_rss_valid: MockerFixture,
) -> None:
    """Test grabbing podcasts."""

    apa.podcast_list[0].live = False

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.archiver"):
        apa.grab_podcasts()

    assert "Processing podcast to archive: PyTest Podcast [Archive]" in caplog.text
    assert '"live": false, in config so not fetching new episodes' in caplog.text
    assert "Cannot find local rss feed file to serve unavailable podcast" in caplog.text
    assert "Unable to host podcast: test, something is wrong" in caplog.text


def test_grab_podcasts_live(
    apa: PodcastArchiver,
    caplog: pytest.LogCaptureFixture,
    mock_podcast_source_rss_valid: MockerFixture,
) -> None:
    """Test grabbing podcasts."""

    apa.podcast_list[0].live = True

    with caplog.at_level(level=logging.DEBUG):
        apa.grab_podcasts()

    assert "Processing podcast to archive: PyTest Podcast [Archive]" in caplog.text
    assert "Wrote rss to disk:" in caplog.text
    assert "Hosted feed: http://localhost:5100/rss/test" in caplog.text
    assert "Loaded rss from file" not in caplog.text

    rss = str(apa.get_rss_feed("test"))

    assert "PyTest Podcast [Archive]" in rss
    assert "http://localhost:5100/content/test/20200101-Test-Episode.mp3" in rss
    assert "http://localhost:5100/content/test/PyTest-Podcast-Archive.jpg" in rss
    assert "<link>http://localhost:5100/</link>" in rss
    assert "<title>Test Episode</title>" in rss

    assert "https://pytest.internal/images/test.jpg" not in rss
    assert "https://pytest.internal/audio/test.mp3" not in rss


def test_create_folder_structure_no_perms(apa: PodcastArchiver, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test creating folder structure with permissions error."""

    def mock_os_makedirs_permission_error(*args: Any, **kwargs: Any) -> None:
        raise PermissionError

    monkeypatch.setattr(Path, "mkdir", mock_os_makedirs_permission_error)

    with pytest.raises(PermissionError):
        apa._make_folder_structure()


def test_grab_podcasts_no_episodes(
    apa: PodcastArchiver,
    caplog: pytest.LogCaptureFixture,
    mock_podcast_source_rss_no_episodes: MockerFixture,
) -> None:
    """Test grabbing podcasts."""
    apa.podcast_list[0].live = True

    rss_path = Path(get_app_paths().instance_path) / "web" / "rss" / "test"
    rss_path.parent.mkdir(parents=True, exist_ok=True)
    rss_path.write_text(DUMMY_RSS_STR)

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.archiver"):
        apa.grab_podcasts()

    assert "Processing podcast to archive: PyTest Podcast [Archive]" in caplog.text  # The case due to config.json
    assert "Cannot find rss feed file" not in caplog.text
    assert "Unable to host podcast, something is wrong" not in caplog.text
    assert "No response, loading rss from file" not in caplog.text  # This shouldn't happen
    assert "has no episodes, not writing to disk" in caplog.text  # This shouldn't happen

    # Since it loads the old version from the disk
    assert (apa.get_rss_feed("test")).decode("utf-8") == DUMMY_RSS_STR
