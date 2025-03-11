"""Configuration management for archivepodcast."""

import os
import pwd
import typing
from datetime import timedelta
from pathlib import Path

import tomlkit
from flask import Flask
from pydantic import BaseModel, HttpUrl

from .config_types import AppConfig, LoggingConfig, PodcastConfig, S3Config, WebPageConfig
from .logger import get_logger

# Logging should be all done at INFO level or higher as the log level hasn't been set yet
# Modules should all setup logging like this so the log messages include the modules name.
logger = get_logger(__name__)

# Default config dictionary, also works as a schema
DEFAULT_LOGGING_CONFIG: dict = {
    "level": "INFO",
    "path": "",
}

DEFAULT_CONFIG: dict[str, dict | list] = {
    "app": {
        "web_page": {
            "title": "Podcast Archive",
            "description": "Podcast archive, generated by archivepodcast, available at https://github.com/kism/archivepodcast",
            "contact": "archivepodcast@localhost",
        },
        "inet_path": "http://localhost:5100/",
        "storage_backend": "local",
        "s3": {
            "cdn_domain": "https://public_url_of_s3_bucket/",
            "api_url": "",
            "bucket": "",
            "access_key_id": "",
            "secret_access_key": "",
        },
    },
    "podcast": [
        {
            "url": "",
            "new_name": "",
            "name_one_word": "",
            "description": "",
            "live": True,
            "contact_email": "",
        }
    ],
    "logging": DEFAULT_LOGGING_CONFIG,
    "flask": {  # This section is for Flask default config entries https://flask.palletsprojects.com/en/3.0.x/config/
        "TESTING": False,
    },
}


class ConfigValidationError(Exception):
    """Error to raise if there is a config validation error."""

    def __init__(self, failure_list: list) -> None:
        """Raise exception with list of config issues."""
        msg = "Config issues >>>\n"

        for failure in failure_list:
            msg += f"\n  {failure}"

        super().__init__(failure_list)


class ArchivePodcastConfig(BaseModel):
    """Config Object."""

    app: AppConfig
    podcast: list[PodcastConfig]
    logging: LoggingConfig
    flask: dict[str, typing.Any]


    def __init__(self, instance_path: Path | None = None, *, load_file: bool = False) -> None:
        """Initiate config object.

        Args:
            instance_path: The flask instance path, should be always from app.instance_path
            config: If provided config won't be loaded from a file.
        """


        self.app: AppConfig = AppConfig()
        self.podcast: list[PodcastConfig] = [PodcastConfig()]
        self.logging: LoggingConfig = LoggingConfig()
        self.flask: dict[str, typing.Any] = {"TESTING": False}

        self._config_path: Path | None = None
        self.instance_path: Path | None = None
        print(f"instance_path: {instance_path}")

        if instance_path:
            self.instance_path = instance_path

        print(f"instance_path: {instance_path}")

        self._get_config_file_path()

        if load_file:
            self._load_file()

        self._validate_config()

        if self._config_path:
            self._write_config()

        logger.info("Configuration loaded successfully!")

    """ These next special methods make this object behave like a dict, a few methods are missing
    __setitem__, __len__,__delitem__
    https://gist.github.com/turicas/1510860
    """

    def _write_config(self) -> None:
        """Write configuration to a file."""
        if not self._config_path:  # Appease mypy
            msg = "Config path not set, cannot write config"
            raise ValueError(msg, self._config_path)

        try:
            self._config_path.write_text(tomlkit.dumps(self._config.model_dump()), encoding="utf8")
        except PermissionError as exc:
            user_account = pwd.getpwuid(os.getuid())[0]
            err = f"Fix permissions: chown {user_account} {self._config_path}"
            raise PermissionError(err) from exc

    def _validate_config(self) -> None:
        """Validate the current config. Raise an exception if it don't validate."""
        failed_items = []

        for podcast in self._config.podcast:
            if not podcast.url:
                failed_items.append("Podcast url is empty")
            if not podcast.name_one_word:
                failed_items.append("Podcast name_one_word is empty")

        # Ensure internet path has a trailing slash
        if not self._config.app.s3.cdn_domain.endswith("/"):
            self._config.app.s3.cdn_domain += "/"

        if not self._config.app.inet_path.endswith("/"):
            self._config.app.inet_path += "/"

        # This is to assure that you don't accidentally test without the tmp_path fixture.
        if self._config.flask.TESTING and not any(
            substring in str(self.instance_path)
            for substring in ["tmp", "temp", "TMP", "TEMP", "/private/var/folders/"]
        ):
            failed_items.append(
                f"['flask']['TESTING'] is True but instance_path is not a tmp_path, its: {self.instance_path}"
            )

        # If the config doesn't validate, we exit.
        if len(failed_items) != 0:
            raise ConfigValidationError(failed_items)

    def _get_config_file_path(self) -> None:
        """Figure out the config path to load config from.

        If a config file doesn't exist it will be created and written with current (default) configuration.
        """

        paths = []

        if self.instance_path:
            paths.append(self.instance_path / "config.toml")

        paths.append(Path.home() / ".config" / "archivepodcast" / "config.toml")
        paths.append(Path("/etc/archivepodcast/config.toml"))

        for path in paths:
            if path.is_file():
                logger.info("Found config at path: %s", path)
                if not self._config_path:
                    logger.info("Using this path as it's the first one that was found")
                    self._config_path = path
            else:
                logger.info("No config file found at: %s", path)

        if not self._config_path:
            self._config_path = paths[0]
            logger.warning("No configuration file found, creating at default location: %s", self._config_path)
            Path(self.instance_path).mkdir(parents=True, exist_ok=True)  # Create instance path if it doesn't exist
            self._write_config()

    def _load_file(self) -> dict:
        """Load configuration from a file."""
        if not self._config_path:  # Appease mypy
            msg = "Config path not set, cannot load config"
            raise ValueError(msg, self._config_path)

        return tomlkit.loads(self._config_path.read_text(encoding="utf8"))


def print_config(app: Flask) -> None:
    """Print application config to log for debugging purposes."""

    def convert_timedelta_to_str(config: dict) -> dict:
        """Convert timedelta to str for printing."""
        for k, v in config.items():
            if isinstance(v, timedelta):
                config[k] = str(v)
        return config

    filtered_config = {k: v for k, v in app.config.items() if v is not None}
    filtered_config = convert_timedelta_to_str(filtered_config)

    app_config_str = "Flask config >>>\n"
    app_config_str += tomlkit.dumps(filtered_config)

    app.logger.debug(app_config_str.strip())
