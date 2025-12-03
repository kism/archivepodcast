"""Constants for the ArchivePodcast application."""

from datetime import UTC, datetime

OUR_TIMEZONE = datetime.now().astimezone().tzinfo or UTC
