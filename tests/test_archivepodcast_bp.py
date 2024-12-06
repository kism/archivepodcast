"""Tests the blueprint's HTTP endpoint."""

import logging
import os
from http import HTTPStatus


def test_app_paths(client_live, tmp_path):
    """Test that the app launches."""
    assert client_live

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
        response = client_live.get(path)
        assert response.status_code == HTTPStatus.OK

    response = client_live.get("/non_existent_page")
    assert response.status_code == HTTPStatus.NOT_FOUND

    response = client_live.get("/about.html")
    assert response.status_code == HTTPStatus.NOT_FOUND

    with open(os.path.join(tmp_path, "web", "about.html"), "w") as file:
        file.write("Test")

    response = client_live.get("/about.html")
    assert response.status_code == HTTPStatus.OK


def test_app_paths_not_initialized(caplog):
    """Test the RSS feed."""
    from archivepodcast import bp_archivepodcast

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
        # bp_archivepodcast.reload_settings,
        bp_archivepodcast.podcast_loop,
    ]

    with caplog.at_level(logging.ERROR):
        for function_path in required_to_be_initialized:
            function_path()
            assert "ArchivePodcast object not initialized" in caplog.text

    with caplog.at_level(logging.ERROR):
        bp_archivepodcast.reload_settings(0)
        assert "ArchivePodcast object not initialized" in caplog.text


def test_rss_feed(
    app_live,
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

    response = client_live.get("/content/test/20200101-Test-Episode.mp3")
    assert response.status_code == HTTPStatus.OK
