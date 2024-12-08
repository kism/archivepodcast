"""Tests the blueprint's HTTP endpoint."""

import datetime
import logging
import os
import signal
from http import HTTPStatus

import pytest

from . import FakeExceptionError


def test_app_paths(client_live, client_live_s3, tmp_path):
    """Test that the app launches."""
    for client in [client_live, client_live_s3]:
        assert client

        valid_path_list = [
            "/",
            "/index.html",
            "/guide.html",
            "/robots.txt",
            "/static/clipboard.js",
            "/favicon.ico",
            "/static/favicon.ico",
            "/static/main.css",
            "/static/fonts/fira-code-v12-latin-600.woff2",
            "/static/fonts/fira-code-v12-latin-700.woff2",
            "/static/fonts/noto-sans-display-latin-500.woff2",
            "/static/fonts/noto-sans-display-latin-500italic.woff2",
        ]

        for path in valid_path_list:
            response = client.get(path)
            assert response.status_code == HTTPStatus.OK

        response = client.get("/non_existent_page")
        assert response.status_code == HTTPStatus.NOT_FOUND

        # Since we are looping...
        if os.path.exists(os.path.join(tmp_path, "web", "about.html")):
            os.remove(os.path.join(tmp_path, "web", "about.html"))

        response = client.get("/about.html")
        assert response.status_code == HTTPStatus.NOT_FOUND

        with open(os.path.join(tmp_path, "web", "about.html"), "w") as file:
            file.write("Test")

        response = client.get("/about.html")
        assert response.status_code == HTTPStatus.OK


def test_app_paths_not_initialized(tmp_path, get_test_config, caplog):
    """Test the RSS feed."""
    from archivepodcast import bp_archivepodcast

    get_test_config("testing_true_valid.toml")

    bp_archivepodcast.ap = None

    required_to_be_initialized_http = [
        bp_archivepodcast.home,
        bp_archivepodcast.home_index,
        bp_archivepodcast.home_guide,
    ]

    for function_path in required_to_be_initialized_http:
        response = function_path()
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

    required_to_be_initialized_str_arg = [
        bp_archivepodcast.send_content,
        bp_archivepodcast.rss,
    ]

    for function_path in required_to_be_initialized_str_arg:
        response = function_path("test")
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

    required_to_be_initialized = [
        bp_archivepodcast.podcast_loop,
    ]

    with caplog.at_level(logging.ERROR):
        for function_path in required_to_be_initialized:
            function_path()
            assert "ArchivePodcast object not initialized" in caplog.text

    with caplog.at_level(logging.ERROR):
        bp_archivepodcast.reload_settings(signal.SIGHUP)
        assert "ArchivePodcast object not initialized" in caplog.text


def test_rss_feed(
    app_live,
    tmp_path,
    caplog,
):
    """Test the RSS feed."""
    from archivepodcast.bp_archivepodcast import ap

    assert ap is not None

    ap.grab_podcasts()

    client_live = app_live.test_client()

    response = client_live.get("/rss/test")
    assert response.status_code == HTTPStatus.OK
    assert response.content_type == "application/rss+xml; charset=utf-8"

    response = client_live.get("/rss/non_existent_feed")
    assert response.status_code == HTTPStatus.NOT_FOUND

    with open(os.path.join(tmp_path, "web", "rss", "test_from_file"), "w") as file:
        file.write(pytest.DUMMY_RSS_STR)

    assert os.path.exists(os.path.join(ap.instance_path, "web", "rss", "test_from_file"))

    with caplog.at_level(logging.WARNING):
        response = client_live.get("/rss/test_from_file")

    response_str = response.data.decode("utf-8")
    assert response_str == pytest.DUMMY_RSS_STR
    assert response.status_code == HTTPStatus.OK
    assert "not live, sending cached version from disk" in caplog.text

    response = client_live.get("/content/test/20200101-Test-Episode.mp3")
    assert response.status_code == HTTPStatus.OK


def test_rss_feed_type_error(
    app_live,
    tmp_path,
    monkeypatch,
    caplog,
):
    """Test the RSS feed."""
    from archivepodcast.bp_archivepodcast import ap

    assert ap is not None

    ap.grab_podcasts()

    client_live = app_live.test_client()

    def return_type_error(*args, **kwargs) -> None:
        raise TypeError

    monkeypatch.setattr(ap, "get_rss_feed", return_type_error)

    response = client_live.get("/rss/test")
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_rss_feed_unhandled_error(
    app_live,
    tmp_path,
    monkeypatch,
    caplog,
):
    """Test the RSS feed."""
    from archivepodcast.bp_archivepodcast import ap

    assert ap is not None

    ap.grab_podcasts()

    client_live = app_live.test_client()

    def return_key_error(*args, **kwargs) -> None:
        raise KeyError

    monkeypatch.setattr(ap, "get_rss_feed", return_key_error)

    def return_unhandled_error(*args, **kwargs) -> None:
        raise FakeExceptionError

    monkeypatch.setattr("lxml.etree.tostring", return_unhandled_error)

    response = client_live.get("/rss/test")
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_content_s3(
    app_live,
):
    """Test the RSS feed."""
    from archivepodcast.bp_archivepodcast import ap

    assert ap is not None

    ap.grab_podcasts()
    ap.app_settings["storage_backend"] = "s3"

    client_live = app_live.test_client()

    response = client_live.get("/content/test/20200101-Test-Episode.mp3")
    assert response.status_code == HTTPStatus.TEMPORARY_REDIRECT


def test_reload_settings(tmp_path, get_test_config, caplog):
    """Test the reload settings function."""
    from archivepodcast import bp_archivepodcast

    get_test_config("testing_true_valid.toml")

    with caplog.at_level(logging.DEBUG):
        bp_archivepodcast.reload_settings(signal.SIGHUP)

    assert "Finished adhoc config reload" in caplog.text


def test_reload_settings_exception(tmp_path, get_test_config, monkeypatch, caplog):
    """Test the reload settings function."""
    from archivepodcast import bp_archivepodcast

    get_test_config("testing_true_valid.toml")

    def load_settings_exception(*args, **kwargs) -> None:
        raise FakeExceptionError

    monkeypatch.setattr(bp_archivepodcast.ap, "load_settings", load_settings_exception)

    with caplog.at_level(logging.ERROR):
        bp_archivepodcast.reload_settings(signal.SIGHUP)

    assert "Error reloading config" in caplog.text


@pytest.mark.parametrize(
    ("time", "expected_seconds"),
    [
        (datetime.datetime(2020, 1, 1, 0, 0, 0), 1200),  # 1200 seconds = 20 minutes
        (datetime.datetime(2020, 1, 1, 0, 30, 0), 3000),  # 3000 seconds = 50 minutes
    ],
)
def test_time_until_next_run(time, expected_seconds):
    """Test the logic for waiting for the next run."""
    from archivepodcast.bp_archivepodcast import _get_time_until_next_run

    assert _get_time_until_next_run(time) == expected_seconds
