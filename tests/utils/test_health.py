"""Test the application health monitoring endpoints."""

import logging
import xml.etree.ElementTree as ET
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from archivepodcast.instances import podcast_archiver
from archivepodcast.utils.health import HostingInfo, PodcastArchiverHealth
from tests.constants import DUMMY_RSS_STR, TEST_RSS_LOCATION

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi.testclient import TestClient

    from archivepodcast.archiver.podcast_archiver import PodcastArchiver
    from archivepodcast.config import ArchivePodcastConfig


def test_health_api(client: TestClient, apa: PodcastArchiver) -> None:
    """Verify health API returns OK status when system is healthy."""

    podcast_archiver._ap = apa

    response = client.get("/api/health")
    # TEST: HTTP OK
    assert response.status_code == HTTPStatus.OK
    # TEST: Content type
    assert response.headers["content-type"] == "application/json"

    assert response.json()["core"]["alive"]


def test_update_podcast_health() -> None:
    """Update the podcast episode info."""
    rss_path = Path(TEST_RSS_LOCATION) / "test_valid.rss"

    with rss_path.open() as file:
        tree = ET.parse(file)

    ap_health = PodcastArchiverHealth()

    ap_health.update_podcast_episode_info("test", tree)
    ap_health.update_podcast_status("test", rss_fetching_live=True)
    ap_health.update_podcast_status("test", rss_available=True)
    ap_health.update_podcast_status("test", last_fetched=0)
    ap_health.update_podcast_status("test", healthy_feed=True)


def test_podcast_health_errors(caplog: pytest.LogCaptureFixture) -> None:
    """Test the podcast section of the health API endpoint."""
    rss_str = DUMMY_RSS_STR.replace("encoding='UTF-8'", "")
    assert "encoding" not in rss_str
    tree = ET.fromstring(rss_str)

    ap_health = PodcastArchiverHealth()

    with caplog.at_level(logging.ERROR):
        ap_health.update_podcast_episode_info("test", tree)

    assert "Error parsing podcast episode info" not in caplog.text  # The dummy rss doesn't have pubDate
    assert ap_health._podcasts["test"].episode_count == 1

    tree = ET.fromstring("<?xml version='1.0'?><rss><channel><item><pubDate>INVALID</pubDate></item></channel></rss>")

    with caplog.at_level(logging.ERROR):
        ap_health.update_podcast_episode_info("test", tree)

    assert "Unable to parse pubDate: INVALID" in caplog.text


@pytest.mark.parametrize(
    "date",
    [
        "Mon, 16 Sep 2024 18:44:16 +0000",
        "Mon, 16 Sep 2024 18:44:16 GMT",
        "Mon, 16 Sep 2024 18:44:16",  # No timezone, gets assumed as UTC
    ],
)
def test_podcast_health_date_formats(caplog: pytest.LogCaptureFixture, date: str) -> None:
    """Test the podcast section of the health API endpoint."""
    rss_str = DUMMY_RSS_STR.replace("encoding='UTF-8'", "")
    assert "encoding" not in rss_str
    tree = ET.fromstring(rss_str)

    ap_health = PodcastArchiverHealth()

    tree = ET.fromstring(f"<?xml version='1.0'?><rss><channel><item><pubDate>{date}</pubDate></item></channel></rss>")

    with caplog.at_level(logging.ERROR):
        ap_health.update_podcast_episode_info("test", tree)

    assert "Unable to parse pubDate: INVALID" not in caplog.text


def test_podcast_health_no_episodes(caplog: pytest.LogCaptureFixture) -> None:
    """A feed with no items leaves the episode info at its defaults."""
    ap_health = PodcastArchiverHealth()
    tree = ET.fromstring("<?xml version='1.0'?><rss><channel></channel></rss>")

    with caplog.at_level(logging.WARNING):
        ap_health.update_podcast_episode_info("test", tree)

    assert "No episodes found in feed" in caplog.text
    assert ap_health._podcasts["test"].episode_count == 0
    assert ap_health._podcasts["test"].latest_episode.title == "Unknown"


def test_hosting_info_frontend_s3(get_test_config: Callable[[str], ArchivePodcastConfig]) -> None:
    """The frontend is hosted by s3 when the site is served from the cdn domain."""
    config = get_test_config("testing_true_valid_s3.json")
    config.app.inet_path = config.app.s3.cdn_domain

    host_info = HostingInfo.load_from_config(config.app)

    assert host_info.frontend.host_type == "s3"
    assert host_info.backend.host_type == "s3"


def test_update_template_status() -> None:
    """Template render times are recorded, unknown attributes are ignored."""
    ap_health = PodcastArchiverHealth()

    ap_health.update_template_status("index.html", last_rendered=12345, not_a_field=True)

    assert ap_health._templates["index.html"].last_rendered == 12345
    assert not hasattr(ap_health._templates["index.html"], "not_a_field")
