import datetime
import os
import threading
import time
import xml.etree.ElementTree as ET
from http import HTTPStatus

from flask import Blueprint, Flask, Response, current_app, redirect, render_template, send_from_directory

from .ap_archiver import PodcastArchiver
from .logger import get_logger

logger = get_logger(__name__)


bp = Blueprint("ansibleinventorycmdb", __name__)


logger = get_logger(__name__)

ap = None


def initialise_archivepodcast() -> None:
    """Initialize the archivepodcast app."""
    global ap  # noqa: PLW0603
    ap = PodcastArchiver(current_app.config["app"], current_app.config["podcast"])

    # Start thread: podcast backup loop
    thread = threading.Thread(target=podcast_loop, daemon=True)
    thread.start()

    # Start thread: upload static (wastes time otherwise, doesn't affect anything)
    # thread = threading.Thread(target=upload_static, daemon=True) # TODO: NOT IMPLEMENTED
    # thread.start()

    # Cleanup
    thread.join()


def podcast_loop() -> None:
    """Main loop, grabs new podcasts every hour."""
    logger.info("🙋 Starting podcast loop: grabbing episodes, building rss feeds. Repeating hourly.")

    if ap is None:
        logger.error("❌ ArchivePodcast object not initialized")
        return

    if ap.s3 is not None:
        emoji = "⛅"  # un-upset black
        logger.info(
            "%s Since we are in s3 storage mode, the first iteration of checking which episodes are downloaded will be slow",
            emoji,
        )

    while True:
        # We do a broad try/except here since god knows what http errors seem to happen at random
        # If there is something uncaught in the grab podcasts function it will crash the scraping
        # part of this program and it will need to be restarted, this avoids it.
        try:
            ap.grab_podcasts()
        except Exception:
            logger.exception("❌ Error that broke grab_podcasts()")

        # Calculate time until next run
        now = datetime.datetime.now()

        one_hour_in_seconds = 3600
        seconds_offset = 1200  # 20 minutes

        seconds_until_next_run = (one_hour_in_seconds + seconds_offset) - ((now.minute * 60) + now.second)
        if seconds_until_next_run > one_hour_in_seconds:
            seconds_until_next_run -= one_hour_in_seconds

        emoji = "🛌"  # un-upset black
        logger.info("%s Sleeping for ~%s minutes", emoji, str(int(seconds_until_next_run / 60)))
        time.sleep(seconds_until_next_run)
        logger.info("🌄 Waking up, looking for new episodes")


def generate_404() -> Response:
    """We use the 404 template in a couple places."""
    returncode = HTTPStatus.NOT_FOUND
    render = render_template(
        "error.j2",
        error_code=str(returncode),
        error_text="Page not found, how did you even?",
        settings=current_app.config["app"],
    )
    return Response(render, status=returncode)


@bp.route("/")
def home() -> Response:
    """Flask Home."""
    if not ap:
        return generate_not_initialized_error()

    return Response(
        render_template("home.j2", settings=current_app.config["app"], about_page=ap.about_page), status=HTTPStatus.OK
    )


@bp.route("/index.html")
def home_index() -> Response:
    """Flask Home, s3 backup compatible."""
    # This ensures that if you transparently redirect / to /index.html
    # for using in cloudflare r2 storage it will work
    # If the vm goes down you can change the main domain dns to point to r2
    # and everything should work.
    if not ap:
        return generate_not_initialized_error()

    return Response(
        render_template("home.j2", settings=current_app.config["app"], about_page=ap.about_page), status=HTTPStatus.OK
    )


@bp.route("/about.html")
def home_about() -> Response:
    """Flask Home, s3 backup compatible."""
    if os.path.exists(os.path.join(current_app.instance_path, "about.html")):
        return send_from_directory(current_app.instance_path, "about.html")
    return generate_404()


@bp.route("/content/<path:path>")
def send_content(path: str) -> Response:
    """Serve Content."""
    response = Response()

    if current_app.config["storage_backend"] == "s3":
        new_path = current_app.config["s3"]["cdn_domain"] + "content/" + path.replace(current_app.instance_path, "")
        response = redirect(new_path, code=HTTPStatus.TEMPORARY_REDIRECT)
        response.headers["Cache-Control"] = "public, max-age=10800"  # 10800 seconds = 3 hours
    else:
        response = send_from_directory(current_app.instance_path + "/content", path)

    return response


@bp.errorhandler(404)
# pylint: disable=unused-argument
def invalid_route(e) -> Response:
    """404 Handler."""
    return generate_404()


@bp.route("/rss/<string:feed>", methods=["GET"])
def rss(feed: str) -> Response:
    """Send RSS Feed."""
    if not ap:
        return generate_not_initialized_error()

    logger.debug("Sending xml feed: %s", feed)
    xml = ""
    returncode = HTTPStatus.OK
    try:
        xml = ap.get_rss_xml(feed)
    except TypeError:
        return Response(
            render_template(
                "error.j2",
                error_code=str(returncode),
                error_text="The developer probably messed something up",
                settings=current_app.config["app"],
            ),
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    except KeyError:
        try:
            tree = ET.parse(os.path.join(current_app.instance_path, "rss", feed))
            xml = ET.tostring(
                tree.getroot(),
                encoding="utf-8",
                method="xml",
                xml_declaration=True,
            )
            logger.warning('❗ Feed "%s" not live, sending cached version from disk', feed)

        except FileNotFoundError:
            return Response(
                render_template(
                    "error.j2",
                    error_code=str(returncode),
                    error_text="Feed not found, you know you can copy and paste yeah?",
                    settings=current_app.config["app"],
                    podcasts=current_app.config["podcast"],
                ),
                status=HTTPStatus.NOT_FOUND,
            )

    return Response(xml, mimetype="application/rss+xml; charset=utf-8", status=HTTPStatus.OK)


@bp.route("/robots.txt")
def static_from_root() -> Response:
    """Serve robots.txt."""
    response = Response(response="User-Agent: *\nDisallow: /\n", status=200, mimetype="text/plain")
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


@bp.route("/favicon.ico")
def favicon() -> Response:
    """Return the favicon."""
    return send_from_directory(
        os.path.join(current_app.root_path, "archivepodcast", "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )

def generate_not_initialized_error() -> Response:
    """Generate a 500 error."""
    return Response(
        render_template(
            "error.j2",
            error_code=str(HTTPStatus.INTERNAL_SERVER_ERROR),
            error_text="ArchivePodcast not initialized",
            settings=current_app.config["app"],
        ),
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
    )
