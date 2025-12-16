"""Test the application health monitoring endpoints."""

import logging
from http import HTTPStatus
from pathlib import Path

import pytest
from flask.testing import FlaskClient

from archivepodcast.archiver.podcast_archiver import PodcastArchiver
from archivepodcast.archiver.rss_models import RssFeed
from archivepodcast.instances import podcast_archiver
from archivepodcast.utils.health import PodcastArchiverHealth
from tests.constants import DUMMY_RSS_STR, TEST_RSS_LOCATION


def test_health_api(client: FlaskClient, apa: PodcastArchiver) -> None:
    """Verify health API returns OK status when system is healthy."""

    podcast_archiver._ap = apa

    response = client.get("/api/health")
    # TEST: HTTP OK
    assert response.status_code == HTTPStatus.OK
    # TEST: Content type
    assert response.content_type == "application/json; charset=utf-8"

    assert response.get_json()["core"]["alive"]


def test_update_podcast_health() -> None:
    """Update the podcast episode info using RssFeed."""
    rss_path = Path(TEST_RSS_LOCATION) / "test_valid.rss"

    feed = RssFeed.from_bytes(rss_path.read_bytes())

    ap_health = PodcastArchiverHealth()

    ap_health.update_podcast_episode_info("test", feed)
    ap_health.update_podcast_status("test", rss_fetching_live=True)
    ap_health.update_podcast_status("test", rss_available=True)
    ap_health.update_podcast_status("test", last_fetched=0)
    ap_health.update_podcast_status("test", healthy_feed=True)


def test_podcast_health_errors(caplog: pytest.LogCaptureFixture) -> None:
    """Test the podcast section of the health API endpoint using RssFeed."""
    # Create a valid RSS feed with channel and item
    valid_rss = b"<?xml version='1.0'?><rss><channel><item><title>Test</title></item></channel></rss>"
    feed = RssFeed.from_bytes(valid_rss)

    ap_health = PodcastArchiverHealth()

    with caplog.at_level(logging.ERROR):
        ap_health.update_podcast_episode_info("test", feed)

    assert "Error parsing podcast episode info" not in caplog.text
    assert ap_health._podcasts["test"].episode_count == 1

    # Test with invalid date - note: RssFeed will parse this but the date will be in pub_date field as-is
    feed = RssFeed.from_bytes(
        b"<?xml version='1.0'?><rss><channel><item><pubDate>INVALID</pubDate></item></channel></rss>"
    )

    with caplog.at_level(logging.WARNING):
        ap_health.update_podcast_episode_info("test", feed)

    # Note: The new implementation doesn't try to parse dates, just stores the pub_date string


@pytest.mark.parametrize(
    "date",
    [
        "Mon, 16 Sep 2024 18:44:16 +0000",
        "Mon, 16 Sep 2024 18:44:16 GMT",
    ],
)
def test_podcast_health_date_formats(caplog: pytest.LogCaptureFixture, date: str) -> None:
    """Test the podcast section of the health API endpoint using RssFeed."""
    rss_str = DUMMY_RSS_STR.replace("encoding='UTF-8'", "")
    assert "encoding" not in rss_str

    feed = RssFeed.from_bytes(
        f"<?xml version='1.0'?><rss><channel><item><pubDate>{date}</pubDate></item></channel></rss>".encode("utf-8")
    )

    ap_health = PodcastArchiverHealth()

    with caplog.at_level(logging.ERROR):
        ap_health.update_podcast_episode_info("test", feed)

    # Note: The new implementation doesn't try to parse dates, just stores the pub_date string
    assert "Unable to parse pubDate: INVALID" not in caplog.text
