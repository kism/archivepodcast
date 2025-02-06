"""Blueprint and helpers for the ArchivePodcast app."""

import datetime
import json
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

ap: PodcastArchiver | None = None


def initialise_archivepodcast() -> None:
    """Initialize the archivepodcast app."""
    global ap  # noqa: PLW0603

    ap = PodcastArchiver(
        current_app.config["app"],
        current_app.config["podcast"],
        current_app.instance_path,
        current_app.root_path,
        current_app.debug,
    )

    signal.signal(signal.SIGHUP, reload_config)

    pid = os.getpid()
    logger.info("🙋 Podcast Archive running! PID: %s", pid)
    logger.debug(f"Get ram usage in % kb: ps -p {pid} -o %mem,rss")
    logger.debug("Reload with: kill -HUP %s", pid)

    # Start thread: podcast backup loop
    threading.Thread(target=podcast_loop, daemon=True).start()


def reload_config(signal_num: int, handler: FrameType | None = None) -> None:
    """Handle Sighup.

    This will stall the webapp while this function is running.
    """
    start_time = time.time()
    if not ap:
        logger.error("❌ ArchivePodcast object not initialized")
        return

    ap.health.update_core_status(currently_loading_config=True)

    logger.debug("Handle Sighup %s %s", signal_num, handler)

    logger.info("🙋 Got SIGHUP, Reloading Config")

    try:
        ap_conf = ArchivePodcastConfig(instance_path=current_app.instance_path)  # Loads app config from disk

        # Other sections handled by config.py
        for key, value in ap_conf.items():
            if key != "flask":
                current_app.config[key] = value

        # Due to application context this cannot be done in a thread
        ap.load_config(current_app.config["app"], current_app.config["podcast"])

        # This is the slow part of the reload, no app context required so we can give run it in a thread.
        logger.info("🙋 Ad-Hoc grabbing podcasts in a thread")
        threading.Thread(target=ap.grab_podcasts, daemon=True).start()

    except Exception:
        logger.exception("❌ Error reloading config")

    end_time = time.time()  # Record the end time
    duration = end_time - start_time  # Calculate the duration
    logger.info("🙋 Finished adhoc config reload in  %.2f seconds", duration)
    ap.health.update_core_status(currently_loading_config=False)


def podcast_loop() -> None:
    """Main loop, grabs new podcasts every hour."""
    logger.info("🙋 Started thread: podcast_loop. Grabbing episodes, building rss feeds. Repeating hourly.")

    if ap is None:
        logger.critical("❌ ArchivePodcast object not initialized, podcast_loop dead")
        return

    if ap.s3 is not None:
        logger.info("⛅ We are in s3 mode, missing episode files will be downloaded, uploaded to s3, and then deleted")

    while True:
        ap.grab_podcasts()  # The function has a big try except block to avoid crashing the loop

        current_datetime = datetime.datetime.now()

        # Calculate time until next run
        seconds_until_next_run = _get_time_until_next_run(current_datetime)

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


@bp.route("/api/reload")
def api_reload() -> Response:
    """Reload the config."""
    if not ap:
        return generate_not_initialized_error()

    msg_success = {"msg": "Config reload command sent"}
    msg_forbidden = {"msg": "Config reload not allowed in production"}

    if not ap.debug:
        return Response(
            json.dumps(msg_forbidden),
            content_type="application/json; charset=utf-8",
            status=HTTPStatus.FORBIDDEN,
        )

    reload_config(signal.SIGHUP)

    return Response(
        json.dumps(msg_success),
        content_type="application/json; charset=utf-8",
        status=HTTPStatus.OK,
    )


@bp.route("/api/health")
def api_health() -> Response:
    """Health check."""
    if not ap:
        return generate_not_initialized_error()

    try:
        health_json = ap.health.get_health(ap)
    except Exception:
        logger.exception("❌ Error getting health")
        health_json = json.dumps({"core": {"alive": False}})

    return Response(
        health_json, mimetype="application/json", content_type="application/json; charset=utf-8", status=HTTPStatus.OK
    )


