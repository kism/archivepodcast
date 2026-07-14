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


bp = APIRouter(include_in_schema=False)


@bp.get("/")
def home() -> RedirectResponse:
    """Redirect to /index.html."""
    return RedirectResponse("/index.html", status_code=HTTPStatus.TEMPORARY_REDIRECT)


@bp.get("/index.html")
def home_index() -> Response:
    """Home."""
    return send_ap_cached_webpage("index.html")


@bp.get("/guide.html")
def home_guide() -> Response:
    """Podcast app guide."""
    return send_ap_cached_webpage("guide.html")


@bp.get("/webplayer.html")
def home_web_player() -> Response:
    """Serve the web player page."""
    return send_ap_cached_webpage("webplayer.html")


@bp.get("/about.html")
def home_about() -> Response:
    """Serve the about page."""
    if get_about_page_exists():
        return send_ap_cached_webpage("about.html")

    return generate_404()


@bp.get("/health")
@bp.get("/health.html")
def health() -> Response:
    """Health check."""
    return send_ap_cached_webpage("health.html")


@bp.get("/filelist.html")
def home_filelist() -> Response:
    """Serve Filelist."""
    return send_ap_cached_webpage("filelist.html")
