"""Test the application home page and static content endpoints."""

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from archivepodcast.instances import podcast_archiver

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from archivepodcast.archiver.podcast_archiver import PodcastArchiver


@pytest.mark.asyncio
async def test_home(client: TestClient, apa: PodcastArchiver) -> None:
    """Verify root path redirects to index.html."""
    podcast_archiver._ap = apa
    await apa.renderer.render_files()

    assert apa.renderer.webpages.get_webpage("index.html") is not None

    response = client.get("/")
    assert response.status_code == HTTPStatus.TEMPORARY_REDIRECT
    assert response.headers["Location"] == "/index.html"


@pytest.mark.asyncio
async def test_home_index(client: TestClient, apa: PodcastArchiver) -> None:
    """Verify index.html returns valid HTML response."""
    podcast_archiver._ap = apa
    await apa.renderer.render_files()

    assert apa.renderer.webpages.get_webpage("index.html") is not None

    response = client.get("/index.html")
    # TEST: HTTP OK
    assert response.status_code == HTTPStatus.OK
    # TEST: Content type
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    # TEST: It is a webpage that we get back
    assert b"<!DOCTYPE html>" in response.content


@pytest.mark.asyncio
async def test_static_js_exists(client: TestClient, apa: PodcastArchiver) -> None:
    """Verify static JavaScript files load correctly."""
    podcast_archiver._ap = apa
    await apa.renderer.render_files()

    response = client.get("/static/clipboard.js")
    assert response.status_code == HTTPStatus.OK
    assert "text/javascript" in response.headers["content-type"]

    response = client.get("/static/filelist.js")
    assert response.status_code == HTTPStatus.OK
    assert "text/javascript" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_favicon_exists(client: TestClient, apa: PodcastArchiver) -> None:
    """Verify favicon.ico loads correctly."""
    podcast_archiver._ap = apa
    await apa.renderer.render_files()

    response = client.get("/favicon.ico")
    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_guide_exists(client: TestClient, apa: PodcastArchiver) -> None:
    """Verify guide.html loads correctly."""
    podcast_archiver._ap = apa
    await apa.renderer.render_files()

    response = client.get("/guide.html")
    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_fonts_exist(client: TestClient, apa: PodcastArchiver) -> None:
    """Verify static font files load correctly."""
    podcast_archiver._ap = apa
    await apa.renderer.render_files()

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
        content_type = response.headers["content-type"]
        assert "font/woff2" in content_type, (
            f"Content type is not woff2 for {font}, got {content_type}, size {len(response.content)}"
        )
