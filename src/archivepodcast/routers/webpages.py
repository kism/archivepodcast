"""Webpage routes for ArchivePodcast."""

from http import HTTPStatus

from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse

from archivepodcast.instances.podcast_archiver import (
    generate_404,
    get_about_page_exists,
    send_ap_cached_webpage,
)
from archivepodcast.utils.logger import get_logger

logger = get_logger(__name__)


router = APIRouter(include_in_schema=False)


@router.get("/")
def home() -> RedirectResponse:
    """Redirect to /index.html."""
    return RedirectResponse("/index.html", status_code=HTTPStatus.TEMPORARY_REDIRECT)


@router.get("/index.html")
def home_index() -> Response:
    """Home."""
    return send_ap_cached_webpage("index.html")


@router.get("/guide.html")
def home_guide() -> Response:
    """Podcast app guide."""
    return send_ap_cached_webpage("guide.html")


@router.get("/webplayer.html")
def home_web_player() -> Response:
    """Serve the web player page."""
    return send_ap_cached_webpage("webplayer.html")


@router.get("/about.html")
def home_about() -> Response:
    """Serve the about page."""
    if get_about_page_exists():
        return send_ap_cached_webpage("about.html")

    return generate_404()


@router.get("/health")
@router.get("/health.html")
def health() -> Response:
    """Health check."""
    return send_ap_cached_webpage("health.html")


@router.get("/filelist.html")
def home_filelist() -> Response:
    """Serve Filelist."""
    return send_ap_cached_webpage("filelist.html")
