"""Constants for the ArchivePodcast application."""

from datetime import UTC, datetime
from pathlib import Path

OUR_TIMEZONE = datetime.now().astimezone().tzinfo or UTC
APP_DIRECTORY = Path(__file__).parent
DEFAULT_INSTANCE_PATH = Path.cwd() / "instance"
