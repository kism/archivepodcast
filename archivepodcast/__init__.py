"""Flask web application for archiving and serving podcasts."""

import time
from pathlib import Path

from flask import Flask, Response
from rich.traceback import install

from .blueprints import bp_api, bp_content, bp_rss, bp_static, bp_webpages
from .instances import podcast_archiver
from .instances.config import get_ap_config
from .utils import logger
from .version import __version__

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

    logger.setup_logger(app, ap_conf.logging)  # Setup logger with config

    app.logger.info("Instance path is: %s", app.instance_path)

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

    app.app_context().push()  # God knows what does this does but it fixes everything

    @app.errorhandler(404)
    def invalid_route(e: str) -> Response:
        """404 Handler."""
        app.logger.debug("Error handler: invalid_route: %s", e)
        return podcast_archiver.generate_404()

    duration = time.time() - start_time
    app.logger.info("🙋 ArchivePodcast Version: %s webapp initialised in %.2f seconds.", __version__, duration)
    podcast_archiver.get_ap().health.set_event_time("flask_app_init", duration)
    app.logger.info("🙋 Starting Web Server")
    app.logger.info(ap_conf.app.inet_path)

    return app
