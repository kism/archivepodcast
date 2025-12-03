"""Log messages for ArchivePodcast."""

import logging
from datetime import datetime

from aiohttp import ClientError

from archivepodcast.constants import OUR_TIMEZONE
from archivepodcast.version import __version__


def log_time(logger: logging.Logger) -> None:
    """Log the current time."""
    time = datetime.now(tz=OUR_TIMEZONE)
    time_str_nice = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    logger.info("Current time: %s", time_str_nice)


def log_intro(mode: str, logger: logging.Logger) -> None:
    """Log introductory information."""
    logger.info("ArchivePodcast version: %s, starting in %s mode.", __version__, mode)
    log_time(logger)


def log_aiohttp_exception(
    feed: str,
    url: str,
    exception: ClientError,
    logger: logging.Logger,
) -> None:
    """Log an aiohttp exception with details."""
    logger.error("[%s] download error for %s: %s", feed, url, type(exception).__name__)
