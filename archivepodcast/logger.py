"""Logging configuration for archivepodcast."""

import logging
import typing
from logging.handlers import RotatingFileHandler
from typing import cast

from colorama import Fore, init
from flask import Flask

init(autoreset=True)

COLOURS = {
    "TRACE": Fore.CYAN,
    "DEBUG": Fore.GREEN,
    "INFO": Fore.WHITE,
    "WARNING": Fore.YELLOW,
    "ERROR": Fore.RED,
    "CRITICAL": Fore.RED,
}

DESIRED_LEVEL_NAME_LEN = 5
DESIRED_NAME_LEN = 16
DESIRED_THREAD_NAME_LEN = 13


class ColorFormatter(logging.Formatter):
    """Custom formatter to add colour to the log messages."""

    def _format_value(self, value: typing.Any) -> str:  # noqa: ANN401
        """Format a log message value into a string representation."""
        if isinstance(value, tuple):
            return "  ".join(map(str, value))
        if isinstance(value, list):
            return "  \n".join(map(str, value))
        return str(value) if value is not None else "<NoneType>"

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record."""
        record.msg = self._format_value(record.msg)
        record.name = record.name.replace("archivepodcast", "ap")

        if record.threadName and "Thread-" in record.threadName:
            record.threadName = record.threadName[record.threadName.find("(") + 1 : record.threadName.find(")")]

        if record.name.startswith("ap") and record.levelno <= logging.INFO:
            record.levelname = record.levelname.ljust(DESIRED_LEVEL_NAME_LEN)
            record.name = record.name.ljust(DESIRED_NAME_LEN)
            record.threadName = record.threadName.ljust(DESIRED_THREAD_NAME_LEN) if record.threadName else ""
        elif not record.name.startswith("ap"):
            record.threadName = ""

        if colour := COLOURS.get(record.levelname):
            record.name = f"{colour}{record.name}"
            record.levelname = f"{colour}{record.levelname}"
            record.msg = f"{colour}{record.msg}"

        return super().format(record)


LOG_LEVELS = [
    "TRACE",
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
]  # Valid str logging levels.

# This is the logging message format that I like.
# LOG_FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"   # noqa: ERA001
LOG_FORMAT = "%(levelname)s:%(name)s:%(threadName)s:%(message)s"
TRACE_LEVEL_NUM = 5


class CustomLogger(logging.Logger):
    """Custom logger to appease mypy."""

    def trace(self, message: object, *args: typing.Any, **kws: typing.Any) -> None:  # noqa: ANN401
        """Create logger level for trace."""
        if self.isEnabledFor(TRACE_LEVEL_NUM):
            # Yes, logger takes its '*args' as 'args'.
            self._log(TRACE_LEVEL_NUM, message, args, **kws)


logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")
logging.setLoggerClass(CustomLogger)

# This is where we log to in this module, following the standard of every module.
# I don't use the function so we can have this at the top
logger = cast(CustomLogger, logging.getLogger(__name__))

# In flask the root logger doesn't have any handlers, its all in app.logger
# root_logger : root,
# app.logger  : root, archivepodcast,
# logger      : root, archivepodcast, archivepodcast.module_name,
# The issue is that waitress, werkzeug (any any other modules that log) will log separately.
# The aim is, remove the default handler from the flask App and create one on the root logger to apply config to all.


# Pass in the whole app object to make it obvious we are configuring the logger object within the app object.
def setup_logger(app: Flask, logging_conf: dict, in_logger: logging.Logger | None = None) -> None:
    """Configure logging for the application.

    Args:
        app: The Flask application instance
        logging_conf: Logging configuration dict with "level" and "path" keys
        in_logger: Optional logger instance to configure (mainly for testing)
    """
    if not in_logger:  # in_logger should only exist when testing with PyTest.
        in_logger = logging.getLogger()  # Get the root logger

    # The root logger has no handlers initially in flask, app.logger does though.
    app.logger.handlers.clear()  # Remove the Flask default handlers

    # If the logger doesn't have a console handler (root logger doesn't by default)
    if not _has_console_handler(in_logger):
        _add_console_handler(in_logger)

    _set_log_level(in_logger, logging_conf["level"])

    # If we are logging to a file
    if not _has_file_handler(in_logger) and logging_conf["path"] != "":
        _add_file_handler(in_logger, logging_conf["path"])

    # Configure modules that are external and have their own loggers
    logging.getLogger("waitress").setLevel(logging.INFO)  # Prod web server, info has useful info.
    logging.getLogger("werkzeug").setLevel(logging.DEBUG)  # Only will be used in dev, debug logs incoming requests.
    logging.getLogger("urllib3").setLevel(logging.WARNING)  # Bit noisy when set to info, used by requests module.
    logging.getLogger("botocore").setLevel(logging.WARNING)  # Can be noisy
    logging.getLogger("boto3").setLevel(logging.WARNING)  # Can be noisy
    logging.getLogger("s3transfer").setLevel(logging.WARNING)  # Can be noisy

    logger.info("Logger configuration set!")


def get_logger(name: str) -> CustomLogger:
    """Get a logger with the name provided."""
    return cast(CustomLogger, logging.getLogger(name))


def _has_file_handler(in_logger: logging.Logger) -> bool:
    """Check if logger has a file handler."""
    return any(isinstance(handler, logging.FileHandler) for handler in in_logger.handlers)


def _has_console_handler(in_logger: logging.Logger) -> bool:
    """Check if logger has a console handler."""
    return any(isinstance(handler, logging.StreamHandler) for handler in in_logger.handlers)


def _add_console_handler(in_logger: logging.Logger) -> None:
    """Add a console handler to the logger."""
    formatter = ColorFormatter(LOG_FORMAT)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    in_logger.addHandler(console_handler)


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
            logger.info("Showing log level: INFO and above")
            logger.debug("Showing log level: DEBUG")
            logger.trace("Showing log level: TRACE")
    else:
        in_logger.setLevel(log_level)


def _add_file_handler(in_logger: logging.Logger, log_path: str) -> None:
    """Add a file handler to the logger."""
    try:
        file_handler = RotatingFileHandler(log_path, maxBytes=1000000, backupCount=5)
    except IsADirectoryError as exc:
        err = "You are trying to log to a directory, try a file"
        raise IsADirectoryError(err) from exc
    except PermissionError as exc:
        err = "The user running this does not have access to the file: " + log_path
        raise PermissionError(err) from exc

    formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(formatter)
    in_logger.addHandler(file_handler)
    logger.info("Logging to file: %s", log_path)
