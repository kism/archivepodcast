"""Tests for PodcastArchiver functionality."""

import logging
from pathlib import Path

import pytest

from . import FakeExceptionError


def test_no_about_page(apa, caplog):
    """Verify behavior when about page is missing."""
    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_archiver"):
        apa.load_about_page()

    assert "About page doesn't exist" in caplog.text


def test_about_page(apa, caplog, tmp_path):
    """Test about page."""
    about_path = tmp_path / "about.md"
    with about_path.open("w") as f:
        f.write("About page exists!")

    with caplog.at_level(level=logging.INFO, logger="archivepodcast.ap_archiver"):
        apa.load_about_page()

    assert "About page exists!" in caplog.text


def test_check_s3_files_no_client(apa, caplog):
    """Test that s3 files are checked."""
    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_archiver"):
        apa.check_s3_files()

    assert "Checking state of s3 bucket" in caplog.text
    assert "No s3 client to list" in caplog.text


def test_grab_podcasts_not_live(
    apa,
    caplog,
    mock_get_podcast_source_rss,
    mock_podcast_source_images,
    mock_podcast_source_mp3,
):
    """Test grabbing podcasts."""
    mock_get_podcast_source_rss("test_valid.rss")

    apa.podcast_list[0]["live"] = False

    rss_path = Path(apa.instance_path) / "web" / "rss" / "test"
    rss_path.parent.mkdir(parents=True, exist_ok=True)
    rss_path.write_text(pytest.DUMMY_RSS_STR)

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_archiver"):
        apa.grab_podcasts()

    assert "Processing podcast to archive: PyTest Podcast [Archive]" in caplog.text
    assert '"live": false, in config so not fetching new episodes' in caplog.text
    assert "Loading rss from file" in caplog.text
    assert "Cannot find rss feed file" not in caplog.text
    assert "Unable to host podcast, something is wrong" not in caplog.text

    assert "No response, loading rss from file" not in caplog.text  # This shouldn't happen

    get_rss = str(apa.get_rss_feed("test"), "utf-8")

    assert get_rss == pytest.DUMMY_RSS_STR


def test_grab_podcasts_unhandled_exception(
    apa,
    caplog,
    mock_get_podcast_source_rss,
    mock_podcast_source_images,
    mock_podcast_source_mp3,
    monkeypatch,
):
    """Test grabbing podcasts."""
    mock_get_podcast_source_rss("test_valid.rss")

    apa.podcast_list[0]["live"] = False

    rss_path = Path(apa.instance_path) / "web" / "rss" / "test"
    rss_path.parent.mkdir(parents=True, exist_ok=True)
    rss_path.write_text(pytest.DUMMY_RSS_STR)

    def mock_get_rss_feed_exception(*args, **kwargs):
        raise FakeExceptionError

    monkeypatch.setattr(apa, "_grab_podcast", mock_get_rss_feed_exception)

    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.ap_archiver"):
        apa.grab_podcasts()

    assert "Error grabbing podcast:" in caplog.text


def test_grab_podcasts_invalid_rss(
    apa,
    caplog,
    mock_get_podcast_source_rss,
    mock_podcast_source_images,
    mock_podcast_source_mp3,
    monkeypatch,
):
    """Test grabbing podcasts."""
    apa.podcast_list[0]["live"] = False

    rss = "INVALID"

    rss_path = Path(apa.instance_path) / "web" / "rss" / "test"
    rss_path.parent.mkdir(parents=True, exist_ok=True)
    rss_path.write_text(rss)

    with caplog.at_level(level=logging.ERROR, logger="archivepodcast.ap_archiver"):
        apa.grab_podcasts()

    assert "Error parsing rss file:" in caplog.text


def test_grab_podcasts_not_live_no_existing_feed(
    apa,
    caplog,
    mock_get_podcast_source_rss,
    mock_podcast_source_images,
    mock_podcast_source_mp3,
):
    """Test grabbing podcasts."""
    mock_get_podcast_source_rss("test_valid.rss")

    apa.podcast_list[0]["live"] = False

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_archiver"):
        apa.grab_podcasts()

    assert "Processing podcast to archive: PyTest Podcast [Archive]" in caplog.text
    assert '"live": false, in config so not fetching new episodes' in caplog.text
    assert "Loading rss from file:" in caplog.text
    assert "Cannot find rss feed file" in caplog.text
    assert "Unable to host podcast: test, something is wrong" in caplog.text


def test_grab_podcasts_live(
    apa,
    caplog,
    mock_get_podcast_source_rss,
    mock_podcast_source_images,
    mock_podcast_source_mp3,
):
    """Test grabbing podcasts."""
    mock_get_podcast_source_rss("test_valid.rss")

    apa.podcast_list[0]["live"] = True

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_archiver"):
        apa.grab_podcasts()

    assert "Processing podcast to archive: PyTest Podcast [Archive]" in caplog.text
    assert "Wrote rss to disk:" in caplog.text
    assert "Hosted: http://localhost:5100/rss/test" in caplog.text

    assert "Loading rss from file" not in caplog.text

    rss = str(apa.get_rss_feed("test"))

    assert "PyTest Podcast [Archive]" in rss
    assert "http://localhost:5100/content/test/20200101-Test-Episode.mp3" in rss
    assert "http://localhost:5100/content/test/PyTest-Podcast-Archive.jpg" in rss
    assert "<link>http://localhost:5100/</link>" in rss
    assert "<title>Test Episode</title>" in rss

    assert "https://pytest.internal/images/test.jpg" not in rss
    assert "https://pytest.internal/audio/test.mp3" not in rss


def test_create_folder_structure_no_perms(apa, monkeypatch):
    """Test creating folder structure with permissions error."""

    def mock_os_makedirs_permission_error(*args, **kwargs):
        raise PermissionError

    monkeypatch.setattr(Path, "mkdir", mock_os_makedirs_permission_error)

    with pytest.raises(PermissionError):
        apa.make_folder_structure()


def test_grab_podcasts_unhandled_exception_rss(
    apa,
    caplog,
    mock_get_podcast_source_rss,
    mock_podcast_source_images,
    mock_podcast_source_mp3,
    monkeypatch,
):
    """Test grabbing podcasts."""
    mock_get_podcast_source_rss("test_valid.rss")

    apa.podcast_list[0]["live"] = True

    monkeypatch.setattr(apa.podcast_downloader, "download_podcast", lambda _: (None, False))

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_archiver"):
        apa.grab_podcasts()

    assert "Unable to download podcast, something is wrong" in caplog.text


def test_grab_podcasts_no_episodes(
    apa,
    caplog,
    mock_get_podcast_source_rss,
    mock_podcast_source_images,
    mock_podcast_source_mp3,
):
    """Test grabbing podcasts."""
    mock_get_podcast_source_rss("test_valid_no_episodes.rss")

    apa.podcast_list[0]["live"] = True

    rss_path = Path(apa.instance_path) / "web" / "rss" / "test"
    rss_path.parent.mkdir(parents=True, exist_ok=True)
    rss_path.write_text(pytest.DUMMY_RSS_STR)

    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_archiver"):
        apa.grab_podcasts()

    assert "Processing podcast to archive: PyTest Podcast [Archive]" in caplog.text  # The case due to config.toml
    assert "Cannot find rss feed file" not in caplog.text
    assert "Unable to host podcast, something is wrong" not in caplog.text
    assert "No response, loading rss from file" not in caplog.text  # This shouldn't happen
    assert "has no episodes, not writing to disk" in caplog.text  # This shouldn't happen

    with pytest.raises(KeyError):
        apa.get_rss_feed("test")
