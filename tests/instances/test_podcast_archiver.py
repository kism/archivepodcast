"""Tests for src/archivepodcast/instances/podcast_archiver.py to achieve 100% coverage."""

import logging
import signal
import threading
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest

from archivepodcast.instances import podcast_archiver

if TYPE_CHECKING:
    from fastapi import FastAPI

    from archivepodcast.archiver.podcast_archiver import PodcastArchiver


def test_reload_config_when_ap_is_none(
    app: FastAPI,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test reload_config when _ap is None."""
    podcast_archiver._ap = None

    with caplog.at_level(logging.ERROR):
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
    app: FastAPI,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test send_ap_cached_webpage when _ap is None."""
    podcast_archiver._ap = None

    with caplog.at_level(logging.ERROR):
        response = podcast_archiver.send_ap_cached_webpage("index.html")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "ArchivePodcast object not initialized" in caplog.text
    assert b"Archive Podcast not initialized" in response.body


def test_generate_404_when_ap_is_none(
    app: FastAPI,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test generate_404 when _ap is None."""

    podcast_archiver._ap = None

    with caplog.at_level(logging.ERROR):
        response = podcast_archiver.generate_404()

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "ArchivePodcast object not initialized" in caplog.text


def test_get_ap_when_ap_is_none() -> None:
    """Test get_ap when _ap is None."""
    podcast_archiver._ap = None

    with pytest.raises(RuntimeError, match="ArchivePodcast object not initialized"):
        podcast_archiver.get_ap()


def test_render_ap_error_when_ap_is_none(
    app: FastAPI,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test render_ap_error when _ap is None."""

    podcast_archiver._ap = None

    with caplog.at_level(logging.ERROR):
        response = podcast_archiver.render_ap_error(HTTPStatus.INTERNAL_SERVER_ERROR, "test error")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "ArchivePodcast object not initialized" in caplog.text
    assert b"Archive Podcast not initialized" in response.body


def test_send_ap_cached_webpage_not_generated(
    app: FastAPI,
    apa: PodcastArchiver,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A page that is neither cached nor on disk errors out."""
    podcast_archiver._ap = apa

    with caplog.at_level(logging.ERROR):
        response = podcast_archiver.send_ap_cached_webpage("not_a_page.html")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "Requested page: not_a_page.html not generated" in caplog.text


def test_initialise_archivepodcast_registers_sighup(
    app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SIGHUP is wired up to reload_config when running in the main thread."""
    registered: dict[int, Any] = {}

    def fake_signal(signal_num: int, handler: Any) -> None:
        registered[signal_num] = handler

    monkeypatch.setattr(signal, "signal", fake_signal)
    monkeypatch.setattr(threading, "current_thread", threading.main_thread)  # Pytest may not be in the main thread

    podcast_archiver.initialise_archivepodcast()

    assert registered[signal.SIGHUP] is podcast_archiver.reload_config
