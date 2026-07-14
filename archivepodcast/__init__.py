"""FastAPI web application for archiving and serving podcasts."""

import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute
from rich.traceback import install

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from .archiver import PodcastArchiver
from .blueprints import bp_api, bp_content, bp_rss, bp_static, bp_webpages
from .constants import DEFAULT_INSTANCE_PATH, JSON_INDENT, PROGRAM_VERSION
from .instances import podcast_archiver
from .instances.config import get_ap_config
from .instances.health import health
from .instances.path_helper import get_app_paths
from .instances.profiler import event_times
from .utils import logger as ap_logger
from .utils.log_messages import log_intro
from .utils.profiler import get_event_times_str

__all__ = ["create_app", "run_ap_adhoc"]

logger = ap_logger.get_logger(__name__)

# Don't install rich if we are in lambda
if not ap_logger.force_simple_logger():
    install()


def create_app(instance_path_override: str | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    start_time = time.time()

    instance_path = Path(instance_path_override) if instance_path_override else DEFAULT_INSTANCE_PATH
    get_app_paths(root_path=Path.cwd(), instance_path=instance_path)

    ap_conf = get_ap_config(instance_path / "config.json")

    if ap_conf.flask.TESTING and not str(instance_path).startswith("/tmp"):  # noqa: S108
        msg = "Flask TESTING mode requires instance_path to be a tmp_path."
        raise ValueError(msg)

    ap_conf.write_config(instance_path / "config.json")
    ap_conf.log_info(running_adhoc=False)

    ap_logger.setup_logger(ap_conf.logging)  # Setup logger with config

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        podcast_archiver.initialise_archivepodcast()
        yield

    app = FastAPI(title="ArchivePodcast", version=PROGRAM_VERSION, lifespan=lifespan)

    for bp in (bp_api, bp_content, bp_rss, bp_static, bp_webpages):
        # Flask served HEAD on every GET route (podcast clients HEAD media files), FastAPI doesn't by default.
        for route in bp.routes:
            if isinstance(route, APIRoute) and route.methods and "GET" in route.methods:
                route.methods.add("HEAD")
        app.include_router(bp)

    @app.exception_handler(404)
    def invalid_route(request: Request, e: Exception) -> Response:
        """404 Handler."""
        logger.debug("Error handler: invalid_route: %s %s", request.url, e)
        return podcast_archiver.generate_404()

    duration = time.time() - start_time
    log_intro(logger)
    event_times.set_event_time("create_app", duration)
    logger.info("Starting Web Server: %s", ap_conf.app.inet_path)

    return app


def run_ap_adhoc(
    instance_path: Path,
) -> None:
    """Main for adhoc running."""
    logger = ap_logger.get_logger(__name__)

    start_time = time.time()

    config_path = instance_path / "config.json"

    ap_conf = get_ap_config(config_path=config_path)
    ap_conf.write_config(config_path)
    ap_conf.log_info(running_adhoc=True)

    ap_logger.setup_logger(logging_conf=ap_conf.logging)  # Setup logger with config

    podcast_archiver_start_time = time.time()

    get_app_paths(root_path=Path.cwd(), instance_path=instance_path)

    ap = PodcastArchiver(
        app_config=ap_conf.app,
        podcast_list=ap_conf.podcasts,
        debug=False,  # The debug of the ap object is only for the web server
    )
    event_times.set_event_time("PodcastArchiver", time.time() - podcast_archiver_start_time)

    ap.grab_podcasts()
    asyncio.run(ap.write_health_s3())
    event_times.set_event_time("/", time.time() - start_time)

    logger.trace(health.get_health().model_dump_json(indent=JSON_INDENT))
    logger.trace(event_times.model_dump_json(indent=JSON_INDENT))
    logger.info(get_event_times_str(event_times))
    logger.info("Done!")
