"""Time related utils for ArchivePodcast."""

from archivepodcast.utils.logger import get_logger

logger = get_logger(__name__)

_WARN_THRESHOLD = 5


def warn_if_too_long(msg: str, seconds: float, *, large_file: bool = False) -> None:
    """Print a log message if an operation took too long."""
    if seconds >= _WARN_THRESHOLD * (10 if large_file else 1):
        logger.warning("%s took longer than expected: %ss", msg, int(seconds))
