"""Test the application home page and static content endpoints."""

from http import HTTPStatus

import pytest
from flask.testing import FlaskClient

from archivepodcast.archiver.podcast_archiver import PodcastArchiver
from archivepodcast.instances import podcast_archiver


@pytest.mark.asyncio
async def test_home(client: FlaskClient, apa: PodcastArchiver) -> None:
    """Verify root path redirects to index.html."""
    podcast_archiver._ap = apa
    await apa._render_files()

    assert apa.webpages.get_webpage("index.html") is not None

    response = client.get("/")
    assert response.status_code == HTTPStatus.TEMPORARY_REDIRECT
    assert response.headers["Location"] == "/index.html"


@pytest.mark.asyncio
async def test_home_index(client: FlaskClient, apa: PodcastArchiver) -> None:
    """Test the hello API endpoint. This one uses the fixture in conftest.py."""
    podcast_archiver._ap = apa
    await apa._render_files()

    assert apa.webpages.get_webpage("index.html") is not None

    response = client.get("/index.html")
    # TEST: HTTP OK
    assert response.status_code == HTTPStatus.OK
    # TEST: Content type
    assert response.content_type == "text/html; charset=utf-8"
    # TEST: It is a webpage that we get back
    assert b"<!DOCTYPE html>" in response.data


@pytest.mark.asyncio
async def test_static_js_exists(client: FlaskClient, apa: PodcastArchiver) -> None:
    """TEST: /static/archivepodcast.js loads."""
    podcast_archiver._ap = apa
    await apa._render_files()

    response = client.get("/static/clipboard.js")
    assert response.status_code == HTTPStatus.OK
    assert "text/javascript" in response.content_type

    response = client.get("/static/filelist.js")
    assert response.status_code == HTTPStatus.OK
    assert "text/javascript" in response.content_type


@pytest.mark.asyncio
async def test_favicon_exists(client: FlaskClient, apa: PodcastArchiver) -> None:
    """TEST: /static/archivepodcast.js loads."""
    podcast_archiver._ap = apa
    await apa._render_files()

    response = client.get("/favicon.ico")
    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_guide_exists(client: FlaskClient, apa: PodcastArchiver) -> None:
    """TEST: /static/archivepodcast.js loads."""
    podcast_archiver._ap = apa
    await apa._render_files()

    response = client.get("/guide.html")
    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_fonts_exist(client: FlaskClient, apa: PodcastArchiver) -> None:
    """TEST: /static/fonts/... loads."""
    podcast_archiver._ap = apa
    await apa._render_files()

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
        assert "font/woff2" in response.content_type, (
            f"Content type is not woff2 for {font}, got {response.content_type}, size {len(response.data)}"
        )
