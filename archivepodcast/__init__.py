"""Flask web application for archiving and serving podcasts."""

import time
from pathlib import Path

from flask import Flask, Response

from . import bp_archivepodcast, logger
from .config import ArchivePodcastConfig
from .helpers import instance_dir
from .version import __version__


def create_app(ap_conf: ArchivePodcastConfig | None = None, instance_path: Path | None = None) -> Flask:
    """Create and configure the Flask application instance."""
    start_time = time.time()

    absolute_instance_path_str = str(instance_path) if instance_path else None

    app = Flask(
        __name__,
        instance_relative_config=True,
        instance_path=absolute_instance_path_str,
        static_folder=None,
    )  # Create Flask app object

    new_instance_path = Path(app.instance_path).resolve()
    instance_dir.set(new_instance_path)

    logger.setup_logger(app)  # Setup logger with defaults defined in config module

    if ap_conf is None:
        ap_conf = ArchivePodcastConfig()  # Loads app config from disk

    app.logger.debug("Instance path is: %s", app.instance_path)

    logger.setup_logger(app, ap_conf.logging)  # Setup logger with config

    # Flask config, at the root of the config object.
    app.config.from_object(ap_conf.flask)

    app.register_blueprint(bp_archivepodcast.bp)  # Register blueprint

    # For modules that need information from the app object we need to start them under `with app.app_context():`
    # Since in the blueprint_one module, we use `from flask import current_app` to get the app object to get the config
    with app.app_context():
        bp_archivepodcast.initialise_archivepodcast()

    app.app_context().push()  # God knows what does this does but it fixes everything

    @app.errorhandler(404)
    def invalid_route(e: str) -> Response:
        """404 Handler."""
        app.logger.debug("Error handler: invalid_route: %s", e)
        return bp_archivepodcast.generate_404()

    app.logger.info(
        "🙋 ArchivePodcast Version: %s webapp initialised in %.2f seconds.", __version__, time.time() - start_time
    )
    app.logger.info("🙋 Starting Web Server")
    return app
