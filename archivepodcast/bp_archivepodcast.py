"""Blueprint and helpers for the ArchivePodcast app."""

import datetime
import os
import signal
import threading
import time
from http import HTTPStatus
from types import FrameType

from flask import Blueprint, Response, current_app, render_template, send_from_directory
from lxml import etree

from .ap_archiver import PodcastArchiver
from .config import ArchivePodcastConfig
from .logger import get_logger

logger = get_logger(__name__)


bp = Blueprint("archivepodcast", __name__)


logger = get_logger(__name__)

ap = None


def initialise_archivepodcast() -> None:
    """Initialize the archivepodcast app."""
    global ap  # noqa: PLW0603

    ap = PodcastArchiver(
        current_app.config["app"], current_app.config["podcast"], current_app.instance_path, current_app.root_path
    )

    signal.signal(signal.SIGHUP, reload_settings)

    logger.info("🙋 Starting Podcast Archive strong, unfazed.")
    logger.info("🙋 Podcast Archive running! PID: %s", os.getpid())

    # Start thread: podcast backup loop
    thread = threading.Thread(target=podcast_loop, daemon=True)
    thread.start()


def reload_settings(signal_num: int, handler: FrameType | None = None) -> None:
    """Handle Sighup."""
    if not ap:
        logger.error("❌ ArchivePodcast object not initialized")
        return

    logger.debug("Handle Sighup %s %s", signal_num, handler)
    logger.info("🙋 Got SIGHUP, Reloading Config")

    try:
        ap_conf = ArchivePodcastConfig(instance_path=current_app.instance_path)  # Loads app config from disk

        # Other sections handled by config.py
        for key, value in ap_conf.items():
            if key != "flask":
                current_app.config[key] = value

        ap.load_settings(current_app.config["app"], current_app.config["podcast"])
        ap.grab_podcasts()  # No point grabbing podcasts adhoc if loading the config fails

        logger.info("🙋 Finished adhoc config reload")
    except Exception:
        logger.exception("❌ Error reloading config")


def podcast_loop() -> None:
    """Main loop, grabs new podcasts every hour."""
    logger.info("🙋 Starting podcast loop: grabbing episodes, building rss feeds. Repeating hourly.")

    if ap is None:
        logger.error("❌ ArchivePodcast object not initialized")
        return

    if ap.s3 is not None:
        logger.info("⛅ We are in s3 mode, missing episode files will be downloaded, uploaded to s3 and then deleted")

    while True:
        ap.grab_podcasts()  # The function has a big try except block to avoid crashing the loop

        # Calculate time until next run
        seconds_until_next_run = _get_time_until_next_run(datetime.datetime.now())

        msg = f"🛌 Sleeping for {int(seconds_until_next_run / 60)} minutes"
        logger.info(msg)
        time.sleep(seconds_until_next_run)
        # So regarding the test coverage, the flask_test client really helps here since it stops the test once the
        # request has completed, meaning that this infinite loop won't ruin everything
        # that being said, this one log message will never be covered, but I don't care
        logger.info("🌄 Waking up, looking for new episodes")  # pragma: no cover


def _get_time_until_next_run(current_time: datetime.datetime) -> int:
    """Calculate the time until the next run of the podcast loop."""
    one_hour_in_seconds = 3600
    seconds_offset = 1200  # 20 minutes

    seconds_until_next_run = (one_hour_in_seconds + seconds_offset) - ((current_time.minute * 60) + current_time.second)
    if seconds_until_next_run > one_hour_in_seconds:
        seconds_until_next_run -= one_hour_in_seconds

    return seconds_until_next_run


def generate_404() -> Response:
    """We use the 404 template in a couple places."""
    returncode = HTTPStatus.NOT_FOUND
    render = render_template(
        "error.html.j2",
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
        render_template(
            "index.html.j2",
            settings=current_app.config["app"],
            podcasts=current_app.config["podcast"],
            about_page=ap.about_page,
        ),
        status=HTTPStatus.OK,
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
        render_template("index.html.j2", settings=current_app.config["app"], about_page=ap.about_page),
        status=HTTPStatus.OK,
    )


