"""Tests for PodcastArchiver functionality."""

import datetime
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from archivepodcast.archiver.podcast_archiver import _load_cached_feed
from archivepodcast.instances.path_helper import get_app_paths
from tests import FakeExceptionError
from tests.constants import DUMMY_RSS_STR
from tests.models.aiohttp import FakeSession

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from pytest_mock import MockerFixture

    from archivepodcast.archiver.podcast_archiver import PodcastArchiver
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
        f.write("exists")

    with caplog.at_level(level=logging.INFO, logger="archivepodcast.archiver"):
        await apa.renderer._load_about_page()

    assert "About page exists" in caplog.text


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
    assert '"live": false, in config, not fetching new episodes, will load feed from disk' in caplog.text
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
    assert '"live": false, in config, not fetching new episodes, will load feed from disk' in caplog.text
    assert "Cannot find local rss feed file to serve unavailable podcast" in caplog.text
    assert "Unable to host podcast: test, something is wrong" in caplog.text


def test_load_cached_feed_no_episodes(apa: PodcastArchiver, caplog: pytest.LogCaptureFixture) -> None:
    """Test that a cached feed with no episodes is discarded."""
    rss_no_items = b"<rss><channel><title>t</title></channel></rss>"

    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.archiver"):
        tree = _load_cached_feed(apa.podcast_list[0], rss_no_items)

    assert tree is None
    assert "Local/cached rss feed has no episodes" in caplog.text


@pytest.mark.asyncio
async def test_grab_podcast_no_name(apa: PodcastArchiver, caplog: pytest.LogCaptureFixture) -> None:
    """Test that a podcast with no name_one_word is skipped."""
    apa.podcast_list[0].name_one_word = ""

    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.archiver"):
        await apa._grab_podcast(apa.podcast_list[0], FakeSession(responses={}))  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]

    assert "Podcast has no name_one_word set in config, cannot proceed" in caplog.text


@pytest.mark.asyncio
async def test_backup_previous_feed_invalid_previous(apa: PodcastArchiver, caplog: pytest.LogCaptureFixture) -> None:
    """Test that an unparseable previous feed is not backed up."""
    tree: ET.ElementTree[ET.Element] = ET.ElementTree(ET.fromstring(DUMMY_RSS_STR))

    with caplog.at_level(level=logging.WARNING, logger="archivepodcast.archiver"):
        await apa._backup_previous_feed(apa.podcast_list[0], tree, b"INVALID")

    assert "backing up previous feed" not in caplog.text


@pytest.mark.asyncio
async def test_download_live_podcast_failure(
    apa: PodcastArchiver, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that a failed live download is logged."""

    async def mock_download_podcast(self: Any) -> None:
        return None

    monkeypatch.setattr("archivepodcast.downloader.PodcastsDownloader.download_podcast", mock_download_podcast)

    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.archiver"):
        tree = await apa._download_live_podcast(apa.podcast_list[0], FakeSession(responses={}))  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]

    assert tree is None
    assert "Unable to download podcast: test" in caplog.text


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


@pytest.mark.asyncio
async def test_backup_previous_feed_on_episode_drop(apa: PodcastArchiver, caplog: pytest.LogCaptureFixture) -> None:
    """Test the served feed is backed up when the downloaded feed has fewer episodes."""
    podcast = apa.podcast_list[0]
    previous_feed = b"<?xml version='1.0' encoding='UTF-8'?>\n<rss><item>One</item><item>Two</item></rss>"
    tree: ET.ElementTree[ET.Element] = ET.ElementTree(ET.fromstring("<rss><item>One</item></rss>"))

    with caplog.at_level(level=logging.WARNING, logger="archivepodcast.archiver"):
        await apa._backup_previous_feed(podcast, tree, previous_feed)

    date = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d")
    backup_path = get_app_paths().web_root / "content" / podcast.name_one_word / f"{date}-rss-backup.xml"
    assert "backing up previous feed" in caplog.text
    assert backup_path.read_bytes() == previous_feed


def test_grab_podcasts_live_episode_drop_backs_up_feed(
    apa: PodcastArchiver,
    caplog: pytest.LogCaptureFixture,
    mock_podcast_source_rss_valid: MockerFixture,
) -> None:
    """Test a live grab backs up the served feed when the new feed has fewer episodes."""
    apa.podcast_list[0].live = True

    # The mock source feed has one episode, serve a two episode feed so the count drops
    previous_rss = "<?xml version='1.0' encoding='UTF-8'?>\n<rss><item>One</item><item>Two</item></rss>"
    rss_path = Path(get_app_paths().instance_path) / "web" / "rss" / "test"
    rss_path.parent.mkdir(parents=True, exist_ok=True)
    rss_path.write_text(previous_rss)

    with caplog.at_level(level=logging.WARNING, logger="archivepodcast.archiver"):
        apa.grab_podcasts()

    assert "backing up previous feed" in caplog.text

    date = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d")
    backup_path = get_app_paths().web_root / "content" / "test" / f"{date}-rss-backup.xml"
    assert backup_path.read_text() == previous_rss

    # The new (smaller) feed is still served
    assert "<title>Test Episode</title>" in str(apa.get_rss_feed("test"))


@pytest.mark.asyncio
async def test_backup_previous_feed_no_episode_drop(apa: PodcastArchiver) -> None:
    """Test no backup is written when the downloaded feed has the same number of episodes."""
    podcast = apa.podcast_list[0]
    previous_feed = b"<?xml version='1.0' encoding='UTF-8'?>\n<rss><item>One</item></rss>"
    tree: ET.ElementTree[ET.Element] = ET.ElementTree(ET.fromstring("<rss><item>One</item></rss>"))

    await apa._backup_previous_feed(podcast, tree, previous_feed)

    content_dir = get_app_paths().web_root / "content" / podcast.name_one_word
    assert not list(content_dir.glob("*-rss-backup.xml"))


def test_archiver_webpages(apa: PodcastArchiver) -> None:
    """Test archiver webpages generation."""
    pages = apa.renderer.webpages.get_all_pages()
    assert len(pages) != 0


def test_archiver_webpages_header(apa: PodcastArchiver) -> None:
    """Test archiver webpages generation."""
    header = apa.renderer.webpages.generate_header("index.html", debug=True)
    assert "/health" in header

    header = apa.renderer.webpages.generate_header("health.html", debug=True)
    assert "/health" not in header

    header = apa.renderer.webpages.generate_header("index.html")
    assert "/health" not in header
