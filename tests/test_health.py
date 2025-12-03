"""Test the application health monitoring endpoints."""

import logging
from http import HTTPStatus
from pathlib import Path

import pytest
from flask.testing import FlaskClient
from lxml import etree

from archivepodcast.archiver.podcast_archiver import PodcastArchiver
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
    """Update the podcast episode info."""
    rss_path = Path(TEST_RSS_LOCATION) / "test_valid.rss"

    with rss_path.open() as file:
        tree = etree.parse(file)

    ap_health = PodcastArchiverHealth()

    ap_health.update_podcast_episode_info("test", tree)
    ap_health.update_podcast_status("test", rss_fetching_live=True)
    ap_health.update_podcast_status("test", rss_available=True)
    ap_health.update_podcast_status("test", last_fetched=0)
    ap_health.update_podcast_status("test", healthy_feed=True)


def test_podcast_health_errors(caplog: pytest.LogCaptureFixture) -> None:
    """Test the podcast section of the health API endpoint."""
    rss_str = DUMMY_RSS_STR.replace("encoding='utf-8'", "")
    assert "encoding" not in rss_str
    tree = etree.fromstring(rss_str)

    ap_health = PodcastArchiverHealth()

    with caplog.at_level(logging.ERROR):
        ap_health.update_podcast_episode_info("test", tree)

    assert "Error parsing podcast episode info" not in caplog.text  # The dummy rss doesn't have pubDate
    assert ap_health._podcasts["test"].episode_count == 1

    tree = etree.fromstring(
        "<?xml version='1.0'?><rss><channel><item><pubDate>INVALID</pubDate></item></channel></rss>"
    )

    with caplog.at_level(logging.ERROR):
        ap_health.update_podcast_episode_info("test", tree)

    assert "Unable to parse pubDate: INVALID" in caplog.text


@pytest.mark.parametrize(
    "date",
    [
        "Mon, 16 Sep 2024 18:44:16 +0000",
        "Mon, 16 Sep 2024 18:44:16 GMT",
    ],
)
def test_podcast_health_date_formats(caplog: pytest.LogCaptureFixture, date: str) -> None:
    """Test the podcast section of the health API endpoint."""
    rss_str = DUMMY_RSS_STR.replace("encoding='utf-8'", "")
    assert "encoding" not in rss_str
    tree = etree.fromstring(rss_str)

    ap_health = PodcastArchiverHealth()

    tree = etree.fromstring(
        f"<?xml version='1.0'?><rss><channel><item><pubDate>{date}</pubDate></item></channel></rss>"
    )

    with caplog.at_level(logging.ERROR):
        ap_health.update_podcast_episode_info("test", tree)

    assert "Unable to parse pubDate: INVALID" not in caplog.text
