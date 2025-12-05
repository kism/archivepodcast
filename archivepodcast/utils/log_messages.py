"""Log messages for ArchivePodcast."""

import logging
from datetime import datetime

from aiohttp import ClientError

from archivepodcast.constants import OUR_TIMEZONE
from archivepodcast.version import __version__


def get_time_str() -> str:
    """Get the current time as a formatted string."""
    time = datetime.now(tz=OUR_TIMEZONE)
    return time.strftime("%Y-%m-%d %H:%M:%S %Z")


def log_intro(logger: logging.Logger) -> None:
    """Log introductory information."""
    logger.info("ArchivePodcast version: %s. Current time: %s", __version__, get_time_str())


def log_aiohttp_exception(
    feed: str,
    url: str,
    exception: ClientError,
    logger: logging.Logger,
) -> None:
    """Log an aiohttp exception with details."""
    logger.error("[%s] download error for %s: %s", feed, url, type(exception).__name__)
