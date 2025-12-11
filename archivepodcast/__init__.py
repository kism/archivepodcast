"""Flask web application for archiving and serving podcasts."""

import asyncio
import time
from pathlib import Path

from flask import Flask, Response
from rich.traceback import install

from .archiver import PodcastArchiver
from .blueprints import bp_api, bp_content, bp_rss, bp_static, bp_webpages
from .constants import JSON_INDENT
from .instances import podcast_archiver
from .instances.config import get_ap_config
from .instances.health import health
from .instances.path_helper import get_app_paths
from .instances.profiler import event_times
from .utils import logger as ap_logger
from .utils.log_messages import log_intro
from .utils.profiler import get_event_times_str
from .version import __version__

__all__ = ["__version__", "create_app", "run_ap_adhoc"]

# Don't install rich if we are in lambda
if not ap_logger.force_simple_logger():
    install()


def create_app(instance_path_override: str | None = None) -> Flask:
    """Create and configure the Flask application instance."""
    start_time = time.time()

    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder=None,
        instance_path=instance_path_override,
    )  # Create Flask app object

    ap_conf = get_ap_config(Path(app.instance_path) / "config.json")

    if ap_conf.flask.TESTING and not app.instance_path.startswith("/tmp"):  # noqa: S108
        msg = "Flask TESTING mode requires instance_path to be a tmp_path."
        raise ValueError(msg)

    ap_conf.write_config(Path(app.instance_path) / "config.json")
    ap_conf.log_info(running_adhoc=False)

    ap_logger.setup_logger(app, ap_conf.logging)  # Setup logger with config

    # Flask config, at the root of the config object.
    app.config.from_object(ap_conf.flask)

    app.register_blueprint(bp_api)
    app.register_blueprint(bp_content)
    app.register_blueprint(bp_rss)
    app.register_blueprint(bp_static)
    app.register_blueprint(bp_webpages)

    # For modules that need information from the app object we need to start them under `with app.app_context():`
    # Since in the blueprint_one module, we use `from flask import current_app` to get the app object to get the config
    with app.app_context():
        podcast_archiver.initialise_archivepodcast()

    @app.errorhandler(404)  # type: ignore[untyped-decorator]
    def invalid_route(e: str) -> Response:
        """404 Handler."""
        app.logger.debug("Error handler: invalid_route: %s", e)
        return podcast_archiver.generate_404()

    duration = time.time() - start_time
    log_intro(app.logger)
    event_times.set_event_time("create_app", duration)
    app.logger.info("Starting Web Server: %s", ap_conf.app.inet_path)

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

    ap_logger.setup_logger(app=None, logging_conf=ap_conf.logging)  # Setup logger with config

    podcast_archiver_start_time = time.time()

    get_app_paths(root_path=Path.cwd(), instance_path=instance_path)

    ap = PodcastArchiver(
        app_config=ap_conf.app,
        podcast_list=ap_conf.podcasts,
        debug=False,  # The debug of the ap object is only for the Flask web server
    )
    event_times.set_event_time("PodcastArchiver", time.time() - podcast_archiver_start_time)

    ap.grab_podcasts()
    asyncio.run(ap.write_health_s3())
    event_times.set_event_time("/", time.time() - start_time)

    logger.trace(health.get_health().model_dump_json(indent=JSON_INDENT))
    logger.trace(event_times.model_dump_json(indent=JSON_INDENT))
    logger.info(get_event_times_str(event_times))
    logger.info("Done!")
