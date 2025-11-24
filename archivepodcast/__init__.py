"""Flask web application for archiving and serving podcasts."""

import time

from flask import Flask, Response
from rich.traceback import install

from . import bp_archivepodcast, logger
from .instances import get_ap_config
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

    ap_conf = get_ap_config()

    if ap_conf.flask.TESTING and not app.instance_path.startswith("/tmp"):  # noqa: S108
        msg = "Flask TESTING mode requires instance_path to be a tmp_path."
        raise ValueError(msg)

    logger.setup_logger(app, ap_conf.logging)  # Setup logger with config

    app.logger.info("Instance path is: %s", app.instance_path)

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