def send_ap_cached_webpage(webpage_name: str) -> Response:
    """Send a cached webpage."""
    if not ap:
        return generate_not_initialized_error()

    try:
        webpage = ap.webpages.get_webpage(webpage_name)
    except KeyError:
        return generate_not_generated_error(webpage_name)

    cache_control = "public, max-age=180"
    if "woff2" in webpage_name:
        cache_control = "public, max-age=31536000"  # 1 year

    return Response(
        webpage.content,
        mimetype=webpage.mime,
        status=HTTPStatus.OK,
        headers={"Cache-Control": cache_control},
    )


@bp.route("/")
def home() -> Response:
    """Flask Home.

    If you are serving static files with s3 or nginx, ensure that / redirects to /index.html,
    """
    return Response(
        "Redirecting to /index.html", status=HTTPStatus.TEMPORARY_REDIRECT, headers={"Location": "/index.html"}
    )


@bp.route("/index.html")
def home_index() -> Response:
    """Flask Home."""
    return send_ap_cached_webpage("index.html")


@bp.route("/guide.html")
def home_guide() -> Response:
    """Podcast app guide."""
    return send_ap_cached_webpage("guide.html")


@bp.route("/webplayer.html")
def home_web_player() -> Response:
    """Podcast app guide."""
    return send_ap_cached_webpage("webplayer.html")


@bp.route("/about.html")
def home_about() -> Response:
    """Flask Home, s3 backup compatible."""
    if get_about_page_exists():
        return send_ap_cached_webpage("about.html")

    return generate_404()


@bp.route("/health")
def health() -> Response:
    """Health check."""
    return send_ap_cached_webpage("health.html")


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
    return send_ap_cached_webpage("filelist.html")


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
                about_page=get_about_page_exists(),
                app_config=current_app.config["app"],
                header=ap.webpages.generate_header("error.html"),
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
                    about_page=get_about_page_exists(),
                    app_config=current_app.config["app"],
                    podcasts=current_app.config["podcast"],
                    header=ap.webpages.generate_header("error.html"),
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
                    about_page=get_about_page_exists(),
                    app_config=current_app.config["app"],
                    podcasts=current_app.config["podcast"],
                    header=ap.webpages.generate_header("error.html"),
                ),
                status=return_code,
            )

    return Response(rss_str, mimetype="application/rss+xml; charset=utf-8", status=HTTPStatus.OK)


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


def generate_not_initialized_error() -> Response:
    """Generate a not initialized 500 error."""
    logger.error("❌ ArchivePodcast object not initialized")
    default_header = '<header><a href="index.html">Home</a><hr></header>'
    return Response(
        render_template(
            "error.html.j2",
            error_code=str(HTTPStatus.INTERNAL_SERVER_ERROR),
            error_text="Archive Podcast not initialized",
            app_config=current_app.config["app"],
            header=default_header,
        ),
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
    )


def generate_not_generated_error(webpage_name: str) -> Response:
    """Generate a 500 error."""
    if not ap:
        return generate_not_initialized_error()

    logger.error(f"❌ Requested page: {webpage_name} not generated")
    return Response(
        render_template(
            "error.html.j2",
            error_code=str(HTTPStatus.INTERNAL_SERVER_ERROR),
            error_text=f"Your requested page: {webpage_name} is not generated, webapp might be still starting up.",
            about_page=get_about_page_exists(),
            app_config=current_app.config["app"],
            header=ap.webpages.generate_header("error.html"),
        ),
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
    )


def generate_404() -> Response:
    """We use the 404 template in a couple places."""
    if not ap:
        return generate_not_initialized_error()

    returncode = HTTPStatus.NOT_FOUND
    render = render_template(
        "error.html.j2",
        error_code=str(returncode),
        error_text="Page not found, how did you even?",
        about_page=get_about_page_exists(),
        app_config=current_app.config["app"],
        header=ap.webpages.generate_header("error.html"),
    )
    return Response(render, status=returncode)


def get_about_page_exists() -> bool:
    """Check if about.html exists, needed for some templates."""
    about_page_exists = False
    if ap is not None:
        about_page_exists = ap.about_page_exists

    return about_page_exists
