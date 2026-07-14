"""Routes for static files and special routes like robots.txt and favicon.ico."""

from fastapi import APIRouter, Response

from archivepodcast.instances.podcast_archiver import (
    send_ap_cached_webpage,
)

router = APIRouter(include_in_schema=False)


@router.get("/robots.txt")
def send_robots() -> Response:
    """Serve robots.txt."""
    return send_ap_cached_webpage("robots.txt")


@router.get("/favicon.ico")
def favicon() -> Response:
    """Return the favicon."""
    return send_ap_cached_webpage("static/favicon.ico")


@router.get("/static/{path:path}")
def send_static(path: str) -> Response:
    """Serve static files."""
    return send_ap_cached_webpage(f"static/{path}")
