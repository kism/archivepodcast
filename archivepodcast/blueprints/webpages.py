"""Webpage blueprints for ArchivePodcast."""

from http import HTTPStatus

from flask import Blueprint, Response

from archivepodcast.instances.podcast_archiver import (
    generate_404,
    get_about_page_exists,
    send_ap_cached_webpage,
)
from archivepodcast.utils.logger import get_logger

logger = get_logger(__name__)


bp = Blueprint("webpages", __name__)


@bp.route("/")  # type: ignore[untyped-decorator]
def home() -> Response:
    """Flask Home.

    If you are serving static files with s3 or nginx, ensure that / redirects to /index.html,
    """
    return Response(
        "Redirecting to /index.html", status=HTTPStatus.TEMPORARY_REDIRECT, headers={"Location": "/index.html"}
    )


@bp.route("/index.html")  # type: ignore[untyped-decorator]
def home_index() -> Response:
    """Flask Home."""
    return send_ap_cached_webpage("index.html")


@bp.route("/guide.html")  # type: ignore[untyped-decorator]
def home_guide() -> Response:
    """Podcast app guide."""
    return send_ap_cached_webpage("guide.html")


@bp.route("/webplayer.html")  # type: ignore[untyped-decorator]
def home_web_player() -> Response:
    """Podcast app guide."""
    return send_ap_cached_webpage("webplayer.html")


@bp.route("/about.html")  # type: ignore[untyped-decorator]
def home_about() -> Response:
    """Flask Home, s3 backup compatible."""
    if get_about_page_exists():
        return send_ap_cached_webpage("about.html")

    return generate_404()


@bp.route("/health")  # type: ignore[untyped-decorator]
@bp.route("/health.html")  # type: ignore[untyped-decorator]
def health() -> Response:
    """Health check."""
    return send_ap_cached_webpage("health.html")


@bp.route("/filelist.html")  # type: ignore[untyped-decorator]
def home_filelist() -> Response:
    """Serve Filelist."""
    return send_ap_cached_webpage("filelist.html")
