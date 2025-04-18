"""Configuration management for archivepodcast."""

import os
import pwd
import typing
from datetime import timedelta
from pathlib import Path

import tomlkit
from flask import Flask

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


class ArchivePodcastConfig:
    """Config Object."""

    def __init__(self, instance_path: Path, config: dict | None = None, config_file_path: Path | None = None) -> None:
        """Initiate config object.

        Args:
            instance_path: The flask instance path, should be always from app.instance_path
            config: If provided config won't be loaded from a file.
            config_file_path: If provided, this will be used as the config file path.
        """
        self._config_path: Path | None = None
        self._config: dict = DEFAULT_CONFIG
        self.instance_path: Path = instance_path

        self._get_config_file_path(config_file_path)

        if not config:  # If no config is passed in (for testing), we load from a file.
            config = self._load_file()

        self._config = self._merge_with_defaults(DEFAULT_CONFIG, config)

        self._validate_config()

        self._write_config()

        logger.info("Configuration loaded successfully!")

    """ These next special methods make this object behave like a dict, a few methods are missing
    __setitem__, __len__,__delitem__
    https://gist.github.com/turicas/1510860
    """

    def __getitem__(self, key: str) -> typing.Any:  # noqa: ANN401 # Yes this will return Any, but it's a dict.
        """Get item from config like a dictionary."""
        return self._config[key]

    def __contains__(self, key: str) -> bool:
        """Check if key is 'in' the configuration."""
        return key in self._config

    def __repr__(self) -> str:
        """Return string representation of the config."""
        return repr(self._config)

    def items(self) -> typing.ItemsView[typing.Any, typing.Any]:
        """Return dictionary items of configuration."""
        return self._config.items()

    def _write_config(self) -> None:
        """Write configuration to a file."""
        if not self._config_path:  # Appease mypy
            msg = "Config path not set, cannot write config"
            raise ValueError(msg, self._config_path)

        try:
            self._config_path.write_text(tomlkit.dumps(self._config), encoding="utf8")
        except PermissionError as exc:
            user_account = pwd.getpwuid(os.getuid())[0]
            err = f"Fix permissions: chown {user_account} {self._config_path}"
            raise PermissionError(err) from exc

    def _validate_config(self) -> None:
        """Validate the current config. Raise an exception if it don't validate."""
        failed_items = []

        self._warn_unexpected_keys(DEFAULT_CONFIG, self._config, "<root>")

        for podcast in self._config["podcast"]:
            if not podcast["url"]:
                failed_items.append("Podcast url is empty")

            if not podcast["name_one_word"]:
                failed_items.append("Podcast name_one_word is empty")

        # Ensure internet path has a trailing slash
        if self._config["app"]["s3"]["cdn_domain"][-1] != "/":
            self._config["app"]["s3"]["cdn_domain"] += "/"

        if self._config["app"]["inet_path"][-1] != "/":
            self._config["app"]["inet_path"] += "/"

        # This is to assure that you don't accidentally test without the tmp_path fixture.
        if self._config["flask"]["TESTING"] and not any(
            substring in str(self.instance_path)
            for substring in ["tmp", "temp", "TMP", "TEMP", "/private/var/folders/"]
        ):
            failed_items.append(
                f"['flask']['TESTING'] is True but instance_path is not a tmp_path, its: {self.instance_path}"
            )

        # If the config doesn't validate, we exit.
        if len(failed_items) != 0:
            raise ConfigValidationError(failed_items)

    def _warn_unexpected_keys(self, target_dict: dict, base_dict: dict, parent_key: str) -> dict:
        """If the loaded config has a key that isn't in the schema (default config), we log a warning.

        This is recursive, be careful.
        """
        if parent_key != "flask":
            for key, value in base_dict.items():
                if isinstance(value, dict) and key in target_dict:
                    self._warn_unexpected_keys(target_dict[key], value, key)
                elif key not in target_dict:
                    if parent_key != "<root>":
                        parent_key = f"[{parent_key}]"

                    msg = f"Found config entry key {parent_key}[{key}] that's not in schema"
                    logger.warning(msg)

        return target_dict

    def _merge_with_defaults(self, base_dict: dict, target_dict: dict) -> dict:
        """Merge a config with another (DEFAULT_CONFIG) to ensure every default key exists.

        This is recursive, be careful.
        """
        for key, value in base_dict.items():
            if isinstance(value, dict) and key in target_dict:
                self._merge_with_defaults(value, target_dict[key])
            elif key not in target_dict:
                target_dict[key] = target_dict.get(key, value)

        return target_dict

    def _get_config_file_path(self, config_file_path: Path | None = None) -> None:
        """Figure out the config path to load config from.

        If a config file doesn't exist it will be created and written with current (default) configuration.
        """
        if config_file_path:
            paths = [config_file_path]
            logger.info("Using config file path provided: %s", config_file_path)
        else:
            paths = [
                Path(self.instance_path) / "config.toml",
                Path.home() / ".config" / "archivepodcast" / "config.toml",
                Path("/etc/archivepodcast/config.toml"),
            ]

        for path in paths:
            if path.is_file():
                logger.info("Found config at path: %s", path)
                if not self._config_path:
                    if not config_file_path:
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
