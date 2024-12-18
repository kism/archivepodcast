"""Tests the app home page."""

from http import HTTPStatus


def test_home(client, apa):
    """Test the hello API endpoint. This one uses the fixture in conftest.py."""
    from archivepodcast import bp_archivepodcast

    bp_archivepodcast.ap = apa
    apa._render_files()

    assert apa.webpages.get_webpage("index.html")

    response = client.get("/")
    # TEST: HTTP OK
    assert response.status_code == HTTPStatus.OK
    # TEST: Content type
    assert response.content_type == "text/html; charset=utf-8"
    # TEST: It is a webpage that we get back
    assert b"<!doctype html>" in response.data


def test_static_js_exists(client):
    """TEST: /static/archivepodcast.js loads."""
    response = client.get("/static/clipboard.js")
    assert response.status_code == HTTPStatus.OK

    response = client.get("/static/filelist.js")
    assert response.status_code == HTTPStatus.OK


def test_favicon_exists(client, apa):
    """TEST: /static/archivepodcast.js loads."""
    from archivepodcast import bp_archivepodcast

    bp_archivepodcast.ap = apa
    apa._render_files()

    response = client.get("/favicon.ico")
    assert response.status_code == HTTPStatus.OK


def test_guide_exists(client, apa):
    """TEST: /static/archivepodcast.js loads."""
    from archivepodcast import bp_archivepodcast

    bp_archivepodcast.ap = apa
    apa._render_files()

    response = client.get("/guide.html")
    assert response.status_code == HTTPStatus.OK
