"""Flask webapp archivepodcast."""

from pprint import pformat

from flask import Flask

from . import bp_archivepodcast, logger
from .config import DEFAULT_CONFIG, ArchivePodcastConfig

__version__ = "1.1.0"  # This is the version of the app, used in pyproject.toml, enforced in a test.


def create_app(test_config: dict | None = None, instance_path: str | None = None) -> Flask:
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True, instance_path=instance_path)  # Create Flask app object

    logger.setup_logger(app, DEFAULT_CONFIG["logging"])  # Setup logger with defaults defined in config module

    if test_config:  # For Python testing we will often pass in a config
        if not instance_path:
            app.logger.critical("When testing supply both test_config and instance_path!")
            raise AttributeError(instance_path)
        ap_conf = ArchivePodcastConfig(config=test_config, instance_path=app.instance_path)
    else:
        ap_conf = ArchivePodcastConfig(instance_path=app.instance_path)  # Loads app config from disk

    app.logger.debug("Instance path is: %s", app.instance_path)

    logger.setup_logger(app, ap_conf["logging"])  # Setup logger with config

    # Flask config, at the root of the config object.
    app.config.from_mapping(ap_conf["flask"])

    # Other sections handled by config.py
    for key, value in ap_conf.items():
        if key != "flask":
            app.config[key] = value

    # Do some debug logging of config
    import tomlkit
    from datetime import timedelta

    def convert_timedelta_to_str(config):
        for k, v in config.items():
            if isinstance(v, timedelta):
                config[k] = str(v)
        return config

    filtered_config = {k: v for k, v in app.config.items() if v is not None}
    filtered_config = convert_timedelta_to_str(filtered_config)

    app_config_str = "Flask config >>>\n"
    app_config_str += tomlkit.dumps(filtered_config)

    app.logger.debug(app_config_str)

    app.register_blueprint(bp_archivepodcast.bp)  # Register blueprint

    # For modules that need information from the app object we need to start them under `with app.app_context():`
    # Since in the blueprint_one module, we use `from flask import current_app` to get the app object to get the config
    with app.app_context():
        bp_archivepodcast.initialise_archivepodcast()

    app.app_context().push()  # God knows what does this does but it fixes everything

    app.logger.info("Starting Web Server")

    return app
