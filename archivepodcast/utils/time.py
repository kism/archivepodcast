from datetime import timedelta

from archivepodcast.utils.logger import get_logger

logger = get_logger(__name__)

WARN_THRESHOLD = 5


def warn_if_too_long(msg: str, time_diff: timedelta | float, *, large_file: bool = False) -> None:
    """Prints a log message if the time difference is too long."""
    threshold = WARN_THRESHOLD * (10 if large_file else 1)

    if isinstance(time_diff, float):
        time_diff = timedelta(seconds=time_diff)
    if time_diff > timedelta(seconds=threshold):
        logger.warning("Operation: %s took longer than expected: %ss", msg, int(time_diff.total_seconds()))
