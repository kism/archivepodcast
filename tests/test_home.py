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
    assert response.status_code == HTTPStatus.TEMPORARY_REDIRECT

    assert response.headers["Location"] == "/index.html"


def test_home_index(client, apa):
    """Test the hello API endpoint. This one uses the fixture in conftest.py."""
    from archivepodcast import bp_archivepodcast

    bp_archivepodcast.ap = apa
    apa._render_files()

    assert apa.webpages.get_webpage("index.html")

    response = client.get("/index.html")
    # TEST: HTTP OK
    assert response.status_code == HTTPStatus.OK
    # TEST: Content type
    assert response.content_type == "text/html; charset=utf-8"
    # TEST: It is a webpage that we get back
    assert b"<!doctype html>" in response.data


def test_static_js_exists(client, apa):
    """TEST: /static/archivepodcast.js loads."""
    from archivepodcast import bp_archivepodcast

    bp_archivepodcast.ap = apa
    apa._render_files()

    response = client.get("/static/clipboard.js")
    assert response.status_code == HTTPStatus.OK
    assert "text/javascript" in response.content_type

    response = client.get("/static/filelist.js")
    assert response.status_code == HTTPStatus.OK
    assert "text/javascript" in response.content_type


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


def test_fonts_exist(client, apa):
    """TEST: /static/fonts/... loads."""
    from archivepodcast import bp_archivepodcast

    bp_archivepodcast.ap = apa
    apa._render_files()

    font_list = [
        "/static/fonts/fira-code-v12-latin-500.woff2",
        "/static/fonts/fira-code-v12-latin-600.woff2",
        "/static/fonts/fira-code-v12-latin-700.woff2",
        "/static/fonts/noto-sans-display-latin-500.woff2",
        "/static/fonts/noto-sans-display-latin-500italic.woff2",
    ]
    for font in font_list:
        response = client.get(font)
        assert response.status_code == HTTPStatus.OK, f"Failed to get {font}"
        assert (
            "font/woff2" in response.content_type
        ), f"Content type is not woff2 for {font}, got {response.content_type}, size {len(response.data)}"
