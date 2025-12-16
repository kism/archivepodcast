"""RSS blueprint for ArchivePodcast."""

from http import HTTPStatus
from pathlib import Path

from flask import Blueprint, Response, current_app, render_template

from archivepodcast.archiver.rss_models import RssFeed
from archivepodcast.constants import XML_ENCODING
from archivepodcast.instances.config import get_ap_config
from archivepodcast.instances.podcast_archiver import (
    get_about_page_exists,
    get_ap,
)
from archivepodcast.utils.logger import get_logger

logger = get_logger(__name__)
bp = Blueprint("rss", __name__)


@bp.route("/rss/<string:feed>", methods=["GET"])  # type: ignore[untyped-decorator]
def rss(feed: str) -> Response:
    """Send RSS Feed."""
    ap = get_ap()

    ap_conf = get_ap_config()

    logger.debug("Sending rss feed: %s", feed)
    rss_bytes = b""
    rss_str = ""
    try:
        rss_bytes = ap.get_rss_feed(feed)
        rss_str = rss_bytes.decode("utf-8")
    except TypeError:
        return_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return Response(
            render_template(
                "error.html.j2",
                error_code=str(return_code),
                error_text="The developer probably messed something up",
                about_page=get_about_page_exists(),
                app_config=ap_conf.app,
                header=ap.renderer.webpages.generate_header("error.html"),
            ),
            status=return_code,
        )

    except KeyError:
        try:
            rss_path = Path(current_app.instance_path) / "web" / "rss" / feed
            # Read raw bytes and optionally validate with RssFeed
            rss_bytes = rss_path.read_bytes()
            # Validate it can be parsed but serve the original bytes
            try:
                RssFeed.from_bytes(rss_bytes)
            except Exception:
                logger.warning("Feed %s from disk cannot be parsed by RssFeed, serving as-is", feed)
            rss_str = rss_bytes.decode(XML_ENCODING)
            logger.warning('❗ Feed "%s" not live, sending cached version from disk', feed)

        # The file isn't there due to user error or not being created yet
        except (FileNotFoundError, OSError):
            return_code = HTTPStatus.NOT_FOUND
            return Response(
                render_template(
                    "error.html.j2",
                    error_code=str(return_code),
                    error_text="Feed not found, you know you can copy and paste yeah?",
                    about_page=get_about_page_exists(),
                    app_config=ap_conf.app,
                    podcasts=ap_conf.podcasts,
                    header=ap.renderer.webpages.generate_header("error.html"),
                ),
                status=return_code,
            )

        except:  # noqa: E722 Bare except since this is a catch all to prevent app crash
            return_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return Response(
                render_template(
                    "error.html.j2",
                    error_code=str(return_code),
                    error_text="Feed not loadable, Internal Server Error",
                    about_page=get_about_page_exists(),
                    app_config=ap_conf.app,
                    podcasts=ap_conf.podcasts,
                    header=ap.renderer.webpages.generate_header("error.html"),
                ),
                status=return_code,
            )

    return Response(rss_str, mimetype="application/rss+xml; charset=utf-8", status=HTTPStatus.OK)
