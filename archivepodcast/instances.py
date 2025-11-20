"""Instances for ArchivePodcast application."""

from .ap_constants import SETTINGS_FILE
from .config import ArchivePodcastConfig

ap_conf = ArchivePodcastConfig().force_load_config_file(SETTINGS_FILE)
