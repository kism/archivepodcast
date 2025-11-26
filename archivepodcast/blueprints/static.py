"""Blueprint for static files and special routes like robots.txt and favicon.ico."""

from flask import Blueprint, Response

from archivepodcast.instances.podcast_archiver import (
    send_ap_cached_webpage,
)

bp = Blueprint("static", __name__)


@bp.route("/robots.txt")
def send_robots() -> Response:
    """Serve robots.txt."""
    return send_ap_cached_webpage("robots.txt")


@bp.route("/favicon.ico")
def favicon() -> Response:
    """Return the favicon."""
    return send_ap_cached_webpage("static/favicon.ico")


@bp.route("/static/<path:path>")
def send_static(path: str) -> Response:
    """Serve static files."""
    return send_ap_cached_webpage(f"static/{path}")
