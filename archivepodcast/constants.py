"""Constants for the ArchivePodcast application."""

import os
from datetime import UTC, datetime
from pathlib import Path

OUR_TIMEZONE = datetime.now().astimezone().tzinfo or UTC
APP_DIRECTORY = Path(__file__).parent
DEFAULT_INSTANCE_PATH = Path.cwd() / "instance"

AP_SELF_TEST = os.getenv("AP_SELF_TEST", "false").lower() in ("true", "1", "yes")
JSON_INDENT = 2
