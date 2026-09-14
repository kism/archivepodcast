"""RSS routes for ArchivePodcast."""

from http import HTTPStatus

from fastapi import APIRouter, Response

from archivepodcast.instances.config import get_ap_config
from archivepodcast.instances.path_helper import get_app_paths
from archivepodcast.instances.podcast_archiver import (
    get_about_page_exists,
    get_ap,
    render_error,
)
from archivepodcast.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["rss"])


@router.get(
    "/rss/{feed}",
    response_class=Response,
    responses={HTTPStatus.OK: {"content": {"application/rss+xml": {}}}},
)
def rss(feed: str) -> Response:
    """Send RSS Feed."""
    ap = get_ap()

    logger.debug("Sending rss feed: %s", feed)
    try:
        rss_bytes = ap.podcast_rss[feed]
    except KeyError:
        try:
            rss_bytes = (get_app_paths().web_root / "rss" / feed).read_bytes()
        except OSError:  # The file isn't there due to user error or not being created yet
            ap_conf = get_ap_config()
            return render_error(
                HTTPStatus.NOT_FOUND,
                error_text="Feed not found, you know you can copy and paste yeah?",
                about_page=get_about_page_exists(),
                app_config=ap_conf.app,
                podcasts=ap_conf.podcasts,
                header=ap.renderer.webpages.generate_header("error.html"),
            )
        logger.warning('❗ Feed "%s" not live, sending cached version from disk', feed)

    return Response(rss_bytes, media_type="application/rss+xml; charset=utf-8", status_code=HTTPStatus.OK)
