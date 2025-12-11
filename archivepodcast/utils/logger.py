"""Logging configuration for archivepodcast."""

import logging
import os
from logging import StreamHandler
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Self, cast

from flask import Flask
from pydantic import BaseModel, field_validator, model_validator
from rich.console import Console
from rich.highlighter import NullHighlighter
from rich.logging import RichHandler
from rich.theme import Theme

DESIRED_LEVEL_NAME_LEN = 5
DESIRED_NAME_LEN = 16
DESIRED_THREAD_NAME_LEN = 13


LOG_LEVELS = [
    "TRACE",
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
]  # Valid str logging levels.


MIN_LOG_LEVEL_INT = 0
MAX_LOG_LEVEL_INT = 50


class LoggingConf(BaseModel):
    """Logging configuration definition."""

    level: str | int = "INFO"
    path: Path | None = None

    @model_validator(mode="after")
    def validate_vars(self) -> Self:
        """Validate the logging level."""
        if isinstance(self.level, int):
            if self.level < MIN_LOG_LEVEL_INT or self.level > MAX_LOG_LEVEL_INT:
                msg = (
                    f"Invalid logging level {self.level}, must be between {MIN_LOG_LEVEL_INT} and {MAX_LOG_LEVEL_INT}."
                )
                logger.warning(msg)
                logger.warning("Defaulting logging level to 'INFO'.")
                self.level = "INFO"
        else:
            self.level = self.level.strip().upper()
            if self.level not in LOG_LEVELS:
                msg = f"Invalid logging level '{self.level}', must be one of {', '.join(LOG_LEVELS)}"
                logger.warning(msg)
                logger.warning("Defaulting logging level to 'INFO'.")
                self.level = "INFO"

        return self

    @field_validator("path", mode="before")
    def set_path(cls, value: str | None) -> Path | None:  # noqa: N805 # ???
        """Set the path to a slugified version."""
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()

        if value == "":
            return None

        return Path(value)

    def setup_verbosity_cli(self, verbosity: int) -> None:
        """Setup the logger from verbosity count from CLI."""
        if verbosity >= 2:  # noqa: PLR2004 Magic number makes sense
            self.level = TRACE_LEVEL_NUM
        elif verbosity == 1:
            self.level = logging.DEBUG
        else:
            self.level = logging.INFO


# This is the logging message format that I like.
# LOG_FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"   # noqa: ERA001
SIMPLE_LOG_FORMAT = "%(levelname)s:%(message)s"
SIMPLE_LOG_FORMAT_DEBUG = "%(levelname)s:%(name)s:%(message)s"
TRACE_LEVEL_NUM = 5


class CustomLogger(logging.Logger):
    """Custom logger to appease mypy."""

    def trace(self, message: object, *args: Any, **kws: Any) -> None:  # noqa: ANN401
        """Create logger level for trace."""
        if self.isEnabledFor(TRACE_LEVEL_NUM):
            # Yes, logger takes its '*args' as 'args'.
            self._log(TRACE_LEVEL_NUM, message, args, **kws)


logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")
logging.setLoggerClass(CustomLogger)

# This is where we log to in this module, following the standard of every module.
# I don't use the function so we can have this at the top
logger = cast("CustomLogger", logging.getLogger(__name__))

# In flask the root logger doesn't have any handlers, its all in app.logger
# root_logger : root,
# app.logger  : root, archivepodcast,
# logger      : root, archivepodcast, archivepodcast.module_name,
# The issue is that waitress, werkzeug (any any other modules that log) will log separately.
# The aim is, remove the default handler from the flask App and create one on the root logger to apply config to all.


