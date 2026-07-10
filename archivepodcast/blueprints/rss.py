"""RSS blueprint for ArchivePodcast."""

from http import HTTPStatus
from pathlib import Path

from flask import Blueprint, Response, current_app, render_template
from lxml import etree

from archivepodcast.constants import XML_ENCODING
from archivepodcast.instances.config import get_ap_config
from archivepodcast.instances.podcast_archiver import (
    get_about_page_exists,
    get_ap,
)
from archivepodcast.utils.logger import get_logger

logger = get_logger(__name__)
bp = Blueprint("rss", __name__)


@bp.route("/rss/<string:feed>", methods=["GET"])
def rss(feed: str) -> Response:
    """Send RSS Feed."""
    ap = get_ap()

    ap_conf = get_ap_config()

    def error_response(return_code: HTTPStatus, error_text: str) -> Response:
        return Response(
            render_template(
                "error.html.j2",
                error_code=str(return_code),
                error_text=error_text,
                about_page=get_about_page_exists(),
                app_config=ap_conf.app,
                podcasts=ap_conf.podcasts,
                header=ap.renderer.webpages.generate_header("error.html"),
            ),
            status=return_code,
        )

    logger.debug("Sending rss feed: %s", feed)
    try:
        rss_str = ap.get_rss_feed(feed).decode("utf-8")
    except TypeError:
        return error_response(HTTPStatus.INTERNAL_SERVER_ERROR, "The developer probably messed something up")

    except KeyError:
        try:
            tree = etree.parse(Path(current_app.instance_path) / "web" / "rss" / feed)
            rss_str = etree.tostring(
                tree.getroot(),
                encoding=XML_ENCODING,
                method="xml",
                xml_declaration=True,
            ).decode(XML_ENCODING)
            logger.warning('❗ Feed "%s" not live, sending cached version from disk', feed)

        # The file isn't there due to user error or not being created yet
        except OSError:
            return error_response(HTTPStatus.NOT_FOUND, "Feed not found, you know you can copy and paste yeah?")

        except:  # noqa: E722 Bare except since this is a catch all to prevent app crash
            return error_response(HTTPStatus.INTERNAL_SERVER_ERROR, "Feed not loadable, Internal Server Error")

    return Response(rss_str, mimetype="application/rss+xml; charset=utf-8", status=HTTPStatus.OK)
