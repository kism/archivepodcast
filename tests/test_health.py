"""Test the health API endpoint."""

import logging
import os
from http import HTTPStatus

import pytest
from lxml import etree

from archivepodcast.ap_health import PodcastArchiverHealth

from . import FakeExceptionError


def test_health_api(client, apa):
    """Test the hello API endpoint. This one uses the fixture in conftest.py."""
    from archivepodcast import bp_archivepodcast

    bp_archivepodcast.ap = apa

    response = client.get("/api/health")
    # TEST: HTTP OK
    assert response.status_code == HTTPStatus.OK
    # TEST: Content type
    assert response.content_type == "application/json"

    data = response.get_json()

    assert data["core"]["alive"]


def test_health_api_error(client, apa, monkeypatch):
    """Test the podcast section of the health API endpoint."""
    from archivepodcast import bp_archivepodcast

    bp_archivepodcast.ap = apa

    monkeypatch.setattr("archivepodcast.ap_health.PodcastArchiverHealth.get_health", lambda: FakeExceptionError)

    response = client.get("/api/health")
    data = response.get_json()

    assert response.status_code == HTTPStatus.OK
    assert response.content_type == "application/json"
    assert not data["core"]["alive"]


def test_update_podcast_health() -> None:
    """Update the podcast episode info."""
    rss_path = os.path.join(pytest.TEST_RSS_LOCATION, "test_valid.rss")

    with open(rss_path) as file:
        tree = etree.parse(file)

    ap_health = PodcastArchiverHealth()

    ap_health.update_podcast_episode_info("test", tree)
    ap_health.update_podcast_status("test", rss_fetching_live=True)
    ap_health.update_podcast_status("test", rss_available=True)
    ap_health.update_podcast_status("test", last_fetched=0)
    ap_health.update_podcast_status("test", healthy=True)


def test_podcast_health_errors(caplog) -> None:
    """Test the podcast section of the health API endpoint."""
    rss_str = pytest.DUMMY_RSS_STR.replace("encoding='utf-8'", "")
    assert "encoding" not in rss_str
    tree = etree.fromstring(rss_str)

    ap_health = PodcastArchiverHealth()

    with caplog.at_level(logging.ERROR):
        ap_health.update_podcast_episode_info("test", tree)

    assert "Error parsing podcast episode info" in caplog.text

    tree = etree.fromstring(
        "<?xml version='1.0'?><rss><channel><item><pubDate>INVALID</pubDate></item></channel></rss>"
    )

    with caplog.at_level(logging.ERROR):
        ap_health.update_podcast_episode_info("test", tree)

    assert "Unable to parse pubDate: INVALID" in caplog.text
