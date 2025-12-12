"""Tests for archivepodcast/instances/podcast_archiver.py to achieve 100% coverage."""

import logging
from http import HTTPStatus

import pytest
from flask import Flask

from archivepodcast.instances import podcast_archiver


def test_reload_config_when_ap_is_none(
    app: Flask,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test reload_config when _ap is None."""
    podcast_archiver._ap = None

    with caplog.at_level(logging.ERROR), app.app_context():
        podcast_archiver.reload_config(1)

    assert "ArchivePodcast object not initialized" in caplog.text


def test_podcast_loop_when_ap_is_none(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test podcast_loop when _ap is None."""
    podcast_archiver._ap = None

    with caplog.at_level(logging.CRITICAL):
        podcast_archiver.podcast_loop()

    assert "ArchivePodcast object not initialized, podcast_loop dead" in caplog.text


def test_send_ap_cached_webpage_when_ap_is_none(
    app: Flask,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test send_ap_cached_webpage when _ap is None."""
    podcast_archiver._ap = None

    with caplog.at_level(logging.ERROR), app.app_context():
        response = podcast_archiver.send_ap_cached_webpage("index.html")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "ArchivePodcast object not initialized" in caplog.text
    assert b"Archive Podcast not initialized" in response.data


def test_generate_404_when_ap_is_none(
    app: Flask,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test generate_404 when _ap is None."""

    podcast_archiver._ap = None

    with caplog.at_level(logging.ERROR), app.app_context():
        response = podcast_archiver.generate_404()

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "ArchivePodcast object not initialized" in caplog.text


def test_get_ap_when_ap_is_none() -> None:
    """Test get_ap when _ap is None."""
    podcast_archiver._ap = None

    with pytest.raises(RuntimeError, match="ArchivePodcast object not initialized"):
        podcast_archiver.get_ap()


def test_generate_not_initialized_error(
    app: Flask,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test generate_not_initialized_error directly."""
    with caplog.at_level(logging.ERROR), app.app_context():
        response = podcast_archiver.generate_not_initialized_error()

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "ArchivePodcast object not initialized" in caplog.text
    assert b"Archive Podcast not initialized" in response.data


def test_generate_not_generated_error_when_ap_is_none(
    app: Flask,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test generate_not_generated_error when _ap is None."""

    podcast_archiver._ap = None

    with caplog.at_level(logging.ERROR), app.app_context():
        response = podcast_archiver.generate_not_generated_error("test.html")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "ArchivePodcast object not initialized" in caplog.text