# Pass in the whole app object to make it obvious we are configuring the logger object within the app object.
def setup_logger(
    app: Flask | None,
    logging_conf: LoggingConf | None = None,
    in_logger: logging.Logger | None = None,
) -> None:
    """Configure logging for the application."""
    if logging_conf is None:
        logging_conf = LoggingConf()

    if not in_logger:  # in_logger should only exist when testing with PyTest.
        in_logger = logging.getLogger()  # Get the root logger

    # The root logger has no handlers initially in flask, app.logger does though.
    if app:
        app.logger.handlers.clear()  # Remove the Flask default handlers

    if not running_in_serverless_environment():
        in_logger.handlers.clear()

    # If the logger doesn't have a console handler (root logger doesn't by default)
    if (not any(isinstance(handler, (RichHandler, StreamHandler)) for handler in in_logger.handlers)) and (
        not running_in_serverless_environment()  # Serverless should have their own handler
    ):
        _add_console_handler(logging_conf, in_logger)

    _set_log_level(in_logger, logging_conf.level)

    # If we are logging to a file
    if not _has_file_handler(in_logger) and logging_conf.path is not None:
        _add_file_handler(in_logger, logging_conf.path)

    # Configure modules that are external and have their own loggers
    logging.getLogger("waitress").setLevel(logging.INFO)  # Prod web server, info has useful info.
    logging.getLogger("werkzeug").setLevel(logging.DEBUG)  # Only will be used in dev, debug logs incoming requests.
    logging.getLogger("urllib3").setLevel(logging.WARNING)  # Bit noisy when set to info, used by requests module.
    logging.getLogger("botocore").setLevel(logging.WARNING)  # Can be noisy
    logging.getLogger("boto3").setLevel(logging.WARNING)  # Can be noisy
    logging.getLogger("s3transfer").setLevel(logging.WARNING)  # Can be noisy
    logging.getLogger("aiobotocore").setLevel(logging.INFO)  # Can be noisy
    logging.getLogger("asyncio").setLevel(logging.INFO)  # Can be noisy

    logger.debug("Logger configuration set!")


def get_logger(name: str) -> CustomLogger:
    """Get a logger with the name provided."""
    return cast("CustomLogger", logging.getLogger(name))


def _has_file_handler(in_logger: logging.Logger) -> bool:
    """Check if logger has a file handler."""
    return any(isinstance(handler, logging.FileHandler) for handler in in_logger.handlers)


def _add_console_handler(
    settings: LoggingConf,
    in_logger: logging.Logger,
) -> None:
    """Add a console handler to the logger."""
    if not force_simple_logger():
        console = Console(theme=Theme({"logging.level.trace": "dim"}))
        rich_handler = RichHandler(
            console=console,
            show_time=False,
            rich_tracebacks=True,
            highlighter=NullHighlighter(),
        )
        in_logger.addHandler(rich_handler)
    else:
        console_handler = StreamHandler()
        if _get_log_level_int(settings.level) <= logging.DEBUG:
            formatter = logging.Formatter(SIMPLE_LOG_FORMAT_DEBUG)
        else:
            formatter = logging.Formatter(SIMPLE_LOG_FORMAT)

        console_handler.setFormatter(formatter)
        in_logger.addHandler(console_handler)


def _get_log_level_int(level: str | int) -> int:
    """Get the log level as an int."""
    if isinstance(level, int):
        return level

    level = level.upper()
    if level == "TRACE":
        return TRACE_LEVEL_NUM
    return getattr(logging, level, logging.INFO)


def _set_log_level(in_logger: logging.Logger, log_level: int | str) -> None:
    """Set the log level of the logger."""
    if isinstance(log_level, str):
        log_level = log_level.upper()
        if log_level not in LOG_LEVELS:
            in_logger.setLevel("INFO")
            logger.warning(
                "❗ Invalid logging level: %s, defaulting to INFO",
                log_level,
            )
        else:
            in_logger.setLevel(log_level)
            logger.debug("Showing log level: INFO and above")
            logger.debug("Showing log level: DEBUG")
            logger.trace("Showing log level: TRACE")
    else:
        in_logger.setLevel(log_level)


def _add_file_handler(in_logger: logging.Logger, log_path: Path | str) -> None:
    """Add a file handler to the logger."""
    if not isinstance(log_path, Path):
        log_path = Path(log_path)

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(log_path, maxBytes=1000000, backupCount=5)
    except IsADirectoryError as exc:
        err = "You are trying to log to a directory, try a file"
        raise IsADirectoryError(err) from exc
    except PermissionError as exc:
        err = f"The user running this does not have access to the file: {log_path}"
        raise PermissionError(err) from exc

    formatter = logging.Formatter(SIMPLE_LOG_FORMAT)
    file_handler.setFormatter(formatter)
    in_logger.addHandler(file_handler)
    logger.info("Logging to file: %s", log_path)


def running_in_serverless_environment() -> bool:
    """Check if the application is running in a serverless environment."""
    return os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None


def force_simple_logger() -> bool:
    """Check if the application is running in a serverless environment."""
    return running_in_serverless_environment() or (os.getenv("AP_SIMPLE_LOGGING", "").lower() in ["1", "true"])
