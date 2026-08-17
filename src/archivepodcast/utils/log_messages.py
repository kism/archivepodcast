"""Log messages for ArchivePodcast."""

from datetime import datetime
from typing import TYPE_CHECKING

from archivepodcast.constants import OUR_TIMEZONE, PROGRAM_NAME_WITH_FULL_VERSION

if TYPE_CHECKING:
    import logging

    from aiohttp import ClientError


def get_time_str() -> str:
    """Get the current time as a formatted string."""
    time = datetime.now(tz=OUR_TIMEZONE)
    return time.strftime("%Y-%m-%d %H:%M:%S %Z")


def log_intro(logger: logging.Logger) -> None:
    """Log introductory information."""
    logger.info("%s. Current time: %s", PROGRAM_NAME_WITH_FULL_VERSION, get_time_str())


def log_aiohttp_exception(
    feed: str,
    url: str,
    exception: ClientError,
    logger: logging.Logger,
) -> None:
    """Log an aiohttp exception with details."""
    logger.error("[%s] download error for %s: %s", feed, url, type(exception).__name__)
