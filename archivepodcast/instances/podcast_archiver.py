"""Blueprint and helpers for the ArchivePodcast app."""

import asyncio
import datetime
import os
import signal
import threading
import time
from http import HTTPStatus
from pathlib import Path
from types import FrameType

from flask import Response, current_app, render_template, send_file

from archivepodcast.archiver import PodcastArchiver
from archivepodcast.config import ArchivePodcastConfig
from archivepodcast.constants import JSON_INDENT
from archivepodcast.instances.health import health
from archivepodcast.instances.path_helper import get_app_paths
from archivepodcast.instances.profiler import event_times
from archivepodcast.utils.log_messages import get_time_str
from archivepodcast.utils.logger import get_logger

from .config import get_ap_config

logger = get_logger(__name__)

_ap: PodcastArchiver | None = None


def initialise_archivepodcast() -> None:
    """Initialize the archivepodcast app."""
    global _ap  # noqa: PLW0603
    ap_conf = get_ap_config()

    start_time = time.time()
    get_app_paths(root_path=Path.cwd(), instance_path=Path(current_app.instance_path))

    _ap = PodcastArchiver(
        app_config=ap_conf.app,
        podcast_list=ap_conf.podcasts,
        debug=current_app.debug,
    )

    signal.signal(signal.SIGHUP, reload_config)

    pid = os.getpid()
    logger.debug("Get ram usage in %% kb: ps -p %s -o %%mem,rss", pid)
    logger.debug("Reload with: kill -HUP %s", pid)

    # Start thread: podcast backup loop
    threading.Thread(target=podcast_loop, daemon=True).start()
    event_times.set_event_time("create_app/initialise_archivepodcast", time.time() - start_time)


def reload_config(signal_num: int, handler: FrameType | None = None) -> None:
    """Handle Sighup.

    This will stall the webapp while this function is running.
    """
    start_time = time.time()
    if not _ap:
        logger.error("ArchivePodcast object not initialized")
        return

    health.update_core_status(currently_loading_config=True)
    logger.debug("Handle Sighup %s %s", signal_num, handler)

    logger.info("Got SIGHUP, Reloading Config")

    try:
        logger.critical(current_app.instance_path)

        ap_conf = ArchivePodcastConfig().force_load_config_file(Path(current_app.instance_path) / "config.json")

        logger.critical(ap_conf.model_dump_json(indent=JSON_INDENT))

        # Due to application context this cannot be done in a thread
        _ap.load_config(ap_conf.app, ap_conf.podcasts)

        # This is the slow part of the reload, no app context required so we can give run it in a thread.
        logger.info("Ad-Hoc grabbing podcasts in a thread")
        threading.Thread(target=_ap.grab_podcasts, daemon=True).start()

    except Exception:
        logger.exception("Error reloading config")

    end_time = time.time()  # Record the end time
    duration = end_time - start_time  # Calculate the duration
    event_times.set_event_time("reload_config", duration)
    logger.info("Finished adhoc config reload in  %.2f seconds", duration)
    health.update_core_status(currently_loading_config=False)


def podcast_loop() -> None:
    """Main loop, grabs new podcasts every hour."""
    logger.info("Started thread: podcast_loop. Grabbing episodes, building rss feeds. Repeating hourly.")

    if _ap is None:
        logger.critical("ArchivePodcast object not initialized, podcast_loop dead")
        return

    while True:
        _ap.grab_podcasts()  # The function has a big try except block to avoid crashing the loop

        current_datetime = datetime.datetime.now(tz=datetime.UTC)

        asyncio.run(_ap.write_health_s3())

        # Calculate time until next run
        seconds_until_next_run = _get_time_until_next_run(current_datetime)

        msg = f"Sleeping for {int(seconds_until_next_run / 60)} minutes"
        logger.info(msg)
        time.sleep(seconds_until_next_run)
        # So regarding the test coverage, the flask_test client really helps here since it stops the test once the
        # request has completed, meaning that this infinite loop won't ruin everything
        # that being said, this one log message will never be covered, but I don't care
        current_datetime = datetime.datetime.now(tz=datetime.UTC)
        logger.info("🌄 Waking up, its %s, looking for new episodes", get_time_str())  # pragma: no cover


def _get_time_until_next_run(current_time: datetime.datetime) -> int:
    """Calculate the time until the next run of the podcast loop."""
    one_hour_in_seconds = 3600
    seconds_offset = 1200  # 20 minutes

    seconds_until_next_run = (one_hour_in_seconds + seconds_offset) - ((current_time.minute * 60) + current_time.second)
    if seconds_until_next_run > one_hour_in_seconds:
        seconds_until_next_run -= one_hour_in_seconds

    return seconds_until_next_run


def send_ap_cached_webpage(webpage_name: str) -> Response:
    """Send a cached webpage."""
    if not _ap:
        return generate_not_initialized_error()

    try:
        webpage = _ap.renderer.webpages.get_webpage(webpage_name)
    except KeyError:
        webpage_parts = webpage_name.split("/")
        static_path = Path(current_app.instance_path) / "web" / "/".join(webpage_parts)
        if static_path.is_file():
            logger.warning("Webpage not in cache serving from disk: %s", static_path)
            return send_file(static_path)

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


def generate_not_initialized_error() -> Response:
    """Generate a not initialized 500 error."""
    logger.error("ArchivePodcast object not initialized")
    default_header = '<header><a href="index.html">Home</a><hr></header>'

    ap_conf = get_ap_config()

    return Response(
        render_template(
            "error.html.j2",
            error_code=str(HTTPStatus.INTERNAL_SERVER_ERROR),
            error_text="Archive Podcast not initialized",
            app_config=ap_conf.app,
            header=default_header,
        ),
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
    )


def generate_not_generated_error(webpage_name: str) -> Response:
    """Generate a 500 error."""
    if not _ap:
        return generate_not_initialized_error()

    ap_conf = get_ap_config()

    logger.error("Requested page: %s not generated", webpage_name)
    return Response(
        render_template(
            "error.html.j2",
            error_code=str(HTTPStatus.INTERNAL_SERVER_ERROR),
            error_text=f"Your requested page: {webpage_name} is not generated, webapp might be still starting up.",
            about_page=get_about_page_exists(),
            app_config=ap_conf.app,
            header=_ap.renderer.webpages.generate_header("error.html"),
        ),
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
    )


def get_about_page_exists() -> bool:
    """Check if about.html exists, needed for some templates."""
    about_page_exists = False
    if _ap is not None:
        about_page_exists = _ap.renderer.about_page_exists

    return about_page_exists


def generate_404() -> Response:
    """We use the 404 template in a couple places."""
    if not _ap:
        return generate_not_initialized_error()

    ap_conf = get_ap_config()

    returncode = HTTPStatus.NOT_FOUND
    render = render_template(
        "error.html.j2",
        error_code=str(returncode),
        error_text="Page not found, how did you even?",
        about_page=get_about_page_exists(),
        app_config=ap_conf.app,
        header=_ap.renderer.webpages.generate_header("error.html"),
    )
    return Response(render, status=returncode)


def get_ap() -> PodcastArchiver:
    """Get the global ArchivePodcast object."""
    if _ap is None:
        logger.error("ArchivePodcast object not initialized")
        msg = "ArchivePodcast object not initialized"
        raise RuntimeError(msg)

    return _ap