@bp.route("/guide.html")
def home_guide() -> Response:
    """Podcast app guide."""
    if not ap:
        return generate_not_initialized_error()

    return Response(
        render_template("guide.html.j2", settings=current_app.config["app"], about_page=ap.about_page),
        status=HTTPStatus.OK,
    )


@bp.route("/about.html")
def home_about() -> Response:
    """Flask Home, s3 backup compatible."""
    if os.path.exists(os.path.join(current_app.instance_path, "web", "about.html")):
        return send_from_directory(os.path.join(current_app.instance_path, "web"), "about.html")
    return generate_404()


@bp.route("/content/<path:path>")
def send_content(path: str) -> Response:
    """Serve Content."""
    if not ap:
        return generate_not_initialized_error()

    if current_app.config["app"]["storage_backend"] == "s3":
        new_path = current_app.config["app"]["s3"]["cdn_domain"] + "content/" + path.replace(ap.web_root, "")
        response = current_app.redirect(location=new_path, code=HTTPStatus.TEMPORARY_REDIRECT)
        response.headers["Cache-Control"] = "public, max-age=10800"  # 10800 seconds = 3 hours
    else:
        response = send_from_directory(os.path.join(current_app.instance_path, "web", "content"), path)

    return response  # type: ignore[return-value] # The conflicting types here are secretly the same


@bp.route("/filelist.html")
def home_filelist() -> Response:
    """Serve Filelist."""
    if not ap:
        return generate_not_initialized_error()

    base_url, file_list = ap.get_file_list()

    return Response(
        render_template("filelist.html.j2", settings=current_app.config["app"], file_list=file_list, base_url=base_url),
        status=HTTPStatus.OK,
    )


@bp.route("/rss/<string:feed>", methods=["GET"])
def rss(feed: str) -> Response:
    """Send RSS Feed."""
    if not ap:
        return generate_not_initialized_error()

    logger.debug("Sending rss feed: %s", feed)
    rss_str = ""
    try:
        rss_str = ap.get_rss_feed(feed)
    except TypeError:
        return_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return Response(
            render_template(
                "error.html.j2",
                error_code=str(return_code),
                error_text="The developer probably messed something up",
                settings=current_app.config["app"],
            ),
            status=return_code,
        )

    except KeyError:
        try:
            tree = etree.parse(os.path.join(current_app.instance_path, "web", "rss", feed))
            rss = etree.tostring(
                tree.getroot(),
                encoding="utf-8",
                method="xml",
                xml_declaration=True,
            )
            rss_str = rss.decode("utf-8")
            logger.warning('❗ Feed "%s" not live, sending cached version from disk', feed)

        # The file isn't there due to user error or not being created yet
        except (FileNotFoundError, OSError):
            return_code = HTTPStatus.NOT_FOUND
            return Response(
                render_template(
                    "error.html.j2",
                    error_code=str(return_code),
                    error_text="Feed not found, you know you can copy and paste yeah?",
                    settings=current_app.config["app"],
                    podcasts=current_app.config["podcast"],
                ),
                status=return_code,
            )

        except:  # noqa: E722: Broad catch to prevent crash
            return_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return Response(
                render_template(
                    "error.html.j2",
                    error_code=str(return_code),
                    error_text="Feed not loadable, Internal Server Error",
                    settings=current_app.config["app"],
                    podcasts=current_app.config["podcast"],
                ),
                status=return_code,
            )

    return Response(rss_str, mimetype="application/rss+xml; charset=utf-8", status=HTTPStatus.OK)


@bp.route("/robots.txt")
def static_from_root() -> Response:
    """Serve robots.txt."""
    response = Response(response="User-Agent: *\nDisallow: /\n", status=200, mimetype="text/plain")
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


@bp.route("/favicon.ico")
def favicon() -> Response:
    """Return the favicon."""
    static_folder_path = os.path.join(current_app.root_path, "static")
    return send_from_directory(
        static_folder_path,
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


def generate_not_initialized_error() -> Response:
    """Generate a 500 error."""
    logger.error("❌ ArchivePodcast object not initialized")
    return Response(
        render_template(
            "error.html.j2",
            error_code=str(HTTPStatus.INTERNAL_SERVER_ERROR),
            error_text="Archive Podcast not initialized",
            settings=current_app.config["app"],
        ),
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
    )
